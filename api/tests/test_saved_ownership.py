from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.main import app
from app.routers import internal

USER_A = UUID('11111111-1111-4111-8111-111111111111')
USER_B = UUID('22222222-2222-4222-8222-222222222222')
SESSION = 'anonymous-browser-session'


@pytest.mark.parametrize('operation', ['status', 'save', 'unsave', 'list'])
def test_internal_owner_is_trusted_header_not_body(monkeypatch, operation):
    captured = []

    async def fake(owner, *args):
        captured.append(owner)
        return []

    monkeypatch.setattr(settings, 'db_feedback_url', 'postgresql://stub')
    for name in ['saved_results_status', 'save_result_records', 'remove_saved_result_records', 'list_saved_result_records']:
        monkeypatch.setattr(internal, name, fake)
    client = TestClient(app)
    payload = {'session_id': SESSION, 'user_id': str(USER_B), 'stable_row_keys': ['experiment:1'],
               'records': [{'record_id': 1, 'stable_row_key': 'experiment:1'}]}
    method, url = {'status': ('POST', '/saved-results/status'), 'save': ('POST', '/saved-results'),
                   'unsave': ('DELETE', '/saved-results'), 'list': ('GET', '/saved-results')}[operation]
    headers = {'Authorization': f'Bearer {settings.internal_api_key}'}
    kwargs = {'params': {'session_id': SESSION, 'user_id': str(USER_B)}} if method == 'GET' else {'json': payload}
    assert client.request(method, url, headers=headers, **kwargs).status_code == 200
    assert captured.pop() == SESSION
    headers['X-Hive-User-Id'] = str(USER_A)
    assert client.request(method, url, headers=headers, **kwargs).status_code == 200
    assert captured.pop() == USER_A
    headers.pop('Authorization')
    assert client.request(method, url, headers=headers, **kwargs).status_code == 401
    assert captured == []


def test_account_needs_no_browser_session_and_invalid_owner_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, 'db_feedback_url', 'postgresql://stub')

    async def fake(owner):
        assert owner == USER_A
        return []

    monkeypatch.setattr(internal, 'list_saved_result_records', fake)
    client = TestClient(app)
    headers = {'Authorization': f'Bearer {settings.internal_api_key}', 'X-Hive-User-Id': str(USER_A)}
    assert client.get('/saved-results', headers=headers).status_code == 200
    headers['X-Hive-User-Id'] = 'not-a-uuid'
    assert client.get('/saved-results', headers=headers).status_code == 422
    headers.pop('X-Hive-User-Id')
    assert client.get('/saved-results', headers=headers).status_code == 400


@pytest.mark.anyio
async def test_rest_six_lane_lifecycle_isolates_accounts_and_anonymous(monkeypatch):
    monkeypatch.setattr(settings, 'supabase_url', 'https://example.supabase.co')
    monkeypatch.setattr(settings, 'supabase_api_key', 'test-server-key')
    monkeypatch.setattr(settings, 'db_feedback_url', '')
    evidence = [{'id': i, 'stable_row_key': f'experiment:{i}'} for i in range(1, 7)]
    snapshot = [dict(r) for r in evidence]
    saved = []

    def matches(row, params):
        for key, value in params:
            if key in ('select', 'order'):
                continue
            if value == 'is.null' and row.get(key) is not None:
                return False
            if value.startswith('eq.') and str(row.get(key)) != value[3:]:
                return False
            if value.startswith('in.') and str(row.get(key)) not in [v.strip('"') for v in value[4:-1].split(',')]:
                return False
        return True

    def get(table, params):
        assert table in ('saved_results', settings.table_name)
        return [dict(r) for r in (saved if table == 'saved_results' else evidence) if matches(r, params)]

    def write(method, table, params, payload=None):
        assert table == 'saved_results', 'Scientific evidence must never be written'
        if method == 'POST':
            for row in payload:
                assert ('user_id' in row) != ('session_id' in row)
                saved.append({**row, 'saved_at': '2026-10-02T00:00:00Z'})
        elif method == 'DELETE':
            saved[:] = [r for r in saved if not matches(r, params)]
        else:
            pytest.fail('Unexpected mutation')
        return []

    monkeypatch.setattr(db, '_supabase_get', get)
    monkeypatch.setattr(db, '_supabase_write', write)
    records = [{'record_id': r['id'], 'stable_row_key': r['stable_row_key']} for r in evidence]
    keys = [r['stable_row_key'] for r in records]
    for owner in [SESSION, USER_A, USER_B]:
        assert await db.saved_results_status(owner, keys) == set()
        await db.save_result_records(owner, records)
        await db.save_result_records(owner, records)
        assert await db.saved_results_status(owner, keys) == set(keys)
        assert len(await db.list_saved_result_records(owner)) == 6
    assert len(saved) == 18
    # A fresh UUID object represents the same account on a different device.
    assert len(await db.list_saved_result_records(UUID(str(USER_A)))) == 6
    assert await db.list_saved_result_records('another-browser') == []
    # Old rows with both owners must never be visible/removable anonymously.
    saved.append({'session_id': SESSION, 'user_id': str(USER_A), 'record_id': 99,
                  'stable_row_key': 'legacy:1', 'saved_at': '2026-10-02T00:00:00Z'})
    assert await db.saved_results_status(SESSION, ['legacy:1']) == set()
    await db.remove_saved_result_records(SESSION, keys + ['legacy:1'])
    assert len(saved) == 13
    await db.remove_saved_result_records(USER_A, keys)
    assert await db.saved_results_status(USER_B, keys) == set(keys)
    assert await db.saved_results_status(USER_A, keys) == set()
    assert saved[-1]['stable_row_key'] == 'legacy:1'
    assert evidence == snapshot


def test_sql_scope_never_infers_account_from_anonymous_uuid_string():
    column, predicate, _ = db._saved_owner_scope(str(USER_A))
    assert column == 'session_id'
    assert 'user_id IS NULL' in predicate
    column, predicate, _ = db._saved_owner_scope(USER_A)
    assert column == 'user_id' and predicate == 'user_id = $1'


@pytest.mark.anyio
@pytest.mark.parametrize('owner', [SESSION, USER_A])
async def test_direct_postgres_scopes_every_operation(monkeypatch, owner):
    monkeypatch.setattr(settings, 'supabase_url', '')
    calls = []

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def transaction(self):
            return self

        async def fetch(self, sql, *args):
            calls.append((sql, args))
            if 'FROM western_blot_records' in sql:
                return [{'id': 1, 'stable_row_key': 'experiment:1'}]
            return []

        async def execute(self, sql, *args):
            calls.append((sql, args))
            return 'DELETE 1'

    class Pool:
        def acquire(self):
            return Connection()

    async def pool():
        return Pool()

    monkeypatch.setattr(db, 'get_feedback_pool', pool)
    monkeypatch.setattr(db, 'get_readonly_pool', pool)
    await db.saved_results_status(owner, ['experiment:1'])
    await db.save_result_records(owner, [{'record_id': 1, 'stable_row_key': 'experiment:1'}])
    await db.list_saved_result_records(owner)
    await db.remove_saved_result_records(owner, ['experiment:1'])
    column, predicate, _ = db._saved_owner_scope(owner)
    saved_calls = [(sql, args) for sql, args in calls if 'saved_results' in sql]
    assert len(saved_calls) == 4
    for sql, args in saved_calls:
        assert args[0] == owner
        if sql.startswith('INSERT'):
            assert f'({column}, record_id, stable_row_key)' in sql
        else:
            assert f'WHERE {predicate}' in sql
    assert all(sql.startswith('SELECT') or 'saved_results' in sql for sql, _ in calls)

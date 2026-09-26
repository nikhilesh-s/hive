import datetime

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.limiter import limiter
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def _row(history_id=4, query="STAT3", filters=None):
    now = datetime.datetime(2026, 9, 25, 20, 42, tzinfo=datetime.timezone.utc)
    return {
        "id": history_id,
        "query": query,
        "filters": filters or {},
        "created_at": now,
        "last_searched_at": now,
    }


def test_history_requires_auth(client):
    assert client.get("/history", params={"session_id": "abc"}).status_code in (401, 403)
    assert client.post("/history", json={"session_id": "abc", "query": "STAT3"}).status_code in (401, 403)


def test_history_post_normalizes_whitespace(client, monkeypatch):
    captured = {}

    async def fake_upsert(session_id, query, normalized_query, filters):
        captured.update(session_id=session_id, query=query,
                       normalized_query=normalized_query, filters=filters)
        return _row(query=query, filters=filters)

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "upsert_search_history", fake_upsert)

    response = client.post(
        "/history",
        headers=AUTH,
        json={"session_id": "browser-a", "query": "  phospho   STAT3 Tyr705  ",
              "filters": {"protein": "STAT3"}},
    )
    assert response.status_code == 200
    assert captured == {
        "session_id": "browser-a",
        "query": "phospho   STAT3 Tyr705",
        "normalized_query": "phospho STAT3 Tyr705",
        "filters": {"protein": "STAT3"},
    }


def test_history_list_is_session_scoped(client, monkeypatch):
    captured = {}

    async def fake_list(session_id, limit):
        captured.update(session_id=session_id, limit=limit)
        return [_row()]

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "list_search_history", fake_list)
    response = client.get("/history", headers=AUTH,
                          params={"session_id": "browser-a", "limit": 12})
    assert response.status_code == 200
    assert captured == {"session_id": "browser-a", "limit": 12}
    assert response.json()["items"][0]["query"] == "STAT3"


def test_history_delete_and_clear_pass_session_key(client, monkeypatch):
    deleted = {}
    cleared = {}

    async def fake_delete(session_id, history_id):
        deleted.update(session_id=session_id, history_id=history_id)
        return True

    async def fake_clear(session_id):
        cleared["session_id"] = session_id
        return 3

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "delete_search_history", fake_delete)
    monkeypatch.setattr(internal, "clear_search_history", fake_clear)
    assert client.delete("/history/9", headers=AUTH,
                         params={"session_id": "browser-a"}).json() == {"deleted": True}
    assert client.delete("/history", headers=AUTH,
                         params={"session_id": "browser-a"}).json() == {"deleted": 3}
    assert deleted == {"session_id": "browser-a", "history_id": 9}
    assert cleared == {"session_id": "browser-a"}


def test_history_rejects_server_side_session(client):
    response = client.get("/history", headers=AUTH, params={"session_id": "ssr"})
    assert response.status_code == 400
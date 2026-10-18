import asyncio

import pytest
from fastapi.testclient import TestClient

from app import corpus_stats as stats
from app.config import settings
from app.main import app


def test_totals_follow_records_not_constants():
    rows = [{"id": 1, "doi": "10.1000/A", "stable_row_key": "a:1"},
            {"id": 2, "doi": "10.1000/a", "stable_row_key": "a:2"},
            {"id": 3, "doi": "10.1000/b", "stable_row_key": "b:1"}]
    assert stats.count_rows(rows).model_dump() == {"reviewed_papers": 2, "experiment_groups": 2, "evidence_rows": 3}
    rows.append({"id": 4, "doi": "10.1000/c", "stable_row_key": "c:1"})
    assert stats.count_rows(rows).model_dump() == {"reviewed_papers": 3, "experiment_groups": 3, "evidence_rows": 4}
    assert stats.count_rows([]).evidence_rows == 0


def test_rest_pagination_reads_short_pages_until_empty(monkeypatch):
    monkeypatch.setattr(stats, "_use_supabase_rest", lambda: True)
    seen = []
    def fetch(table, params):
        assert table == "western_blot_records"
        last = dict(params).get("id")
        seen.append(last)
        return [{"id": 1}, {"id": 2}] if last is None else [{"id": 3}] if last == "gt.2" else []
    monkeypatch.setattr(stats, "_supabase_get", fetch)
    assert len(asyncio.run(stats._load_rows())) == 3
    assert seen == [None, "gt.2", "gt.3"]


def test_rest_repeated_page_fails_instead_of_counting_duplicates(monkeypatch):
    monkeypatch.setattr(stats, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(stats, "_supabase_get", lambda *args: [{"id": 1}])
    with pytest.raises(RuntimeError, match="advance"):
        asyncio.run(stats._load_rows())


def test_cache_expires_and_recounts(monkeypatch):
    monkeypatch.setattr(stats, "_cached", None)
    monkeypatch.setattr(stats, "_lock", asyncio.Lock())
    now = [0.0]
    monkeypatch.setattr(stats.time, "monotonic", lambda: now[0])
    calls = []
    async def load():
        calls.append(True)
        return [{"id": n, "doi": f"10.1000/{n}", "stable_row_key": f"{n}:1"} for n in range(len(calls))]
    monkeypatch.setattr(stats, "_load_rows", load)
    async def exercise():
        assert (await stats.get_corpus_stats()).evidence_rows == 1
        assert (await stats.get_corpus_stats()).evidence_rows == 1
        now[0] = stats.CACHE_SECONDS + 1
        assert (await stats.get_corpus_stats()).evidence_rows == 2
    asyncio.run(exercise())
    assert len(calls) == 2


def test_stats_endpoint_requires_key_and_returns_failure_not_fake_counts(monkeypatch):
    from app.routers import internal
    async def broken():
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(internal, "get_corpus_stats", broken)
    with TestClient(app) as client:
        assert client.get('/corpus-stats').status_code == 401
        result = client.get('/corpus-stats', headers={"Authorization": f"Bearer {settings.internal_api_key}"})
        assert result.status_code == 503
        assert "reviewed_papers" not in result.json()

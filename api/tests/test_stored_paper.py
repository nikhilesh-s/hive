"""Read-only DOI retrieval: auth, exact matching, completed runs and no model work."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.experimental import ingest, router
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}


@pytest.fixture
def client(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("DOI lookup must not start extraction, inference, or spend quota")
    monkeypatch.setattr(ingest, "start_job", forbidden)
    monkeypatch.setattr(ingest, "run_job", forbidden)
    monkeypatch.setattr(router, "_spend_daily", forbidden)
    with TestClient(app) as client:
        yield client


def test_lookup_requires_server_key_before_reading(client, monkeypatch):
    async def forbidden(doi):
        pytest.fail("Unauthorized requests must not reach the database")
    monkeypatch.setattr(router, "lookup_live_paper", forbidden)
    for headers in ({}, {"Authorization": "Bearer wrong"},
                    {"Authorization": f"Bearer {settings.agent_api_keys_set.copy().pop()}"}):
        assert client.get("/experimental/live/paper", params={"doi": "10.1000/a"}, headers=headers).status_code == 401


@pytest.mark.parametrize("doi", ["10.1000/ABC", " https://doi.org/10.1000/ABC ",
                                 "doi:10.1000/ABC", "http://dx.doi.org/10.1000/ABC",
                                 "10.1000/ABC).", "see https://doi.org/10.1000/ABC;"])
def test_lookup_normalizes_and_refresh_is_readonly(client, monkeypatch, doi):
    seen = []

    async def lookup(value):
        seen.append(value)
        return {"status": "found", "doi": value, "paper": {
            "doi": value, "title": "Stored paper", "rows": 1, "experiments": 1,
            "discovery_query": "original STAT3 query"}, "results": [{
                "id": 1, "paper_id": value, "doi": value, "target": "STAT3",
                "image_crop_ref": "/private/internal/crop.png", "provenance": {"internal": True}}]}
    monkeypatch.setattr(router, "lookup_live_paper", lookup)
    for _ in range(2):
        response = client.get("/experimental/live/paper", params={"doi": doi, "lab": "not-auth"}, headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["paper"]["discovery_query"] == "original STAT3 query"
        assert data["results"][0]["image_crop_ref"] == "crop.png"
        assert "provenance" not in data["results"][0]
    assert seen == ["10.1000/abc"] * 2


@pytest.mark.parametrize("status", ["not_extracted", "pending"])
def test_missing_and_pending_are_not_extracted(client, monkeypatch, status):
    async def lookup(doi):
        return {"doi": doi, "status": status, "paper": None, "results": []}
    monkeypatch.setattr(router, "lookup_live_paper", lookup)
    response = client.get("/experimental/live/paper", params={"doi": "10.1000/none"}, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["results"] == []


@pytest.mark.parametrize("doi", ["garbage", "10.1/a", "10.5 mM STAT3", "10.1000/" + "a" * 200])
def test_invalid_doi(client, doi):
    assert client.get("/experimental/live/paper", params={"doi": doi}, headers=AUTH).status_code == 422


def test_database_failure_is_not_reported_as_missing(client, monkeypatch):
    async def broken(doi):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(router, "lookup_live_paper", broken)
    response = client.get("/experimental/live/paper", params={"doi": "10.1000/a"}, headers=AUTH)
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def _pool(monkeypatch, rows, job):
    class Conn:
        async def fetch(self, sql, doi):
            assert "LEFT JOIN ingest_jobs" in sql and "j.status" not in sql
            assert "lower(r.doi) = $1" in sql  # row DOIs keep the extractor's case
            assert "LIMIT" not in sql and "ILIKE" not in sql
            assert doi == "10.1000/a"
            return rows

        async def fetchrow(self, sql, doi):
            assert "lower(doi) = $1" in sql and "interval '30 minutes'" in sql and doi == "10.1000/a"
            return job

    class Acquire:
        async def __aenter__(self): return Conn()
        async def __aexit__(self, *args): pass

    class Pool:
        def acquire(self): return Acquire()

    async def pool(): return Pool()
    monkeypatch.setattr(db, "get_readonly_pool", pool)


@pytest.mark.parametrize("job_status,fresh,expected", [
    ("extracting", True, "pending"), ("loading", True, "pending"),
    ("extracting", False, "not_extracted"),  # a restart left the job stuck
    ("failed", True, "not_extracted"), ("done", True, "not_extracted"),
    ("awaiting_full_text", True, "not_extracted"), (None, None, "not_extracted")])
def test_database_lookup_uses_bound_exact_doi_and_complete_rows(monkeypatch, job_status, fresh, expected):
    _pool(monkeypatch, [], {"status": job_status, "fresh": fresh} if job_status else None)
    result = asyncio.run(db.lookup_live_paper("10.1000/a"))
    assert result["status"] == expected and not result["results"]


def test_live_rows_are_found_without_a_done_job_row(monkeypatch):
    rows = [{"id": 2, "doi": "10.1000/A", "title": "Row title", "stable_row_key": "k1:a",
             "job_id": "j1", "original_query": None, "stored_title": None},
            {"id": 3, "doi": "10.1000/A", "title": None, "stable_row_key": "k1:b",
             "job_id": "j1", "original_query": None, "stored_title": None}]
    _pool(monkeypatch, rows, None)  # no ingest_jobs row at all
    result = asyncio.run(db.lookup_live_paper("10.1000/a"))
    assert result["status"] == "found"
    assert result["paper"]["title"] == "Row title" and result["paper"]["discovery_query"] is None
    assert result["paper"]["rows"] == 2 and result["paper"]["experiments"] == 1
    assert all("original_query" not in r and "stored_title" not in r for r in result["results"])

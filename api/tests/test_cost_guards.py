"""Cost and exposure guards: per-researcher rate-limit keys behind the web
proxy, the daily ceiling on paid model work, and no public API schema."""
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import settings
from app.experimental import ingest, router as exp_router
from app.limiter import client_key
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}


def _req(headers: dict[str, str]) -> Request:
    return Request({"type": "http", "client": ("10.0.0.1", 1), "headers":
                    [(k.lower().encode(), v.encode()) for k, v in headers.items()]})


def test_forwarded_client_ip_is_trusted_only_from_the_web_proxy():
    assert client_key(_req({**AUTH, "X-Hive-Client-IP": "203.0.113.7"})) == "203.0.113.7"
    assert client_key(_req({"X-Hive-Client-IP": "203.0.113.7"})) == "10.0.0.1"
    assert client_key(_req({"Authorization": "Bearer wrong", "X-Hive-Client-IP": "203.0.113.7"})) == "10.0.0.1"
    assert client_key(_req(AUTH)) == "10.0.0.1"


def test_daily_question_cap_returns_429(monkeypatch):
    async def fake_answer(*_a, **_k):
        return {"answer": "ok"}
    monkeypatch.setattr(exp_router, "ask_answer", fake_answer)
    monkeypatch.setattr(settings, "daily_ask_cap", 2)
    exp_router._spent.clear()
    with TestClient(app) as c:
        codes = [c.post("/experimental/ask", json={"question": "what antibody for STAT3?"},
                        headers={**AUTH, "X-Hive-Client-IP": "198.51.100.1"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_daily_extraction_cap_skips_reused_runs(monkeypatch):
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, ""))
    monkeypatch.setattr(ingest, "start_job", lambda doi, reuse=False: SimpleNamespace(
        job_id="j", to_dict=lambda: {"job_id": "j", "reuse": reuse}))
    monkeypatch.setattr(ingest, "run_job", lambda job_id: None)
    monkeypatch.setattr(settings, "daily_ingest_cap", 1)
    exp_router._spent.clear()
    hdr = {**AUTH, "X-Hive-Client-IP": "198.51.100.2"}
    with TestClient(app) as c:
        assert c.post("/experimental/ingest", json={"doi": "10.1000/a"}, headers=hdr).status_code == 200
        assert c.post("/experimental/ingest", json={"doi": "10.1000/b"}, headers=hdr).status_code == 429


def test_api_schema_and_docs_are_not_public():
    with TestClient(app) as c:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(path).status_code == 404, path


def test_extractions_run_one_at_a_time(monkeypatch):
    """Two concurrent extractions starved Render's health check and both died."""
    import asyncio
    import threading
    import time

    active, peak, lock = [0], [0], threading.Lock()

    def slow_fetch(doi, out_dir):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.2)
        with lock:
            active[0] -= 1
        return {"pdf_path": None}

    monkeypatch.setattr(settings, "db_ingest_url", "")
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "stub"))
    monkeypatch.setattr(ingest.fulltext, "fetch_pdf", slow_fetch)
    a, b = ingest.start_job("10.1000/a"), ingest.start_job("10.1000/b")

    async def both():
        await asyncio.gather(ingest.run_job(a.job_id), ingest.run_job(b.job_id))
    asyncio.run(both())
    assert peak[0] == 1 and a.status == b.status == "failed"


def test_job_orphaned_by_a_restart_reads_as_failed(monkeypatch):
    async def stored(limit=20):
        return [{"job_id": "zombie1", "status": "preprocessing", "error": None, "created_at": "2026-09-27"},
                {"job_id": "old1", "status": "done", "error": None, "created_at": "2026-09-26"}]
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://hive_ingest:x@localhost/x")
    monkeypatch.setattr(exp_router, "list_ingest_jobs", stored)
    with TestClient(app) as c:
        z = c.get("/experimental/ingest/zombie1", headers=AUTH).json()
        assert z["status"] == "failed" and "restart" in z["error"]
        assert c.get("/experimental/ingest/old1", headers=AUTH).json()["status"] == "done"
        listed = {j["job_id"]: j["status"] for j in c.get("/experimental/ingest", headers=AUTH).json()["jobs"]}
        assert listed["zombie1"] == "failed" and listed["old1"] == "done"

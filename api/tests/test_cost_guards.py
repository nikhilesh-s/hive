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

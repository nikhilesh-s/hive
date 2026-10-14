"""Upload boundary tests; model and database are stubbed, never production."""
import asyncio
import base64
import json
import time
from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.experimental import ingest, router, uploads
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}", "X-Hive-User-Id": str(uuid4())}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://isolated-test")
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "JOBS", {})
    monkeypatch.setattr(router, "_spent", {})
    monkeypatch.setattr(uploads, "_lock", asyncio.Lock())
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "mock test only"))
    async def missing(doi):
        return {"status": "not_extracted", "paper": None}
    async def latest(doi):
        return None
    async def persist(job):
        pass
    async def run(job_id, path):
        assert path.is_file()
        assert ingest.JOBS[job_id].metadata_source == "upload"
        assert ingest.JOBS[job_id].access_status is None
        ingest.JOBS[job_id].status = "done"
        path.unlink()
    monkeypatch.setattr(db, "lookup_live_paper", missing)
    monkeypatch.setattr(db, "latest_ingest_job", latest)
    monkeypatch.setattr(db, "upsert_ingest_job", persist)
    monkeypatch.setattr(ingest, "run_job", run)
    with TestClient(app) as c:
        yield c


def pdf():
    with fitz.open() as document:
        document.new_page().insert_text((30, 30), "Upload validation fixture; not scientific evidence")
        return document.tobytes()


def ticket(client, doi="10.1000/upload"):
    response = client.post("/experimental/upload-ticket", json={"doi": doi}, headers=AUTH)
    assert response.status_code == 200, response.text
    return response.json()["token"]


def headers(token):
    return {"Authorization": "Bearer " + token, "Content-Type": "application/pdf", "X-Pdf-Rights": "confirmed"}


def test_ticket_requires_internal_key_and_verified_user(client):
    for h in ({}, {"X-Hive-User-Id": AUTH["X-Hive-User-Id"]},
              {"Authorization": AUTH["Authorization"]}, {**AUTH, "X-Hive-User-Id": "forged"}):
        assert client.post("/experimental/upload-ticket", json={"doi": "10.1000/upload"}, headers=h).status_code == 401


@pytest.mark.parametrize("doi", ["hello", "10.1/no", "10.1000/has space", "10.1000/a?query", "10.1000/" + "a" * 200])
def test_invalid_doi(client, doi):
    assert client.post("/experimental/upload-ticket", json={"doi": doi}, headers=AUTH).status_code == 422


def test_explicit_upload_normalizes_persists_and_spends_once(client):
    token = ticket(client, "https://doi.org/10.1000/UPLOAD")
    assert not ingest.JOBS and not router._spent
    response = client.post("/experimental/uploads", headers=headers(token), content=pdf())
    assert response.status_code == 200, response.text
    assert response.json()["doi"] == "10.1000/upload"
    assert response.json()["metadata_source"] == "upload"
    assert len(ingest.JOBS) == 1
    assert router._spent["extraction"][1] == 1


@pytest.mark.parametrize("token", ["", "wrong", "abc.wrong"])
def test_invalid_upload_authorization(client, token):
    assert client.post("/experimental/uploads", headers=headers(token), content=pdf()).status_code == 401
    assert not ingest.JOBS and not router._spent


def test_expired_ticket(client):
    payload = base64.urlsafe_b64encode(json.dumps({"doi": "10.1000/a", "user": AUTH["X-Hive-User-Id"], "expires": time.time()-1}).encode()).decode()
    assert client.post("/experimental/uploads", headers=headers(payload + "." + uploads._signature(payload)), content=pdf()).status_code == 401


@pytest.mark.parametrize("body,extra,code", [(b"not pdf", {}, 400), (b"", {}, 400),
    (b"x", {"Content-Type": "image/png"}, 415), (b"x", {"X-Pdf-Rights": "no"}, 422),
    (b"x", {"Content-Length": str(uploads.MAX_PDF_BYTES + 1)}, 413)])
def test_validation_without_job_or_quota(client, body, extra, code):
    response = client.post("/experimental/uploads", headers={**headers(ticket(client)), **extra}, content=body)
    assert response.status_code == code, response.text
    assert not ingest.JOBS and not router._spent
    assert not list(ingest.PDF_DIR.rglob("*.pdf"))


def test_stream_size_limit_without_content_length(client, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_PDF_BYTES", 10)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=iter([b"123456", b"789012"]))
    assert response.status_code == 413
    assert not ingest.JOBS and not router._spent


@pytest.mark.parametrize("state", ["completed", "pending", "zero"])
def test_existing_doi_never_spends_or_runs(client, monkeypatch, state):
    async def lookup(doi):
        return {"status": "found" if state == "completed" else "pending", "paper": {"rows": 10}}
    async def latest(doi):
        return {"job_id": "existing", "status": "done" if state == "zero" else "extracting"}
    monkeypatch.setattr(db, "lookup_live_paper", lookup)
    monkeypatch.setattr(db, "latest_ingest_job", latest)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 200
    assert response.json()["existing"] is True
    assert not ingest.JOBS and not router._spent


def test_missing_model_fails_honestly(client, monkeypatch):
    monkeypatch.setattr(ingest, "backend_ready", lambda: (False, "No extraction model configured"))
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 503
    assert "No extraction model" in response.json()["detail"]
    assert not ingest.JOBS and not router._spent


def test_cors_supports_authorized_direct_upload(client):
    response = client.options("/experimental/uploads", headers={"Origin": settings.allowed_origins_list[0],
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type,x-pdf-rights"})
    assert response.status_code == 200


def test_encrypted_pdf_is_rejected(client):
    with fitz.open() as document:
        document.new_page()
        content = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="fixture", user_pw="fixture")
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=content)
    assert response.status_code == 400
    assert not ingest.JOBS and not router._spent


def test_quota_stops_upload_without_creating_job(client, monkeypatch):
    monkeypatch.setattr(settings, "daily_ingest_cap", 0)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 429
    assert not ingest.JOBS
    assert not list(ingest.PDF_DIR.rglob("*.pdf"))


def test_legacy_direct_upload_disabled(client, monkeypatch):
    monkeypatch.setenv("WBM_UPLOAD", "true")
    response = client.post("/experimental/upload-ticket", json={"doi": "10.1000/a"}, headers=AUTH)
    assert response.status_code == 503
    assert not ingest.JOBS and not router._spent


def test_pending_upload_is_reused_and_spends_only_once(client, monkeypatch):
    async def keep_pending(job_id, path):
        path.unlink()
    monkeypatch.setattr(ingest, "run_job", keep_pending)
    token = ticket(client)
    first = client.post("/experimental/uploads", headers=headers(token), content=pdf())
    second = client.post("/experimental/uploads", headers=headers(token), content=pdf())
    assert first.json()["job_id"] == second.json()["job_id"]
    assert second.json()["existing"] is True
    assert len(ingest.JOBS) == 1 and router._spent["extraction"][1] == 1


def test_job_storage_failure_returns_error_and_refunds_quota(client, monkeypatch):
    async def fail(*args):
        raise RuntimeError("test outage")
    monkeypatch.setattr(db, "upsert_ingest_job", fail)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 503 and not ingest.JOBS
    assert router._spent["extraction"][1] == 0
    assert not list(ingest.PDF_DIR.rglob("*.pdf"))


def test_database_lookup_failure_is_not_a_missing_paper(client, monkeypatch):
    async def fail(*args):
        raise RuntimeError("test outage")
    monkeypatch.setattr(db, "lookup_live_paper", fail)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 503 and not ingest.JOBS and not router._spent


def test_upload_pipeline_does_not_download_or_invent_access(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest, "JOBS", {})
    monkeypatch.setattr(ingest, "_SLOTS", asyncio.Semaphore(1))
    job = ingest.start_job("10.1000/pipeline", metadata={"source": "upload"})
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf())
    (tmp_path / "rows.json").write_text("[]")
    def forbidden(*args, **kwargs):
        pytest.fail("Supplied PDF must not trigger remote full-text discovery/download")
    for name in ("paper_metadata", "check_access", "fetch_pdf"):
        monkeypatch.setattr(ingest.fulltext, name, forbidden)
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "mock test"))
    monkeypatch.setattr(ingest.pdf_preprocess, "preprocess_pdf", lambda *a, **k: {"out_dir": str(tmp_path), "paper_id": job.doi, "llm_candidate_count": 0})
    monkeypatch.setattr(ingest.pipeline, "run_records_stage", lambda *a, **k: {"rows_path": str(tmp_path / "rows.json"), "records": 0, "failures": 0})
    async def persist(*args):
        pass
    async def load(job, rows, directory):
        assert rows == []
    monkeypatch.setattr(db, "upsert_ingest_job", persist)
    monkeypatch.setattr(ingest, "load_rows", load)
    asyncio.run(ingest.run_job(job.job_id, path))
    assert job.status == "done" and job.rows == 0
    assert job.access_status is None and job.access_url is None
    assert json.loads((tmp_path / "upload_metadata.json").read_text())["source"] == "upload"
    assert not path.exists()


@pytest.mark.parametrize("mismatch", [True, False])
def test_mismatch_or_failed_panels_never_store_partial_evidence(monkeypatch, tmp_path, mismatch):
    monkeypatch.setattr(ingest, "JOBS", {})
    monkeypatch.setattr(ingest, "_SLOTS", asyncio.Semaphore(1))
    job = ingest.start_job("10.1000/expected", metadata={"source": "upload"})
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf())
    async def persist(*args):
        pass
    async def forbidden(*args):
        pytest.fail("Failed upload must not store partial results")
    monkeypatch.setattr(db, "upsert_ingest_job", persist)
    monkeypatch.setattr(ingest, "load_rows", forbidden)
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "mock test"))
    monkeypatch.setattr(ingest.pdf_preprocess, "preprocess_pdf", lambda *a, **k: {"out_dir": str(tmp_path), "paper_id": job.doi, "extracted_doi": "10.1000/other" if mismatch else None})
    monkeypatch.setattr(ingest.pipeline, "run_records_stage", lambda *a, **k: {"failures": 1})
    asyncio.run(ingest.run_job(job.job_id, path))
    assert job.status == "failed"
    assert not path.exists()

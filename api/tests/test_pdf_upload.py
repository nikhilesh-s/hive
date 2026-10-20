"""Upload boundary tests; model and database are stubbed, never production."""
import asyncio
import base64
import hashlib
import json
import sys
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import fitz
import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.experimental import ingest, router, uploads
from app.limiter import limiter
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}", "X-Hive-User-Id": str(uuid4())}


@pytest.fixture
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.delenv("WBM_UPLOAD", raising=False)
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://isolated-test")
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "JOBS", {})
    monkeypatch.setattr(router, "_spent", {})
    monkeypatch.setattr(uploads, "_lock", asyncio.Lock())
    monkeypatch.setattr(uploads, "_UPLOAD_SLOTS", asyncio.Semaphore(2))
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "mock test only"))
    stored = []
    async def missing(doi):
        return {"status": "not_extracted", "paper": None}
    async def latest(doi):
        return None
    async def persist(job):
        stored.append(job)
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
        c.stored = stored
        yield c
    limiter.reset()


def pdf(text="Upload validation fixture; not scientific evidence. https://doi.org/10.1000/upload",
        pages=1, size=(612, 792), metadata=None):
    with fitz.open() as document:
        for _ in range(pages):
            document.new_page(width=size[0], height=size[1]).insert_text((30, 30), text)
        if metadata:
            document.set_metadata(metadata)
        return document.tobytes()


def ticket(client, doi="10.1000/upload", user=None):
    response = client.post("/experimental/upload-ticket", json={"doi": doi},
                           headers={**AUTH, "X-Hive-User-Id": user or AUTH["X-Hive-User-Id"]})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def headers(token):
    return {"Authorization": "Bearer " + token, "Content-Type": "application/pdf", "X-Pdf-Rights": "confirmed"}


def no_job_or_extraction_quota():
    return not ingest.JOBS and "extraction" not in router._spent and not list(ingest.PDF_DIR.rglob("*.pdf"))


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
    assert no_job_or_extraction_quota()


def test_stream_size_limit_without_content_length(client, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_PDF_BYTES", 10)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=iter([b"123456", b"789012"]))
    assert response.status_code == 413
    assert no_job_or_extraction_quota()


@pytest.mark.parametrize("state", ["completed", "pending", "zero"])
def test_existing_doi_never_spends_or_runs(client, monkeypatch, state):
    async def lookup(doi):
        return {"status": "found" if state == "completed" else "pending", "paper": {"rows": 10}}
    async def latest(doi):
        return {"job_id": "existing", "status": "done" if state == "zero" else "extracting",
                "metadata_source": None, "fresh": True}
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
    assert no_job_or_extraction_quota()


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
        raise RuntimeError("test outage (or migration 012 not applied)")
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


# --- 1: bounded work, rejected before any rendering -------------------------

@pytest.mark.parametrize("document", [pdf(pages=uploads.MAX_PAGES + 1), pdf(size=(3000, 3000))])
def test_page_count_and_page_area_are_capped_before_rendering(client, monkeypatch, document):
    monkeypatch.setattr(ingest.pdf_preprocess, "render_pdf", lambda *a, **k: pytest.fail("rendered"))
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=document)
    assert response.status_code == 413, response.text
    assert no_job_or_extraction_quota()


def test_largest_supported_page_is_accepted(client):
    response = client.post("/experimental/uploads", headers=headers(ticket(client)),
                           content=pdf(pages=uploads.MAX_PAGES, size=(1191, 1684)))
    assert response.status_code == 200, response.text


# --- 2: legacy WBM_UPLOAD guard uses the pipeline's parser ------------------

@pytest.mark.parametrize("value", ["", "true", "enabled", "2"])
def test_any_pipeline_truthy_wbm_upload_blocks_both_routes(client, monkeypatch, value):
    token = ticket(client)
    monkeypatch.setenv("WBM_UPLOAD", value)
    assert ingest.pipeline._env_bool("WBM_UPLOAD", False)
    assert client.post("/experimental/upload-ticket", json={"doi": "10.1000/a"}, headers=AUTH).status_code == 503
    assert client.post("/experimental/uploads", headers=headers(token), content=pdf()).status_code == 503
    assert not ingest.JOBS and not router._spent


@pytest.mark.parametrize("value", ["0", "false", "off"])
def test_falsy_wbm_upload_allows_uploads(client, monkeypatch, value):
    monkeypatch.setenv("WBM_UPLOAD", value)
    assert client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf()).status_code == 200


# --- 3: parsing happens in a limited child process --------------------------

def test_pdf_is_parsed_in_a_limited_child_without_credentials(monkeypatch, tmp_path):
    path = tmp_path / "probe.pdf"
    path.write_bytes(pdf())
    monkeypatch.setenv("INTERNAL_API_KEY", "must-not-reach-child")
    probe = ("import os\nprint(json.dumps({'pages': 1, 'max_area': 1, 'text': json.dumps("
             "[sorted(os.environ), resource.getrlimit(resource.RLIMIT_CPU), resource.getrlimit(resource.RLIMIT_AS)])}))\n"
             "sys.exit(0)\nimport fitz")
    monkeypatch.setattr(uploads, "_INSPECT", uploads._INSPECT.replace("import fitz", probe, 1))
    env, cpu, memory = json.loads(uploads.inspect_pdf(path))
    assert set(env) <= {"PATH", "LC_CTYPE", "__CF_USER_TEXT_ENCODING"}  # the last two are set by Python/macOS
    assert cpu == [uploads.CHECK_CPU_SECONDS] * 2
    if sys.platform.startswith("linux"):
        assert memory == [uploads.CHECK_MEMORY_BYTES] * 2


def test_slow_pdf_parse_is_killed_by_wall_clock(monkeypatch, tmp_path):
    path = tmp_path / "slow.pdf"
    path.write_bytes(pdf())
    monkeypatch.setattr(uploads, "_INSPECT", "import time; time.sleep(30)")
    monkeypatch.setattr(uploads, "CHECK_WALL_SECONDS", 0.5)
    started = time.monotonic()
    with pytest.raises(uploads.HTTPException) as caught:
        uploads.inspect_pdf(path)
    assert caught.value.status_code == 400 and time.monotonic() - started < 10


# --- 4: quota and abuse -----------------------------------------------------

def test_daily_cap_is_checked_before_streaming(client, monkeypatch):
    monkeypatch.setattr(settings, "daily_ingest_cap", 0)
    monkeypatch.setattr(uploads, "inspect_pdf", lambda path: pytest.fail("streamed and parsed"))
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 429
    assert not router._spent and no_job_or_extraction_quota()


def test_per_user_daily_upload_limit(client, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_UPLOADS_PER_USER_PER_DAY", 2)
    token = ticket(client)
    for _ in range(2):  # failed attempts count: each one streamed a body
        assert client.post("/experimental/uploads", headers=headers(token), content=b"not pdf").status_code == 400
    assert client.post("/experimental/uploads", headers=headers(token), content=pdf()).status_code == 429
    other = ticket(client, user=str(uuid4()))
    assert client.post("/experimental/uploads", headers=headers(other), content=pdf()).status_code == 200


def test_concurrent_upload_slots_are_capped(client, monkeypatch):
    monkeypatch.setattr(uploads, "_UPLOAD_SLOTS", asyncio.Semaphore(0))
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 503 and "Retry" in response.json()["detail"]
    assert not router._spent and no_job_or_extraction_quota()


def test_upload_body_has_a_read_timeout(client, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_READ_SECONDS", 0)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 408
    assert no_job_or_extraction_quota()


def test_file_writes_run_off_the_event_loop(client, monkeypatch):
    calls = []
    real = asyncio.to_thread
    async def spy(func, *args, **kwargs):
        calls.append(getattr(func, "__name__", ""))
        return await real(func, *args, **kwargs)
    monkeypatch.setattr(uploads.asyncio, "to_thread", spy)
    assert client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf()).status_code == 200
    assert "write" in calls and "inspect_pdf" in calls


def test_ticket_minting_is_rate_limited_per_user(client):
    for _ in range(10):
        ticket(client)
    assert client.post("/experimental/upload-ticket", json={"doi": "10.1000/upload"}, headers=AUTH).status_code == 429
    ticket(client, user=str(uuid4()))


# --- 5: DOI must be printed in the PDF's page text --------------------------

@pytest.mark.parametrize("document", [
    pdf(text="A paper without any identifier."),
    pdf(text="A different paper. https://doi.org/10.1000/other"),
    pdf(text="DOI only in metadata.", metadata={"subject": "doi:10.1000/upload", "keywords": "10.1000/upload"}),
])
def test_doi_must_match_page_text_or_no_job_exists(client, document):
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=document)
    assert response.status_code == 422, response.text
    assert no_job_or_extraction_quota()


def test_empty_upload_job_or_stale_pending_job_never_blocks_the_real_paper(client, monkeypatch):
    jobs = iter([{"job_id": "old-upload", "status": "done", "metadata_source": "upload", "fresh": False},
                 {"job_id": "restarted", "status": "extracting", "metadata_source": None, "fresh": False}])
    async def latest(doi):
        return next(jobs, None)
    monkeypatch.setattr(db, "latest_ingest_job", latest)
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=pdf())
    assert response.status_code == 200, response.text
    assert "existing" not in response.json() and len(ingest.JOBS) == 1


# --- 6: audit ---------------------------------------------------------------

def test_upload_audit_is_persisted_on_the_job_but_not_returned(client):
    body = pdf()
    response = client.post("/experimental/uploads", headers=headers(ticket(client)), content=body)
    assert response.status_code == 200
    first = client.stored[0]
    assert first["uploaded_by"] == UUID(AUTH["X-Hive-User-Id"])
    assert first["pdf_sha256"] == hashlib.sha256(body).hexdigest()
    assert first["uploaded_at"] and first["job_id"] == response.json()["job_id"]
    assert not set(db.UPLOAD_AUDIT_COLS) & set(response.json())


# --- 7: derivatives and crops -----------------------------------------------

def upload_job(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest, "JOBS", {})
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "_SLOTS", asyncio.Semaphore(1))
    monkeypatch.setattr(ingest, "backend_ready", lambda: (True, "mock test"))
    async def persist(*args):
        pass
    monkeypatch.setattr(db, "upsert_ingest_job", persist)
    job = ingest.start_job("10.1000/upload", metadata={"source": "upload"})
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf())
    run_dir = tmp_path / "uploads" / job.job_id
    def preprocess(pdf_path, paper_id, out_dir):
        assert out_dir == run_dir  # per-job, never the DOI's shared pdf_runs dir
        (out_dir / "rendered_pages").mkdir(parents=True)
        (out_dir / "rendered_pages" / "page_001.png").write_bytes(b"png")
        (out_dir / "rows.json").write_text("[]")
        return {"out_dir": str(out_dir), "paper_id": paper_id, "llm_candidate_count": 0}
    monkeypatch.setattr(ingest.pdf_preprocess, "preprocess_pdf", preprocess)
    return job, path, run_dir


def test_upload_pipeline_stores_then_removes_derivatives_and_invents_no_access(monkeypatch, tmp_path):
    job, path, run_dir = upload_job(monkeypatch, tmp_path)
    for name in ("paper_metadata", "check_access", "fetch_pdf"):
        monkeypatch.setattr(ingest.fulltext, name, lambda *a, **k: pytest.fail("Supplied PDF must not trigger remote full-text discovery/download"))
    monkeypatch.setattr(ingest.pipeline, "run_records_stage", lambda *a, **k: {"rows_path": str(run_dir / "rows.json"), "records": 0, "failures": 0})
    stored = []
    async def load(job, rows, directory):
        assert (directory / "rendered_pages" / "page_001.png").exists()  # still there while storing
        stored.append(rows)
    monkeypatch.setattr(ingest, "load_rows", load)
    asyncio.run(ingest.run_job(job.job_id, path))
    assert job.status == "done" and job.rows == 0 and stored == [[]]
    assert job.access_status is None and job.access_url is None
    assert not path.exists() and not run_dir.exists()


def test_failed_panels_store_nothing_and_still_remove_derivatives(monkeypatch, tmp_path):
    job, path, run_dir = upload_job(monkeypatch, tmp_path)
    async def forbidden(*args):
        pytest.fail("Failed upload must not store partial results")
    monkeypatch.setattr(ingest, "load_rows", forbidden)
    monkeypatch.setattr(ingest.pipeline, "run_records_stage", lambda *a, **k: {"failures": 1})
    asyncio.run(ingest.run_job(job.job_id, path))
    assert job.status == "failed"
    assert not path.exists() and not run_dir.exists()


def fake_pool(monkeypatch, row):
    class Conn:
        async def fetchrow(self, *args):
            return row
    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield Conn()
    async def get():
        return Pool()
    monkeypatch.setattr(db, "get_readonly_pool", get)


@pytest.mark.parametrize("source,access,hidden", [("upload", None, True), ("upload", "unknown", True),
                                                  ("upload", "open_access", False), ("europe_pmc", None, False), (None, None, False)])
def test_upload_crops_without_verified_open_access_are_hidden(monkeypatch, source, access, hidden):
    fake_pool(monkeypatch, {"png": b"png", "metadata_source": source, "access_status": access})
    if hidden:
        with pytest.raises(db.UploadCropHidden):
            asyncio.run(db.fetch_live_crop("job", "c.png"))
    else:
        assert asyncio.run(db.fetch_live_crop("job", "c.png")) == b"png"


def test_hidden_crop_route_returns_clear_403(monkeypatch):
    async def record(record_id):
        return {"id": 1, "job_id": "upload-job", "image_crop_ref": "c.png"}
    async def hidden(*args):
        raise db.UploadCropHidden(db.UPLOAD_CROP_HIDDEN)
    monkeypatch.setattr(router, "fetch_live_record", record)
    monkeypatch.setattr(router, "fetch_live_crop", hidden)
    with TestClient(app) as c:
        response = c.get("/experimental/records/1/crop", headers={"Authorization": AUTH["Authorization"]})
    assert response.status_code == 403
    assert response.json()["detail"].startswith("Crop hidden for uploaded copy")

"""Explicit PDF uploads using short-lived capabilities issued to signed-in users."""
from __future__ import annotations

import asyncio
import base64
import shutil
import hashlib
import hmac
import json
import logging
import os
import re
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .. import db
from ..auth import require_internal_key
from ..config import settings
from ..limiter import limiter
from . import ingest
from .router import _daily_used, _spend_daily

logger = logging.getLogger("hive.experimental.uploads")

MAX_PDF_BYTES = 50 * 1024 * 1024
# Work one upload can cause (preprocessing renders every page at 350 DPI).
MAX_PAGES = 60
# A2 (0.25 m^2) in PDF points^2: about 47 Mpx / 140 MB per page at 350 DPI.
# Journal pages are letter/A4, tabloid at most.
MAX_PAGE_AREA_PT2 = 1191 * 1684
# Whole document at the render DPI (about 52 letter pages); bounds render time and disk.
MAX_RENDER_PIXELS = 600_000_000
# Untrusted parsing happens in a child process under these limits.
CHECK_WALL_SECONDS = 30
CHECK_CPU_SECONDS = 20
CHECK_MEMORY_BYTES = 1024 ** 3
UPLOAD_READ_SECONDS = 180          # whole body; bounds slow-loris uploads
MAX_UPLOADS_PER_USER_PER_DAY = 10  # attempts that stream a body, accepted or not
# ponytail: in-process semaphore and counters (single Render instance); move to the DB with a second instance.
_UPLOAD_SLOTS = asyncio.Semaphore(2)
_ACTIVE_USERS: set[str] = set()  # one in-flight upload per user
_lock = asyncio.Lock()
UNREADABLE = "Select a readable, unencrypted PDF with at least one page."


@asynccontextmanager
async def _sweep_orphans(app):
    # Jobs run in-process, so anything here at startup was left by a crash or
    # redeploy: uploaded PDFs and per-job render dirs of possibly paywalled copies.
    shutil.rmtree(ingest.PDF_DIR / "uploads", ignore_errors=True)
    yield


ticket_router = APIRouter(prefix="/experimental", dependencies=[Depends(require_internal_key)])
router = APIRouter(prefix="/experimental", lifespan=_sweep_orphans)


def normalize_doi(value: str) -> str:
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).strip().lower()
    if len(value) > 200 or not re.fullmatch(r"10\.\d{4,9}/[^\s?#]+", value):
        raise HTTPException(422, "Enter a valid DOI, such as 10.1234/example.")
    return value


def _legacy_upload_on() -> bool:
    # Same parser as the pipeline that would act on it, so this guard is never looser.
    return ingest.pipeline._env_bool("WBM_UPLOAD", False)


def _signature(payload: str) -> str:
    if not settings.internal_api_key:
        raise HTTPException(503, "Upload authorization is not configured.")
    return hmac.new(settings.internal_api_key.encode(),
                    ("pdf-upload-v1:" + payload).encode(), hashlib.sha256).hexdigest()


def authorize(authorization: str | None) -> dict:
    try:
        token = (authorization or "").removeprefix("Bearer ")
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _signature(payload)):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(payload))
        UUID(data["user"])
        normalize_doi(data["doi"])
        if data["expires"] <= time.time():
            raise ValueError()
        return data
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Upload authorization expired or is invalid. Submit again.") from None


class Ticket(BaseModel):
    doi: str = Field(min_length=6, max_length=260)


def _ticket_user(request: Request) -> str:
    # The route requires the internal key, so the header comes from our BFF.
    return "upload-ticket:" + request.headers.get("x-hive-user-id", "")


@ticket_router.post("/upload-ticket")
@limiter.limit("10/minute;60/day", key_func=_ticket_user)
async def upload_ticket(request: Request, body: Ticket, x_hive_user_id: str | None = Header(default=None)):
    try:
        user = str(UUID(x_hive_user_id or ""))
    except ValueError:
        raise HTTPException(401, "Sign in before uploading a PDF.") from None
    doi = normalize_doi(body.doi)
    if not settings.db_ingest_url:
        raise HTTPException(503, "PDF storage is not configured.")
    if _legacy_upload_on():
        raise HTTPException(503, "Disable legacy WBM_UPLOAD before using PDF uploads; uploaded evidence must stay in the live tier.")
    data = {"doi": doi, "user": user, "expires": int(time.time()) + 300}
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    return {"token": payload + "." + _signature(payload), "max_bytes": MAX_PDF_BYTES}


async def existing(doi: str) -> dict | None:
    """Evidence or a live job that should be reused instead of a new upload.

    Failed, stale, or upload-produced empty jobs never block: a wrong or
    unlucky upload must not stop the real paper from being uploaded later.
    """
    try:
        stored = await db.lookup_live_paper(doi)
    except Exception:
        raise HTTPException(503, "Could not check stored evidence. Please retry; no job was started.") from None
    if stored["status"] == "found":
        return {"doi": doi, "status": "done", "rows": stored["paper"]["rows"],
                "message": "Stored evidence already exists.", "existing": True}
    for job in ingest.JOBS.values():
        if job.doi.lower() == doi and job.status not in {"done", "failed", "awaiting_full_text"}:
            return {**job.to_dict(), "existing": True}
    try:
        job = await db.latest_ingest_job(doi)
    except Exception:
        raise HTTPException(503, "Could not check extraction status. Please retry; no job was started.") from None
    if job and job["status"] == "done" and job.get("metadata_source") != "upload":
        return {"doi": doi, "status": "done", "rows": 0,
                "message": "This PDF was processed without stored Western blot evidence.", "existing": True}
    if job and job["status"] not in {"done", "failed", "awaiting_full_text"} and job.get("fresh"):
        return {"job_id": job["job_id"], "doi": doi, "status": job["status"],
                "message": "An extraction already exists for this DOI.", "existing": True}
    return None


# Runs as `python -I -c` with an empty environment: no credentials, no repo on
# sys.path. Prints page count, largest and total page area and page-1 text as JSON.
_INSPECT = r"""
import json, resource, sys
path, cpu, memory = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
max_pages = int(sys.argv[4])
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
try:
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
except ValueError:
    if sys.platform != "darwin":  # macOS refuses RLIMIT_AS; Linux (Render) enforces it
        raise
import fitz
with fitz.open(path) as doc:
    if not doc.is_pdf or doc.is_encrypted or not doc.page_count:
        sys.exit(2)
    out = {"pages": doc.page_count}
    if doc.page_count <= max_pages:
        areas = [max(p.rect.get_area(), p.mediabox.get_area()) for p in doc]
        out.update(max_area=max(areas), total_area=sum(areas), text=doc[0].get_text()[:200000])
print(json.dumps(out))
"""


def inspect_pdf(path: Path) -> str:
    """Validate an untrusted PDF without parsing it in the API process.

    Bounds the work the later render can cause (pages, page area, total
    pixels at the render DPI) and returns page-1 text for DOI binding.
    """
    with path.open("rb") as source:
        if not source.read(1024).lstrip().startswith(b"%PDF-"):
            raise HTTPException(400, UNREADABLE)
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-c", _INSPECT, str(path),
             str(CHECK_CPU_SECONDS), str(CHECK_MEMORY_BYTES), str(MAX_PAGES)],
            capture_output=True, check=False, timeout=CHECK_WALL_SECONDS, env={"PATH": os.environ.get("PATH", "")})
    except subprocess.TimeoutExpired:
        raise HTTPException(400, "This PDF took too long to read. Upload the publisher's PDF of the paper.") from None
    try:
        if done.returncode:
            raise ValueError()
        facts = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise HTTPException(400, UNREADABLE) from None
    if facts["pages"] > MAX_PAGES:
        raise HTTPException(413, f"PDF must have at most {MAX_PAGES} pages; upload the main paper without supplements.")
    if not 0 < facts["max_area"] <= MAX_PAGE_AREA_PT2:
        raise HTTPException(413, "PDF page size is outside the supported range (up to A2).")
    pixels = facts["total_area"] * (ingest.pdf_preprocess.DEFAULT_DPI / 72) ** 2
    if pixels > MAX_RENDER_PIXELS:
        raise HTTPException(413, f"PDF is too large to process ({pixels / 1e6:.0f} megapixels at "
                                 f"{ingest.pdf_preprocess.DEFAULT_DPI} DPI; limit {MAX_RENDER_PIXELS // 1_000_000}). "
                                 "Upload the main paper without supplements.")
    return facts["text"]


def check_doi(text: str, doi: str) -> None:
    """The supplied DOI must be printed on page 1 (page text, never metadata,
    which is trivially editable and often stale). Other DOIs there, such as a
    related article, are fine. A forged page 1 still passes: the operator path
    for removing such an upload is in tickets/o2-pdf-upload-verification.md."""
    found = {ingest.fulltext.normalize_doi(d) for d in ingest.pdf_preprocess._extract_dois(text)}
    if doi not in found:
        raise HTTPException(422, f"DOI {doi} was not found in the text of the PDF's first page, so it cannot be "
                                 "matched to this paper. Check the DOI, or upload the publisher's version.")


@router.post("/uploads")
async def upload(request: Request, background: BackgroundTasks,
                 authorization: str | None = Header(default=None)):
    data = authorize(authorization)
    if request.headers.get("content-type", "").split(";")[0] != "application/pdf":
        raise HTTPException(415, "Only PDF files are accepted.")
    if request.headers.get("x-pdf-rights") != "confirmed":
        raise HTTPException(422, "Confirm that you have permission to upload this PDF.")
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise HTTPException(400, "Invalid file size.") from None
    if length > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF must be 50 MB or smaller.")
    doi, user = data["doi"], data["user"]
    if _legacy_upload_on():
        raise HTTPException(503, "Disable legacy WBM_UPLOAD before using PDF uploads.")
    if not settings.db_ingest_url:
        raise HTTPException(503, "PDF storage is not configured.")
    found = await existing(doi)
    if found:
        return found
    ok, why = ingest.backend_ready()
    if not ok:
        raise HTTPException(503, why)
    # Read-only quota checks before accepting a single byte.
    if _daily_used("extraction") >= settings.daily_ingest_cap:
        raise HTTPException(429, f"The beta's daily extraction limit ({settings.daily_ingest_cap}) is reached. "
                                 "It resets at 00:00 UTC.")
    if _daily_used("upload:" + user) >= MAX_UPLOADS_PER_USER_PER_DAY:
        raise HTTPException(429, f"You have reached today's upload limit ({MAX_UPLOADS_PER_USER_PER_DAY}). "
                                 "It resets at 00:00 UTC.")
    if user in _ACTIVE_USERS:
        raise HTTPException(429, "Your previous upload is still being received. Wait for it to finish.")
    if _UPLOAD_SLOTS.locked():
        raise HTTPException(503, "Other uploads are being processed. Retry in a minute.")
    async with _UPLOAD_SLOTS:
        _ACTIVE_USERS.add(user)
        try:
            _spend_daily("upload:" + user, MAX_UPLOADS_PER_USER_PER_DAY)
            return await _receive(request, background, doi, user)
        finally:
            _ACTIVE_USERS.discard(user)


async def _receive(request: Request, background: BackgroundTasks, doi: str, user: str) -> dict:
    directory = ingest.PDF_DIR / "uploads"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (uuid4().hex + ".pdf")
    accepted = False
    try:
        size, digest = 0, hashlib.sha256()
        try:
            async with asyncio.timeout(UPLOAD_READ_SECONDS):
                with path.open("xb") as output:
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > MAX_PDF_BYTES:
                            raise HTTPException(413, "PDF must be 50 MB or smaller.")
                        digest.update(chunk)
                        await asyncio.to_thread(output.write, chunk)
        except TimeoutError:
            raise HTTPException(408, "The upload took too long. Check your connection and retry.") from None
        text = await asyncio.to_thread(inspect_pdf, path)
        check_doi(text, doi)
        # Existing runner is single-process: serialize DOI checks and job creation.
        async with _lock:
            found = await existing(doi)
            if found:
                return found
            from .router import _spent
            _spend_daily("extraction", settings.daily_ingest_cap)
            charged_day = _spent["extraction"][0]
            job = ingest.start_job(doi, source="upload")
            job.doi = doi  # Keep the validated identifier, not citation punctuation heuristics.
            audit = {"uploaded_by": UUID(user), "uploaded_at": ingest._now(), "pdf_sha256": digest.hexdigest()}
            try:
                await db.upsert_ingest_job({**job.to_dict(), **audit})
            except Exception:
                ingest.JOBS.pop(job.job_id, None)
                day, used = _spent["extraction"]
                if day == charged_day:
                    _spent["extraction"] = (day, max(0, used - 1))
                raise HTTPException(503, "Could not store the upload job. Please retry.") from None
            logger.info("pdf upload accepted job=%s doi=%s user=%s sha256=%s bytes=%d",
                        job.job_id, doi, user, audit["pdf_sha256"], size)
            background.add_task(ingest.run_job, job.job_id, path)
            accepted = True
            return job.to_dict()
    finally:
        if not accepted:
            path.unlink(missing_ok=True)

"""Explicit PDF uploads using short-lived capabilities issued to signed-in users."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .. import db
from ..auth import require_internal_key
from ..config import settings
from . import ingest
from .router import _spend_daily

MAX_PDF_BYTES = 50 * 1024 * 1024
_lock = asyncio.Lock()
ticket_router = APIRouter(prefix="/experimental", dependencies=[Depends(require_internal_key)])
router = APIRouter(prefix="/experimental")


def normalize_doi(value: str) -> str:
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).strip().lower()
    if len(value) > 200 or not re.fullmatch(r"10\.\d{4,9}/[^\s?#]+", value):
        raise HTTPException(422, "Enter a valid DOI, such as 10.1234/example.")
    return value


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


@ticket_router.post("/upload-ticket")
async def upload_ticket(body: Ticket, x_hive_user_id: str | None = Header(default=None)):
    try:
        user = str(UUID(x_hive_user_id or ""))
    except ValueError:
        raise HTTPException(401, "Sign in before uploading a PDF.") from None
    doi = normalize_doi(body.doi)
    if not settings.db_ingest_url:
        raise HTTPException(503, "PDF storage is not configured.")
    if os.environ.get("WBM_UPLOAD", "").lower() in {"1", "true", "yes", "on"}:
        raise HTTPException(503, "Disable legacy WBM_UPLOAD before using PDF uploads; uploaded evidence must stay in the live tier.")
    data = {"doi": doi, "user": user, "expires": int(time.time()) + 300}
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    return {"token": payload + "." + _signature(payload), "max_bytes": MAX_PDF_BYTES}


async def existing(doi: str) -> dict | None:
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
    if job and job["status"] == "done":
        return {"doi": doi, "status": "done", "rows": 0,
                "message": "This PDF was processed without stored Western blot evidence.", "existing": True}
    if job and job["status"] not in {"done", "failed", "awaiting_full_text"}:
        return {"job_id": job["job_id"], "doi": doi, "status": job["status"],
                "message": "An extraction already exists for this DOI.", "existing": True}
    return None


def validate_pdf(path: Path) -> None:
    import fitz
    try:
        with path.open("rb") as source:
            if not source.read(1024).lstrip().startswith(b"%PDF-"):
                raise ValueError()
        with fitz.open(path) as document:
            if not document.is_pdf or document.is_encrypted or not document.page_count:
                raise ValueError()
    except Exception:
        raise HTTPException(400, "Select a readable, unencrypted PDF with at least one page.") from None


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
    doi = data["doi"]
    if os.environ.get("WBM_UPLOAD", "").lower() in {"1", "true", "yes", "on"}:
        raise HTTPException(503, "Disable legacy WBM_UPLOAD before using PDF uploads.")
    if not settings.db_ingest_url:
        raise HTTPException(503, "PDF storage is not configured.")
    found = await existing(doi)
    if found:
        return found
    ok, why = ingest.backend_ready()
    if not ok:
        raise HTTPException(503, why)
    directory = ingest.PDF_DIR / "uploads"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (uuid4().hex + ".pdf")
    accepted = False
    try:
        size = 0
        with path.open("xb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise HTTPException(413, "PDF must be 50 MB or smaller.")
                output.write(chunk)
        await asyncio.to_thread(validate_pdf, path)
        # Existing runner is single-process: serialize DOI checks and job creation.
        async with _lock:
            found = await existing(doi)
            if found:
                return found
            from .router import _spent
            _spend_daily("extraction", settings.daily_ingest_cap)
            charged_day = _spent["extraction"][0]
            job = ingest.start_job(doi, metadata={"source": "upload"})
            job.doi = doi  # Keep the validated identifier, not citation punctuation heuristics.
            try:
                await db.upsert_ingest_job(job.to_dict())
            except Exception:
                ingest.JOBS.pop(job.job_id, None)
                day, used = _spent["extraction"]
                if day == charged_day:
                    _spent["extraction"] = (day, max(0, used - 1))
                raise HTTPException(503, "Could not store the upload job. Please retry.") from None
            background.add_task(ingest.run_job, job.job_id, path)
            accepted = True
            return job.to_dict()
    finally:
        if not accepted:
            path.unlink(missing_ok=True)

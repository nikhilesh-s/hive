"""Live DOI ingestion jobs (EXPERIMENTAL).

DOI -> open-access PDF (Europe PMC / Unpaywall) -> the existing HiveBlot
pipeline (OpenCV panel candidates -> model claims -> deterministic biology
-> Evidence Records) -> rows in `western_blot_records_live` tagged
`review_tier = 'live_unreviewed'`. The reviewed corpus is never written.

One job = one DOI. Jobs run as FastAPI background tasks in-process (Render
free tier is a single instance); state lives in memory and is mirrored to
`ingest_jobs` when DB_INGEST_URL is configured, crops are stored as bytes in
`ingest_crops` because the API host's disk is ephemeral.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings

logger = logging.getLogger("hive.experimental.ingest")

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # `western_blot_miner` lives at the repo root
    sys.path.insert(0, str(REPO))

from western_blot_miner import fulltext, pdf_preprocess, pipeline  # noqa: E402

from .. import db  # noqa: E402

PDF_DIR = Path(os.environ.get("WBM_PDF_CACHE", str(REPO / "western_blot_miner" / "data" / "live_pdfs")))
JSONB_COLS = {"aliases_used_in_paper", "experiment_flags", "antibody_source_evidence",
              "provenance", "validation", "anomaly_flags", "experiment_type_evidence"}
STAGES = ("queued", "fetching", "preprocessing", "extracting", "loading", "done", "failed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    job_id: str
    doi: str
    status: str = "queued"
    message: str = "Queued"
    pmcid: str | None = None
    paper_id: str | None = None
    title: str | None = None
    candidates: int | None = None
    records: int | None = None
    rows: int | None = None
    backend: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


JOBS: dict[str, Job] = {}


def backend_ready() -> tuple[bool, str]:
    """Is a live model backend configured? (mock counts, for tests/dry runs)"""
    backend = os.environ.get("WBM_LLM_BACKEND", "").lower()
    env = os.environ
    if backend == "anthropic":
        ok = bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))
        return ok, "anthropic" if ok else "WBM_LLM_BACKEND=anthropic but no ANTHROPIC_API_KEY"
    if backend == "bedrock":
        ok = bool(env.get("AWS_ACCESS_KEY_ID") or env.get("AWS_PROFILE"))
        return ok, "bedrock" if ok else "WBM_LLM_BACKEND=bedrock but no AWS credentials"
    if backend in ("openai", "openai_compatible"):
        ok = bool(env.get("WBM_LLM_API_KEY") or env.get("OPENAI_API_KEY"))
        return ok, backend if ok else "WBM_LLM_BACKEND=openai but no WBM_LLM_API_KEY"
    if backend == "mock":
        return True, "mock"
    return False, "No extraction model configured (set WBM_LLM_BACKEND + credentials)"


def start_job(doi: str) -> Job:
    doi = fulltext.normalize_doi(doi)
    if not doi:
        raise ValueError("not a DOI")
    job = Job(job_id=uuid.uuid4().hex[:12], doi=doi)
    JOBS[job.job_id] = job
    return job


async def _persist(job: Job) -> None:
    if not settings.db_ingest_url:
        return
    try:
        await db.upsert_ingest_job(job.to_dict())
    except Exception:  # persistence is best-effort; the in-memory job is authoritative
        logger.exception("ingest job persist failed")


async def _set(job: Job, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    job.updated_at = _now()
    await _persist(job)


async def run_job(job_id: str) -> Job:
    job = JOBS[job_id]
    loop = asyncio.get_running_loop()
    try:
        ok, why = backend_ready()
        if not ok:
            raise RuntimeError(why)
        job.backend = why
        await _set(job, status="fetching", message="Locating open-access full text (Europe PMC / Unpaywall)…")
        got = await loop.run_in_executor(None, fulltext.fetch_pdf, job.doi, PDF_DIR)
        if not got.get("pdf_path"):
            raise RuntimeError("No open-access PDF is available for this DOI (PMC / Unpaywall); "
                               "HiveBlot only reads papers it is allowed to download.")
        await _set(job, pmcid=got.get("pmcid"), status="preprocessing",
                   message="Rendering pages and scoring blot-panel candidates (OpenCV)…")
        summary = await loop.run_in_executor(
            None, lambda: pdf_preprocess.preprocess_pdf(got["pdf_path"], paper_id=job.doi))
        n = summary.get("llm_candidate_count", 0)
        await _set(job, paper_id=summary.get("paper_id"), candidates=n, status="extracting",
                   message=f"Reading {n} candidate panel{'s' if n != 1 else ''} with the model, then reconciling biology…")
        rec = await loop.run_in_executor(None, lambda: pipeline.run_records_stage(summary, use_cache=False))
        rows = json.loads(Path(rec["rows_path"]).read_text(encoding="utf-8"))
        await _set(job, records=rec.get("records"), rows=len(rows), status="loading",
                   message="Storing live rows and crops…")
        await load_rows(job, rows, Path(summary["out_dir"]))
        await _set(job, status="done",
                   message=f"{rec.get('records', 0)} experiment record(s), {len(rows)} lane row(s). Unreviewed.")
    except Exception as exc:
        logger.exception("ingest job %s failed", job_id)
        await _set(job, status="failed", error=str(exc)[:500], message="Extraction failed")
    return job


async def load_rows(job: Job, rows: list[dict], run_dir: Path) -> None:
    """Replace this DOI's live rows; store referenced crops as bytes."""
    if not settings.db_ingest_url:
        raise RuntimeError("DB_INGEST_URL is not configured")
    crops: dict[str, bytes] = {}
    for r in rows:
        ref = r.get("image_crop_ref")
        if not ref:
            continue
        name = Path(str(ref)).name
        if name not in crops:
            p = Path(str(ref))
            if not p.is_absolute():
                p = run_dir / "panel_candidates" / name
            if p.is_file():
                crops[name] = p.read_bytes()
        r["image_crop_ref"] = name
        r["doi"] = r.get("doi") or job.doi
        r["job_id"] = job.job_id
        r["review_tier"] = "live_unreviewed"
    await db.replace_live_rows(job.doi, job.job_id, rows, crops, JSONB_COLS)

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
import shutil
import subprocess
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

from western_blot_miner import fulltext, llm_client, pdf_preprocess, pipeline  # noqa: E402

from .. import db  # noqa: E402

PDF_DIR = Path(os.environ.get("WBM_PDF_CACHE", str(REPO / "western_blot_miner" / "data" / "live_pdfs")))
JSONB_COLS = {"aliases_used_in_paper", "experiment_flags", "antibody_source_evidence",
              "provenance", "validation", "anomaly_flags", "experiment_type_evidence"}
STAGES = ("queued", "metadata", "checking_access", "fetching", "preprocessing", "extracting", "loading", "awaiting_full_text", "done", "failed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    job_id: str
    doi: str
    status: str = "queued"
    message: str = "Queued"
    pmcid: str | None = None
    pmid: str | None = None
    paper_id: str | None = None
    title: str | None = None
    abstract: str | None = None
    authors: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    metadata_source: str | None = None
    discovery_query: str | None = None
    access_status: str | None = None
    access_url: str | None = None
    access_source: str | None = None
    access_checked_at: str | None = None
    relevance_status: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    relevance_checked_at: str | None = None
    candidates: int | None = None
    records: int | None = None
    rows: int | None = None
    backend: str | None = None
    error: str | None = None
    reuse: bool = False       # load a previous run's rows without re-extracting
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


JOBS: dict[str, Job] = {}
# Extractions run inside the API process. On a small instance two at once
# starved the health check and the platform restarted the process, killing
# both (2026-09-27), so jobs past this many wait their turn as "queued".
_SLOTS = asyncio.Semaphore(max(1, settings.ingest_concurrency))


def interrupted(stored: dict) -> dict:
    """A persisted job missing from this process's JOBS that never finished was
    killed by a restart (jobs only run in-process): report it as failed."""
    if stored.get("status") in ("done", "failed", "awaiting_full_text"):
        return stored
    return {**stored, "status": "failed",
            "error": "Interrupted by a server restart. Start the extraction again."}


def backend_ready() -> tuple[bool, str]:
    """Is a live model backend configured? One source of truth for extraction
    and paper QA: western_blot_miner.llm_client.backend_status."""
    return llm_client.backend_status()


# Uploaded PDFs are untrusted: render + OpenCV run in a child process with no
# credentials in its environment, a CPU and wall-clock budget, and a per-file
# size cap. Validation already capped pages and total pixels.
UPLOAD_PREPROCESS_SECONDS = 900
UPLOAD_MAX_FILE_BYTES = 512 * 1024 ** 2
_PREPROCESS = r"""
import resource, sys
repo, pdf, doi, out_dir, cpu, fsize = sys.argv[1:7]
resource.setrlimit(resource.RLIMIT_CPU, (int(cpu), int(cpu)))
resource.setrlimit(resource.RLIMIT_FSIZE, (int(fsize), int(fsize)))
sys.path.insert(0, repo)
from western_blot_miner import pdf_preprocess
pdf_preprocess.preprocess_pdf(pdf, paper_id=doi, out_dir=out_dir)
"""


def preprocess_upload(pdf_path: Path, doi: str, out_dir: Path) -> dict:
    """pdf_preprocess.preprocess_pdf for an uploaded PDF, in a limited child.
    The miner code and its behaviour for non-upload jobs are unchanged."""
    try:
        subprocess.run(
            [sys.executable, "-I", "-c", _PREPROCESS, str(REPO), str(pdf_path), doi, str(out_dir),
             str(UPLOAD_PREPROCESS_SECONDS), str(UPLOAD_MAX_FILE_BYTES)],
            capture_output=True, check=True, timeout=UPLOAD_PREPROCESS_SECONDS,
            env={"PATH": os.environ.get("PATH", "")})
        return json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    except (subprocess.SubprocessError, OSError, ValueError):
        raise RuntimeError("Rendering the uploaded PDF failed or exceeded its time or size limits.") from None


def run_dir_for(doi: str) -> Path:
    """Where pdf_preprocess writes this DOI's run (mirrors _safe_path_segment)."""
    import re

    return REPO / "western_blot_miner" / "data" / "pdf_runs" / re.sub(r"[^A-Za-z0-9._-]+", "_", doi)


def start_job(doi: str, reuse: bool = False, *, discovery_query: str | None = None,
              metadata: dict | None = None) -> Job:
    doi = fulltext.normalize_doi(doi)
    if not doi:
        raise ValueError("not a DOI")
    metadata = metadata or {}
    authors = metadata.get("authors")
    if isinstance(authors, list):
        authors = ", ".join(str(a) for a in authors if a)
    year = metadata.get("publication_year") or metadata.get("year")
    try:
        year = int(str(year)[:4]) if year else None
    except (TypeError, ValueError):
        year = None
    job = Job(
        job_id=uuid.uuid4().hex[:12],
        doi=doi,
        reuse=reuse,
        discovery_query=discovery_query,
        pmcid=metadata.get("pmcid"),
        pmid=metadata.get("pmid"),
        title=metadata.get("title"),
        abstract=metadata.get("abstract"),
        authors=authors,
        journal=metadata.get("journal") or metadata.get("venue"),
        publication_year=year,
        metadata_source=metadata.get("metadata_source") or metadata.get("source"),
        access_status=metadata.get("access_status"),
        access_url=metadata.get("access_url"),
        access_source=metadata.get("access_source"),
        relevance_status=metadata.get("relevance_status"),
        relevance_score=metadata.get("relevance_score"),
        relevance_reason=metadata.get("relevance_reason"),
    )
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


async def run_job(job_id: str, uploaded_pdf: Path | None = None) -> Job:
    job = JOBS[job_id]
    loop = asyncio.get_running_loop()
    upload_run_dir = PDF_DIR / "uploads" / job_id if uploaded_pdf else None
    try:
        prior = run_dir_for(job.doi) / "supabase_rows.json"
        if job.reuse and prior.exists():
            # Re-load an already-extracted run (demo resilience: no model call).
            rows = json.loads(prior.read_text(encoding="utf-8"))
            await _set(job, backend="reuse", candidates=None, rows=len(rows),
                       records=len({str(r.get("stable_row_key", "")).split(":")[0] for r in rows}),
                       status="loading", message="Loading the previous extraction of this paper (no model call)…")
            await load_rows(job, rows, prior.parent)
            await _set(job, status="done", message=f"{job.records} experiment record(s), {len(rows)} lane row(s) re-loaded. Unreviewed.")
            return job
        if _SLOTS.locked():
            await _set(job, message="Waiting for another extraction to finish (one runs at a time)…")
        async with _SLOTS:
            # Metadata, relevance, and access are useful even when full text is
            # unavailable, so they deliberately run before any model work.
            await _set(job, status="metadata", message="Using the supplied PDF…" if uploaded_pdf else "Fetching paper metadata…")
            seed = {
                "title": job.title, "abstract": job.abstract, "authors": job.authors,
                "journal": job.journal, "publication_year": job.publication_year,
                "pmid": job.pmid, "pmcid": job.pmcid, "metadata_source": job.metadata_source,
            }
            meta = seed if uploaded_pdf else await loop.run_in_executor(
                None, lambda: fulltext.paper_metadata(job.doi, seed=seed))
            meta_authors = meta.get("authors")
            if isinstance(meta_authors, list):
                meta_authors = ", ".join(str(a) for a in meta_authors if a)
            await _set(
                job,
                pmid=meta.get("pmid"),
                pmcid=meta.get("pmcid"),
                title=meta.get("title"),
                abstract=meta.get("abstract"),
                authors=meta_authors,
                journal=meta.get("journal"),
                publication_year=meta.get("publication_year"),
                metadata_source=meta.get("metadata_source"),
            )

            relevance = fulltext.assess_relevance(job.discovery_query, meta)
            await _set(
                job,
                relevance_status=relevance.get("relevance_status"),
                relevance_score=relevance.get("relevance_score"),
                relevance_reason=relevance.get("relevance_reason"),
                relevance_checked_at=_now(),
                status="checking_access",
                message="Using supplied full text; access status is unverified." if uploaded_pdf else "Checking open-access availability…",
            )

            access = {} if uploaded_pdf else await loop.run_in_executor(
                None, lambda: fulltext.check_access(job.doi, pmcid=job.pmcid))
            await _set(
                job,
                access_status=access.get("access_status"),
                access_url=access.get("access_url"),
                access_source=access.get("access_source"),
                access_checked_at=None if uploaded_pdf else _now(),
            )

            if job.access_status == "no_open_copy_found":
                await _set(
                    job,
                    status="awaiting_full_text",
                    message="No open copy found. Check institutional access; extraction can continue once full text is available.",
                )
                return job

            await _set(job, status="fetching", message="Reading supplied full text…" if uploaded_pdf else "Retrieving usable open-access full text…")
            got = {"pdf_path": str(uploaded_pdf)} if uploaded_pdf else await loop.run_in_executor(None, fulltext.fetch_pdf, job.doi, PDF_DIR)
            if not got.get("pdf_path"):
                await _set(
                    job,
                    pmcid=got.get("pmcid") or job.pmcid,
                    status="awaiting_full_text",
                    message=(
                        "Open-access metadata was found, but HiveBlot could not retrieve a usable PDF automatically. "
                        "Open the source in your browser or provide the PDF later."
                        if job.access_status == "open_access"
                        else "Access could not be confirmed and no usable PDF was retrieved."
                    ),
                )
                return job

            ok, why = backend_ready()
            if not ok:
                raise RuntimeError(why)
            job.backend = why
            await _set(job, pmcid=got.get("pmcid") or job.pmcid, pmid=got.get("pmid") or job.pmid,
                       access_status=job.access_status if uploaded_pdf else "open_access",
                       access_source=job.access_source or got.get("source"),
                       access_url=job.access_url if uploaded_pdf else job.access_url or f"https://doi.org/{job.doi}",
                       status="preprocessing",
                       message="Rendering pages and scoring blot-panel candidates (OpenCV)…")
            # Uploads get a per-job run dir (deleted below) so a user's copy never
            # mixes with, or outlives, the DOI's shared pdf_runs directory. The
            # DOI was already matched to the PDF's page text before the job existed.
            summary = await loop.run_in_executor(
                None, lambda: preprocess_upload(uploaded_pdf, job.doi, upload_run_dir) if uploaded_pdf
                else pdf_preprocess.preprocess_pdf(got["pdf_path"], paper_id=job.doi))
            n = summary.get("llm_candidate_count", 0)
            await _set(job, paper_id=summary.get("paper_id"), candidates=n, status="extracting",
                       message=f"Reading {n} candidate panel{'s' if n != 1 else ''} with the model, then reconciling biology…")
            rec = await loop.run_in_executor(None, lambda: pipeline.run_records_stage(summary, use_cache=False))
            if uploaded_pdf and rec.get("failures"):
                raise RuntimeError("One or more panel extractions failed. No partial upload results were stored; retry after checking the model service.")
            rows = json.loads(Path(rec["rows_path"]).read_text(encoding="utf-8"))
            await _set(job, records=rec.get("records"), rows=len(rows), status="loading",
                       message="Storing live rows and crops…")
            await load_rows(job, rows, Path(summary["out_dir"]))
            await _set(job, status="done",
                       message=f"{rec.get('records', 0)} experiment record(s), {len(rows)} lane row(s). Unreviewed.")
    except Exception as exc:
        logger.exception("ingest job %s failed", job_id)
        await _set(job, status="failed", error=str(exc)[:500], message="Extraction failed")
    finally:
        if uploaded_pdf:
            uploaded_pdf.unlink(missing_ok=True)
            # Rendered pages, crops and page text are derivatives of a possibly
            # paywalled copy: rows and crops are already in the DB by now.
            shutil.rmtree(upload_run_dir, ignore_errors=True)
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
        r["paper_id"] = r.get("paper_id") or job.doi  # NOT NULL in the live table
        r["job_id"] = job.job_id
        r["review_tier"] = "live_unreviewed"
    await db.replace_live_rows(job.doi, job.job_id, rows, crops, JSONB_COLS)

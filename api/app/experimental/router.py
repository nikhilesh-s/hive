"""EXPERIMENTAL routes. All internal-key protected; nothing here reads or
writes the reviewed corpus except the read-only search over it that the
paper-QA endpoint shares with /search."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..auth import require_internal_key
from ..config import settings
from ..db import (
    count_live_rows,
    delete_live_job,
    fetch_live_crop,
    fetch_live_record,
    list_ingest_jobs,
    list_live_papers,
)
from ..limiter import limiter
from ..record_detail import build_record_detail
from ..schemas import RecordDetail, SearchRequest, SearchResponse
from ..search_service import execute_search
from ..valency import ValencyClient, ValencyError
from . import ingest
from .ask import answer as ask_answer

logger = logging.getLogger("hive.experimental")

router = APIRouter(prefix="/experimental", dependencies=[Depends(require_internal_key)],
                   tags=["experimental"])


class PaperSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    limit: int = Field(default=8, ge=1, le=25)
    source: str = Field(default="auto", pattern="^(auto|valency|pmc)$")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    doi: str | None = Field(default=None, max_length=200)
    include_live: bool = True


class IngestRequest(BaseModel):
    doi: str = Field(min_length=6, max_length=200)
    force: bool = False


@router.get("/status")
async def status():
    ok, why = ingest.backend_ready()
    try:
        live = await count_live_rows()
    except Exception:
        live = None
    return {
        "experimental": True,
        "model_backend_ready": ok, "model_backend": why,
        "valency_configured": bool(settings.valency_api_token),
        "ingest_db_configured": bool(settings.db_ingest_url),
        "live_rows": live,
        "jobs": [j.to_dict() for j in list(ingest.JOBS.values())[-10:]],
    }


@router.post("/papers/search")
async def papers_search(body: PaperSearchRequest):
    """Discovery: Valency Bond (semantic, when a token exists) with PubMed
    Central open-access search as the always-available fallback."""
    results: list[dict] = []
    used: list[str] = []
    errors: dict[str, str] = {}
    if body.source in ("auto", "valency") and settings.valency_api_token:
        try:
            client = ValencyClient(settings.valency_api_token, settings.valency_mcp_url)
            results += client.search_papers(body.query, body.limit)
            used.append("valency")
        except ValencyError as e:
            errors["valency"] = str(e)[:300]
        except Exception as e:  # network etc.
            errors["valency"] = f"{type(e).__name__}: {e}"[:300]
    elif body.source == "valency":
        errors["valency"] = "VALENCY_API_TOKEN not configured"
    if body.source in ("auto", "pmc") and (body.source == "pmc" or len(results) < body.limit):
        try:
            results += ingest.fulltext.pmc_search(body.query, body.limit)
            used.append("pmc")
        except Exception as e:
            errors["pmc"] = f"{type(e).__name__}: {e}"[:300]
    seen, deduped = set(), []
    for r in results:
        key = r.get("doi") or r.get("title")
        if key and key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return {"query": body.query, "results": deduped[: body.limit], "sources_used": used, "errors": errors}


@router.post("/ingest")
@limiter.limit("6/minute")
async def ingest_start(request: Request, body: IngestRequest, background: BackgroundTasks):
    ok, why = ingest.backend_ready()
    if not ok:
        raise HTTPException(503, why)
    try:
        job = ingest.start_job(body.doi)
    except ValueError:
        raise HTTPException(400, "Not a DOI")
    background.add_task(ingest.run_job, job.job_id)
    return job.to_dict()


@router.get("/ingest")
async def ingest_list():
    mem = [j.to_dict() for j in ingest.JOBS.values()]
    if settings.db_ingest_url:
        try:
            stored = await list_ingest_jobs(20)
            ids = {j["job_id"] for j in mem}
            mem += [j for j in stored if j["job_id"] not in ids]
        except Exception:
            pass
    return {"jobs": sorted(mem, key=lambda j: j["created_at"], reverse=True)[:20]}


@router.get("/live/papers")
async def live_papers():
    """Papers already in the live tier (DOI, counts), newest first."""
    try:
        return {"papers": await list_live_papers()}
    except Exception as e:
        logger.warning("live papers listing failed: %s", e)
        return {"papers": [], "error": "live tier unavailable"}


@router.get("/ingest/{job_id}")
async def ingest_status(job_id: str):
    job = ingest.JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")
    return job.to_dict()


@router.delete("/ingest/{job_id}")
async def ingest_delete(job_id: str):
    """Wipe one live extraction (rows + crops). Demo reset; never touches the reviewed corpus."""
    n = await delete_live_job(job_id)
    ingest.JOBS.pop(job_id, None)
    return {"job_id": job_id, "rows_deleted": n}


@router.post("/search", response_model=SearchResponse)
@limiter.limit(settings.search_rate_limit)
async def live_search(request: Request, body: SearchRequest):
    """Same deterministic parser, same sql_guard, same read-only role — over
    the live, unreviewed table only."""
    return await execute_search(body.query, body.limit, table_name=settings.live_table_name)


@router.get("/records/{record_id}", response_model=RecordDetail)
async def live_record(record_id: int):
    row = await fetch_live_record(record_id)
    if row is None:
        raise HTTPException(404, "Record not found")
    return build_record_detail(row)


@router.get("/records/{record_id}/crop")
async def live_crop(record_id: int):
    row = await fetch_live_record(record_id)
    if row is None or not row.get("image_crop_ref"):
        raise HTTPException(404, "No figure crop for this record")
    png = await fetch_live_crop(row.get("job_id"), str(row["image_crop_ref"]).rsplit("/", 1)[-1])
    if not png:
        raise HTTPException(404, "Crop not available")
    return Response(content=png, media_type="image/png")


@router.post("/ask")
@limiter.limit("10/minute")
async def ask(request: Request, body: AskRequest):
    """Grounded paper QA: deterministic retrieval over the reviewed corpus
    (+ live tier), then a model answer that may only cite the shown records."""
    return await ask_answer(body.question, body.doi or None, body.include_live)

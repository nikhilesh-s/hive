"""
Internal API - called only by web/'s server-side `/api/search` route
handler (Next.js BFF), never directly by a browser or a third party.
Free to change shape as the frontend's needs change.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..auth import require_internal_key
from ..config import settings
from ..db import fetch_record_by_id, get_supabase, insert_feedback
from ..limiter import limiter
from ..record_detail import build_record_detail
from ..schemas import (
    FeedbackResponse,
    FeedbackSubmission,
    ProteinSearchResponse,
    RecordDetail,
    SearchRequest,
    SearchResponse,
)
from ..search_service import execute_search

logger = logging.getLogger("hive.api")

router = APIRouter()


@router.get("/health")
def health():
    """Public liveness check - use this for uptime pings, not `/`."""
    return {"status": "ok"}


@router.get("/")
def index():
    try:
        resp = get_supabase().table(settings.table_name).select("*").limit(5).execute()
        return {"connected": True, "sample_rows": resp.data}
    except Exception as e:
        logger.exception("Supabase connectivity check failed")
        raise HTTPException(500, "Supabase query failed") from e


@router.get("/proteins", response_model=ProteinSearchResponse, dependencies=[Depends(require_internal_key)])
def search_protein(
    name: str = Query(..., description="Protein name to search, e.g. p53"),
    limit: int = Query(100, ge=1, le=settings.max_search_limit),
):
    if not name.strip():
        raise HTTPException(400, "name query param cannot be empty")

    try:
        resp = (
            get_supabase().table(settings.table_name)
            .select("*")
            .ilike("target", f"%{name}%")
            .limit(limit)
            .execute()
        )
    except Exception as e:
        logger.exception("Supabase query failed in /proteins")
        raise HTTPException(500, "Supabase query failed") from e

    return {"protein": name, "count": len(resp.data), "results": resp.data}


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(require_internal_key)])
@limiter.limit(settings.search_rate_limit)
async def search(request: Request, body: SearchRequest):
    return await execute_search(body.query, body.limit)


@router.get("/records/{record_id}", response_model=RecordDetail,
            dependencies=[Depends(require_internal_key)])
async def record_detail(record_id: int):
    """Full provenance for ONE record — the 'Why does HiveBlot say this?'
    payload: field-level evidence envelopes (value/status/sources/candidates),
    antibodies with detection-vs-association confidence, per-lane bands, and
    validation state. List responses stay lean; this endpoint carries the
    audit story."""
    try:
        row = await fetch_record_by_id(record_id)
    except Exception as e:
        logger.exception("record detail query failed")
        raise HTTPException(500, "Record lookup failed") from e
    if row is None:
        raise HTTPException(404, "Record not found")
    return build_record_detail(row)


@router.post("/feedback", response_model=FeedbackResponse,
             dependencies=[Depends(require_internal_key)])
@limiter.limit(settings.search_rate_limit)
async def submit_feedback(request: Request, body: FeedbackSubmission):
    """Store researcher feedback (migration 002). The AI extraction is never
    mutated here — corrections are stored beside it, keyed to the record and
    the model_value snapshot, so 'AI claim -> human correction' stays
    auditable and usable as future evaluation labels."""
    err = body.validate_scope()
    if err:
        raise HTTPException(400, err)
    if not settings.db_feedback_url:
        raise HTTPException(503, "Feedback storage is not configured (DB_FEEDBACK_URL)")
    # Column names come from this fixed dict — never from client-supplied keys.
    fields = {
        "app_version": "beta-local",
        "feedback_scope": body.feedback_scope,
        "record_id": body.record_id,
        "paper_id": body.paper_id,
        "figure_label": body.figure_label,
        "search_query": body.search_query,
        "field_name": body.field_name,
        "model_value": body.model_value,
        "feedback_type": body.feedback_type,
        "suggested_value": body.suggested_value,
        "comment": body.comment,
        "ui_location": body.ui_location,
        "session_id": body.session_id,
    }
    try:
        feedback_id = await insert_feedback(fields)
    except Exception as e:
        logger.exception("feedback insert failed")
        raise HTTPException(500, "Failed to store feedback") from e
    return FeedbackResponse(feedback_id=feedback_id)

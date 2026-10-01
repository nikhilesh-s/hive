"""
Internal API - called only by web/'s server-side `/api/search` route
handler (Next.js BFF), never directly by a browser or a third party.
Free to change shape as the frontend's needs change.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi import Path as PathParam

from ..auth import require_internal_key
from ..config import settings
from ..crops import resolve_reviewed_crop
from ..db import (
    clear_search_history,
    delete_search_history,
    fetch_feedback_for_record,
    fetch_record_by_id,
    insert_feedback,
    list_search_history,
    search_targets,
    list_saved_result_records,
    remove_saved_result_records,
    save_result_records,
    saved_results_configured,
    saved_results_status,
    upsert_search_history,
)
from ..limiter import limiter
from ..record_detail import build_record_detail
from ..schemas import (
    FeedbackItem,
    FeedbackResponse,
    FeedbackSubmission,
    ProteinSearchResponse,
    RecordDetail,
    RecordFeedbackResponse,
    SearchRequest,
    SearchResponse,
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchHistorySubmission,
    SavedStatusRequest,
    SavedStatusResponse,
    SaveResultsRequest,
    SaveResultsResponse,
    UnsaveResultsRequest,
    WesternBlotRecord,
)
from ..search_service import execute_search

logger = logging.getLogger("hive.api")

router = APIRouter()


@router.get("/health")
def health():
    """Public liveness check - use this for uptime pings, not `/`."""
    # app_version is also stamped on every feedback row (F-5), so a deploy can
    # be told apart from a demo laptop when reading the export.
    return {"status": "ok", "app_version": settings.app_version}


@router.get("/")
def index():
    """Unauthenticated index. Never returns data: the reviewed corpus is only
    reachable through the authenticated search endpoints below."""
    return {
        "service": "hiveblot-api",
        "health": "/health",
        "search": "POST /search (internal, INTERNAL_API_KEY)",
        "agent_search": "POST /v1/search (AGENT_API_KEYS)",
    }


@router.get("/proteins", response_model=ProteinSearchResponse, dependencies=[Depends(require_internal_key)])
async def search_protein(
    name: str = Query(..., description="Protein name to search, e.g. p53"),
    limit: int = Query(100, ge=1, le=settings.max_search_limit),
):
    if not name.strip():
        raise HTTPException(400, "name query param cannot be empty")
    try:
        rows = await search_targets(name.strip(), limit)
    except Exception as e:
        logger.exception("target lookup failed in /proteins")
        raise HTTPException(500, "Protein lookup failed") from e
    return {"protein": name, "count": len(rows), "results": rows}


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(require_internal_key)])
@limiter.limit(settings.search_rate_limit)
async def search(request: Request, body: SearchRequest):
    return await execute_search(body.query, body.limit)


@router.get("/records/{record_id}", response_model=RecordDetail,
            dependencies=[Depends(require_internal_key)])
async def record_detail(record_id: int = PathParam(ge=1, le=2**63 - 1)):  # bigint; larger was a 500
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


@router.get("/records/{record_id}/crop", dependencies=[Depends(require_internal_key)])
async def record_crop(record_id: int = PathParam(ge=1, le=2**63 - 1)):
    """The record's own panel crop (the actual blot the evidence refers to).

    The path comes from the record's `image_crop_ref` column — never from the
    client — and is additionally required to resolve inside the configured
    crops base directory and be a .png, so a poisoned DB value cannot read
    arbitrary files. 404 (not 500) when the file isn't present: deployments
    without the crop archive degrade to the text-only evidence panel.
    """
    from fastapi.responses import FileResponse

    try:
        row = await fetch_record_by_id(record_id)
    except Exception as e:
        logger.exception("record crop lookup failed")
        raise HTTPException(500, "Record lookup failed") from e
    if row is None or not row.get("image_crop_ref"):
        raise HTTPException(404, "No figure crop for this record")
    crop = resolve_reviewed_crop(row["image_crop_ref"])
    if crop is None:
        raise HTTPException(404, "Crop file not available")
    return FileResponse(crop, media_type="image/png")


@router.get("/records/{record_id}/feedback", response_model=RecordFeedbackResponse,
            dependencies=[Depends(require_internal_key)])
async def record_feedback(record_id: int = PathParam(ge=1, le=2**63 - 1)):
    """Prior researcher feedback for one record (rehydration after refresh).
    Reads hiveblot_feedback only; the Evidence Record is immutable here."""
    if not settings.db_feedback_url:
        raise HTTPException(503, "Feedback storage is not configured (DB_FEEDBACK_URL)")
    srk = None
    try:
        rec = await fetch_record_by_id(record_id)
        srk = (rec or {}).get("stable_row_key")
    except Exception:
        pass  # rehydration still works by serial id alone
    try:
        rows = await fetch_feedback_for_record(record_id, srk)
    except Exception as e:
        logger.exception("feedback fetch failed")
        raise HTTPException(500, "Feedback lookup failed") from e
    items = [FeedbackItem(
        feedback_id=r["feedback_id"],
        stable_row_key=r.get("stable_row_key"),
        created_at=str(r["created_at"]),
        feedback_scope=r["feedback_scope"],
        field_name=r["field_name"],
        model_value=r["model_value"],
        feedback_type=r["feedback_type"],
        suggested_value=r["suggested_value"],
        comment=r["comment"],
        session_id=r["session_id"],
    ) for r in rows]
    return RecordFeedbackResponse(record_id=record_id, items=items)


@router.post("/feedback", response_model=FeedbackResponse,
             dependencies=[Depends(require_internal_key)])
@limiter.limit(settings.feedback_rate_limit)
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
    if body.record_id is not None and body.stable_row_key:
        # Both keys are stored and rehydration matches on them, so they must name the same record.
        try:
            row = await fetch_record_by_id(body.record_id)
        except Exception as e:
            logger.exception("feedback record check failed")
            raise HTTPException(500, "Record lookup failed") from e
        if row is not None and row.get("stable_row_key") and row["stable_row_key"] != body.stable_row_key:
            raise HTTPException(400, "record_id and stable_row_key refer to different records")
    # Column names come from this fixed dict — never from client-supplied keys.
    fields = {
        "app_version": settings.app_version,
        "feedback_scope": body.feedback_scope,
        "record_id": body.record_id,
        "stable_row_key": body.stable_row_key,
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
        "contact": body.contact,
    }
    try:
        feedback_id = await insert_feedback(fields)
    except Exception as e:
        logger.exception("feedback insert failed")
        raise HTTPException(500, "Failed to store feedback") from e
    return FeedbackResponse(feedback_id=feedback_id)


def _history_session_id(session_id: str) -> str:
    value = session_id.strip()
    if not value or value == "ssr":
        raise HTTPException(400, "A browser session id is required")
    return value


def _history_item(row: dict) -> SearchHistoryItem:
    return SearchHistoryItem(
        id=row["id"],
        query=row["query"],
        filters=row.get("filters") or {},
        created_at=row["created_at"].isoformat(),
        last_searched_at=row["last_searched_at"].isoformat(),
    )


@router.get("/history", response_model=SearchHistoryResponse,
            dependencies=[Depends(require_internal_key)])
async def get_search_history(
    session_id: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(50, ge=1, le=100),
):
    try:
        rows = await list_search_history(_history_session_id(session_id), limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("history lookup failed")
        raise HTTPException(500, "History lookup failed") from e
    return SearchHistoryResponse(items=[_history_item(row) for row in rows])


@router.post("/history", response_model=SearchHistoryItem,
             dependencies=[Depends(require_internal_key)])
async def record_search_history(request: Request, body: SearchHistorySubmission):
    session_id = _history_session_id(body.session_id)
    query = body.query.strip()
    normalized_query = " ".join(query.split())
    try:
        row = await upsert_search_history(session_id, query, normalized_query, body.filters)
    except Exception as e:
        logger.exception("history insert failed")
        raise HTTPException(500, "Failed to store search history") from e
    return _history_item(row)


@router.delete("/history/{history_id}", dependencies=[Depends(require_internal_key)])
async def remove_search_history(
    history_id: int = PathParam(ge=1, le=2**63 - 1),
    session_id: str = Query(..., min_length=1, max_length=128),
):
    try:
        await delete_search_history(_history_session_id(session_id), history_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("history delete failed")
        raise HTTPException(500, "Failed to delete history item") from e
    return {"deleted": True}


@router.delete("/history", dependencies=[Depends(require_internal_key)])
async def remove_all_search_history(
    session_id: str = Query(..., min_length=1, max_length=128),
):
    try:
        deleted = await clear_search_history(_history_session_id(session_id))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("history clear failed")
        raise HTTPException(500, "Failed to clear history") from e
    return {"deleted": deleted}


def _saved_session_id(session_id: str) -> str:
    return _history_session_id(session_id)


def _validated_stable_keys(keys: list[str]) -> list[str]:
    out = []
    for key in keys:
        value = key.strip()
        if not value:
            raise HTTPException(400, "stable_row_keys cannot contain blanks")
        out.append(value)
    return list(dict.fromkeys(out))


@router.post("/saved-results/status", response_model=SavedStatusResponse,
             dependencies=[Depends(require_internal_key)])
async def get_saved_results_status(body: SavedStatusRequest):
    if not saved_results_configured():
        raise HTTPException(503, "Saved results storage is not configured")
    session_id = _saved_session_id(body.session_id)
    keys = _validated_stable_keys(body.stable_row_keys)
    try:
        saved = await saved_results_status(session_id, keys)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("saved status lookup failed")
        raise HTTPException(500, "Saved status lookup failed") from e
    return SavedStatusResponse(saved_keys=sorted(saved))


@router.post("/saved-results", response_model=SaveResultsResponse,
             dependencies=[Depends(require_internal_key)])
async def add_saved_results(body: SaveResultsRequest):
    if not saved_results_configured():
        raise HTTPException(503, "Saved results storage is not configured")
    session_id = _saved_session_id(body.session_id)
    records = [
        {"record_id": item.record_id, "stable_row_key": item.stable_row_key.strip()}
        for item in body.records
    ]
    keys = _validated_stable_keys([item["stable_row_key"] for item in records])
    try:
        saved_keys = await save_result_records(session_id, records)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("saved results insert failed")
        raise HTTPException(500, "Failed to save results") from e
    return SaveResultsResponse(saved=True, saved_keys=sorted(set(saved_keys or keys)))


@router.delete("/saved-results", dependencies=[Depends(require_internal_key)])
async def discard_saved_results(body: UnsaveResultsRequest):
    if not saved_results_configured():
        raise HTTPException(503, "Saved results storage is not configured")
    session_id = _saved_session_id(body.session_id)
    keys = _validated_stable_keys(body.stable_row_keys)
    try:
        await remove_saved_result_records(session_id, keys)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("saved results removal failed")
        raise HTTPException(500, "Failed to remove saved results") from e
    return {"saved": False}


@router.get("/saved-results", response_model=list[WesternBlotRecord],
            dependencies=[Depends(require_internal_key)])
async def get_saved_results(session_id: str = Query(..., min_length=1, max_length=128)):
    if not saved_results_configured():
        raise HTTPException(503, "Saved results storage is not configured")
    try:
        rows = await list_saved_result_records(_saved_session_id(session_id))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("saved results listing failed")
        raise HTTPException(500, "Saved results could not be loaded") from e
    for row in rows:
        saved_at = row.get("saved_at")
        if hasattr(saved_at, "isoformat"):
            row["saved_at"] = saved_at.isoformat()
    return rows

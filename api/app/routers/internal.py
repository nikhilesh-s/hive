"""
Internal API - called only by web/'s server-side `/api/search` route
handler (Next.js BFF), never directly by a browser or a third party.
Free to change shape as the frontend's needs change.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..auth import require_internal_key
from ..config import settings
from ..db import supabase
from ..limiter import limiter
from ..schemas import ProteinSearchResponse, SearchRequest, SearchResponse
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
        resp = supabase.table(settings.table_name).select("*").limit(5).execute()
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
            supabase.table(settings.table_name)
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

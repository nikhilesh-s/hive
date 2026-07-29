import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth import require_api_key
from .config import settings
from .db import supabase, run_readonly_query
from .nlp import generate_sql
from .schemas import ProteinSearchResponse, SearchRequest, SearchResponse
from .sql_guard import SQLGuardError, guard_and_limit_sql

logger = logging.getLogger("hive.api")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Hive API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health():
    """Public liveness check - use this for uptime pings, not `/`."""
    return {"status": "ok"}


@app.get("/")
def index():
    try:
        resp = supabase.table(settings.table_name).select("*").limit(5).execute()
        return {"connected": True, "sample_rows": resp.data}
    except Exception as e:
        logger.exception("Supabase connectivity check failed")
        raise HTTPException(500, "Supabase query failed") from e


@app.get("/proteins", response_model=ProteinSearchResponse, dependencies=[Depends(require_api_key)])
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


@app.post("/search", response_model=SearchResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(settings.search_rate_limit)
async def search(request: Request, body: SearchRequest):
    try:
        raw_sql = generate_sql(body.query)
    except Exception as e:
        logger.exception("SQL generation failed")
        raise HTTPException(502, "Failed to generate search query") from e

    try:
        safe_sql = guard_and_limit_sql(raw_sql, body.limit)
    except SQLGuardError as e:
        logger.warning("Rejected generated SQL: %s | sql=%s", e, raw_sql)
        raise HTTPException(400, str(e)) from e

    try:
        results = await run_readonly_query(safe_sql)
    except Exception as e:
        logger.exception("Read-only query execution failed")
        raise HTTPException(500, "Search query failed") from e

    return {
        "question": body.query,
        "generated_sql": safe_sql,
        "count": len(results),
        "results": results,
    }

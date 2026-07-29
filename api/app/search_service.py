"""
The one search pipeline (NL -> SQL -> guard -> execute), shared by the
internal endpoint (used by web/'s BFF route) and the external endpoint
(used by agents). Both need to go through the exact same sql_guard +
scoped-read-only-role path - duplicating this per-router would risk one
copy drifting and losing the sandboxing.
"""

import logging

from fastapi import HTTPException

from .db import run_readonly_query
from .nlp import generate_sql
from .schemas import SearchResponse
from .sql_guard import SQLGuardError, guard_and_limit_sql

logger = logging.getLogger("hive.api")


async def execute_search(query: str, limit: int) -> SearchResponse:
    try:
        raw_sql = generate_sql(query)
    except Exception as e:
        logger.exception("SQL generation failed")
        raise HTTPException(502, "Failed to generate search query") from e

    try:
        safe_sql = guard_and_limit_sql(raw_sql, limit)
    except SQLGuardError as e:
        logger.warning("Rejected generated SQL: %s | sql=%s", e, raw_sql)
        raise HTTPException(400, str(e)) from e

    try:
        results = await run_readonly_query(safe_sql)
    except Exception as e:
        logger.exception("Read-only query execution failed")
        raise HTTPException(500, "Search query failed") from e

    return SearchResponse(
        question=query,
        generated_sql=safe_sql,
        count=len(results),
        results=results,
    )

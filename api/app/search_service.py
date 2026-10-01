"""
The one search pipeline (NL -> SQL -> guard -> execute), shared by the
internal endpoint (used by web/'s BFF route) and the external endpoint
(used by agents). Both need to go through the exact same sql_guard +
scoped-read-only-role path - duplicating this per-router would risk one
copy drifting and losing the sandboxing.
"""

import logging

from fastapi import HTTPException

from .bio_query import generate_bio_sql
from .config import settings
from .db import run_readonly_query, run_supabase_search
from .experiment_identity import identity_for_row
from .schemas import SearchResponse
from .sql_guard import SQLGuardError, guard_and_limit_sql

logger = logging.getLogger("hive.api")


async def execute_search(query: str, limit: int, table_name: str | None = None) -> SearchResponse:
    """`table_name` is only ever one of the two known tables (reviewed default,
    or the experimental live tier); the guard pins the query to exactly it."""
    # Two generators, one trust model: whichever produces the SQL, it goes
    # through the same sql_guard + read-only role. The deterministic biological
    # parser (bio_query) runs when no OPENAI_KEY is configured — it covers the
    # structured queries researchers actually type (protein / phospho-site /
    # vendor+catalog / cell line / co-IP) with transparent, inspectable SQL.
    try:
        if settings.openai_key and not table_name:
            from .nlp import generate_sql  # lazy: needs an OpenAI client
            raw_sql = generate_sql(query)
        else:
            raw_sql = generate_bio_sql(query, table_name)
    except Exception as e:
        logger.exception("SQL generation failed")
        raise HTTPException(502, "Failed to generate search query") from e

    try:
        safe_sql = guard_and_limit_sql(raw_sql, limit, table_name)
    except SQLGuardError as e:
        logger.warning("Rejected generated SQL: %s | sql=%s", e, raw_sql)
        raise HTTPException(400, str(e)) from e

    try:
        if settings.supabase_url and settings.supabase_api_key:
            results = await run_supabase_search(query, limit, table_name)
        else:
            results = await run_readonly_query(safe_sql)
    except Exception as e:
        logger.exception("Search query execution failed")
        raise HTTPException(500, "Search query failed") from e

    truncated = len(results) >= max(1, min(limit, settings.max_search_limit))
    if truncated:
        # The row cap can cut the last experiment mid-lanes, and a cut time course
        # misstates the design: drop that experiment's partial lanes and say so.
        last = _experiment_key(results[-1])
        results = [r for r in results if _experiment_key(r) != last] or results

    if not table_name:
        for row in results:
            row["experiment_key"], _ = identity_for_row(row)

    return SearchResponse(
        question=query,
        generated_sql=safe_sql,
        count=len(results),
        results=results,
        truncated=truncated,
    )


def _experiment_key(row: dict) -> str:
    srk = row.get("stable_row_key")  # "<experiment>:<lane>"
    return srk.split(":")[0] if srk else f"{row.get('paper_id')}|{row.get('id')}"

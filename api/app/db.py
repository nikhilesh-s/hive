import asyncpg
from supabase import Client, create_client

from .config import settings

# Used only for simple, already-parameterized queries (.ilike(), .limit(), ...)
# via the Supabase query builder - never for the LLM-generated SQL.
# Created lazily: only /proteins and the index page need PostgREST, and the
# /search path must be able to boot and run against DB_READONLY_URL alone
# (e.g. the local dev database from scripts/local_db.py) with no Supabase
# project configured. create_client("") raises at import time otherwise.
_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase

_pool: asyncpg.Pool | None = None


async def _decode_json(conn: asyncpg.Connection) -> None:
    # asyncpg returns json/jsonb as raw strings by default; the response
    # models type these columns as lists/dicts (e.g. anomaly_flags,
    # experiment_flags), so decode them at the driver boundary.
    import json

    for typename in ("json", "jsonb"):
        await conn.set_type_codec(
            typename, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def get_readonly_pool() -> asyncpg.Pool:
    """
    Lazily-created pool for db_readonly_url, which must point at a Postgres
    role granted SELECT on settings.table_name only. This is what actually
    executes the validated, LLM-generated SQL from /search.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.db_readonly_url, min_size=1, max_size=5, init=_decode_json
        )
    return _pool


async def close_readonly_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_readonly_query(sql: str) -> list[dict]:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
        return [dict(row) for row in rows]

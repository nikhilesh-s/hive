import asyncpg
from supabase import Client, create_client

from .config import settings

# Used only for simple, already-parameterized queries (.ilike(), .limit(), ...)
# via the Supabase query builder - never for the LLM-generated SQL.
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

_pool: asyncpg.Pool | None = None


async def get_readonly_pool() -> asyncpg.Pool:
    """
    Lazily-created pool for db_readonly_url, which must point at a Postgres
    role granted SELECT on settings.table_name only. This is what actually
    executes the validated, LLM-generated SQL from /search.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.db_readonly_url, min_size=1, max_size=5)
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

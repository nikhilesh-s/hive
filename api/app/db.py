import asyncpg

from .config import settings

# Every database access in this API goes through one of two asyncpg pools,
# each bound to a scoped Postgres role (hive_readonly / hive_feedback). There
# is deliberately NO PostgREST / anon-key client: migration 004 revoked the
# Supabase client roles from the application tables, so the anon key cannot
# read or write them, and the API must not depend on it either.

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


async def search_targets(name: str, limit: int) -> list[dict]:
    """Parameterized ILIKE on target for /proteins. Runs on the read-only
    role; the pattern is a bound parameter, never interpolated."""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM {settings.table_name} WHERE target ILIKE $1 "
            "ORDER BY id LIMIT $2",
            f"%{name}%", limit,
        )
        return [dict(r) for r in rows]


async def fetch_record_by_id(record_id: int) -> dict | None:
    """One full row (including the provenance/validation JSONB envelopes) for
    the record-detail endpoint. Parameterized; runs on the read-only role."""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM {settings.table_name} WHERE id = $1", record_id
        )
        return dict(row) if row else None


# --- feedback write path (hive_feedback role; migration 002) ---------------
_feedback_pool: asyncpg.Pool | None = None


async def get_feedback_pool() -> asyncpg.Pool:
    global _feedback_pool
    if _feedback_pool is None:
        _feedback_pool = await asyncpg.create_pool(
            settings.db_feedback_url, min_size=1, max_size=3, init=_decode_json
        )
    return _feedback_pool


async def close_feedback_pool() -> None:
    global _feedback_pool
    if _feedback_pool is not None:
        await _feedback_pool.close()
        _feedback_pool = None


async def fetch_feedback_for_record(record_id: int,
                                    stable_row_key: str | None = None) -> list[dict]:
    """All researcher feedback rows for one record (rehydration). Matches the
    volatile serial id OR the reseed-proof stable_row_key (migration 003) —
    a DB reload replaces serial ids, and feedback keyed only to them orphaned
    (manual-beta P0 finding). Read via the feedback role's own SELECT grant;
    the Evidence Record itself is never touched."""
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT feedback_id, created_at, feedback_scope, stable_row_key, "
            "field_name, model_value, feedback_type, suggested_value, comment, "
            "session_id FROM hiveblot_feedback "
            "WHERE record_id = $1 OR (stable_row_key IS NOT NULL AND stable_row_key = $2) "
            "ORDER BY feedback_id",
            record_id, stable_row_key,
        )
        return [dict(r) for r in rows]


async def insert_feedback(fields: dict) -> int:
    """Insert one feedback row; returns feedback_id. Human feedback lives in
    hiveblot_feedback ONLY — the hive_feedback role has no grants on
    western_blot_records, so the AI extraction cannot be overwritten here."""
    pool = await get_feedback_pool()
    cols = list(fields)
    placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 1))
    sql = (
        f'INSERT INTO hiveblot_feedback ({", ".join(cols)}) '
        f"VALUES ({placeholders}) RETURNING feedback_id"
    )
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *[fields[c] for c in cols])


# --- EXPERIMENTAL: live (unreviewed) tier ----------------------------------
_ingest_pool: asyncpg.Pool | None = None


async def get_ingest_pool() -> asyncpg.Pool:
    """hive_ingest role: INSERT/DELETE on western_blot_records_live,
    ingest_jobs, ingest_crops — nothing on the reviewed table."""
    global _ingest_pool
    if _ingest_pool is None:
        if not settings.db_ingest_url:
            raise RuntimeError("DB_INGEST_URL is not configured")
        _ingest_pool = await asyncpg.create_pool(
            settings.db_ingest_url, min_size=1, max_size=2, init=_decode_json
        )
    return _ingest_pool


async def count_live_rows() -> int:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(f"SELECT count(*) FROM {settings.live_table_name}")


async def list_live_papers(limit: int = 50) -> list[dict]:
    """Distinct DOIs in the live tier with row/experiment counts (for
    "open an already-ingested paper" without re-extracting)."""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT doi, max(title) AS title, max(job_id) AS job_id, count(*) AS rows, "
            f"count(DISTINCT split_part(stable_row_key, ':', 1)) AS experiments, max(ingested_at) AS ingested_at "
            f"FROM {settings.live_table_name} GROUP BY doi ORDER BY max(ingested_at) DESC LIMIT $1", limit)
        return [{**dict(r), "ingested_at": r["ingested_at"].isoformat() if r["ingested_at"] else None} for r in rows]


async def fetch_live_record(record_id: int) -> dict | None:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {settings.live_table_name} WHERE id = $1", record_id)
        return dict(row) if row else None


async def fetch_live_crop(job_id: str | None, filename: str) -> bytes | None:
    if not job_id:
        return None
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT png FROM ingest_crops WHERE job_id = $1 AND filename = $2", job_id, filename)


async def list_ingest_jobs(limit: int = 20) -> list[dict]:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ingest_jobs ORDER BY created_at DESC LIMIT $1", limit)
        out = []
        for r in rows:
            d = dict(r)
            for k in ("created_at", "updated_at"):
                d[k] = d[k].isoformat() if d.get(k) else None
            out.append(d)
        return out


async def upsert_ingest_job(job: dict) -> None:
    pool = await get_ingest_pool()
    cols = ("job_id", "doi", "status", "message", "pmcid", "paper_id", "title",
            "candidates", "records", "rows", "backend", "error")
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols[1:])
    async with pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO ingest_jobs ({', '.join(cols)}, updated_at) "
            f"VALUES ({', '.join(f'${i}' for i in range(1, len(cols) + 1))}, now()) "
            f"ON CONFLICT (job_id) DO UPDATE SET {sets}, updated_at = now()",
            *[job.get(c) for c in cols])


async def replace_live_rows(doi: str, job_id: str, rows: list[dict],
                            crops: dict[str, bytes], jsonb_cols: set[str]) -> int:
    """Delete this DOI's previous live rows/crops, insert the new ones (one
    transaction). Unknown keys are dropped against the live table's columns."""
    import json

    pool = await get_ingest_pool()
    table = settings.live_table_name
    async with pool.acquire() as conn:
        cols = {r["column_name"] for r in await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = $1", table)}
        async with conn.transaction():
            old_jobs = [r["job_id"] for r in await conn.fetch(
                f"SELECT DISTINCT job_id FROM {table} WHERE doi = $1", doi)]
            await conn.execute(f"DELETE FROM {table} WHERE doi = $1", doi)
            for oj in old_jobs:
                if oj and oj != job_id:
                    await conn.execute("DELETE FROM ingest_crops WHERE job_id = $1", oj)
            # hive_ingest has INSERT/DELETE but deliberately no UPDATE, so no
            # ON CONFLICT DO UPDATE: clear this job's crops, then insert.
            await conn.execute("DELETE FROM ingest_crops WHERE job_id = $1", job_id)
            for name, png in crops.items():
                await conn.execute(
                    "INSERT INTO ingest_crops (job_id, filename, png) VALUES ($1, $2, $3)", job_id, name, png)
            n = 0
            for row in rows:
                data = {k: v for k, v in row.items() if k in cols and k != "id"}
                keys = list(data)
                vals, casts = [], []
                for i, k in enumerate(keys, 1):
                    v = data[k]
                    if k in jsonb_cols and v is not None:
                        vals.append(json.dumps(v))
                        casts.append(f"${i}::jsonb")
                    else:
                        vals.append(v)
                        casts.append(f"${i}")
                await conn.execute(
                    f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join(casts)})", *vals)
                n += 1
            return n


async def delete_live_job(job_id: str) -> int:
    pool = await get_ingest_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            res = await conn.execute(f"DELETE FROM {settings.live_table_name} WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM ingest_crops WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM ingest_jobs WHERE job_id = $1", job_id)
            return int(res.split()[-1]) if res else 0

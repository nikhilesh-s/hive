import asyncpg
import asyncio
import json
import logging
import re
from uuid import UUID
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import settings

logger = logging.getLogger("hive.api")

# Every database access in this API goes through one of two asyncpg pools,
# each bound to a scoped Postgres role (hive_readonly / hive_feedback). There
# is deliberately NO PostgREST / anon-key client: migration 004 revoked the
# Supabase client roles from the application tables, so the anon key cannot
# read or write them, and the API must not depend on it either.

_pool: asyncpg.Pool | None = None

TERM_COLUMNS = (
    "target", "raw_target_name", "canonical_target", "uniprot_id", "cell_line",
    "sample", "treatment_name", "treatment_context", "antibody_target",
    "modification_label", "antibody_catalog_number", "doi",
)


def _use_supabase_rest() -> bool:
    return bool(settings.supabase_url and settings.supabase_api_key)


def _rest_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_api_key,
        "Authorization": f"Bearer {settings.supabase_api_key}",
        "Accept": "application/json",
    }


def _clean_like(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9/+.\- ]", "", value).strip()


def _supabase_get(table: str, params: list[tuple[str, str]]) -> list[dict]:
    base = settings.supabase_url.rstrip("/")
    if not base.endswith("/rest/v1"):
        base = f"{base}/rest/v1"
    url = f"{base}/{table}?{urlencode(params)}"
    req = Request(url, headers=_rest_headers())
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _supabase_write(
    method: str,
    table: str,
    params: list[tuple[str, str]],
    payload: object | None = None,
    prefer: str = "return=representation",
) -> list[dict]:
    base = settings.supabase_url.rstrip("/")
    if not base.endswith("/rest/v1"):
        base = f"{base}/rest/v1"
    url = f"{base}/{table}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        **_rest_headers(),
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else []


def _pg_in(values: list[object]) -> str:
    return f"in.({','.join(str(v) for v in values)})"


def _norm_doi(value: object) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _norm_query(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _iso(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value else None)


def saved_results_configured() -> bool:
    return bool(settings.db_feedback_url or _use_supabase_rest())


async def run_supabase_search(query: str, limit: int, table_name: str | None = None) -> list[dict]:
    table = table_name or settings.table_name
    params: list[tuple[str, str]] = [
        ("select", "*"),
        ("order", "needs_review.asc,id.asc"),
        ("limit", str(limit)),
    ]
    tokens = [_clean_like(t) for t in re.split(r"[\s,;]+", query) if len(t.strip()) >= 2]
    for token in [t for t in tokens if t]:
        ors = ",".join(f"{col}.ilike.*{token}*" for col in TERM_COLUMNS)
        params.append(("or", f"({ors})"))
    return await asyncio.to_thread(_supabase_get, table, params)


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


INGEST_PAPER_FLAG_COLUMNS = (
    "doi",
    "access_status",
    "access_url",
    "access_source",
    "access_checked_at",
    "relevance_status",
    "relevance_score",
    "relevance_reason",
    "relevance_checked_at",
    "discovery_query",
    "updated_at",
    "created_at",
)


def _paper_flags_from_job(job: dict, query: str) -> dict | None:
    flags: dict[str, object] = {}
    access_status = job.get("access_status")
    if access_status:
        flags.update({
            "access_status": access_status,
            "access_url": job.get("access_url"),
            "access_source": job.get("access_source"),
            "access_checked_at": _iso(job.get("access_checked_at")),
        })

    if _norm_query(job.get("discovery_query")) == _norm_query(query):
        relevance_status = job.get("relevance_status")
        if relevance_status:
            flags.update({
                "relevance_status": relevance_status,
                "relevance_score": job.get("relevance_score"),
                "relevance_reason": job.get("relevance_reason"),
                "relevance_checked_at": _iso(job.get("relevance_checked_at")),
            })

    return flags or None


def _job_sort_key(job: dict) -> tuple[bool, str, str]:
    return (
        bool(job.get("access_status") or job.get("relevance_status")),
        str(job.get("updated_at") or ""),
        str(job.get("created_at") or ""),
    )


async def attach_paper_flags(rows: list[dict], query: str) -> list[dict]:
    """Attach DOI-level ingest_jobs access/relevance metadata to reviewed rows.

    Access is paper-level and can be shown for any DOI match. Relevance is
    query-dependent and is only shown when the ingest job's discovery_query
    matches the current search query after simple whitespace/case normalization.
    """
    original_dois = sorted({str(row.get("doi")).strip() for row in rows if str(row.get("doi") or "").strip()})
    dois = sorted({_norm_doi(doi) for doi in original_dois if _norm_doi(doi)})
    if not dois:
        return rows

    try:
        if _use_supabase_rest():
            rest_dois = sorted(set(original_dois + dois))
            jobs = await asyncio.to_thread(
                _supabase_get,
                "ingest_jobs",
                [
                    ("select", ",".join(INGEST_PAPER_FLAG_COLUMNS)),
                    ("doi", _pg_in(rest_dois)),
                ],
            )
        else:
            pool = await get_readonly_pool()
            async with pool.acquire() as conn:
                fetched = await conn.fetch(
                    f"SELECT {', '.join(INGEST_PAPER_FLAG_COLUMNS)} "
                    "FROM ingest_jobs WHERE lower(doi) = ANY($1::text[])",
                    dois,
                )
            jobs = [dict(row) for row in fetched]
    except Exception as e:
        logger.info("Paper flag lookup skipped: %s", e)
        return rows

    by_doi: dict[str, list[dict]] = {}
    for job in jobs:
        doi = _norm_doi(job.get("doi"))
        if doi:
            by_doi.setdefault(doi, []).append(job)

    for matches in by_doi.values():
        matches.sort(key=_job_sort_key, reverse=True)

    for row in rows:
        doi = _norm_doi(row.get("doi"))
        if not doi:
            continue
        for job in by_doi.get(doi, []):
            flags = _paper_flags_from_job(job, query)
            if flags:
                row["paper_flags"] = flags
                break
    return rows


async def search_targets(name: str, limit: int) -> list[dict]:
    """Parameterized ILIKE on target for /proteins. Runs on the read-only
    role; the pattern is a bound parameter, never interpolated."""
    if _use_supabase_rest():
        return await run_supabase_search(name, limit)
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
    if _use_supabase_rest():
        rows = await asyncio.to_thread(
            _supabase_get,
            settings.table_name,
            [("select", "*"), ("id", f"eq.{record_id}"), ("limit", "1")],
        )
        return rows[0] if rows else None
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
            # A row with a stable key matches only by that key: after a reseed the serial id
            # can belong to a different record. Rows without one (legacy) match by id.
            "WHERE (stable_row_key IS NOT NULL AND stable_row_key = $2) "
            "OR (record_id = $1 AND (stable_row_key IS NULL OR $2::text IS NULL)) "
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


async def upsert_search_history(session_id: str, query: str,
                                normalized_query: str, filters: dict,
                                lab_tag: str | None = None,
                                utm_source: str | None = None) -> dict:
    """Record a successfully executed search for one anonymous session.

    The unique key makes repeated searches useful history rather than a list
    of identical events; the original query and most recent timestamp remain
    available for display and re-running.
    """
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO search_history "
            "(session_id, query, normalized_query, filters, last_searched_at, lab_tag, utm_source) "
            "VALUES ($1, $2, $3, $4::jsonb, now(), $5, $6) "
            "ON CONFLICT (session_id, normalized_query, filters) DO UPDATE SET "
            "query = EXCLUDED.query, last_searched_at = now(), "
            "lab_tag = COALESCE(EXCLUDED.lab_tag, search_history.lab_tag), "
            "utm_source = COALESCE(EXCLUDED.utm_source, search_history.utm_source) "
            "RETURNING id, query, filters, created_at, last_searched_at",
            session_id, query, normalized_query, filters, lab_tag, utm_source,
        )
        return dict(row)


async def list_search_history(session_id: str, limit: int = 50) -> list[dict]:
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, query, filters, created_at, last_searched_at "
            "FROM search_history WHERE session_id = $1 "
            "ORDER BY last_searched_at DESC LIMIT $2",
            session_id, limit,
        )
        return [dict(row) for row in rows]


async def delete_search_history(session_id: str, history_id: int) -> bool:
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM search_history WHERE id = $1 AND session_id = $2",
            history_id, session_id,
        )
        return result.endswith("1")


async def clear_search_history(session_id: str) -> int:
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM search_history WHERE session_id = $1", session_id,
        )
        return int(result.split()[-1])


# UUID owners originate only from the trusted BFF header; strings are the
# existing anonymous browser session. Never infer ownership from string shape.
def _saved_owner_scope(owner: str | UUID) -> tuple[str, str, list[tuple[str, str]]]:
    if isinstance(owner, UUID):
        return "user_id", "user_id = $1", [("user_id", f"eq.{owner}")]
    return "session_id", "session_id = $1 AND user_id IS NULL", [
        ("session_id", f"eq.{owner}"), ("user_id", "is.null"),
    ]


# --- Saved results (anonymous browser session or verified account) --------
async def saved_results_status(owner: str | UUID, stable_row_keys: list[str]) -> set[str]:
    _, predicate, filters = _saved_owner_scope(owner)
    if not stable_row_keys:
        return set()
    if _use_supabase_rest() and not settings.db_feedback_url:
        rows = await asyncio.to_thread(
            _supabase_get,
            "saved_results",
            [
                ("select", "stable_row_key"),
                *filters,
                ("stable_row_key", _pg_in(stable_row_keys)),
            ],
        )
        return {row["stable_row_key"] for row in rows}
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT stable_row_key FROM saved_results "
            f"WHERE {predicate} AND stable_row_key = ANY($2::text[])",
            owner, stable_row_keys,
        )
        return {row["stable_row_key"] for row in rows}


async def save_result_records(owner: str | UUID, records: list[dict]) -> list[str]:
    column, _, _ = _saved_owner_scope(owner)
    ids = [r["record_id"] for r in records]
    keys = [r["stable_row_key"] for r in records]
    if _use_supabase_rest():
        valid_rows = await asyncio.to_thread(
            _supabase_get,
            settings.table_name,
            [
                ("select", "id,stable_row_key"),
                ("id", _pg_in(ids)),
                ("stable_row_key", _pg_in(keys)),
            ],
        )
    else:
        readonly = await get_readonly_pool()
        async with readonly.acquire() as conn:
            valid_rows = await conn.fetch(
                f"SELECT id, stable_row_key FROM {settings.table_name} "
                "WHERE id = ANY($1::bigint[]) AND stable_row_key = ANY($2::text[])",
                ids, keys,
            )
    valid = {(row["id"], row["stable_row_key"]) for row in valid_rows}
    requested = {(r["record_id"], r["stable_row_key"]) for r in records}
    if valid != requested:
        raise ValueError("One or more saved records do not exist")

    if _use_supabase_rest() and not settings.db_feedback_url:
        existing = await saved_results_status(owner, keys)
        missing = [record for record in records if record["stable_row_key"] not in existing]
        if missing:
            try:
                await asyncio.to_thread(
                    _supabase_write,
                    "POST",
                    "saved_results",
                    [],
                    [
                        {
                            column: str(owner),
                            "record_id": record["record_id"],
                            "stable_row_key": record["stable_row_key"],
                        }
                        for record in missing
                    ],
                )
            except HTTPError as exc:
                if exc.code != 409:
                    raise
                after_insert = await saved_results_status(owner, keys)
                if not set(keys).issubset(after_insert):
                    raise
        return keys

    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for record in records:
                await conn.execute(
                    f"INSERT INTO saved_results ({column}, record_id, stable_row_key) "
                    "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    owner, record["record_id"], record["stable_row_key"],
                )
    return keys


async def remove_saved_result_records(owner: str | UUID, stable_row_keys: list[str]) -> int:
    _, predicate, filters = _saved_owner_scope(owner)
    if _use_supabase_rest() and not settings.db_feedback_url:
        await asyncio.to_thread(
            _supabase_write,
            "DELETE",
            "saved_results",
            [
                *filters,
                ("stable_row_key", _pg_in(stable_row_keys)),
            ],
        )
        return 0
    pool = await get_feedback_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM saved_results "
            f"WHERE {predicate} AND stable_row_key = ANY($2::text[])",
            owner, stable_row_keys,
        )
        return int(result.split()[-1])


async def list_saved_result_records(owner: str | UUID) -> list[dict]:
    _, predicate, filters = _saved_owner_scope(owner)
    if _use_supabase_rest() and not settings.db_feedback_url:
        saved = await asyncio.to_thread(
            _supabase_get,
            "saved_results",
            [
                ("select", "record_id,stable_row_key,saved_at"),
                *filters,
                ("order", "saved_at.desc,record_id.asc"),
            ],
        )
    else:
        pool = await get_feedback_pool()
        async with pool.acquire() as conn:
            saved = await conn.fetch(
                "SELECT record_id, stable_row_key, saved_at FROM saved_results "
                f"WHERE {predicate} ORDER BY saved_at DESC, record_id",
                owner,
            )
    if not saved:
        return []
    saved_by_id = {row["record_id"]: row for row in saved}
    if _use_supabase_rest():
        rows = await asyncio.to_thread(
            _supabase_get,
            settings.table_name,
            [("select", "*"), ("id", _pg_in(list(saved_by_id)))],
        )
    else:
        readonly = await get_readonly_pool()
        async with readonly.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM {settings.table_name} WHERE id = ANY($1::bigint[])",
                list(saved_by_id),
            )
    by_id = {row["id"]: dict(row) for row in rows}
    out = []
    for saved_row in saved:
        record = by_id.get(saved_row["record_id"])
        if not record:
            continue
        record["saved_at"] = saved_row["saved_at"]
        out.append(record)
    return out


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


async def close_ingest_pool() -> None:
    global _ingest_pool
    if _ingest_pool is not None:
        await _ingest_pool.close()
        _ingest_pool = None


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
            for k in ("created_at", "updated_at", "access_checked_at", "relevance_checked_at"):
                d[k] = d[k].isoformat() if d.get(k) else None
            out.append(d)
        return out


async def upsert_ingest_job(job: dict) -> None:
    pool = await get_ingest_pool()
    cols = (
        "job_id", "doi", "status", "message", "pmcid", "pmid", "paper_id", "title",
        "abstract", "authors", "journal", "publication_year", "metadata_source",
        "discovery_query", "access_status", "access_url", "access_source",
        "access_checked_at", "relevance_status", "relevance_score",
        "relevance_reason", "relevance_checked_at",
        "candidates", "records", "rows", "backend", "error",
    )
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
    transaction). Unknown keys are dropped against the live table's columns.
    JSONB values are passed as Python objects: the pool's json codec encodes
    them exactly once (a manual json.dumps here would store a JSON *string*)."""
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
                    vals.append(v)
                    casts.append(f"${i}::jsonb" if k in jsonb_cols and v is not None else f"${i}")
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

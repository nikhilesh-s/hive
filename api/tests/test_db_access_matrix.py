"""Database access matrix for the application tables (migration 008).

Runs the canonical SQL chain (base schema -> 001 -> 002 -> 003 -> 004) on a
scratch Postgres and then checks, role by role, what each one can do. This is
the security boundary behind sql_guard: even a query that slips past the AST
guard can only do what the connecting role is allowed to do.

Needs a real Postgres. Skipped unless HIVE_DB_TEST_URL points at a SUPERUSER
connection to a throwaway database, e.g. the embedded local one:

    .venv/bin/python scripts/local_db.py up
    HIVE_DB_TEST_URL=$(.venv/bin/python scripts/local_db.py test-url) \
        .venv/bin/python -m pytest api/tests/test_db_access_matrix.py -v

The Supabase client roles (anon / authenticated) do not exist on a plain
Postgres, so the test creates them (NOLOGIN) before applying the chain.
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DB_URL = os.environ.get("HIVE_DB_TEST_URL", "")

pytestmark = pytest.mark.skipif(not DB_URL, reason="HIVE_DB_TEST_URL not set")

CHAIN = [
    "api/db/schema.sql",
    "migrations/001_evidence_record.sql",
    "migrations/002_feedback.sql",
    "migrations/003_stable_row_key.sql",
    "migrations/004_secure_public_tables.sql",
    "migrations/005_experimental_live_tables.sql",   # EXPERIMENTAL live tier
    "migrations/006_feedback_contact.sql",           # F-5 opt-in contact column
    "migrations/007_search_history.sql",
    "migrations/008_saved_results.sql",
    "migrations/011_ingest_jobs_paper_access_relevance.sql",
]
LIVE_SQL = ("INSERT INTO western_blot_records_live (paper_id, target, job_id) "
            "VALUES ('live-paper', 'STAT3', 'job1')")

RECORD_SQL = ("INSERT INTO western_blot_records (paper_id, target) "
              "VALUES ('test-paper', 'STAT3')")
FEEDBACK_SQL = ("INSERT INTO hiveblot_feedback (feedback_scope, comment) "
                "VALUES ('ui', 'matrix') RETURNING feedback_id")


def _run(coro):
    return asyncio.run(coro)


async def _apply_chain(conn):
    import asyncpg

    for role in ("anon", "authenticated"):
        await conn.execute(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') "
            f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$;")
    for t in ("ingest_crops", "ingest_jobs", "western_blot_records_live"):
        await conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    await conn.execute("DROP TABLE IF EXISTS hiveblot_feedback CASCADE")
    await conn.execute("DROP TABLE IF EXISTS search_history CASCADE")
    await conn.execute("DROP TABLE IF EXISTS saved_results CASCADE")
    await conn.execute("DROP TABLE IF EXISTS western_blot_records CASCADE")
    for rel in CHAIN:
        sql = (REPO / rel).read_text()
        try:
            await conn.execute(sql)
        except asyncpg.PostgresError as e:
            if "pg_trgm" not in str(e):
                raise
            # Local pgserver has no pg_trgm; the trigram index is a latency
            # optimisation, not part of the access model (same as local_db.py).
            sql = re.sub(r"create extension if not exists pg_trgm;", "", sql)
            sql = re.sub(r"create index if not exists idx_western_blot_records_target[^;]+;", "", sql)
            await conn.execute(sql)
    # One reviewed-looking row so SELECT checks return something, and one
    # feedback row so hive_feedback's SELECT policy is exercised on data.
    await conn.execute(RECORD_SQL)
    await conn.execute("INSERT INTO hiveblot_feedback (feedback_scope, comment) VALUES ('ui', 'seed')")


async def _as_role(conn, role: str, sql: str) -> str:
    """Run one statement as `role` inside a savepoint. Returns 'ok', or the
    SQLSTATE class of the failure ('42501' = insufficient privilege)."""
    import asyncpg

    tr = conn.transaction()
    await tr.start()
    try:
        await conn.execute(f"SET LOCAL ROLE {role}")
        await conn.execute(sql)
        return "ok"
    except asyncpg.PostgresError as e:
        return e.sqlstate
    finally:
        await tr.rollback()


async def _rows_as_role(conn, role: str, sql: str) -> int:
    tr = conn.transaction()
    await tr.start()
    try:
        await conn.execute(f"SET LOCAL ROLE {role}")
        return len(await conn.fetch(sql))
    finally:
        await tr.rollback()


@pytest.fixture(scope="module")
def conn():
    import asyncpg

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    c = loop.run_until_complete(asyncpg.connect(DB_URL))
    loop.run_until_complete(_apply_chain(c))
    yield c
    loop.run_until_complete(c.close())
    loop.close()


def run(conn, coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_rls_enabled_on_both_tables(conn):
    rows = run(conn, conn.fetch(
        "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN "
        "('western_blot_records', 'hiveblot_feedback', 'search_history', 'saved_results')"))
    assert {r["relname"]: r["relrowsecurity"] for r in rows} == {
        "western_blot_records": True, "hiveblot_feedback": True, "search_history": True,
        "saved_results": True}


def test_policies_target_explicit_roles(conn):
    rows = run(conn, conn.fetch(
        "SELECT tablename, policyname, roles::text, cmd FROM pg_policies "
        "WHERE schemaname='public' ORDER BY policyname"))
    got = {(r["tablename"], r["policyname"], r["roles"], r["cmd"]) for r in rows}
    assert got >= {
        ("western_blot_records", "hive_readonly_select_records", "{hive_readonly}", "SELECT"),
        ("hiveblot_feedback", "hive_feedback_insert_feedback", "{hive_feedback}", "INSERT"),
        ("hiveblot_feedback", "hive_feedback_select_feedback", "{hive_feedback}", "SELECT"),
    }


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_public_client_roles_have_no_access(conn, role):
    denied = "42501"
    assert run(conn, _as_role(conn, role, "SELECT * FROM western_blot_records")) == denied
    assert run(conn, _as_role(conn, role, RECORD_SQL)) == denied
    assert run(conn, _as_role(conn, role, "UPDATE western_blot_records SET target='x'")) == denied
    assert run(conn, _as_role(conn, role, "DELETE FROM western_blot_records")) == denied
    assert run(conn, _as_role(conn, role, "SELECT * FROM hiveblot_feedback")) == denied
    assert run(conn, _as_role(conn, role, FEEDBACK_SQL)) == denied
    assert run(conn, _as_role(conn, role, "UPDATE hiveblot_feedback SET comment='x'")) == denied
    assert run(conn, _as_role(conn, role, "DELETE FROM hiveblot_feedback")) == denied
    assert run(conn, _as_role(conn, role, "SELECT * FROM search_history")) == denied
    assert run(conn, _as_role(conn, role, "DELETE FROM search_history")) == denied
    assert run(conn, _as_role(conn, role, "SELECT * FROM saved_results")) == denied
    assert run(conn, _as_role(conn, role, "DELETE FROM saved_results")) == denied


def test_public_client_roles_get_no_future_tables(conn):
    """The default-privilege leak: a table created by the migration role after
    004 must not be readable by anon / authenticated."""
    run(conn, conn.execute("DROP TABLE IF EXISTS matrix_future"))
    run(conn, conn.execute("CREATE TABLE matrix_future (id int)"))
    try:
        for role in ("anon", "authenticated", "hive_readonly"):
            assert run(conn, _as_role(conn, role, "SELECT * FROM matrix_future")) == "42501", role
    finally:
        run(conn, conn.execute("DROP TABLE matrix_future"))


def test_hive_readonly_reads_records_only(conn):
    assert run(conn, _rows_as_role(conn, "hive_readonly", "SELECT * FROM western_blot_records")) == 1
    assert run(conn, _as_role(conn, "hive_readonly", RECORD_SQL)) == "42501"
    assert run(conn, _as_role(conn, "hive_readonly", "UPDATE western_blot_records SET target='x'")) == "42501"
    assert run(conn, _as_role(conn, "hive_readonly", "DELETE FROM western_blot_records")) == "42501"
    assert run(conn, _as_role(conn, "hive_readonly", "SELECT * FROM hiveblot_feedback")) == "42501"
    assert run(conn, _as_role(conn, "hive_readonly", FEEDBACK_SQL)) == "42501"


def test_hive_feedback_is_insert_and_read_only_on_feedback(conn):
    # Exactly what api/app/db.py does: INSERT ... RETURNING, then SELECT for
    # rehydration. Both must work under RLS.
    assert run(conn, _as_role(conn, "hive_feedback", FEEDBACK_SQL)) == "ok"
    assert run(conn, _rows_as_role(conn, "hive_feedback",
               "SELECT feedback_id, comment FROM hiveblot_feedback")) >= 1
    assert run(conn, _as_role(conn, "hive_feedback", "UPDATE hiveblot_feedback SET comment='x'")) == "42501"
    assert run(conn, _as_role(conn, "hive_feedback", "DELETE FROM hiveblot_feedback")) == "42501"
    # and nothing at all on the reviewed corpus
    assert run(conn, _as_role(conn, "hive_feedback", "SELECT * FROM western_blot_records")) == "42501"
    assert run(conn, _as_role(conn, "hive_feedback", RECORD_SQL)) == "42501"
    assert run(conn, _as_role(conn, "hive_feedback", "UPDATE western_blot_records SET target='x'")) == "42501"
    assert run(conn, _as_role(conn, "hive_feedback", "DELETE FROM western_blot_records")) == "42501"


def test_hive_feedback_owns_search_history_access(conn):
    # Each helper call rolls back, so insert and read back in one statement.
    assert run(conn, _rows_as_role(conn, "hive_feedback",
               "INSERT INTO search_history (session_id, query, normalized_query) "
               "VALUES ('session-a', 'STAT3', 'STAT3') RETURNING *")) == 1
    assert run(conn, _as_role(conn, "hive_feedback",
               "UPDATE search_history SET query='pSTAT3' WHERE session_id='session-a'")) == "ok"
    assert run(conn, _as_role(conn, "hive_feedback",
               "DELETE FROM search_history WHERE session_id='session-a'")) == "ok"
    assert run(conn, _as_role(conn, "hive_feedback", "SELECT * FROM western_blot_records")) == "42501"


def test_hive_feedback_owns_saved_results_access(conn):
    async def exercise():
        record = await conn.fetchrow(
            "SELECT id, stable_row_key FROM western_blot_records "
            "WHERE stable_row_key IS NOT NULL LIMIT 1")
        if record is None:
            pytest.skip("fixture has no stable_row_key rows")
        tr = conn.transaction()
        await tr.start()
        try:
            await conn.execute("SET LOCAL ROLE hive_feedback")
            await conn.execute(
                "INSERT INTO saved_results (session_id, record_id, stable_row_key) "
                "VALUES ('session-a', $1, $2) ON CONFLICT DO NOTHING",
                record["id"], record["stable_row_key"])
            await conn.execute(
                "INSERT INTO saved_results (session_id, record_id, stable_row_key) "
                "VALUES ('session-a', $1, $2) ON CONFLICT DO NOTHING",
                record["id"], record["stable_row_key"])
            assert await conn.fetchval("SELECT count(*) FROM saved_results") == 1
            await conn.execute(
                "DELETE FROM saved_results WHERE session_id = 'session-a' "
                "AND stable_row_key = $1", record["stable_row_key"])
            assert await conn.fetchval("SELECT count(*) FROM saved_results") == 0
        finally:
            await tr.rollback()

    run(conn, exercise())


def test_saved_results_grants_do_not_expand_feedback_access(conn):
    assert run(conn, _as_role(conn, "hive_feedback", "SELECT * FROM western_blot_records")) == "42501"
    assert run(conn, _as_role(conn, "hive_feedback", "SELECT * FROM saved_results")) == "ok"


def test_live_tier_matrix(conn):
    """Migration 005: hive_ingest writes ONLY the live tables; hive_readonly
    reads them; client roles get nothing; the reviewed table stays closed."""
    denied = "42501"
    for role in ("anon", "authenticated"):
        assert run(conn, _as_role(conn, role, "SELECT * FROM western_blot_records_live")) == denied
        assert run(conn, _as_role(conn, role, LIVE_SQL)) == denied
        assert run(conn, _as_role(conn, role, "SELECT * FROM ingest_crops")) == denied
    assert run(conn, _as_role(conn, "hive_ingest", LIVE_SQL)) == "ok"
    assert run(conn, _as_role(conn, "hive_ingest", "DELETE FROM western_blot_records_live")) == "ok"
    assert run(conn, _as_role(conn, "hive_ingest", "UPDATE western_blot_records_live SET target='x'")) == denied
    assert run(conn, _as_role(conn, "hive_ingest",
               "INSERT INTO ingest_jobs (job_id, doi, status) VALUES ('j', '10.1000/x', 'queued')")) == "ok"
    assert run(conn, _as_role(conn, "hive_ingest",
               "INSERT INTO ingest_crops (job_id, filename, png) VALUES ('j', 'a.png', '\\x89'::bytea)")) == "ok"
    assert run(conn, _as_role(conn, "hive_ingest", "SELECT * FROM western_blot_records")) == denied
    assert run(conn, _as_role(conn, "hive_ingest", RECORD_SQL)) == denied
    assert run(conn, _as_role(conn, "hive_ingest", "SELECT * FROM hiveblot_feedback")) == denied
    assert run(conn, _as_role(conn, "hive_readonly", "SELECT * FROM western_blot_records_live")) == "ok"
    assert run(conn, _as_role(conn, "hive_readonly", LIVE_SQL)) == denied
    assert run(conn, _as_role(conn, "hive_feedback", "SELECT * FROM western_blot_records_live")) == denied
    rows = run(conn, conn.fetch(
        "SELECT relname, relrowsecurity FROM pg_class WHERE relname IN "
        "('western_blot_records_live', 'ingest_jobs', 'ingest_crops')"))
    assert len(rows) == 3 and all(r["relrowsecurity"] for r in rows)


def test_live_loader_stores_real_jsonb(conn, monkeypatch):
    """replace_live_rows through the API's ingest pool (json codec) must store
    JSONB arrays/objects, not JSON strings (the double-encoding regression)."""
    from app import db as appdb
    from app.config import settings

    monkeypatch.setattr(settings, "db_ingest_url", DB_URL)
    monkeypatch.setattr(settings, "live_table_name", "western_blot_records_live")
    appdb._ingest_pool = None
    rows = [{"paper_id": "10.1000/live", "doi": "10.1000/live", "target": "LC3B", "stable_row_key": "h:1",
             "experiment_flags": ["standard_western"], "provenance": {"target": {"raw_target_name": "LC3B"}},
             "image_crop_ref": "c.png", "job_id": "jsonjob", "review_tier": "live_unreviewed"}]
    n = run(conn, appdb.replace_live_rows("10.1000/live", "jsonjob", rows, {"c.png": b"\x89PNG"},
                                          {"experiment_flags", "provenance"}))
    assert n == 1
    got = run(conn, conn.fetchrow(
        "SELECT jsonb_typeof(experiment_flags) f, jsonb_typeof(provenance) p FROM western_blot_records_live WHERE job_id='jsonjob'"))
    assert (got["f"], got["p"]) == ("array", "object")
    assert run(conn, conn.fetchval("SELECT count(*) FROM ingest_crops WHERE job_id='jsonjob'")) == 1
    # re-load the same DOI replaces rows and crops without needing UPDATE
    n = run(conn, appdb.replace_live_rows("10.1000/live", "jsonjob", rows, {"c.png": b"\x89PNG2"}, {"experiment_flags", "provenance"}))
    assert n == 1 and run(conn, conn.fetchval("SELECT count(*) FROM western_blot_records_live WHERE doi='10.1000/live'")) == 1
    run(conn, appdb.close_ingest_pool())


def test_stored_doi_lookup_reads_exact_completed_paper_without_search_cap(conn, monkeypatch):
    import asyncpg
    from app import db as appdb

    async def exercise():
        async def readonly(connection):
            await appdb._decode_json(connection)
            await connection.execute("SET ROLE hive_readonly")

        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=1, init=readonly)
        async def get_pool(): return pool
        monkeypatch.setattr(appdb, "get_readonly_pool", get_pool)
        try:
            await conn.execute("INSERT INTO ingest_jobs (job_id, doi, status, discovery_query) VALUES "
                               "('w1-done', '10.1000/w1', 'done', 'original query'), "
                               "('w1-pending', '10.1000/pending', 'extracting', NULL)")
            await conn.execute("INSERT INTO western_blot_records_live "
                               "(paper_id, doi, target, job_id, stable_row_key) "
                               "SELECT '10.1000/w1', '10.1000/W1', 'STAT3', 'w1-done', 'w1:' || n "
                               "FROM generate_series(1, 501) n")
            # A prefix match is not the requested DOI; loading rows are not complete.
            await conn.execute("INSERT INTO western_blot_records_live (paper_id, doi, target, job_id) VALUES "
                               "('neighbor', '10.1000/w1-other', 'GAPDH', 'w1-done'), "
                               "('pending', '10.1000/pending', 'STAT3', 'w1-pending')")
            result = await appdb.lookup_live_paper('10.1000/w1')
            assert result['status'] == 'found'
            assert len(result['results']) == 501
            assert result['paper']['experiments'] == 1
            assert result['paper']['discovery_query'] == 'original query'
            assert all(r['doi'] == '10.1000/W1' for r in result['results'])
            assert (await appdb.lookup_live_paper('10.1000/pending'))['status'] == 'pending'
            assert (await appdb.lookup_live_paper('10.1000/missing'))['status'] == 'not_extracted'
        finally:
            await pool.close()
            await conn.execute("DELETE FROM western_blot_records_live WHERE job_id IN ('w1-done', 'w1-pending')")
            await conn.execute("DELETE FROM ingest_jobs WHERE job_id IN ('w1-done', 'w1-pending')")

    run(conn, exercise())


def test_upload_metadata_and_latest_job_use_scoped_roles_without_reviewed_writes(conn, monkeypatch):
    import asyncpg
    from app import db as appdb

    async def exercise():
        async def ingest_role(connection):
            await appdb._decode_json(connection)
            await connection.execute("SET ROLE hive_ingest")
        async def readonly(connection):
            await appdb._decode_json(connection)
            await connection.execute("SET ROLE hive_readonly")
        writer = await asyncpg.create_pool(DB_URL, min_size=1, max_size=1, init=ingest_role)
        reader = await asyncpg.create_pool(DB_URL, min_size=1, max_size=1, init=readonly)
        async def get_writer(): return writer
        async def get_reader(): return reader
        monkeypatch.setattr(appdb, "get_ingest_pool", get_writer)
        monkeypatch.setattr(appdb, "get_readonly_pool", get_reader)
        before = await conn.fetchval("SELECT count(*) FROM western_blot_records")
        try:
            await appdb.upsert_ingest_job({"job_id": "o2-upload", "doi": "10.1000/o2", "status": "queued", "metadata_source": "upload"})
            assert await appdb.latest_ingest_job("10.1000/o2") == {"job_id": "o2-upload", "status": "queued"}
            assert await appdb.latest_ingest_job("10.1000/o2-prefix") is None
            assert (await appdb.lookup_live_paper("10.1000/o2"))["status"] == "pending"
            row = await conn.fetchrow("SELECT metadata_source, access_status FROM ingest_jobs WHERE job_id='o2-upload'")
            assert row["metadata_source"] == "upload" and row["access_status"] is None
            assert await conn.fetchval("SELECT count(*) FROM western_blot_records") == before
            async with writer.acquire() as connection:
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await connection.execute(RECORD_SQL)
        finally:
            await writer.close()
            await reader.close()
            await conn.execute("DELETE FROM ingest_jobs WHERE job_id='o2-upload'")
    run(conn, exercise())


def test_hive_roles_are_not_privileged(conn):
    rows = run(conn, conn.fetch(
        "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
        "FROM pg_roles WHERE rolname IN ('hive_readonly', 'hive_feedback')"))
    assert len(rows) == 2
    for r in rows:
        assert not (r["rolsuper"] or r["rolbypassrls"] or r["rolcreaterole"] or r["rolcreatedb"]), r


def test_down_migration_is_reversible(conn):
    """Apply the .down file, confirm RLS is off and policies are gone, then
    re-apply 004 and confirm the matrix is restored (the module fixture is
    shared, so the table must be left in the secured state)."""
    run(conn, conn.execute((REPO / "migrations/004_secure_public_tables.down.sql").read_text()))
    rows = run(conn, conn.fetch(
        "SELECT relrowsecurity FROM pg_class WHERE relname IN ('western_blot_records', 'hiveblot_feedback')"))
    assert all(not r["relrowsecurity"] for r in rows)
    assert run(conn, conn.fetch("SELECT 1 FROM pg_policies WHERE schemaname='public' "
                                "AND tablename IN ('western_blot_records', 'hiveblot_feedback')")) == []
    run(conn, conn.execute((REPO / "migrations/004_secure_public_tables.sql").read_text()))
    assert run(conn, _rows_as_role(conn, "hive_readonly", "SELECT * FROM western_blot_records")) == 1
    assert run(conn, _as_role(conn, "anon", "SELECT * FROM western_blot_records")) == "42501"

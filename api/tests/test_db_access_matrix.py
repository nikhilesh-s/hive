"""Database access matrix for the two application tables (migration 004).

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
]

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
    await conn.execute("DROP TABLE IF EXISTS hiveblot_feedback CASCADE")
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
        "('western_blot_records', 'hiveblot_feedback')"))
    assert {r["relname"]: r["relrowsecurity"] for r in rows} == {
        "western_blot_records": True, "hiveblot_feedback": True}


def test_policies_target_explicit_roles(conn):
    rows = run(conn, conn.fetch(
        "SELECT tablename, policyname, roles::text, cmd FROM pg_policies "
        "WHERE schemaname='public' ORDER BY policyname"))
    got = {(r["tablename"], r["policyname"], r["roles"], r["cmd"]) for r in rows}
    assert got == {
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
    assert run(conn, conn.fetch("SELECT 1 FROM pg_policies WHERE schemaname='public'")) == []
    run(conn, conn.execute((REPO / "migrations/004_secure_public_tables.sql").read_text()))
    assert run(conn, _rows_as_role(conn, "hive_readonly", "SELECT * FROM western_blot_records")) == 1
    assert run(conn, _as_role(conn, "anon", "SELECT * FROM western_blot_records")) == "42501"

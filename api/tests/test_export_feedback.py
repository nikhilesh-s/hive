"""scripts/export_feedback.py (ticket F-1) against a real Postgres.

Skipped unless HIVE_DB_TEST_URL points at a SUPERUSER connection to a
throwaway database, same as test_db_access_matrix.py:

    .venv/bin/python scripts/local_db.py up
    HIVE_DB_TEST_URL=$(.venv/bin/python scripts/local_db.py test-url) \
        .venv/bin/python -m pytest api/tests/test_export_feedback.py -v
"""
from __future__ import annotations

import asyncio
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DB_URL = os.environ.get("HIVE_DB_TEST_URL", "")

pytestmark = pytest.mark.skipif(not DB_URL, reason="HIVE_DB_TEST_URL not set")

FEEDBACK_MIGRATIONS = [  # only the ones that touch hiveblot_feedback
    "migrations/002_feedback.sql",
    "migrations/006_feedback_contact.sql",
]


async def _seed() -> int:
    import asyncpg

    conn = await asyncpg.connect(DB_URL)
    try:
        for rel in FEEDBACK_MIGRATIONS:
            await conn.execute((REPO / rel).read_text())  # idempotent
        return await conn.fetchval(
            "INSERT INTO hiveblot_feedback (feedback_scope, comment, search_query) "
            "VALUES ('ui', 'export-test', 'stat3') RETURNING feedback_id")
    finally:
        await conn.close()


async def _drop(feedback_id: int) -> None:
    import asyncpg

    conn = await asyncpg.connect(DB_URL)
    try:
        await conn.execute("DELETE FROM hiveblot_feedback WHERE feedback_id = $1", feedback_id)
    finally:
        await conn.close()


def _export(*args: str) -> str:
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "export_feedback.py"), "--dsn", DB_URL, *args],
        capture_output=True, text=True, check=True)
    assert DB_URL not in out.stdout and DB_URL not in out.stderr  # never print the DSN
    return out.stdout


def test_export_csv_header_and_row():
    fid = asyncio.run(_seed())
    try:
        rows = list(csv.DictReader(io.StringIO(_export())))
    finally:
        asyncio.run(_drop(fid))
    assert rows, "export produced no rows"
    for col in ("feedback_id", "created_at", "feedback_scope", "comment", "search_query"):
        assert col in rows[0]
    mine = [r for r in rows if r["feedback_id"] == str(fid)]
    assert len(mine) == 1 and mine[0]["comment"] == "export-test"
    ids = [int(r["feedback_id"]) for r in rows]
    assert ids == sorted(ids), "rows are not ordered by created_at"

"""Export researcher feedback (hiveblot_feedback) as CSV or JSON, ordered by
created_at. This is the only path from "researchers gave feedback" to "we
looked at it" (ticket F-1).

Usage (from repo root):
    DB_FEEDBACK_URL=... .venv/bin/python scripts/export_feedback.py            # CSV to stdout
    DB_FEEDBACK_URL=... .venv/bin/python scripts/export_feedback.py --json
    .venv/bin/python scripts/export_feedback.py --dsn "$(...)" --since 2026-09-09

Reads the DSN from DB_FEEDBACK_URL (or --dsn); the DSN is never printed, not
even in error messages. The hive_feedback role's own SELECT grant is enough.

The output can contain unpublished data pasted by researchers, and (since
migration 006) an opt-in contact address: NEVER commit an export.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import date

TABLE = "hiveblot_feedback"


async def _rows(dsn: str, since: date | None) -> tuple[list[str], list[dict]]:
    import asyncpg

    sql = f"SELECT * FROM {TABLE}"
    args: list[object] = []
    if since is not None:
        sql += " WHERE created_at >= $1"
        args.append(since)
    sql += " ORDER BY created_at, feedback_id"
    conn = await asyncpg.connect(dsn)
    try:
        stmt = await conn.prepare(sql)
        cols = [a.name for a in stmt.get_attributes()]  # header survives an empty export
        return cols, [dict(r) for r in await stmt.fetch(*args)]
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--json", action="store_true", help="JSON array instead of CSV")
    p.add_argument("--since", metavar="YYYY-MM-DD", help="only rows created on/after this date")
    p.add_argument("--dsn", help="Postgres DSN; defaults to $DB_FEEDBACK_URL")
    a = p.parse_args(argv)

    dsn = a.dsn or os.environ.get("DB_FEEDBACK_URL", "")
    if not dsn:
        print("DB_FEEDBACK_URL is not set (or pass --dsn)", file=sys.stderr)
        return 2
    since = date.fromisoformat(a.since) if a.since else None

    try:
        cols, rows = asyncio.run(_rows(dsn, since))
    except Exception as e:
        # Never echo the DSN: some driver errors carry the connection string.
        print(f"feedback export failed: {type(e).__name__}", file=sys.stderr)
        return 1

    if a.json:
        json.dump([{c: _plain(r[c]) for c in cols} for r in rows], sys.stdout,
                  indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: _plain(r[c]) for c in cols})
    print(f"{len(rows)} row(s)", file=sys.stderr)
    return 0


def _plain(v: object) -> object:
    return v if v is None or isinstance(v, (str, int, float, bool)) else str(v)


if __name__ == "__main__":
    raise SystemExit(main())

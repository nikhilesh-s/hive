"""Build an isolated PostgreSQL/PDF fixture. Never connects to hosted Supabase.

Run with the project's Python, from the repository root. Writes only /private/tmp.
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg
import fitz

ROOT = Path(__file__).resolve().parents[1]
SOCKET = "/private/tmp/hiveblot-w1/.localdb"
NAME = "hiveblot_o2"
sys.path[:0] = [str(ROOT / "api"), str(ROOT / "api/tests")]
import conftest  # noqa: E402
from test_db_access_matrix import _apply_chain  # noqa: E402


async def main():
    admin = await asyncpg.connect(f"postgresql://postgres:@/postgres?host={SOCKET}")
    if await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", NAME):
        raise RuntimeError("Fixture database already exists; refusing to overwrite it.")
    await admin.execute(f"CREATE DATABASE {NAME}")
    await admin.close()
    conn = await asyncpg.connect(f"postgresql://postgres:@/{NAME}?host={SOCKET}")
    try:
        await _apply_chain(conn)
        for migration in ("009_saved_results_upsert_index.sql", "010_outreach_attribution_activity_tables.sql"):
            await conn.execute((ROOT / "migrations" / migration).read_text())
        await conn.execute("DELETE FROM western_blot_records WHERE paper_id='test-paper'")
        for kind in ("json", "jsonb"):
            await conn.set_type_codec(kind, schema="pg_catalog", encoder=json.dumps, decoder=json.loads)
        columns = {r["column_name"] for r in await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='western_blot_records'")}
        for source in sorted((ROOT / "eval/demo").glob("*/supabase_rows.json")):
            for row in json.loads(source.read_text()):
                values = {k: v for k, v in row.items() if k in columns and k != "id"}
                await conn.execute(f"INSERT INTO western_blot_records ({','.join(values)}) VALUES "
                    f"({','.join(f'${i}' for i in range(1, len(values)+1))})", *values.values())
        print("Isolated O-2 database ready:", await conn.fetchval("SELECT count(*) FROM western_blot_records"), "reviewed fixture rows")
    finally:
        await conn.close()
    crop = ROOT / "api/crops/10.3892_br.2026.2108/panel_candidates/page_004_cand_0029.png"
    with fitz.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((30, 40), "O-2 TEST FIXTURE: figure excerpt, not a complete research paper")
        page.insert_text((30, 65), "DOI: 10.1000/o2-fixture. Mock responses are not scientific evidence.")
        page.insert_image(fitz.Rect(60, 120, 550, 650), filename=str(crop))
        document.save("/private/tmp/hiveblot-o2-sample.pdf")
    print("Sample PDF: /private/tmp/hiveblot-o2-sample.pdf")


if __name__ == "__main__":
    asyncio.run(main())

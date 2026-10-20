"""Real readonly-role access metadata selection; all fixtures roll back."""
import asyncio
import os
from pathlib import Path

import pytest

from app import db

DB_URL = os.environ.get('HIVE_DB_TEST_URL', '')
pytestmark = pytest.mark.skipif(not DB_URL, reason='HIVE_DB_TEST_URL not set')


def test_stored_access_and_relevance_are_independent_and_missing_stays_unknown(monkeypatch):
    import asyncpg

    async def exercise():
        conn = await asyncpg.connect(DB_URL)
        await db._decode_json(conn)
        # Initialize the existing schema before the rollback-only fixture transaction.
        await conn.execute((Path(__file__).resolve().parents[2] /
            'migrations/011_ingest_jobs_paper_access_relevance.sql').read_text())
        transaction = conn.transaction()
        await transaction.start()

        class Acquire:
            async def __aenter__(self): return conn
            async def __aexit__(self, *args): pass

        class Pool:
            def acquire(self): return Acquire()

        async def pool(): return Pool()
        monkeypatch.setattr(db, 'get_readonly_pool', pool)
        monkeypatch.setattr(db, '_use_supabase_rest', lambda: False)
        try:
            await conn.execute("INSERT INTO ingest_jobs "
                "(job_id,doi,status,access_status,access_source,access_checked_at) VALUES "
                "('w6-open','10.9999/w6-open','done','open_access','test_fixture','2026-10-01'),"
                "('w6-closed','10.9999/w6-closed','done','no_open_copy_found','test_fixture','2026-10-01'),"
                "('w6-invalid','10.9999/w6-invalid','done','unsupported','test_fixture','2026-10-01')")
            await conn.execute("INSERT INTO ingest_jobs "
                "(job_id,doi,status,discovery_query,relevance_status,relevance_checked_at) VALUES "
                "('w6-relevance','10.9999/w6-open','done','STAT3','likely_relevant','2026-10-02')")
            await conn.execute('SET LOCAL ROLE hive_readonly')
            assert await conn.fetchval('SELECT current_user') == 'hive_readonly'
            rows = [{'doi': f'10.9999/w6-{suffix}'} for suffix in ['open', 'closed', 'missing', 'invalid']]
            results = await db.attach_paper_flags(rows, 'STAT3')
            flags = [row['paper_flags'] for row in results]
            assert flags[0]['access_status'] == 'open_access'
            assert flags[0]['relevance_status'] == 'likely_relevant'
            assert flags[1]['access_status'] == 'no_open_copy_found'
            assert flags[2] == {'access_status': 'unknown'}
            assert flags[3] == {'access_status': 'unknown'}
        finally:
            await transaction.rollback()
            await conn.close()

    asyncio.run(exercise())

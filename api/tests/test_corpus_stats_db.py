"""Real PostgreSQL counts; all fixture records are rolled back."""
import asyncio
import os

import pytest

from app import corpus_stats as stats, db

DB_URL = os.environ.get('HIVE_DB_TEST_URL', '')
pytestmark = pytest.mark.skipif(not DB_URL, reason='HIVE_DB_TEST_URL not set')


def test_counts_change_with_database_records(monkeypatch):
    import asyncpg

    async def exercise():
        conn = await asyncpg.connect(DB_URL)
        await db._decode_json(conn)
        transaction = conn.transaction()
        await transaction.start()

        class Acquire:
            async def __aenter__(self): return conn
            async def __aexit__(self, *args): pass

        class Pool:
            def acquire(self): return Acquire()

        async def pool(): return Pool()
        monkeypatch.setattr(stats, 'get_readonly_pool', pool)
        monkeypatch.setattr(stats, '_use_supabase_rest', lambda: False)
        monkeypatch.setattr(stats, '_cached', None)
        monkeypatch.setattr(stats, '_lock', asyncio.Lock())
        monkeypatch.setattr(stats, 'CACHE_SECONDS', 0)
        try:
            await conn.execute('SET LOCAL ROLE hive_readonly')
            assert await conn.fetchval('SELECT current_user') == 'hive_readonly'
            before = await stats.get_corpus_stats()
            for lane in [1, 2]:
                await conn.execute('RESET ROLE')
                await conn.execute("INSERT INTO western_blot_records (paper_id, doi, stable_row_key, target) "
                    "VALUES ('audit-only-count-fixture','10.9999/audit-only',$1,'TEST_FIXTURE')",
                    f'audit-only-count:{lane}')
                await conn.execute('SET LOCAL ROLE hive_readonly')
                after = await stats.get_corpus_stats()
                assert after.reviewed_papers == before.reviewed_papers + 1
                assert after.experiment_groups == before.experiment_groups + 1
                assert after.evidence_rows == before.evidence_rows + lane
        finally:
            await transaction.rollback()
            await conn.close()

    asyncio.run(exercise())

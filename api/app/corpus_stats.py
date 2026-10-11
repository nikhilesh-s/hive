"""Reviewed corpus totals, using the same experiment identity as search."""

import asyncio
import time

from pydantic import BaseModel, Field

from .db import _supabase_get, _use_supabase_rest, get_readonly_pool
from .experiment_identity import identity_for_row


class CorpusStats(BaseModel):
    reviewed_papers: int = Field(ge=0)
    experiment_groups: int = Field(ge=0)
    evidence_rows: int = Field(ge=0)


TABLE = "western_blot_records"
COLUMNS = "id,doi,paper_id,stable_row_key,image_crop_ref,page,target,experiment_type,cell_line,sample,modification_label"
CACHE_SECONDS = 60
_cached: tuple[float, CorpusStats] | None = None
_lock = asyncio.Lock()


def count_rows(rows: list[dict]) -> CorpusStats:
    papers = set()
    experiments = set()
    for row in rows:
        doi = (row.get("doi") or "").strip().lower()
        paper = doi or (row.get("paper_id") or "").strip()
        if paper:
            papers.add(paper)
        experiments.add(identity_for_row(row)[0])
    return CorpusStats(reviewed_papers=len(papers), experiment_groups=len(experiments), evidence_rows=len(rows))


async def _load_rows() -> list[dict]:
    if not _use_supabase_rest():
        pool = await get_readonly_pool()
        async with pool.acquire() as conn:
            return [dict(row) for row in await conn.fetch(f"SELECT {COLUMNS} FROM {TABLE}")]

    rows = []
    last_id = None
    while True:
        params = [("select", COLUMNS), ("order", "id.asc"), ("limit", "1000")]
        if last_id is not None:
            params.append(("id", f"gt.{last_id}"))
        page = await asyncio.to_thread(_supabase_get, TABLE, params)
        if not page:
            return rows
        # Continue even for short pages: the server's row cap may be below ours.
        next_id = page[-1]["id"]
        if last_id is not None and next_id <= last_id:
            raise RuntimeError("Corpus pagination did not advance")
        rows.extend(page)
        last_id = next_id


async def get_corpus_stats() -> CorpusStats:
    global _cached
    async with _lock:
        if _cached is not None and time.monotonic() - _cached[0] < CACHE_SECONDS:
            return _cached[1]
        result = count_rows(await _load_rows())
        _cached = (time.monotonic(), result)
        return result

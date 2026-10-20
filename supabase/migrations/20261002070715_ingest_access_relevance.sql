-- =====================================================================
-- Migration 008: paper metadata, access, and relevance on ingest_jobs
-- =====================================================================
-- MVP decision: ingest_jobs remains the source of truth for paper-level
-- discovery/access/relevance state. The reviewed scientific tables are
-- intentionally untouched.
BEGIN;

ALTER TABLE IF EXISTS public.ingest_jobs
    ADD COLUMN IF NOT EXISTS pmid TEXT,
    ADD COLUMN IF NOT EXISTS abstract TEXT,
    ADD COLUMN IF NOT EXISTS authors TEXT,
    ADD COLUMN IF NOT EXISTS journal TEXT,
    ADD COLUMN IF NOT EXISTS publication_year INTEGER,
    ADD COLUMN IF NOT EXISTS metadata_source TEXT,
    ADD COLUMN IF NOT EXISTS discovery_query TEXT,
    ADD COLUMN IF NOT EXISTS access_status TEXT,
    ADD COLUMN IF NOT EXISTS access_url TEXT,
    ADD COLUMN IF NOT EXISTS access_source TEXT,
    ADD COLUMN IF NOT EXISTS access_checked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS relevance_status TEXT,
    ADD COLUMN IF NOT EXISTS relevance_score REAL,
    ADD COLUMN IF NOT EXISTS relevance_reason TEXT,
    ADD COLUMN IF NOT EXISTS relevance_checked_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ingest_jobs_doi_idx
    ON public.ingest_jobs (doi);

COMMIT;

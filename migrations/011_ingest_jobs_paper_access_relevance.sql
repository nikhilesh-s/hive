-- Paper access/relevance metadata for reviewed-result display.
-- Source of truth remains ingest_jobs; western_blot_records is not changed.
BEGIN;

ALTER TABLE public.ingest_jobs
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

CREATE INDEX IF NOT EXISTS ingest_jobs_discovery_query_idx
  ON public.ingest_jobs (discovery_query);

COMMIT;

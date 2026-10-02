-- Roll back migration 008. This intentionally removes only the columns
-- added for paper metadata/access/relevance and leaves scientific tables alone.
BEGIN;

DROP INDEX IF EXISTS public.ingest_jobs_doi_idx;

ALTER TABLE IF EXISTS public.ingest_jobs
    DROP COLUMN IF EXISTS relevance_checked_at,
    DROP COLUMN IF EXISTS relevance_reason,
    DROP COLUMN IF EXISTS relevance_score,
    DROP COLUMN IF EXISTS relevance_status,
    DROP COLUMN IF EXISTS access_checked_at,
    DROP COLUMN IF EXISTS access_source,
    DROP COLUMN IF EXISTS access_url,
    DROP COLUMN IF EXISTS access_status,
    DROP COLUMN IF EXISTS discovery_query,
    DROP COLUMN IF EXISTS metadata_source,
    DROP COLUMN IF EXISTS publication_year,
    DROP COLUMN IF EXISTS journal,
    DROP COLUMN IF EXISTS authors,
    DROP COLUMN IF EXISTS abstract,
    DROP COLUMN IF EXISTS pmid;

COMMIT;

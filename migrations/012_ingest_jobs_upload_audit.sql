-- O-2 PDF upload audit: who uploaded which file, and when.
-- Set only on upload jobs; operator-only (the API strips these from job lists).
BEGIN;

ALTER TABLE public.ingest_jobs
  ADD COLUMN IF NOT EXISTS uploaded_by UUID,
  ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS pdf_sha256 TEXT;

COMMIT;

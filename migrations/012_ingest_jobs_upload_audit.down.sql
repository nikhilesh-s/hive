BEGIN;

ALTER TABLE public.ingest_jobs
  DROP COLUMN IF EXISTS pdf_sha256,
  DROP COLUMN IF EXISTS uploaded_at,
  DROP COLUMN IF EXISTS uploaded_by;

COMMIT;

-- =====================================================================
-- HiveBlot -- Migration 009: saved results upsert conflict target
-- =====================================================================
-- PostgREST cannot infer a partial unique index for
-- on_conflict=session_id,stable_row_key. Use a normal unique index so browser
-- session saves remain idempotent through Supabase REST upserts.
BEGIN;

DROP INDEX IF EXISTS public.saved_results_unique_session_record;

CREATE UNIQUE INDEX saved_results_unique_session_record
ON public.saved_results (session_id, stable_row_key);

COMMIT;

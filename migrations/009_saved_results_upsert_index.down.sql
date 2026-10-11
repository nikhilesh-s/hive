BEGIN;

DROP INDEX IF EXISTS public.saved_results_unique_session_record;

CREATE UNIQUE INDEX saved_results_unique_session_record
ON public.saved_results (session_id, stable_row_key)
WHERE session_id IS NOT NULL;

COMMIT;

-- =====================================================================
-- HiveBlot -- Migration 008: saved results backend grants
-- =====================================================================
-- The saved_results table already exists. Browser code never accesses it
-- directly; FastAPI uses the existing hive_feedback writer role, with the
-- same session_id value already used by search_history.
BEGIN;

GRANT SELECT, INSERT, DELETE
ON TABLE public.saved_results
TO hive_feedback;

GRANT USAGE, SELECT
ON SEQUENCE public.saved_results_id_seq
TO hive_feedback;

ALTER TABLE public.saved_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS hive_feedback_select_saved_results ON public.saved_results;
CREATE POLICY hive_feedback_select_saved_results
ON public.saved_results
FOR SELECT
TO hive_feedback
USING (true);

DROP POLICY IF EXISTS hive_feedback_insert_saved_results ON public.saved_results;
CREATE POLICY hive_feedback_insert_saved_results
ON public.saved_results
FOR INSERT
TO hive_feedback
WITH CHECK (true);

DROP POLICY IF EXISTS hive_feedback_delete_saved_results ON public.saved_results;
CREATE POLICY hive_feedback_delete_saved_results
ON public.saved_results
FOR DELETE
TO hive_feedback
USING (true);

COMMIT;

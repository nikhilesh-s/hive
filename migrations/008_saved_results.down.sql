BEGIN;

DROP POLICY IF EXISTS hive_feedback_select_saved_results ON public.saved_results;
DROP POLICY IF EXISTS hive_feedback_insert_saved_results ON public.saved_results;
DROP POLICY IF EXISTS hive_feedback_delete_saved_results ON public.saved_results;

REVOKE SELECT, INSERT, DELETE
ON TABLE public.saved_results
FROM hive_feedback;

REVOKE USAGE, SELECT
ON SEQUENCE public.saved_results_id_seq
FROM hive_feedback;

COMMIT;

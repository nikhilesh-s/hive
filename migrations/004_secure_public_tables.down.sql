-- Rollback for 004_secure_public_tables.sql.
-- Drops the policies and disables RLS. It deliberately does NOT re-grant
-- anon / authenticated CRUD or hive_readonly's feedback SELECT: those grants
-- were never part of the application design, only of the platform defaults.
BEGIN;

DROP POLICY IF EXISTS hive_readonly_select_records  ON public.western_blot_records;
DROP POLICY IF EXISTS hive_feedback_insert_feedback ON public.hiveblot_feedback;
DROP POLICY IF EXISTS hive_feedback_select_feedback ON public.hiveblot_feedback;

ALTER TABLE public.western_blot_records DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.hiveblot_feedback    DISABLE ROW LEVEL SECURITY;

COMMIT;

-- =====================================================================
-- HiveBlot beta -- Migration 004: least-privilege access to the public tables
-- =====================================================================
-- WHY (found 2026-09-01, UCSF beta-readiness pass):
--   * Row Level Security was DISABLED on both application tables, and the
--     Supabase platform defaults had granted anon / authenticated full CRUD
--     on them. The publishable anon key could therefore read AND mutate the
--     reviewed corpus and researcher feedback straight through PostgREST,
--     bypassing every FastAPI safeguard (sql_guard, scoped roles).
--   * The base schema's `ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES
--     TO hive_readonly` (and 002's explicit grant) gave the search role SELECT
--     on hiveblot_feedback, which the application never uses.
--
-- END STATE (verified by api/tests/test_db_access_matrix.py):
--   anon / authenticated : NO privileges on either table or their sequences,
--                          and no default privileges on future public tables
--   hive_readonly        : SELECT western_blot_records only  (RLS policy)
--   hive_feedback        : INSERT + SELECT hiveblot_feedback only (RLS
--                          policies) + USAGE on its id sequence. SELECT is a
--                          real requirement: INSERT ... RETURNING feedback_id
--                          and GET /records/{id}/feedback (rehydration) both
--                          read through this role. No UPDATE, no DELETE.
--   postgres / service_role : unchanged. Both are server-only and BYPASSRLS;
--                          neither is ever exposed to a browser.
--
-- Runs on a plain local Postgres too (scripts/local_db.py): the Supabase
-- client roles are handled only when they exist. Idempotent. Touches no data.
-- Rollback: 004_secure_public_tables.down.sql
-- =====================================================================

BEGIN;

-- 1. Row Level Security on both application tables. With RLS on, a role
--    needs BOTH a table grant AND a matching policy to touch a row.
ALTER TABLE public.western_blot_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hiveblot_feedback    ENABLE ROW LEVEL SECURITY;

-- 2. Public client roles (Supabase-managed; absent on a local Postgres).
--    No browser or PostgREST path is part of the application architecture:
--    the web app only ever talks to the FastAPI server, which connects with
--    the two hive_* roles below.
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('REVOKE ALL ON TABLE public.western_blot_records, '
                           'public.hiveblot_feedback FROM %I', r);
            EXECUTE format('REVOKE ALL ON SEQUENCE public.western_blot_records_id_seq, '
                           'public.hiveblot_feedback_feedback_id_seq FROM %I', r);
            -- Tables created later by the migration role must not inherit
            -- CRUD either (this is what made the two tables public).
            EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                           'REVOKE ALL ON TABLES FROM %I', r);
            EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                           'REVOKE ALL ON SEQUENCES FROM %I', r);
        END IF;
    END LOOP;
END
$$;

-- 3. hive_readonly: the reviewed corpus and nothing else. The base schema's
--    default-privilege grant is withdrawn so future tables stop leaking to
--    the search role.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM hive_readonly;
REVOKE ALL ON TABLE public.hiveblot_feedback FROM hive_readonly;
GRANT SELECT ON TABLE public.western_blot_records TO hive_readonly;

-- 4. hive_feedback: exactly the feedback path, re-asserted explicitly.
REVOKE ALL ON TABLE public.western_blot_records FROM hive_feedback;
REVOKE ALL ON TABLE public.hiveblot_feedback FROM hive_feedback;
GRANT INSERT, SELECT ON TABLE public.hiveblot_feedback TO hive_feedback;
GRANT USAGE ON SEQUENCE public.hiveblot_feedback_feedback_id_seq TO hive_feedback;

-- 5. Policies: explicit role targets, one operation each. No policy exists
--    for anon / authenticated on purpose -- they have no grants to begin
--    with, and a permissive policy would only silence the advisor.
DROP POLICY IF EXISTS hive_readonly_select_records ON public.western_blot_records;
CREATE POLICY hive_readonly_select_records ON public.western_blot_records
    FOR SELECT TO hive_readonly USING (true);

DROP POLICY IF EXISTS hive_feedback_insert_feedback ON public.hiveblot_feedback;
CREATE POLICY hive_feedback_insert_feedback ON public.hiveblot_feedback
    FOR INSERT TO hive_feedback WITH CHECK (true);

DROP POLICY IF EXISTS hive_feedback_select_feedback ON public.hiveblot_feedback;
CREATE POLICY hive_feedback_select_feedback ON public.hiveblot_feedback
    FOR SELECT TO hive_feedback USING (true);

COMMIT;

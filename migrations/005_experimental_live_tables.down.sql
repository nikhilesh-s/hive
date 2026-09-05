-- Rollback for 005_experimental_live_tables.sql. Drops ONLY the live /
-- experimental tables and role; the reviewed corpus is untouched.
BEGIN;
DROP TABLE IF EXISTS public.ingest_crops;
DROP TABLE IF EXISTS public.ingest_jobs;
DROP TABLE IF EXISTS public.western_blot_records_live;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hive_ingest') THEN
        REVOKE ALL ON SCHEMA public FROM hive_ingest;
        REVOKE USAGE ON SEQUENCE public.western_blot_records_id_seq FROM hive_ingest;
        DROP ROLE hive_ingest;
    END IF;
END
$$;
COMMIT;

-- =====================================================================
-- Migration 005 (EXPERIMENTAL): live, unreviewed extraction tables
-- =====================================================================
-- The reviewed corpus in western_blot_records is never touched by live
-- ingestion. Papers extracted on demand (demo-day DOI ingestion) land in a
-- SEPARATE table with the same columns plus a review tier, so search can
-- show them with an explicit "live · unreviewed" badge and a wipe is one
-- DELETE. Crops are stored as bytes (the API host has an ephemeral disk).
--
-- Roles: hive_readonly may SELECT the live table (search/detail);
-- hive_ingest (new, login) writes live rows, jobs and crops. Client roles
-- get nothing. RLS is on everywhere, same policy style as migration 004.
-- Additive, idempotent. Rollback: 005_experimental_live_tables.down.sql
BEGIN;

CREATE TABLE IF NOT EXISTS public.western_blot_records_live
    (LIKE public.western_blot_records INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
ALTER TABLE public.western_blot_records_live
    ADD COLUMN IF NOT EXISTS review_tier TEXT NOT NULL DEFAULT 'live_unreviewed',
    ADD COLUMN IF NOT EXISTS job_id TEXT,
    ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_wbr_live_job ON public.western_blot_records_live (job_id);
CREATE INDEX IF NOT EXISTS idx_wbr_live_doi ON public.western_blot_records_live (doi);

CREATE TABLE IF NOT EXISTS public.ingest_jobs (
    job_id      TEXT PRIMARY KEY,
    doi         TEXT NOT NULL,
    status      TEXT NOT NULL,          -- queued|fetching|preprocessing|extracting|loading|done|failed
    message     TEXT,
    pmcid       TEXT,
    paper_id    TEXT,
    title       TEXT,
    candidates  INTEGER,
    records     INTEGER,
    rows        INTEGER,
    backend     TEXT,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ingest_crops (
    job_id      TEXT NOT NULL,
    filename    TEXT NOT NULL,
    png         BYTEA NOT NULL,
    PRIMARY KEY (job_id, filename)
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hive_ingest') THEN
        CREATE ROLE hive_ingest WITH LOGIN;
    END IF;
END
$$;
-- alter role hive_ingest with password '<generated>';  -- out of band, never here

GRANT USAGE ON SCHEMA public TO hive_ingest;
GRANT SELECT ON TABLE public.western_blot_records_live TO hive_readonly;
GRANT SELECT ON TABLE public.ingest_jobs, public.ingest_crops TO hive_readonly;
GRANT SELECT, INSERT, DELETE ON TABLE public.western_blot_records_live TO hive_ingest;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ingest_jobs TO hive_ingest;
GRANT SELECT, INSERT, DELETE ON TABLE public.ingest_crops TO hive_ingest;
GRANT USAGE ON SEQUENCE public.western_blot_records_id_seq TO hive_ingest;  -- LIKE ... INCLUDING DEFAULTS shares it

ALTER TABLE public.western_blot_records_live ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingest_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingest_crops ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS hive_readonly_select_live ON public.western_blot_records_live;
CREATE POLICY hive_readonly_select_live ON public.western_blot_records_live FOR SELECT TO hive_readonly USING (true);
DROP POLICY IF EXISTS hive_readonly_select_jobs ON public.ingest_jobs;
CREATE POLICY hive_readonly_select_jobs ON public.ingest_jobs FOR SELECT TO hive_readonly USING (true);
DROP POLICY IF EXISTS hive_readonly_select_crops ON public.ingest_crops;
CREATE POLICY hive_readonly_select_crops ON public.ingest_crops FOR SELECT TO hive_readonly USING (true);

DROP POLICY IF EXISTS hive_ingest_select_live ON public.western_blot_records_live;
CREATE POLICY hive_ingest_select_live ON public.western_blot_records_live FOR SELECT TO hive_ingest USING (true);
DROP POLICY IF EXISTS hive_ingest_insert_live ON public.western_blot_records_live;
CREATE POLICY hive_ingest_insert_live ON public.western_blot_records_live FOR INSERT TO hive_ingest WITH CHECK (true);
DROP POLICY IF EXISTS hive_ingest_delete_live ON public.western_blot_records_live;
CREATE POLICY hive_ingest_delete_live ON public.western_blot_records_live FOR DELETE TO hive_ingest USING (true);

DROP POLICY IF EXISTS hive_ingest_all_jobs ON public.ingest_jobs;
CREATE POLICY hive_ingest_select_jobs ON public.ingest_jobs FOR SELECT TO hive_ingest USING (true);
DROP POLICY IF EXISTS hive_ingest_insert_jobs ON public.ingest_jobs;
CREATE POLICY hive_ingest_insert_jobs ON public.ingest_jobs FOR INSERT TO hive_ingest WITH CHECK (true);
DROP POLICY IF EXISTS hive_ingest_update_jobs ON public.ingest_jobs;
CREATE POLICY hive_ingest_update_jobs ON public.ingest_jobs FOR UPDATE TO hive_ingest USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS hive_ingest_delete_jobs ON public.ingest_jobs;
CREATE POLICY hive_ingest_delete_jobs ON public.ingest_jobs FOR DELETE TO hive_ingest USING (true);

DROP POLICY IF EXISTS hive_ingest_select_crops ON public.ingest_crops;
CREATE POLICY hive_ingest_select_crops ON public.ingest_crops FOR SELECT TO hive_ingest USING (true);
DROP POLICY IF EXISTS hive_ingest_insert_crops ON public.ingest_crops;
CREATE POLICY hive_ingest_insert_crops ON public.ingest_crops FOR INSERT TO hive_ingest WITH CHECK (true);
DROP POLICY IF EXISTS hive_ingest_delete_crops ON public.ingest_crops;
CREATE POLICY hive_ingest_delete_crops ON public.ingest_crops FOR DELETE TO hive_ingest USING (true);

COMMIT;

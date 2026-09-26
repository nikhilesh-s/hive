-- =====================================================================
-- HiveBlot -- Migration 007: anonymous search history (additive)
-- =====================================================================
-- Authentication is not implemented yet. Until it exists, the browser's
-- existing anonymous session id is the ownership key. The API always filters
-- by that key; authenticated ownership can replace it without changing the
-- history UI contract.
BEGIN;

CREATE TABLE IF NOT EXISTS public.search_history (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL CHECK (length(session_id) BETWEEN 1 AND 128),
    query           TEXT NOT NULL CHECK (length(query) BETWEEN 1 AND 500),
    normalized_query TEXT NOT NULL CHECK (length(normalized_query) BETWEEN 1 AND 500),
    filters         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_searched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, normalized_query, filters)
);

CREATE INDEX IF NOT EXISTS idx_search_history_session_recent
    ON public.search_history (session_id, last_searched_at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.search_history TO hive_feedback;
GRANT USAGE ON SEQUENCE public.search_history_id_seq TO hive_feedback;

ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS hive_feedback_search_history ON public.search_history;
CREATE POLICY hive_feedback_search_history ON public.search_history
    FOR ALL TO hive_feedback USING (true) WITH CHECK (true);

COMMIT;
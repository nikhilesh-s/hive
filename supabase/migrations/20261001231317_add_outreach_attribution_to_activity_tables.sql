-- =====================================================================
-- HiveBlot -- Migration 010: outreach attribution on activity tables
-- =====================================================================
-- Lab tags and UTM source are outreach attribution only. They are stored on
-- browser activity rows, not on scientific evidence rows.
BEGIN;

ALTER TABLE public.search_history
ADD COLUMN IF NOT EXISTS lab_tag text,
ADD COLUMN IF NOT EXISTS utm_source text;

ALTER TABLE public.hiveblot_feedback
ADD COLUMN IF NOT EXISTS lab_tag text,
ADD COLUMN IF NOT EXISTS utm_source text;

CREATE INDEX IF NOT EXISTS search_history_lab_tag_idx
ON public.search_history (lab_tag);

CREATE INDEX IF NOT EXISTS hiveblot_feedback_lab_tag_idx
ON public.hiveblot_feedback (lab_tag);

COMMIT;

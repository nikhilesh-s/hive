BEGIN;

DROP INDEX IF EXISTS public.search_history_lab_tag_idx;
DROP INDEX IF EXISTS public.hiveblot_feedback_lab_tag_idx;

ALTER TABLE public.search_history
DROP COLUMN IF EXISTS lab_tag,
DROP COLUMN IF EXISTS utm_source;

ALTER TABLE public.hiveblot_feedback
DROP COLUMN IF EXISTS lab_tag,
DROP COLUMN IF EXISTS utm_source;

COMMIT;

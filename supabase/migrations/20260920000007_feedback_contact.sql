-- =====================================================================
-- Migration 006: optional researcher contact on feedback (additive)
-- =====================================================================
-- Ticket F-5. session_id is a browser-local random string, so a researcher
-- who asks to be followed up about a comment cannot be reached. This adds ONE
-- nullable column, written only when the person ticked an explicit, unchecked
-- opt-in that states the purpose.
--
-- Privacy rules that live with this column:
--   * It is NEVER returned by the rehydration path (FeedbackItem and the
--     SELECT in db.fetch_feedback_for_record list columns explicitly), so one
--     person's address can never render in another person's browser.
--   * No new role, policy or grant: hive_feedback's existing INSERT/SELECT on
--     hiveblot_feedback covers it (see api/tests/test_db_access_matrix.py).
--   * Exports from scripts/export_feedback.py contain it. Never commit one.
--
-- Run AFTER 002. Idempotent. Rollback: 006_feedback_contact.down.sql.
-- =====================================================================

BEGIN;

ALTER TABLE hiveblot_feedback ADD COLUMN IF NOT EXISTS contact TEXT;

COMMIT;

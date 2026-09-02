# HiveBlot migrations

Additive, idempotent SQL migrations for the Supabase `western_blot_records`
table and related beta tables. **Nothing here drops or retypes an existing
column**, so the deployed `/search` and `/proteins` endpoints and the current
frontend keep working while the new biological Evidence Record fields fill in.

| File | What it does | Reversible |
|------|--------------|------------|
| `001_evidence_record.sql` | Adds all Western Blot Evidence Record columns (protein identity, modification/site, experiment type, treatment, antibody, reported/expected MW, provenance, validation, `needs_review`) + FUTURE (unpopulated) densitometry columns + filter indexes. | `001_evidence_record.down.sql` |
| `002_feedback.sql` | `hiveblot_feedback` table for per-field / missing-field / result / UI / search feedback and human corrections (kept separate from AI extraction) + the insert-only `hive_feedback` role. | `002_feedback.down.sql` |
| `003_stable_row_key.sql` | Reseed-proof `stable_row_key` on both tables (feedback survives a corpus reload). | `003_stable_row_key.down.sql` |
| `004_secure_public_tables.sql` | Enables Row Level Security on both tables, revokes the Supabase `anon` / `authenticated` client roles (and their default privileges), scopes `hive_readonly` to the records table and `hive_feedback` to INSERT+SELECT on feedback, with explicit per-role policies. | `004_secure_public_tables.down.sql` |

## How to apply

Supabase SQL editor, or:

```bash
psql "$SUPABASE_DB_URL" -f api/db/schema.sql
psql "$SUPABASE_DB_URL" -f migrations/001_evidence_record.sql
psql "$SUPABASE_DB_URL" -f migrations/002_feedback.sql
psql "$SUPABASE_DB_URL" -f migrations/003_stable_row_key.sql
psql "$SUPABASE_DB_URL" -f migrations/004_secure_public_tables.sql
# Canonical path is the Supabase CLI (DEPLOYMENT.md §1); this is the fallback.
```

## Notes

- **Backfill:** existing rows get `NULL` in new columns and `needs_review = true`.
  Re-running the ingestion pipeline (`western_blot_miner`) upserts enriched
  values via PostgREST, which auto-exposes the new columns.
- **Idempotency key unchanged:** the existing unique index
  `(paper_id, page, figure_label, target, condition)` is intentionally left
  as-is in this migration. Changing the dedupe key is a separate, reviewed
  decision because it affects how re-ingested rows merge.
- **Densitometry columns are deliberately unpopulated.** They exist only so a
  future deterministic measurement pipeline has somewhere to write. Never
  present a value there as "measured" unless that pipeline actually ran.

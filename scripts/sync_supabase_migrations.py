"""Copy the canonical SQL files into the Supabase CLI migration layout.
Run after editing api/db/schema.sql or migrations/*.sql. The pytest drift
guard (api/tests/test_supabase_migrations_sync.py) enforces equality."""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAIRS = [
    ("api/db/schema.sql", "supabase/migrations/20260701000001_base_schema.sql"),
    ("migrations/001_evidence_record.sql", "supabase/migrations/20260701000002_evidence_record.sql"),
    ("migrations/002_feedback.sql", "supabase/migrations/20260701000003_feedback.sql"),
    ("migrations/003_stable_row_key.sql", "supabase/migrations/20260701000004_stable_row_key.sql"),
    ("migrations/004_secure_public_tables.sql", "supabase/migrations/20260901000005_secure_hiveblot_public_tables.sql"),
    ("migrations/005_experimental_live_tables.sql", "supabase/migrations/20260905000006_experimental_live_tables.sql"),
    ("migrations/006_feedback_contact.sql", "supabase/migrations/20260920000007_feedback_contact.sql"),
    ("migrations/007_search_history.sql", "supabase/migrations/20260925000007_search_history.sql"),
    ("migrations/008_saved_results.sql", "supabase/migrations/20261011000008_saved_results.sql"),
    ("migrations/009_saved_results_upsert_index.sql", "supabase/migrations/20261011000009_saved_results_upsert_index.sql"),
    ("migrations/010_outreach_attribution_activity_tables.sql", "supabase/migrations/20261001231317_add_outreach_attribution_to_activity_tables.sql"),
    ("migrations/011_ingest_jobs_paper_access_relevance.sql", "supabase/migrations/20261011000011_ingest_jobs_paper_access_relevance.sql"),
]

if __name__ == "__main__":
    for src, dst in PAIRS:
        shutil.copyfile(REPO / src, REPO / dst)
        print(f"synced {src} -> {dst}")

"""Drift guard: the Supabase CLI migration copies must stay byte-identical to
the canonical SQL files, so `supabase db push` and the local/psql flow can
never apply different schemas. Fix drift with scripts/sync_supabase_migrations.py."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAIRS = [
    ("api/db/schema.sql", "supabase/migrations/20260701000001_base_schema.sql"),
    ("migrations/001_evidence_record.sql", "supabase/migrations/20260701000002_evidence_record.sql"),
    ("migrations/002_feedback.sql", "supabase/migrations/20260701000003_feedback.sql"),
    ("migrations/003_stable_row_key.sql", "supabase/migrations/20260701000004_stable_row_key.sql"),
    ("migrations/004_secure_public_tables.sql", "supabase/migrations/20260901000005_secure_hiveblot_public_tables.sql"),
    ("migrations/005_experimental_live_tables.sql", "supabase/migrations/20260905000006_experimental_live_tables.sql"),
    ("migrations/006_feedback_contact.sql", "supabase/migrations/20260920000007_feedback_contact.sql"),
    ("migrations/007_search_history.sql", "supabase/migrations/20260925000007_search_history.sql"),
    ("migrations/008_saved_results.sql", "supabase/migrations/20260927000008_saved_results.sql"),
]


def test_supabase_migrations_match_canonical_sql():
    for src, dst in PAIRS:
        a, b = (REPO / src), (REPO / dst)
        assert b.exists(), f"missing CLI copy {dst} — run scripts/sync_supabase_migrations.py"
        assert a.read_bytes() == b.read_bytes(), (
            f"{dst} drifted from {src} — run scripts/sync_supabase_migrations.py")

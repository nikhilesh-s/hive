# W-6 - Paper Access Flag Verification

Date: 2026-10-14. Branch: `w-6-paper-access-flags`.
Split from verified local commit `1e53518`, independently based on main
`f77d311710603e3bea949a432094134195cbc711`. No homepage/count-hook changes
are included, and this branch does not depend on W-5.

## Behavior

Missing or unrecognized access metadata explicitly displays Access unknown.
The stored no_open_copy_found status displays No open copy found / Check
institutional access, rather than asserting Paywalled. No institutional
entitlement or open/closed classification is inferred from absent data.

Access and query-scoped relevance use independent latest applicable checks,
so a relevance-only job cannot hide a recorded access check. Existing reviewed
and experimental search responses attach these flags. Experiment identities,
scientific values, extraction code and quotas are unchanged.

## Evidence and Tests

- Read-only Supabase verification: the reviewed corpus still has 3 papers,
  93 groups and 475 rows. None of its three papers has stored access metadata.
  Unknown remains the only supported label for those missing classifications.
- API: 242 passed / 16 skipped. Missing/failed metadata lookup, independent
  check selection, newer explicit unknown and live-search response coverage.
- Isolated PostgreSQL role matrix plus access integration: 14 passed / 1 skipped.
  Open/no-open-copy/missing/unsupported cases and separate relevance checks
  were read under hive_readonly. Fixture jobs were rolled back. The existing
  metadata migration only initializes the throwaway test schema.
- Frontend: 9 unit tests. Browser: 12 desktop/mobile Search/Research scenarios.
  Open/no-open-copy fixtures exist only in the local test database/browser;
  they do not classify the real papers or write to Supabase.
- TypeScript, lint and production build passed. Miner pytest: 133 passed /
  2 skipped; biology/reconcile/enrichment/extract/pipeline 165/21/18/10/13;
  stable keys 34; densitometry 116; seed benchmark 34/34.

Frontend unit tests and the real-database integration are included in CI.
No Supabase access metadata, reviewed records or schema were changed. The
original checkout, combined audit branch and W-1 worktree are preserved.

## Remaining Limitations

The patch displays stored metadata honestly but does not populate missing
metadata. Source-backed ingestion/review is needed before the three reviewed
papers can show known access labels. Institutional entitlement is outside this
feature. No deployment was performed. Nik reviews and merges the PR; a later
authorized release should check hosted labels with actual stored metadata.

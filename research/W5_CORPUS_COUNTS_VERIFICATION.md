# W-5 - Dynamic Corpus Counts Verification

Date: 2026-10-14. Branch: `w-5-dynamic-corpus-counts`.
Split from verified local commit `1e53518`, independently based on main
`f77d311710603e3bea949a432094134195cbc711`. This ticket contains no access-label
or access-metadata selection changes.

## Behavior

The homepage now uses the same database-backed statistics hook as Search and
About instead of the literal 3/93/475 totals. HTTP 429/502/503/504 and network
failures retry with bounded delays; unmount cancels pending retries.
Authentication and invalid-payload failures are not retried. Persistent
failure displays unavailable rather than invented counts.

The existing `/api/corpus-stats` proxy, internal-key-protected FastAPI
`/corpus-stats`, canonical experiment identity, readonly role and Supabase
tables are reused. No schema or production-record changes are required.

## Evidence and Tests

- Read-only Supabase SQL: 3 reviewed papers, 93 distinct stable-key experiment
  prefixes and 475 records; no missing stable keys. The database totals agree
  with the deployed statistics API and the existing Search/About UI.
- API: 243 passed / 16 skipped. Count changes, short-page REST pagination,
  non-advancing pagination, cache expiry and API failures are covered.
- Isolated PostgreSQL role matrix plus count integration: 14 passed / 1 skipped.
  Two temporary lanes changed the totals under the readonly role; rolled back.
- Frontend: 11 unit tests. Browser: 16 desktop/mobile scenarios, checking
  Home/Search/About with real local API data, changed payloads, transient
  recovery and persistent failure. No access-label behavior is assumed.
- TypeScript, lint and production build passed. Miner pytest: 133 passed /
  2 skipped; biology/reconcile/enrichment/extract/pipeline 165/21/18/10/13;
  stable keys 34; densitometry 116; seed benchmark 34/34.

Frontend unit tests and the real-database integration are included in CI.
Browser fixtures are local; they do not alter Supabase records. The original
checkout, combined audit branch and W-1 worktree are preserved.

## Remaining Limitations

The backend retains its 60-second cache; these are request-time counts, not
Realtime subscriptions. After retry exhaustion the UI honestly reports
unavailable. Nothing has been deployed. Nik reviews and merges the PR, and a
later authorized release should repeat hosted Home/Search/About smoke checks.

# HiveBlot Agent Handoff

> Read this file first. It is the single source of truth for **current project
> state**. Any agent (Claude Code, another Claude session, Codex, a human) should
> be able to read this and immediately know what HiveBlot is, what's done, what's
> blocked, and the exact next task. The **CURRENT STATE** section below is
> authoritative; everything under "Historical session log" is chronology and
> may contain statements that were true only at the time.

## Blind benchmark and PR merges (2026-10-18)

### Main

Main is at `d01f08d` after these merges, all with CI green:
- W-5 (#20)
- W-6 (#21), with review fixes: an `access_checked_at` / `relevance_checked_at` value is required
  before a job can set a label, PostgREST `in.()` values are quoted, and `access_url` must be
  http(s)
- O-3 (#25)
- G-4 (#26)
- W-1 (#19), with review fixes: a LEFT JOIN on live rows, a 30-minute stale-pending guard, and
  ingest's `normalize_doi` shared with the web

Other PRs:
- Copilot #2 is closed.
- B-3 is now draft PR #24 (`feature/saved-results`). It changes `record_builder.py`, so hold it
  until the benchmark is scored.
- O-2 (#22) is moved onto main and stays a draft until Srushti's checks and the security review
  are done.

Deployment:
- **Nothing is deployed.** Render (`3839ee3`) and Vercel (`ffc54a0`) still run the 10-11
  release. R-5 deploys the merged web/API changes, API first, then a smoke test.

### Blind extraction benchmark (P0)

- **Where:** branch `eval/blind-benchmark-2026-10`, worktree `/Users/niks/hive-blind-eval`,
  folder `eval/blind_2026_10/`. Private data lives outside the repo in
  `/Users/niks/hive-blind-eval-private`: the PDFs, the sealed model outputs and the mapper pack.
  Never commit it, and never share `runs/` before scoring.
- **Design:** pre-registered at `38bf0a6`, with amendments A1 and A2 in `DEVIATIONS.md`.
  - The draw is seeded with `20261018` over 15 eligible papers from `eval/candidates.json`.
  - Frozen papers: ranks 1, 2 and 4 (PMC9283986, PMC5328321, PMC4393234), plus rank 8
    (PMC7757890) provisionally until Nik tries a browser download of rank 3 (PMC7948984).
- **System under test:** `western_blot_miner/` at `f77d311`, the production default model
  `claude-opus-5` through the local `claude_cli` backend, concurrency 1, no uploads.
- **Stage 1:** 298 crops were found and 66 sent to the model.
- **Model stage:** started 2026-10-18 for ranks 1, 2 and 4. The log is
  `/Users/niks/hive-blind-eval-private/extract_run1.log`.
- **Scorer:** `score_blind.py` (self-test passes). It aligns on figure, panel, target and lane
  index, and it refuses to run if a sealed output changed.

### Production usage (read-only, 10-18)

- 16 anonymous searches in 8 sessions, no lab tags.
- The last feedback was 9-16.
- No confirmed lab use. See `research/ADOPTION_STATUS_2026-10-18.md` on the benchmark branch.

### Security

The `hive_ingest` DB password was printed in an agent session on 10-18. Rotate it (ticket O-9):
1. `ALTER ROLE`.
2. Update Render `DB_INGEST_URL` and `~/hive_ingest_dsn.txt`.
3. Redeploy.

### Tests run 10-18

- Biology 165/165, densitometry 116/116, reconcile 21/21, extract 10/10, pipeline 13/13.
- Seed benchmark 34/34.
- Benchmark scorer self-test passes.
- PR CI green on #19, #20, #21, #25 and #26.

### Exact next task

1. When the model stage finishes, settle rank 3 or rank 8 and run the 4th paper.
2. Run `run_extraction.py seal`, then commit and push the seal **before** any annotation
   arrives.
3. When Tanvi's sheet and Yashvi's crop map arrive, follow `RUNBOOK.md` steps 5-7.
4. Then do R-5.

## W-6 Paper Access Review (2026-10-14)

Branch: `w-6-paper-access-flags`; worktree `/private/tmp/hiveblot-w6`.
Base/latest commit before task: `f77d311710603e3bea949a432094134195cbc711`.
Split flags-only from local audit `1e53518`. Implementation commit: `6a2de69`.
PR: https://github.com/nikhilesh-s/hive/pull/21. Nik (`nikhilesh-s`) was requested
as reviewer. This follow-up records the PR; it does not change implementation.

Missing/invalid metadata displays Access unknown. No open copy found no longer
asserts Paywalled. Access and query-scoped relevance use independent checks;
reviewed/live search attach the flags. No count-hook/Home changes, extraction,
scientific values, quotas or production-schema changes. User authorized pushing
this dedicated branch and requesting Nik's review; never merge or deploy it.

Read-only Supabase verification: 3 reviewed papers / 93 groups / 475 rows, and
zero reviewed papers with access metadata. Do not fabricate or backfill labels.
API 242 passed / 16 skipped; isolated PostgreSQL matrix+access test 14 passed /
1 skipped; frontend 9 passed; browser 12 desktop/mobile Search/Research cases;
miner 133 passed / 2 skipped; biology/reconcile/enrich/extract/pipeline
165/21/18/10/13; stable keys 34; densitometry 116; seed benchmark 34/34.
TypeScript, lint and production build passed. CI includes the new regressions.

Report: `research/W6_PAPER_ACCESS_VERIFICATION.md`. Local fixtures are not
source-paper access classifications. No Supabase access metadata was modified;
original checkout, combined audit and W-1 preserved. Next: verify PR #21 CI,
await Nik's review and leave unmerged/undeployed. Missing metadata and
institutional entitlement remain limitations; source-backed population and
deployment require separate authorization.

## W-5 Corpus Counts Review (2026-10-14)

Branch: `w-5-dynamic-corpus-counts`; worktree `/private/tmp/hiveblot-w5`.
Base/latest commit before task: `f77d311710603e3bea949a432094134195cbc711`.
Split counts-only from local audit `1e53518`. Implementation commit: `2bc1f10`.
PR: https://github.com/nikhilesh-s/hive/pull/20. Nik (`nikhilesh-s`) was requested
as reviewer. This follow-up records the PR; it does not change implementation.

Home now uses the live count hook. Transient stats/network failures retry with
bounds and abort cleanup; invalid/auth failures are not retried. No fake totals.
Existing backend cache is 60 seconds; no Realtime or schema changes. No
paper-access changes in this ticket. User authorized pushing this dedicated
branch and opening a PR for Nik; never merge or deploy it.

Read-only Supabase check: 3 reviewed papers / 93 experiment groups / 475 rows.
API 243 passed / 16 skipped; isolated PostgreSQL matrix+count test 14 passed /
1 skipped; frontend 11 passed; browser 16 desktop/mobile scenarios; miner
133 passed / 2 skipped; biology/reconcile/enrich/extract/pipeline 165/21/18/10/13;
stable keys 34; densitometry 116; seed benchmark 34/34. TypeScript, lint,
production build passed. CI runs frontend and database regressions.

Report: `research/W5_CORPUS_COUNTS_VERIFICATION.md`. No Supabase writes,
production changes or modifications to the original checkout. The combined
audit and W-1 remain preserved. Next: verify PR #20 CI and await Nik's review;
leave the PR unmerged and undeployed. Persistent backend failure
still reports unavailable after bounded retries; release verification awaits
an authorized deployment.

## W-1 DOI deep links and stored-paper lookup (2026-10-13)

Branch: `w-1-doi-deep-link`.
Base: `f77d311710603e3bea949a432094134195cbc711` (origin/main).
Core implementation commit: `ab23dd7`; PR metadata follow-up: `3fda112`.
Draft PR: https://github.com/nikhilesh-s/hive/pull/19 (opened 2026-10-14).

Research links with `?doi=` normalize DOI URLs, prefixes, whitespace and case,
then open stored live evidence with the original discovery query
when recorded. The existing research input also accepts DOIs without invoking
paper discovery or extraction. Missing papers retain the DOI and show the
existing explicit extraction button; pending jobs and lookup errors are
distinct states. No lookup starts an ingest job, inference or quota spend.
The access gate already preserves DOI/lab parameters; browser tests cover
successful and failed access verification, refresh and encoded DOI suffixes.

Added read-only GET `/experimental/live/paper?doi=...` behind the existing
internal-key boundary and `/api/experimental/stored-paper` behind the server
beta-access gate. Uses the existing readonly PostgreSQL pool, configured live
table and `ingest_jobs`; exact bound DOI lookup LEFT JOINs job rows (found = live rows exist; pending only if the job updated within 30 min) and avoids
the recent-50-paper list and search's 500-row truncation. Response shaping uses
`WesternBlotRecord`. No migrations, extraction-pipeline or quota changes.
Live evidence remains shared within beta access, not account-owned. Lab tags
are attribution only. Reviewed-only papers are outside this live-tier ticket.

Verification: API 257 passed / 16 skipped (DB tests checked separately);
local PostgreSQL permission matrix 14 passed / 1 skipped, including exact DOI,
job-less rows, stale pending jobs and all 501 lanes; miner pytest 133 passed / 2 skipped;
biology 165/165, reconciliation 21/21, enrichment 18/18, extraction 10/10,
pipeline 13/13; seed benchmark 34/34; web unit tests 11 passed; browser 13
scenarios passed at desktop/mobile with no extraction/discovery POSTs.
TypeScript, lint, production build and diff checks pass.
GitHub's API/miner, PostgreSQL RLS, web build and hygiene checks passed on
`3fda112`. The web CI job now also runs the frontend unit tests. The same 13
browser scenarios passed against the local production build as well as dev.

Not deployed; hosted Supabase, Render and Vercel were not modified. Older runs
without a persisted discovery query cannot display that original query.
Next: have Nik review/merge PR #19 after its CI checks, deploy API before web, then verify a real wave-1
DOI through a fresh beta access visit. Continue with O-2 in a separate branch.
Local preview uses an isolated test database, not the hosted corpus.

## Release of Srushti's Oct 1-3 work, PR #11, ticket board (2026-10-11)

- **Released.** Main and `release/hosted` are at `ac85a6e`. Render (API) and Vercel (web) both
  run it.
  - PR #12 fixed the red main CI: the web lockfile was out of sync, and migration 008 now
    creates `saved_results`. It also lined up the Supabase CLI history with the remote.
  - `supabase db push` applied `20261011000008/9/11`. `hive_feedback` now has
    SELECT/INSERT/DELETE plus policies on `saved_results`, and migration history shows no
    drift.
  - Vercel production now has `NEXT_PUBLIC_SUPABASE_URL` and
    `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. Supabase Auth already allowed the prod
    `/auth/callback`, and Google sign-in is enabled.
  - Hosted smoke test passed: search and live counts; anonymous save, then `/saved` shows
    it, then remove; `?lab=smoke_test` reaches `search_history.lab_tag` (row deleted); the
    access gate; `/auth/callback` without a code redirects to `/auth/error`.
  - Nik verified Google sign-in and Save on the live site (R-2 done). The first request after
    idle still returns 503 for about 30 s while free-tier Render wakes up (O-1).
- **PR #11** (Srushti, metadata-first ingestion) merged and deployed.
  - The research page shows access and relevance badges.
  - A paywalled paper's job (10.1007/s11033-011-0734-1) ended `awaiting_full_text` in
    2 s, with the institutional-access link.
  - The review found browser-sent metadata trusted too far; that is ticket W-4.
  - The deploy check found every paper button stayed disabled after `awaiting_full_text`.
    PR #15 fixes it on both research and live.
  - Open-access extraction verified live: PLOS ONE 10.1371/journal.pone.0193022 gave 25
    experiments and 158 lane rows (job e04856ab406a).
  - The same check found every ingest_jobs write after the first stage failing:
    `*_checked_at` was sent to asyncpg as a string. PR #16 fixed it, five frozen test
    jobs were corrected, and a new job now persists `awaiting_full_text`.
  - Main, Render and `release/hosted` are at `3839ee3`; Vercel web is at `ffc54a0`, and PR #16 has no web changes.
- **Ticket board:** `tickets/README.md` is the single board, with owners (Srushti + Codex,
  Yashvi + Claude, Tanvi bio QA, Nik release) and the rules agents follow. New tickets are
  in `tickets/oct-push.md`; team updates go in `tickets/team-log.md`.
- **Outreach:** wave 1 was 27 emails (Yashvi 9-30, Tanvi 10-05), with 0 replies and almost
  no visits.
- **Exact next task:** the release is closed (R-1 to R-4 done). Agents pick up W-1, O-2 and W-2
  (Srushti) and G-1 and G-2 (Yashvi). Tanvi does Q-1 and Q-2. Nik owes O-7 (mailbox) and the
  decisions in TEAM_HANDOFF section 9. `TEAM_HANDOFF.md` was rewritten to the 10-11 state.

## Live Reviewed-Corpus Statistics (2026-10-02)

Branch: `feature/saved-results`. Previous commit: `c4bea0b`; this entry is
committed with the implementation (resolve its SHA with
`git log -1 --format=%H -- HANDOFF.md`).

Search and About now load reviewed-paper, experiment-group, and evidence-row
totals from the API rather than displaying hard-coded corpus sizes. The API
uses the same experiment identity helper as search, pages through REST results
when configured for Supabase, and caches the computed totals for 60 seconds.
Failures are shown as unavailable/loading states rather than substituting stale
or invented counts. The About copy now accurately distinguishes selected
papers from the reviewed corpus.

Verification: API 237 passed / 15 skipped; biological checks 165/165,
reconciliation 21/21, enrichment 18/18, extraction 10/10, pipeline 13/13;
seed benchmark 34/34. Web lint, TypeScript check, production build, and
`git diff --check` passed.

Not deployed. Exact next task: verify the live totals on Search and About
against the configured API, then continue the pending manual Saved Results
Google-account verification documented below. The uncommitted
`api/.env.example` edits are unrelated and were not included.

## Authenticated Saved Results (2026-10-02)

Branch: `feature/saved-results`. Base/latest commit before this task: `ee0ed15`.
This entry is committed with the implementation; resolve that commit with
`git log -1 --format=%H -- HANDOFF.md`.

Saved Results now uses the verified Supabase `user.id` for account saves and
the existing `hiveblot_session` localStorage ID for anonymous saves. Next.js
Saved Results handlers call the existing server client's `auth.getUser()` and
assert `X-Hive-User-Id` only over the internal-key-protected API. Browser-supplied
owner IDs/headers and emails never determine account ownership. Verification
errors fail closed. All status/save/list/unsave paths share the same scope in
both REST and direct Postgres: user UUID for accounts; session ID AND user_id
IS NULL for anonymous. New account rows have no session ID. Search/Saved reload
on account changes and responses are private/no-store. Google auth was not
redesigned; experiment grouping and all lane keys remain unchanged.

No anonymous-to-account merge is implemented. A separate claim feature needs
explicit consent, proof of the anonymous session, verified account identity,
transactional deduplication of all lane keys, and deletion only after success.
The current localStorage session is a bearer identifier, not strong ownership
proof. See `web/AUTH.md` for the trust boundary and deployment order.

Supabase inspected: saved_results already has nullable session_id/user_id,
auth.users foreign key, unique owner/key indexes, and RLS enabled. Browser
roles have no direct grants. No schema change is required for the tested
server-only REST path. Existing migration 008 grants/policies for hive_feedback
are still absent on this project: apply it before a deployment that uses
DB_FEEDBACK_URL. No new broad browser RLS policies should be added.

Verification: API 237 passed / 15 skipped (including DB-dependent tests);
web redirect/ownership tests 7 passed; lint, typecheck, production build and
diff check passed. Biology 165/165, reconciliation 21/21, enrichment 18/18,
extraction 10/10, pipeline 13/13; seed benchmark 34/34.
Live `web/tests/saved-results.smoke.mjs` passed through local Next.js -> API ->
Supabase with temporary real Supabase sessions: anonymous save/refresh/unsave,
six-lane account save/idempotency/status/list, one regrouped card, independent
second-device session, sign-out/sign-in persistence, two-account isolation,
and owner-scoped unsave. Reviewed scientific table contents were identical
before/after. Temporary accounts and saves removed; independent DB counts
confirmed zero remaining test users/saves. Saved page HTTP 200 and grouping
verified; interactive Google login/browser visual behavior was not automated.

Next: manually verify Save/Unsave on Search and Saved with the working Google
account at localhost:3000, including sign-out while viewing Saved. Deploy API
before web; production deployment not performed. The paper access/relevance
population gap is unrelated and remains open. User's api/.env.example edits
are unrelated and excluded from this commit. Local API remains on port 8000
and web on port 3000.

## Google OAuth Implementation (2026-10-02)

Branch: `feature/saved-results`. Previous commit: `5053e65`; the commit containing
this entry implements Google OAuth (resolve its SHA with `git log -1`).
Frontend now has Supabase browser/server clients (`web/lib/supabase/`), a
PKCE `/auth/callback` route with internal-only `next`, `/auth/error`, session
refresh in the existing proxy, and navigation login/email/sign-out controls.
Packages: `@supabase/ssr` 0.12.7 and `@supabase/supabase-js` 2.117.2.
Saved Results, Search History, anonymous session IDs, API code, and scientific
tables were not changed. Existing experimental beta access gate is preserved.

Verified: lint/typecheck/build clean; 2 redirect tests passed; biological
checks 165/165, reconciliation 21/21, enrichment 18/18, extraction 10/10,
pipeline 13/13; seed benchmark 34/34. Existing localhost:3001 server responds
200; missing-code callback responds 307 to `/auth/error`, rejecting an external
next. Browser automation tooling was unavailable in this session.

Blocker / exact next task: add `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` to `web/.env` and Vercel. No public
Supabase auth variables were present in web/.env at implementation time.
Allow localhost:3001 and production `/auth/callback` URLs in Supabase.
Then test with an allowed Google user: login, callback, refresh persistence,
Authentication Users entry, and sign-out. None of those authenticated steps
or production deployment was verified. See `web/AUTH.md` for the setup.
Dependency audit also reports existing Next.js/transitive advisories; dependency
upgrades beyond adding Supabase were not part of this task.

## Saved Results Details (2026-10-01)

Saved Results is implemented on branch `feature/saved-results` using the existing
Next.js -> FastAPI -> Supabase/Postgres pattern. It reuses the same anonymous
browser session ID as Search History (`hiveblot_session` in localStorage); no
second saved-user cookie or auth identity is used. Result cards save at lane
row grain: saving one grouped experiment inserts one `saved_results` row per
underlying `western_blot_records` lane, and unsaving deletes all of that card's
stable row keys for the current session only. `/saved` loads saved lane rows,
runs the existing `groupResults()` helper, and renders the same
`DatabaseResultCard` component as Search.

Backend routes added:
- `POST /saved-results/status` batched by `session_id` + `stable_row_keys`
- `POST /saved-results` validates every `(record_id, stable_row_key)` pair
  against `western_blot_records`, then inserts idempotently
- `DELETE /saved-results` deletes only the current session's supplied row keys
- `GET /saved-results?session_id=...` returns `WesternBlotRecord[]` rows with
  optional `saved_at`

Migration 008 now assumes `public.saved_results` already exists with
`session_id`, `record_id`, `stable_row_key`, and `saved_at`; it grants
`SELECT/INSERT/DELETE` plus sequence access to `hive_feedback` and adds
`hive_feedback_*_saved_results` RLS policies. Do not revert this to the older
`owner_id/experiment_key/identity` design.

Verification after this implementation:
- `cd api && ../.venv/bin/python -m pytest`: 220 passed / 15 skipped
- `cd web && npm run lint`: clean
- `cd web && npx tsc --noEmit`: clean
- `cd web && npm run build`: clean

Known follow-up: apply migration 008 to the linked Supabase project before
deploying this branch; otherwise saved-results endpoints will fail when the
`hive_feedback` role lacks access to `public.saved_results`.

Local dev note: when `DB_FEEDBACK_URL` is blank but `SUPABASE_URL` and
`SUPABASE_API_KEY` are present, saved-results now uses the Supabase REST API for
status/save/unsave/list. This keeps the search card saved button working in the
local setup without falling back to any local database.

**2026-10-01 follow-up:** migration 009 fixes Supabase REST save upserts by
replacing the partial `saved_results_unique_session_record` index with a normal
unique index on `(session_id, stable_row_key)`. This is required because
PostgREST cannot use a partial unique index for
`on_conflict=session_id,stable_row_key` and otherwise returns PostgreSQL 42P10.
The local CLI is not linked/authenticated (`SUPABASE_ACCESS_TOKEN` missing), so
apply `20261001000009_saved_results_upsert_index.sql` before hosted Save smoke.
The local REST fallback now avoids that upsert path by checking existing saved
keys and inserting only missing `saved_results` rows, so local Save works before
migration 009 is applied. Smoke with the STAT3 Tyr705 six-lane card returned
200 for first save, duplicate save, and unsave.
`/saved` REST listing also handles `saved_at` strings returned by Supabase REST
instead of assuming asyncpg datetime objects; the saved page now returns 200 for
the same six-lane STAT3 Tyr705 browser session.

## B-9 Search NL-to-SQL Removal (2026-10-01)

B-9 is closed on `feature/saved-results`: the stale `api/app/nlp.py` OpenAI
natural-language-to-SQL path was deleted, and `api/app/search_service.py` now
always uses the deterministic HiveBlot `api/app/bio_query.py` generator before
`sql_guard.py`. This was intentional because `bio_query.py` already encodes the
HiveBlot search concepts we support, is testable/inspectable, and stays aligned
with the current Evidence Record schema. Normal search no longer changes
behavior just because `OPENAI_KEY` is present. OpenAI-compatible extraction is a
separate path controlled by `WBM_LLM_BACKEND`, not normal search.

## Outreach Attribution (2026-10-01)

Outreach attribution is implemented for the live migration
`20261001231317_add_outreach_attribution_to_activity_tables.sql`, which added
nullable `lab_tag` and `utm_source` columns to `search_history` and
`hiveblot_feedback` only. The web client captures `?lab=...` and
`?utm_source=...`, validates them, stores them in localStorage, and attaches
them to search-history and feedback writes. `lab_tag` accepts
`^[a-z0-9_]{1,40}$`; `utm_source` accepts alphanumeric plus `_`, `-`, and `.`
up to 80 chars. Invalid values are nulled/ignored server-side. These tags are
outreach attribution only, not auth or ownership, and `western_blot_records`
is untouched.

## Paper Access / Relevance Flags (2026-10-02)

The main reviewed-corpus Results page now shows paper-level access and
relevance badges when matching metadata exists in `public.ingest_jobs`. The
bug was architectural: PR #11-style paper metadata was only present on the
paper/research discovery surface and/or another branch, while the normal
`/search` response still returned only `western_blot_records` fields to
`DatabaseResultCard`.

Fix on `feature/saved-results`:
- Added migration 011 / Supabase migration
  `20261002000011_ingest_jobs_paper_access_relevance.sql` for nullable
  `ingest_jobs` metadata, access, and relevance columns plus DOI/query indexes.
- Added reviewed-search enrichment that joins by
  `western_blot_records.doi -> ingest_jobs.doi` without modifying either
  `western_blot_records` or `western_blot_records_live`.
- Access badges are DOI-level: `open_access`, `no_open_copy_found`, `unknown`.
- Relevance badges are query-dependent and only attach when the
  `ingest_jobs.discovery_query` matches the current search after simple
  whitespace/case normalization, so relevance from another query is not shown.
- `DatabaseResultCard` renders these as paper-level badges separate from the
  scientific `Supported` / review badge. If no ingest job matches, no paper
  badge is shown.

Verification:
- `cd api && ../.venv/bin/python -m pytest`: 228 passed / 15 skipped
- `cd web && npm run lint`: clean
- `cd web && npx tsc --noEmit`: clean
- `cd web && npm run build`: clean
- `git diff --check`: clean

## Search History (2026-09-25)

Search History is implemented on `main` via the existing Next.js -> FastAPI ->
Supabase architecture. It includes migration 007, session-scoped persistence,
normalized deduplication, `/history`, rerun links through `/search?q=...`,
individual deletion, clear-all confirmation, and loading/error/empty states.
Authentication is not implemented, so ownership is browser-session scoped via
the existing anonymous localStorage session ID. Saved Results now reuses that
same session ID (see the 2026-10-01 section above).

**2026-09-24:** team summary lives in [`TEAM_HANDOFF.md`](TEAM_HANDOFF.md).
Branch layout changed (see there): `main`, `release/hosted`, `outreach/oct20`, old branches as `archive/*` tags.
Outreach plan is on branch `outreach/oct20`.

**2026-09-26:** owners and reminders to 10-20 are in
[`SUN_SEP_26_MEETING_ACTION_ITEMS.md`](SUN_SEP_26_MEETING_ACTION_ITEMS.md) (goal: unique labs using
the beta). CI on main was red after the search-history merge (test bug, fixed `8885a7b`). Pending
release now needs migrations `20260920000007` and `20260925000007` before the API deploy.

**2026-09-27 — release shipped (supersedes the PAUSED block's "not deployed" and resume steps 1-4):**
- Migrations 006 + 007 applied to Supabase. Render and Vercel both run `main`; `release/hosted`
  tracks the deployed commit. Hosted smoke passed (zero-result, survey + opt-in contact,
  not-useful, per-field ✓, search history add/delete); smoke rows deleted.
- PR #4: `/experimental/*` is behind `BETA_ACCESS_CODE` (Vercel env; value only in
  `~/.hive-secrets/beta_access.env`). Invite links use `?access=<code>`; `/access` form otherwise.
  Daily caps: 30 extractions / 200 answers per UTC day. Rate limits keyed per researcher via
  `X-Hive-Client-IP` (trusted only with the internal key). `/docs` and `/openapi.json` are 404.
- PR #5: publisher `citation_pdf_url` fallback for OA papers (PLOS, Nature family, microPublication).
- PR #6: records use the job's DOI when the PDF text has none (paper_id NOT NULL failure).
- PR #9: one extraction at a time (`INGEST_CONCURRENCY`, default 1). Two at once on the free
  instance timed out Render's health check and the restart killed both; jobs orphaned by a
  restart now read as failed. Re-test: two submitted together, second queued, both done in
  7 min, no restart. **Render and `release/hosted` at `e5e332d`**; Vercel web code unchanged
  since `f105813`.
- Wave-1 pre-extraction: 9 of 17 candidate papers are in the hosted live tier (local
  `claude_cli`); 8 blocked by publisher bot checks. Check sheet and Tanvi sign-off gate:
  `outreach/PREEXTRACT_CHECK.md` on branch `outreach/oct20`. It surfaced B-12..B-14 (target
  normalization misses, Northern blots stored as westerns, unresolved targets never flagged
  for review) in `tickets/bio-qa.md`; O-8 (research page abandons a job on transient 429s).
- Still open: Render is free (Starter needs a card on file), `UNPAYWALL_EMAIL`, most OA publishers
  bot-block downloads (bring-your-own-PDF ticket), record 1189 feedback kept pending Nik's call.
  All in [`tickets/ops-2026-09-27.md`](tickets/ops-2026-09-27.md).

## PAUSED 2026-09-20 22:00 PT — READ FIRST (state, flaws, exact resume steps)

Nik paused all HiveBlot work. `main` is the only branch; everything below is on it and pushed.
Older sections of this file are history and may contradict this block; this block wins.

### What is hosted and verified (2026-09-20)
- One link: https://hiveblot-beta.vercel.app (Vercel prod from `main` @ `7c7a7c5`) and
  https://hiveblot-api.onrender.com (Render free `srv-da1rbvs9v7es738635ug`, built from `main`
  @ `0aa5fdf` with `api/Dockerfile.experimental`; `autoDeploy` off).
- `/search`: reviewed corpus (3 papers / 475 rows, recounted live), evidence panel, crops, field
  feedback. Smoke report: `SMOKE_TEST_REPORT.md` (11 pass / 0 fail / 1 not verified).
- `/experimental/research`: Valency semantic search (`sources_used: ["valency"]`), PMC fallback,
  **live extraction proven hosted** (job `a8263b4d520f`, DOI 10.3892/br.2026.2108: 9 candidate
  panels, 20 experiment records, 113 lane rows, ~4.5 min, backend `anthropic`). Live tier now
  holds those 113 unreviewed rows.
- `/experimental/ask`: paper QA with citations verified on the reviewed corpus.
- `/experimental/densitometry`: v0.3.0 verified hosted on record 1189 (near-tie warning, no leak).
- Supabase: migration 005 applied (live tables + `hive_ingest` role). Render env var names:
  `ANTHROPIC_API_KEY`, `WBM_LLM_BACKEND=anthropic`, `EXPERIMENTAL_ENABLED=true`, `DB_INGEST_URL`,
  `VALENCY_API_TOKEN` plus the beta set. Operator files on Nik's laptop only:
  `~/.hive-secrets/render.env` (Render API key), `~/.hive-secrets/valency.env`, `~/hive_ingest_dsn.txt`.

### Merged to main but NOT deployed (commit `4911bc0`, feedback tickets F-1..F-6)
Export script, zero-result search capture, result-level useful / not relevant, 3-question session
survey, opt-in contact column (**migration 006**), real `app_version`, separate feedback rate limit,
failed submits now visible. api 201 passed / 12 skipped, tsc clean, lint clean, build clean.
**Deploying the API without migration 006 will 500 every feedback submit** (it inserts `contact`).

### Exact resume steps, in order
1. `supabase db push --dry-run` must list only `20260920000007_feedback_contact.sql`; then `supabase db push`.
2. Deploy API: `K=$(sed -n 's/^RENDER_API_KEY=//p' ~/.hive-secrets/render.env)`;
   `POST https://api.render.com/v1/services/srv-da1rbvs9v7es738635ug/deploys` with
   `{"clearCache":"do_not_clear"}` (env-var edits do not auto-deploy). Poll `.../deploys/<id>`.
3. Deploy web: `cd web && vercel deploy --prod --yes`.
4. F-8 hosted smoke: submit one row through each new control, read back with
   `scripts/export_feedback.py --json`, delete the test rows (`supabase db query --linked`).
5. Send the email (draft in chat 2026-09-20 and `BETA_EMAIL_WITH_TALLY_AND_BRIEF.md`; add the
   research-page paragraph). Tally: https://tally.so/r/A7kzWB, add hidden-field params per lab.

### Known flaws and risks (pick up here)
- **Paper access is fragile.** Europe PMC (403) and PMC (proof-of-work page) block scripted PDF
  downloads since 2026-08; NCBI retired the OA web service. Live ingestion now depends on OpenAlex
  resolving a publisher PDF URL and the publisher answering a plain client (Spandidos and Springer
  do; a browser user agent gets blocked). Unpaywall is skipped because no real contact email is
  configured (`UNPAYWALL_EMAIL`); decide which mailbox to use. Papers without a publisher PDF fail
  honestly ("No open-access PDF"). No retry queue, no caching of PDFs across Render restarts.
- **Live extraction is slow and costly:** ~4.5 min and one Anthropic call per panel; jobs run in the
  API process on a free Render instance with no worker, no concurrency guard beyond the app's own,
  and a 15-minute idle spin-down that kills in-flight jobs. Two testers extracting at once is untested.
- **Live tier feedback is read-only by design**; testers cannot correct unreviewed rows.
- **Corpus stats are hardcoded copy** (`web/app/about/page.tsx`, `web/app/search/page.tsx`); they will
  drift as the live tier grows. Live rows are not counted there.
- **Record 1189** carries 2026-09-16 internal "marked correct" feedback visible to testers; decide
  whether to delete (`hiveblot_feedback`, ids from `export_feedback.py`).
- **API `/docs` is public** (route names only). `docs_url=None` in `api/app/main.py` if unwanted.
- **Rate limits are per proxy IP**: all Vercel traffic shares one bucket on Render (search 20/min,
  feedback 120/min, densitometry 60/min). A lab session could hit 429 on search.
- **Crops are baked into the image at an absolute laptop path**; `api/crops/` must be re-staged by
  hand when the reviewed corpus changes. Live crops go to `ingest_crops` in Postgres instead.
- **No auth on the experimental pages**: anyone with the link can start paid model jobs. Acceptable
  for a private beta; add a shared beta key before wider sharing.
- **Cold start** 30–60 s on the first request; the UI says so, but extraction plus cold start is slow.
- **Docs pack at repo root** (`README_CASE_STUDY.md`, `UCSF_BETA_*.md`, `BETA_EMAIL_*.md`,
  `PAPER_ACCESS_AUDIT.md`, `HOSTING_STATUS.md`, `SMOKE_TEST_REPORT.md`) was written before the
  experimental stack was hosted; several sentences still say live search is "not yet in this link".
  Nik paused this work; update or delete before sharing.
- **Old branches** (`feature/bio-context-beta`, `experimental/*`, `execute-plan-verification`) are
  fully contained in `main`; safe to delete after Nik's review. `render.yaml` now says `main`.
- Untested hosted: per-field ✓/✗ after the F-6 change, mobile layout, other browsers, `/v1/search`.

## UCSF PUSH STATE (2026-09-14 → founder hard stop Tue 2026-09-15 19:00 PT) — READ FIRST

**Active integration branch: `experimental/ucsf-demo-2026-09-09`** (the only
branch new work lands on; `experimental/densitometry`, `experimental/paper-qa`,
`experimental/valency-live-ingest`, `experimental/demo-day` are historical
pointers already contained in it; `feature/bio-context-beta` = frozen hosted
beta; `main` is stale). Launcher: `CLAUDE_RUN_2026-09-14.md`. Plan:
`research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md`. Running log:
`research/overnight/2026-09-14-session-log.md`. Latest commit: `git log -1`
(this block written at `7238a8f`).

**Shipped this push (window 1, 2026-09-14 night):**
- **Densitometry v0.2** (`western_blot_miner/densitometry.py`,
  `api/app/experimental/densitometry_router.py`,
  `web/app/api/experimental/densitometry/route.ts`,
  `web/app/experimental/densitometry/page.tsx`): region reaches the analyzer
  (D-1 fixed); researcher-defined `lane_bounds` + `lane_labels` are the product
  path, count/auto lanes are labelled diagnostics; per-lane contract (raw,
  background, corrected, relative, clipped_fraction, snr, quality, reasons,
  stability envelope); gates: band-core clipping warn 2% / refuse 10% within
  8 DN of the floor, robust-SNR no-signal, invalid geometry = HTTP 400;
  whole-strip refusal (`relative: null` everywhere) when the reference lane is
  clipped, no lane has signal, or the strongest lane changes under ±5% lane
  width / ±10% row height perturbation; method name/version/thresholds and
  image sha256 in every response; UI drag-region, seeded/draggable dividers,
  labels, quality-coloured overlay, quality card, ranges not two-decimal
  points, JSON/CSV export. Verified end-to-end in the local browser (refusal
  on a clipped lane; valid 1.0 / 0.5 / 0.25 / 0 recovery).
- **Validation:** `research/experiments/D2_clip_threshold_study.md` (synthetic
  known ratios: gate fires at 18% clipped core with 3.9% ratio error, before
  the 13–95% error regime; JPEG floor smearing does not hide clipping; jitter
  envelope) and `research/experiments/D5_real_crops_refusal.md` (21 reviewed
  crops, auto geometry: 21/21 have a clipped row past the gate, 78/112 rows
  refused, 15 ok, 19 warning — refusing is the feature on published figures).
  D1's 59.7% is retired with a header; never quote it.
- **B-1** `pipeline._split_text_context`: caption/methods routed separately;
  `figure_caption` sources are real caption text. **B-2**
  `record_builder._antibody_info`: deterministic vendor/catalog/dilution/clone
  backstop only when the model left the field empty (source type
  `deterministic`, rank below methods, confidence 0.6); disagreement is kept
  as a candidate, never overwrites.

**Window 2 (2026-09-15 early):** adversarial probes run by the orchestrator
(30 random fixtures: no refused lane ever carries a number, deterministic
output, clamped region echo, 400/422 at the trust boundary); B-2 scoped to the
sentence fragment naming this target (multi-antibody sentence bug); CI hygiene
grep ignores `@localhost`; polarity decided on the whole image (a tight box
around dense bands flipped it on record 4455); near-tie reference change is a
warning with values kept, a clearly-weaker winner refuses; `rows_text_like` +
printed-text warning; record-crop path verified in the browser on the local DB
(record 4455: P-STAT3 strip valid + stable, T-Stat3 strip near-tie warning);
real-crop gate checks added to the test script. Full state, limitations,
branch audit and Nik's manual steps: **`research/overnight/2026-09-14-summary.md`**.

**Later in window 2:** background kernel sized from the whole image (a tight
box collapsed ratios toward 1 while reporting ok — the most serious bug found
this push); explicit `band_row` in API/UI; overlay PNG export; demo_check
exercises the product path on record 4455; run-of-show step 9 rewritten with
concrete records (4455 valid strip + β-actin near tie, 4686 clipped refusal);
Tally/distribution specs reviewed and trimmed to ~5 min; L1 marked stale.

**Method v0.3.0 (2026-09-15):** per-lane flank baseline (membrane rows one
band-height above/below the band, lower of the two medians) on top of the
rolling-ball opening, flank MAD as the noise scale; synthetic unclipped ratio
error 7.4% → ≤1.8%, tight and re-boxed real strips agree within 0.04; a box
with no membrane margin warns; a multi-strip box is at least a warning and the
UI's row buttons re-box the chosen strip. About/Learn name the experimental
route without changing the Evidence Record statement.

**Also landed 2026-09-15:** printed-text rows = short dark runs (clipped
bands no longer called text); per-lane vertical profile + sparkline column;
row buttons re-box a strip inside a multi-strip box; TIFF uploads through an
8-bit PNG preview endpoint; densitometry rate limit 60/min; run-of-show step 9
rehearsed in the browser for records 4455 (valid) and 4686 (clipped refusal).

**Tests (2026-09-15):** densitometry 84/84 · api 166 passed / 11 skipped (DB
matrix needs `HIVE_DB_TEST_URL`) · miner pytest 56 · biology / reconcile 21 /
loader / extract 10 / pipeline 13 / stable-row-key 34 all green · benchmark
34/34 · `tsc` clean · lint 0/0 · `next build` clean · `git diff --check` clean.

**Not done / known:** no loading-control pairing, no cross-image comparison,
nothing stored (reserved intensity columns stay NULL); thresholds are v0.2
synthetic-justified defaults (D-7 real dilution series pending); Valency token
not on this laptop (PMC fallback works); nothing experimental is hosted;
`scripts/local_db.py up` prints a harmless "policy already exists" error on
re-run.

**Latest (2026-09-15):** opening kernel floored at 61 px after a third
adversarial pass (strips closer than a band height on small images); `next
build` clean with the dev server stopped; `scripts/demo_check.py` green
(see session log for the count).

**Hardening pass (2026-09-15 afternoon):** adversarial QA fixed refusal-invariant leaks (stability
ranges and pair relatives on refused lanes), five HTTP 500 input classes, alpha polarity, antibody
attribution theft in the B-2 backstop, p-prefix non-phospho names (pVHL/pRB/P-gp), two-site captions,
MW source provenance, the caption/methods header split, caveats hidden under a "valid" card, pairing
lane-offset warnings and frontend response races. Details and commits: session log "Window 4".
Known limit: adjacent strips < ~3 band sigmas apart merge into one row without a warning.
Later the same afternoon: lane-condition / lane dose / lane-text band patterns typed as image
evidence (`ec8218d`); single lane = warning, thin band-row refusal explains itself (`68f1c7c`);
antibody backstop regressions from the scoping rewrite fixed on the real corpus - full catalog
numbers, comma-grouped dilutions, abstain on two antibodies against one target (`079124d`);
page errors visible before an image loads, readable validation errors, lead copy consistent with
the pairing (`4c98e6e`). Pre-existing source typing fixed (`c42f1ee`): a source is methods/caption only if its
text is verbatim there, otherwise "model reading" (UI label `0396aee`); caption "pVHL"/"pRB" no
longer read as phospho (`e6e86ad`); treatment dose/duration from model wording are model readings
(`9080341`); co-IP bait from lane labels is image evidence with lane-only quotes (`8f766fe`,
`1d6c431`); CI lint fix for unescaped JSX apostrophes (`29bf167`) — run lint with pipefail.
B-2 on the LIVE path (`8dd8735` + follow-up): a live claude_cli extraction of the demo panel showed
every antibody catalog empty because the context blob truncated the methods snippets away (50/128
stored contexts had none) and never targeted reagent sentences. Per-section budgets, reagent snippets
first, a methods-scoped verbatim backstop with dash folding, and repeated-sentence dedupe now recover
beta-actin CST #4967 / 1:2000 with a deterministic quote; phospho/total STAT3 abstain. Stored corpus
values unchanged. Pre-warmed papers keep their stored contexts; a re-extraction would use the new ones.

**Loading-control pairing (2026-09-15, browser-verified):** analyzer
`pair_ratio` + `POST /experimental-densitometry/pair` + page section 4. On
record 4455, P-STAT3 strip ÷ β-actin strip gave normalized 0.6–0.8 / 1.0–1.1 /
0.3 / 0.0 / 0.0–0.1 (wide-range warning) / 0.3–0.4, overall warning
(inherited from the β-actin near tie), same-membrane caveat shown first, no
console errors. Quality card no longer uses a side-tab border.

**Paper QA hardening (`d056c83`):** record text can no longer inject into the prompt (one-line,
delimiter-neutralised `<record>` blocks); a reviewed-tier retrieval failure says "Retrieval failed", not
"no evidence"; capitalised prose is not a search term; an unfilterable question never reads the whole
table; `[E1, E2]` is a citation and phantom refs are reported in `invalid_cited`; MISSING modification
renders "not stated". Open gap: citations are checked for existence, not for agreement with the cited
record's status.

**Final pre-demo hardening (2026-09-15 16:00-19:00 PT):** paper-QA answers now get a labelled, deterministic
status check (`cb4caeb`) — a sentence whose wording contradicts the statuses of the records it cites
(CONFLICTING stated as settled, a supported phosphorylation denied, a not-stated modification called total,
certainty on a needs-review record, intensity language, live records cited without "unreviewed", a target
named that only uncited records carry) adds a warning to the note. It is lexical, NOT semantic: partial
support inside one sentence is undetectable and stays a documented limit. The `claude -p` backend now runs
with `--setting-sources project` (`85b20b2`) so the operator's own Claude Code plugins / hooks / output
styles cannot shape extraction or answers — a user style hook was turning demo answers into clipped prose.
co-IP classification no longer settles on page-level caption prose (`afc9f19`): a single
"Immunoprecipitation (IP) assays ..." sentence had been making 47 records co_ip with bait "IP" on a live
re-extraction. Short-symbol search boundaries were measured and left as they are (0 rows would change);
the limit is documented in `bio_query._term_clause`.

**Search hardening (`da0f5c9`, `e4936f3`):** a short gene symbol no longer matches inside a word (MYC
returned 86 Rapamycin/Bafilomycin rows); a pasted DOI is an exact paper filter (before, a truncated DOI
showed another paper's rows on the research page and "(00)" in a DOI parsed as a Ser92 site); record ids
bounded to bigint (422, not 500); deleting a running live job is refused (409), and 503 without the
ingest DB. Research/live pages (`035bbb1`): late responses cannot land on a newer paper; failed
listings/searches/job polls show an alert instead of an empty list; every experimental proxy answers
invalid JSON with 400. Main search (third attack pass): results are no longer cut at 100 lane rows
mid-experiment (500-row cap, trailing partial experiment dropped, `truncated` note); vendor catalogs
like "Santa Cruz sc-398486" / "abcam ab108629" are found; "T24", "HEK 293 CST", "CST 1:1000" and
"IκBα" are no longer misparsed; the search page drops stale responses; feedback rejects NUL bytes and a
record_id paired with another record's stable_row_key. Known, not fixed (would need synonym expansion):
pSTAT3 / beta-actin / SQSTM1 / ERK1/2 / 4E-BP1 spellings return nothing.

**Tests (latest):** densitometry 116 checks · api 192 passed / 11 skipped · miner
pytest 133 · demo_check 19 PASS / 2 WARN / 0 FAIL · biology / reconcile 21 / extract 10 / pipeline 13 /
stable-row-key 34 green · benchmark 34/34 · DB access matrix 11 · tsc, lint and next build clean.

**EXACT NEXT TASK (after the 2026-09-15 final hardening window):** the package is frozen and green. Before
the demo, run the stack per `research/UCSF_DEMO_2026-09-09.md`, run `scripts/demo_check.py` (expect 0 FAIL)
and rehearse step 9 (4455 valid, beta-actin pairing warning, 4686 refused). Everything below still holds:
(1) pull `experimental/ucsf-demo-2026-09-09`, start the stack per
`research/UCSF_DEMO_2026-09-09.md`, run `scripts/demo_check.py` (expect 0 FAIL) and rehearse step 9
(4455 valid, beta-actin pairing warning, 4686 refused); restart the API after any Python change (no
auto-reload). (2) Further adversarial QA only if budget remains — the open, documented limits are
adjacent strips < ~3 band widths merging into one row and a soft exposure knee compressing ratios below
the clip gate (both need a dilution series, D-7, not code). (3) Human-blocked: B-4 panel inventories
(Tanvi), Tally form, page-name decision, branch cleanup list, D-7 dilution series. Checkpoint rule:
commit and push after every block; run lint with pipefail; sub-agents report early.

## CURRENT STATE (2026-09-01, UCSF beta-readiness pass — session 31)

**1. What is HiveBlot?** A biologically accurate Western blot evidence search
platform. It turns published blot figures, captions and methods into
structured, searchable, auditable *experiment-level* Evidence Records (per-field
value + status + source + verbatim wording), for wet-lab researchers who need
to locate and compare blot evidence (antibody/target/context already
published?). Beta target: UCSF wet-lab researchers.

**2. Canonical branch.** `feature/bio-context-beta` (frozen beta; the UCSF demo runs from `experimental/ucsf-demo-2026-09-09`, see below) on
`git@github.com:nikhilesh-s/hive.git`, in sync with origin. `main` predates the
beta and must not be treated as current or merged into. Tip: run `git log -1`;
the last four commits of this pass are `beaec0f` (RLS hardening), `393ffa6`
(About/Learn P0), `5c54352` (QA/UX fixes) and the handoff commit on top.

**3. What is deployed.**
| Piece | Where | State |
|---|---|---|
| Web | Vercel `hiveblot-beta` → https://hiveblot-beta.vercel.app | **deployed from `5c54352`** via `vercel deploy --prod` (Vercel does not auto-deploy this branch) |
| API | Render free Web Service `hiveblot-api` (`srv-da1rbvs9v7es738635ug`) → https://hiveblot-api.onrender.com | **deployed from `96678c8354b16c67984f4329ab964e54bc27a07c`** (deploy `dep-dabrjdojo6nc738n1to0`, live 2026-09-02 05:53 UTC, triggered by `render deploys create`; `autoDeploy` stays off) |
| DB | Supabase `zafombwswztvnjikcsdm` (us-east-1, PG 17.6) | **migration 004 applied 2026-09-01**; 5/5 migrations in remote history; Security Advisor 0 errors (1 WARN: pg_trgm in public, deferred) |
Legacy QIB `belalrbfrndxvdwvjxte` is never touched.

**4. Data in the beta.** Reviewed reference corpus: **3 papers · 93 experiment
groups · 475 evidence rows** (475 distinct `stable_row_key`, 21 crops in
`api/crops/`). Papers: 10.3892/br.2026.2108 (phospho-STAT3, Hep3B),
10.3892/ijmm.2022.5188 (mouse SMG loading controls),
10.1186/s12964-025-02385-8 (BEX2/PIK3CA co-IP). `hiveblot_feedback` holds
**1 real researcher row** (id 5, 2026-08-18, search scope); all smoke rows from
this pass were deleted.

**5. Scientifically proven (on the reviewed corpus).** Structured Evidence
Records; experiment-level search; field-level provenance with quoted
wording; explicit uncertainty/abstention; conflicts preserved (value null +
both claims); researcher feedback stored beside model output, reseed-proof;
independent QA re-run this pass found **no false SUPPORTED**.

**6. Explicitly NOT proven.** Literature-wide coverage; automated extraction
accuracy on unseen papers (Stage 2 has only ever run agent-in-the-loop);
precision/recall/F1 on unseen papers (no number exists); densitometry or any
band-intensity inference. The site now says exactly this.

**7. What changed in this pass** (full report: `research/UCSF_BETA_READINESS.md`).
- **Git forensics:** Srushti's work = Case A, all 14 commits already on the branch; nothing to merge; `requirements-local.txt` verified (pgserver local-only).
- **Security (P0):** migration `004_secure_public_tables` — RLS on both tables, anon/authenticated revoked (tables, sequences, default privileges), hive_readonly scoped to records, hive_feedback INSERT+SELECT on feedback via explicit policies. Verified live: anon key gets 401 on read/insert/update/delete; hosted search/feedback/crop unaffected. API dropped its PostgREST client (`/`, `/proteins` on hive_readonly; `supabase` dependency removed). New `api/tests/test_db_access_matrix.py`.
- **Communication (P0):** `/about` and `/learn` rewritten honestly (no 2.8K/12.4K/520, no automated-ingestion story, no Upregulated/Downregulated, no densitometry); glossary added; metadata/nav tagline fixed.
- **API shaping:** `review_reasons` on list rows + detail; crop refs serialized as filename only (no `/Users/...` leak); `ambiguous_family` / `{}` / empty sources hidden; null candidates dropped; modification candidate `none` relabeled "no modification (total protein)"; flag `detail` passed through; lane measures without float noise.
- **UX:** home explains scope + examples + cold start; cards show the record's own crop (stand-in `STATE3.png` removed), review reasons, DOI link and an `Evidence & sources` toggle (provenance had become unreachable); evidence panel empty-state, lane-series `?`, mixed-unit dose, flags section; search page examples/empty state/slow note; bare dash removed; lint 0/0; legacy `ResultsTable`/`ResultsCard`/`OrbitCanvas` deleted.
- **Docs:** `DEPLOYMENT.md` security matrix; `TEAM_ASSIGNMENTS.md` + `MASTER_DELEGATION.md` marked consolidated; `TEAM_BETA_HANDOFF.md` status refreshed; `.claude/launch.json` gained API launch configs.

**8. Security architecture now active.** Browser → Next.js server route
(`INTERNAL_API_KEY`, never in the bundle) → FastAPI → `sql_guard` AST check →
asyncpg pools on two scoped Postgres roles. RLS enabled on both tables with
explicit per-role policies; no PostgREST path; anon key unused. Verified by
`test_db_access_matrix.py` and by live probes (see readiness report §B).

**9. Supabase roles and what they may do.**
| Role | `western_blot_records` | `hiveblot_feedback` |
|---|---|---|
| `hive_readonly` (login; `DB_READONLY_URL`) | SELECT (policy `hive_readonly_select_records`) | nothing |
| `hive_feedback` (login; `DB_FEEDBACK_URL`) | nothing | INSERT + SELECT (policies `hive_feedback_insert_feedback`, `hive_feedback_select_feedback`), USAGE on id sequence; no UPDATE/DELETE |
| `anon`, `authenticated` | nothing | nothing |
| `postgres`, `service_role` | owner / BYPASSRLS (migrations, seeding; server-only) | same |
Neither hive role is superuser/createrole/createdb/bypassrls.

**10. Tests currently passing** (branch tip, 2026-09-01): biology 165/165,
reconcile 21/21, loader enrichment 18/18, extract 10/10, pipeline wiring
11/11, stable-row-key 34/34, benchmark 34/34 (seed self-consistency only),
api **129/129** (incl. 9 access-matrix tests that need `HIVE_DB_TEST_URL`;
they skip without it), `tsc` clean, `npm run lint` 0 errors / 0 warnings,
`npm run build` clean, `git diff --check` clean.

**11. Bugs / limitations remaining.** pg_trgm-in-public advisor WARN deferred
with procedure; corpus findings QA-1…5
(abstentions/classification nits, each needs a reviewed reseed); organism
filtering is text-based (documented, deliberately unchanged); "why did this
match" not surfaced; free-tier cold start ~21 s measured.

**12. Absorbed from the former teammate handoffs.** Ananya (Fig 3C/3D re-verified,
one experiment per paper audited, every abstention judged, glossary),
Suhas (GAPDH mouse analysis, crop-ref consumer map + fix, raw-value shaping,
review_reasons, cold-start measurement), Srushti (first-run home, needs-review
comprehension, presentation fixes, confidence-display decision, next-action
ranking), Tanvi (About/Learn/glossary/audience/cold-start copy), Yashvi
(issue table + dedup). No teammate deliverable is pending.

**13. Founder decisions remaining.** (a) ~~Deploy the API build to Render~~
done 2026-09-02. (b) Whether to apply corpus corrections QA-1…QA-5 via a reviewed reseed.
(c) Structured organism filter go/no-go (recommendation: `organism = X OR
text`, exact tokens only). (d) Which next action to build first
(recommendation: "more from this paper" by making DOI searchable).
(e) Move pg_trgm to `extensions` after a proven dry run. (f) Model
credentials → run the unseen-paper extraction evaluation.

**14. EXACT NEXT TASK.** None before UCSF: the beta is **FROZEN** (see
"Release freeze" below). On presentation day run the 6-step checklist in
`research/UCSF_BETA_READINESS.md` §J. After UCSF, the first task is Nik's
decision on the deferred corpus corrections QA-1…QA-5 (reviewed reseed).

### Post-UCSF sprint (2026-09-09 → ship 2026-09-16) — see `tickets/README.md`

The UCSF meeting happened 2026-09-09. Three ticket tracks live in
`tickets/` (feedback, densitometry, bio-qa) with a day-by-day timeline and
the decisions Nik must make first (release vehicle, page naming, no reseed
this week). Supabase `zafombwswztvnjikcsdm` verified 2026-09-09: ACTIVE,
RLS on both tables, advisor 0 errors / 1 deferred WARN, 1 feedback row;
feedback is pullable today with `supabase db query --linked` (details in
`tickets/feedback.md`, `super-based-ticket.md`). The local demo stack
(web :3000, API :8010, embedded Postgres) was shut down after the meeting.

### UCSF demo track (2026-09-09) — branch `experimental/ucsf-demo-2026-09-09` — THE DEMO BRANCH

Created from `experimental/demo-day` @ `439300a`. `feature/bio-context-beta`
(frozen, hosted), `experimental/demo-day` and `main` are untouched. Exact
demo path and fallback path: **`research/UCSF_DEMO_2026-09-09.md`**.
Architecture: `research/DEMO_DAY_ARCHITECTURE.md`. Latest commit: `git log -1`.

**What works today (rehearsed locally, 2026-09-09):**
- **Unified research page** `/experimental/research`: topic → papers with
  discovery source (PubMed Central; Valency first once the token exists) and
  an open-access-PDF chip → choose → extract live or **open an already-
  extracted paper** → stepper → `LIVE · UNREVIEWED` cards with read-only
  evidence panels (crop, sources, statuses, lanes) → question scoped to the
  paper → cited answer over numbered evidence; model failure degrades to the
  numbered evidence. Older pages (`/experimental/live`, `/ask`,
  `/densitometry`) stay as diagnostics.
- **Model backend `WBM_LLM_BACKEND=claude_cli`**: the authenticated local
  Claude Code install via `claude -p` (JSON envelope, custom system prompt,
  no tools for text; images written to a private temp dir with only Read
  allowed; never `--bare`). Proven on real calls: text 6 s; the image path
  read the reviewed STAT3 crop correctly. Extraction and paper QA share one
  provider abstraction (`llm_client.complete_text`, `backend_status`).
  `OPENAI_KEY` is optional for this experimental backend family only; normal
  search no longer uses the deleted OpenAI NL→SQL path.
- **Open-access acquisition** fixed: Europe PMC's own PDF render (retry /
  backoff) → listed URL → legacy → Unpaywall (real `UNPAYWALL_EMAIL` only).
  Discovery annotates `oa_pdf`; the UI refuses papers without a PDF.
- **Parallel extraction** (`WBM_CONCURRENCY`, default 1; demo 4).
- **Live loader** stores real JSONB, needs no UPDATE privilege; `reuse:true`
  re-loads a finished run without a model call.
- **Pre-warmed live tier (local DB):** `10.1111/1759-7714.13925` (PMC8088950,
  31 candidate panels → 97 experiments / 334 lane rows) and
  `10.1186/s12931-015-0285-4` (PMC4640373, 5 panels → 17 / 143, extracted in
  ~1m50s with concurrency 4). Paper QA scoped to the second paper answered
  with citations [E1]–[E12], all live-tier, and correctly said no phospho
  claim exists in it.
- **Experimental CI** `.github/workflows/experimental-ci.yml`: push/PR gates
  (api + miner tests, RLS matrix on a Postgres service, tsc/lint/build,
  hygiene) with no credentials; manual `workflow_dispatch` live Valency smoke
  reads the `VALENCY_API_TOKEN` secret and skips cleanly when absent.
- **`scripts/demo_check.py`** — PASS/WARN/FAIL pre-demo check (branch,
  claude executable + real inference, env names, API, model backend, live
  tier, discovery, reviewed retrieval, pre-warmed papers, QA, web).
**Tests today (2026-09-09):** api **160 passed, 11 skipped** (the skips are
the DB matrix, which ran separately: **11 passed** incl. live tier + loader
JSONB check); biology 165, reconcile 21/21, loader enrichment ok, extract
10/10, pipeline wiring **13/13** (parallel mode covered), stable-row-key
34/34, densitometry 20/20 (v0.1 then; 84/84 at v0.3, see the UCSF push block), benchmark 34/34 (seed self-consistency only);
`tsc` clean, lint 0/0, `next build` clean, `git diff --check` clean.
`scripts/demo_check.py`: 18 PASS · 2 WARN (Valency token absent locally) · 0 FAIL.

**Blocked / not done:**
- **Valency contract verified live (2026-09-09, GitHub Actions run
  34413782117, manual `run_live_valency=true`, secret `VALENCY_API_TOKEN`
  set on the repo):** initialize → `valency-research-mcp 0.3.79`;
  tools/list → 38 tools; `semantic_search_papers` takes `query` (required)
  and `limit`, so `_arg_names` needed no change; the STAT3/IL-6/HCC query
  returned 8 normalized results, 7 with DOIs, 4 resolving to a PMCID;
  an invalid token is rejected with HTTP 401; PMC search answers
  independently (3 hits) and locally without a token
  (`valency_smoke.py` exits 2 with 5 PMC hits). Known gap: `year` is
  `None` for every Valency result (normalizer does not find the year
  field in the live shape) — cosmetic for discovery, not fixed. The token
  is still not on this laptop, so local discovery uses PMC.
- The `hygiene` job of `experimental-ci.yml` fails on every run of this
  branch (push and dispatch alike): its credential-shape grep matches the
  dummy localhost DSNs in `api/conftest.py:17` and
  `api/tests/test_experimental_ingest.py` (`postgresql://hive_ingest:x@
  localhost/x`). Not credentials. Fix is one workflow line (`| grep -v
  '@localhost'` before the `||`) or drop the fake passwords from the
  fixtures; left untouched on purpose.
- L1 self-consistency (`research/experiments/L1_live_ingest_eval.md`, claude_cli/
  sonnet, 183 s, 9 panels → 20 records = the reviewed count): on matched lanes
  protein identity 1.0, cell line 1.0, modification 0.83, experiment type 0.83,
  antibody catalog 0.83, band state 0.86; lane-label matching is imperfect
  (29 lanes matched). Not an accuracy claim; do not quote as one.
- Nothing experimental is hosted; the demo runs on this laptop.

### EXPERIMENTAL track (2026-09-05) — branch `experimental/demo-day`

The frozen beta above is unchanged. A parallel, clearly labelled track for
UCSF demo day lives on `experimental/demo-day` (stack of
`experimental/valency-live-ingest` → `experimental/paper-qa` →
`experimental/densitometry`; `main` and `feature/bio-context-beta` untouched).
Full design, demo flow, experiment plan and Nik's checklist:
`research/DEMO_DAY_ARCHITECTURE.md`.

| Piece | What it does | Where |
|---|---|---|
| Live DOI ingestion | DOI → open-access PDF (Europe PMC / Unpaywall) → the existing pipeline → rows in a SEPARATE `western_blot_records_live` tier (`review_tier='live_unreviewed'`), crops as bytes; background job with a stepper | `api/app/experimental/ingest.py`, `western_blot_miner/fulltext.py`, `migrations/005_experimental_live_tables.sql` (new `hive_ingest` role, RLS on), `/experimental/live` |
| Paper discovery | Valency Bond MCP (bearer token, tool schema read at runtime) + PubMed Central OA search fallback | `api/app/valency.py`, `POST /experimental/papers/search` |
| Grounded paper QA | biological terms from the question → same parser/guard → numbered evidence blocks → Claude answers only from them, citations validated; retrieval-only without a key | `api/app/experimental/ask.py`, `/experimental/ask` |
| Densitometry | `POST /experimental-densitometry`: background-subtracted relative lane intensity on a crop/upload, region box, disclaimer, never stored | `western_blot_miner/densitometry.py`, `/experimental/densitometry` |

State: scaffolded, tested (api 149 passed + RLS matrix 10 incl. live tier,
densitometry 20/20 synthetic checks, tsc/lint clean), verified in the local
browser. **Not deployed.** Needs from Nik, in order: `ANTHROPIC_API_KEY`
(+ `WBM_LLM_BACKEND=anthropic`), `VALENCY_API_TOKEN`, migration 005 pushed +
`hive_ingest` password + `DB_INGEST_URL`, a second Render service from
`api/Dockerfile.experimental`, a Vercel preview of the branch. Experiment
D1 ran (59.7% naive agreement, sanity only); L1 (live vs reviewed
self-consistency) runs once a model key exists.

### Release freeze — final hosted verification (2026-09-02 ~06:00 UTC)

Web `hiveblot-beta.vercel.app` (Vercel, from `5c54352`; the handoff commit
changed docs only) · API `hiveblot-api.onrender.com` (Render, `96678c8`) ·
DB `zafombwswztvnjikcsdm` (migration 004 live).

| Check | Result |
|---|---|
| `/health` | 200, 0.27 s warm; `/` returns the static index (proves the new build; the old build returned sample rows) |
| Flagship searches through the hosted Vercel proxy | `phospho STAT3 Tyr705` 3/18 · `co-IP PIK3CA` 4/14 · `CST 9145` 3/18 · `P-ERK` 2/10 with `modification_type = null` on all CONFLICTING rows · `GAPDH mouse` 5/31 · `needs review` 4/20 · `BRCA1 MCF7 olaparib` 0 |
| `review_reasons` | present on every needs-review row (4 reasons on the P-ERK rows), absent on settled rows |
| `image_crop_ref` | filename only in every list and detail response; scan for `/Users/`, `/home/`, leading `/` found nothing |
| Crops | `/api/record/{1200,1252,999,1310}/crop` → 200, PNG signature, 180–340 KB; the UI loads them as real images (1140×564 etc.) |
| Raw values | hosted detail 1252 contains no `ambiguous_family`, `"{}"`, `"none"`; modification candidates read "phosphorylation" / "no modification (total protein)" |
| Feedback | UI ✓ on a field (row 9) and the BETA FEEDBACK widget (row 10) reached `hiveblot_feedback` through the live FastAPI path; reload showed RESEARCHER FEEDBACK rehydrated; both smoke rows deleted; table back to **1 real row** (id 5) |
| Provenance | `Evidence & sources` opens on every card: crop, quoted source sentences, "Why unresolved", lanes, DOI link, feedback controls; empty-identity state renders a sentence, not a bare heading |
| Theme | Light chosen → persisted in `localStorage` and re-applied after reload; dark default verified |
| Mobile | 375 px: filter drawer opens from the Filters button, Escape closes it; cards stack |
| About / Learn | hosted HTML: no 2.8K/12.4K/520, no Upregulated/Downregulated, no "thousands", densitometry named only as out of scope, corpus scope stated |
| Security | RLS on both tables; grants: hive_readonly SELECT records only, hive_feedback INSERT+SELECT feedback only, anon/authenticated nothing; 3 policies; anon key 401 on read and insert; Security Advisor 0 ERROR (1 WARN pg_trgm, deferred); 475 rows / 475 distinct `stable_row_key` / 1 feedback row |

**Frozen.** Only a real security issue, a scientific-correctness bug, or a
demo-blocking runtime failure justifies a change before UCSF. No P2 polish.

---

## Historical session log
- **2026-09-20 (session 33)** — Claude Code (Opus 5), worktree branch
  `worktree-agent-a6deafad371bd895c` off `main`, committed there and not
  pushed. **TRACK F: RESEARCHER FEEDBACK WE CAN ANALYZE (F-1..F-6).** New
  `scripts/export_feedback.py` (CSV or JSON, ordered by `created_at`,
  `--json` / `--since` / `--dsn`, DSN read from the feedback env var and never
  printed) with a pytest that skips unless the DB test-url env var is set.
  Zero-result searches now render the search prompt and write a
  `no_results` row carrying the query, with the zero-count signal in
  `ui_location` so no column was added. The evidence panel's record-level row
  gained "This was useful" / "Not what I needed" (new free-TEXT feedback types,
  no migration), hidden on read-only live cards. The beta widget gained the
  three DEMO.md §7 questions as one row per answered question, offered once per
  browser session and dismissible, plus an unchecked opt-in that stores a
  contact address only when ticked — migration 006 adds that one nullable
  column (with a down file, mirrored into the Supabase CLI layout, green under
  the sync and access-matrix tests) and it is excluded from the rehydration
  path, so it can never render in another browser. `app_version` is now read
  from settings (env var, else the build SHA the host injects) instead of the
  hardcoded literal, and `/health` reports it. Feedback got its own generous
  rate limit instead of sharing the search bucket that every hosted researcher
  hits through one proxy IP, and every client call now checks the response:
  a dropped submission says so and keeps the controls on screen instead of
  showing a checkmark. Tests: api 201 passed / 12 skipped (212 passed with the
  DB test url set), web typecheck, lint and build clean. Not done: F-7 and F-8
  — nothing is deployed, so no hosted feedback row was written or read back.
- **2026-09-20 (session 32)** — Claude Code (Fable 5.1). **UCSF BETA SHARE
  PACK (docs only; no code, no deploy, no schema change).** Seven markdown
  files at the repo root, written from the "Nik tasks prompts" orchestration
  doc: `README_CASE_STUDY.md` (product design case study),
  `SMOKE_TEST_REPORT.md` (hosted beta, 11 pass / 0 fail / 1 not verified;
  papers and rows re-counted live in Supabase: 3 / 475), `PAPER_ACCESS_AUDIT.md`
  (verdict: hosted runtime makes no literature call; only ingestion does),
  `UCSF_BETA_HANDOFF_MESSAGE.md`, `UCSF_BETA_ONE_PAGER.md`,
  `BETA_EMAIL_WITH_TALLY_AND_BRIEF.md` (beta and Tally links filled in, `[CONTACT_EMAIL]` still a placeholder) and `HOSTING_STATUS.md`
  (live, both free plans, no blockers; API `/docs` is public). One smoke
  feedback row (feedback_id 42, record 1189) was created and then deleted.
  Prior 2026-09-16 "marked correct" feedback on record 1189 is still visible
  in the evidence panel; Nik decides whether to keep it. Links filled in:
  beta https://hiveblot-beta.vercel.app, Tally https://tally.so/r/A7kzWB.
  Hosted beta unchanged (Render autoDeploy
  off; Vercel not auto-deploying this branch).
- **2026-09-01 (session 31)** — Claude Code (Fable 5.1). **UCSF BETA-READINESS
  PASS (security migration + P0 communication + consolidated QA/UX; deployed
  web; Supabase migrated).** See CURRENT STATE above and
  `research/UCSF_BETA_READINESS.md` for the full report (before/after security
  matrix, QA findings, flagship results, UX findings, tests, verdict, checklist).
- **2026-08-27 (session 30)** — Claude Code (Fable 5). **PROFESSOR ORCHESTRATION
  BRIEF (docs only — no code, no deploy, no DB change).**
  `research/PROFESSOR_ORCHESTRATION_BRIEF.md`: a ~5-minute technical handoff
  for an external AI/ML professor reviewing our model orchestration. Contents:
  system overview, problem motivation, the ingestion cascade (CV Stage 1 →
  cheap-model Stage 2 → deterministic reconcile Stage 3 → status-gated Stage 4
  escalation) and query path as an annotated pipeline + component table
  (model / retrieval / deterministic / routing), current metrics with the
  central caveat stated plainly (Stage 2 has only ever run agent-in-the-loop;
  unseen-paper F1, escalation rate, token cost all unmeasured), a ranked
  optimization-candidate table (measure-first eval set → calibrated
  confidence routing → deterministic early-exit → error-specific escalation →
  k-sample agreement → panel batching), and 5 specific questions for the
  professor. Shareable web version published as a Claude artifact (URL inside
  the doc). Also: root `.gitignore` now ignores `.serena/` (local MCP tool
  state that appeared untracked). No tests affected.
- **2026-08-26 (session 29)** — Codex. **LIGHT/DARK THEME SYSTEM
  (frontend theme/styling only; no backend, search API, query semantics, URL,
  result schema, filters, database, evidence logic, ranking, extraction, or
  result-state change).** Added a compact, keyboard-accessible Light/Dark
  segmented control beside the header navigation. Theme selection updates the
  document immediately without reload/API activity, stores the explicit choice
  in browser `localStorage` under `hiveblot-theme`, and otherwise follows the
  initial system `prefers-color-scheme`. A pre-hydration script in the root
  layout applies `data-theme` and `color-scheme` before body rendering to avoid
  wrong-theme flash. Refactored the frontend around shared semantic CSS tokens
  for background/surfaces/text/borders/accent/status/chips/overlay/focus states,
  retaining the existing dark palette as the default and adding the intentional
  light scientific palette (`#f7f8f6` page, white cards/inputs, soft green-gray
  sidebar, dark text, deep teal accents, restrained purple, amber warnings,
  muted red errors). Converted hard-coded theme colors across home, About,
  Learn, search/results, filters, feedback, evidence, legacy results, and header
  surfaces to those tokens. Search is white with a filled teal submit action in
  light mode; cards remain white and restrained; figure/panel image backgrounds
  remain white in both themes. IBM Plex typography, all layout/data hierarchy,
  mobile filter drawer, and responsive behavior remain intact; on small screens
  theme labels collapse to icons and the wordmark text hides at <=520px to
  prevent header crowding. Files changed: `web/app/layout.tsx`,
  `web/app/globals.css`, active frontend pages/components with theme colors,
  new `web/components/ThemeToggle.tsx`, and this handoff. Verification: final
  `cd web && npm run build` passed; targeted ESLint passed for layout,
  ThemeToggle, Navigation, search page, filters, DatabaseResultCard, and
  BetaFeedback; `SearchFeedback.tsx` still has its documented pre-existing
  `react-hooks/set-state-in-effect` error unrelated to theme styling; `git diff
  --check` passed; live `/search?q=phospho%20STAT3%20Tyr705` returned 200 and
  server HTML contained both accessible theme labels plus the pre-hydration
  `hiveblot-theme` script; required biology checks passed under `.venv`:
  biology 165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10,
  pipeline wiring 11/11, benchmark 34/34. Automated browser screenshots were
  unavailable because the in-app browser control tool was not exposed; the
  local themed page was opened for direct inspection. No environment values or
  secrets were committed.
- **2026-08-26 (session 28)** — Codex. **SEARCH BAR ALIGNMENT VISIBILITY
  CORRECTION (frontend CSS only; no layout ownership, search behavior, filters,
  API, URL semantics, backend, schema, data, or evidence change).** Follow-up
  to session 27 after user feedback that the search bar itself did not look
  changed. The shared workspace grid was live, but the retained 920px search
  max-width and near-identical dimensions made the alignment shift too subtle.
  Removed the desktop max-width cap so the search control and examples visibly
  span the full results column, reduced control height from 52px to 48px,
  reduced the search heading from 22px to 19px, and tightened heading/helper
  spacing. The left edge remains exactly aligned with results and all search
  interactions/API behavior are unchanged. File changed:
  `web/app/globals.css` plus this handoff. Verification: final `cd web && npm
  run build` passed; targeted search/filter ESLint passed; `git diff --check`
  passed; reopened the local search route with a cache-busting URL; required
  biology checks passed under `.venv`: biology 165/165, reconcile 21/21,
  loader enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark
  34/34. No environment values or secrets were committed.
- **2026-08-26 (session 27)** — Codex. **SEARCH/RESULTS RESEARCH-WORKSPACE
  ALIGNMENT + MOBILE FILTER DRAWER (frontend presentation only; no search API,
  query semantics, URL parameters, database, backend, ranking, schema, filter
  composition, extraction, or evidence-classification change).** Reframed
  `/search` around one shared desktop workspace grid: the search heading,
  control, and examples now begin on the same horizontal axis as the results
  column while the persistent filter sidebar occupies the first grid track.
  Reduced search-section and result-card whitespace, tightened the desktop
  faceted sidebar, and retained the existing wide card hierarchy, prominent
  Western blot preview, temporary-preview disclosure, metadata, IBM Plex
  typography, dark theme, and teal accents. At <=900px, the sidebar is removed
  from document flow and exposed through a real Filters button as a scrollable
  off-canvas panel with backdrop, close control, Escape dismissal, background
  scroll lock, active-filter count, and hidden-when-closed keyboard behavior.
  The drawer reuses the same draft/applied filter state and existing
  Apply/Reset handlers; Apply still builds the same query and now also closes
  the drawer. No fake controls were added and View Evidence remains absent.
  Files changed: `web/app/search/page.tsx`, `web/components/FiltersBar.tsx`,
  `web/app/globals.css`, and this handoff. `SearchInput.tsx` and
  `DatabaseResultCard.tsx` were inspected but required no changes because their
  preserved content/behavior already matched the requested hierarchy.
  Verification: `cd web && npm run build` passed; targeted ESLint on search,
  filters, SearchInput, and DatabaseResultCard passed; `git diff --check`
  passed; live `/search?q=phospho%20STAT3%20Tyr705` returned 200 and the
  unchanged local `/api/search` proxy returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. Automated
  browser screenshots were unavailable because the in-app browser control tool
  was not exposed in this session. No environment values or secrets were
  committed.
- **2026-08-26 (session 26)** — Codex. **IBM PLEX TYPOGRAPHY SYSTEM
  (frontend styling only; no layout structure, search behavior, filters, API,
  backend, schema, data model, extraction, or result-data change).** Replaced
  the render-blocking Google Fonts CSS `@import` (Newsreader + Manrope + IBM
  Plex Mono) with Next.js `next/font/google` loading for IBM Plex Serif, IBM
  Plex Sans, and IBM Plex Mono. The optimized font variables are exposed as
  `--font-serif`, `--font-sans`, and `--font-mono` from the root layout and used
  consistently across the frontend. Semantic mapping now uses Serif for the
  HiveBlot/scientific identity, research headings, target/modification titles,
  experimental descriptions, and figure-caption text; Sans for navigation,
  search controls, result counts, filter values/actions, feedback controls,
  ordinary metadata values, and general UI copy; Mono for section/field labels,
  status/technical chips, lanes, and identifiers. Reduced prior monospace
  overuse in navigation/sidebar controls and removed all remaining
  Newsreader/Manrope declarations. Preserved existing dimensions, spacing,
  colors, borders, card/sidebar hierarchy, and behavior. Files changed:
  `web/app/layout.tsx`, `web/app/globals.css`, frontend pages under `web/app/`,
  typography-bearing components under `web/components/`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on the root
  layout, search page, result card, filters, and canvas passed; `git diff
  --check` passed; source scan found no legacy Newsreader/Manrope/font-import
  declarations; live `/search?q=phospho%20STAT3%20Tyr705` returned 200,
  preloaded optimized local WOFF2 assets, and exposed all three CSS variables;
  required biology checks passed under `.venv`: biology 165/165, reconcile
  21/21, loader enrichment 18/18, extract 10/10, pipeline wiring 11/11,
  benchmark 34/34. Automated browser inspection was unavailable because the
  in-app browser control tool was not exposed in this session. No environment
  values or secrets were committed.
- **2026-08-26 (session 25)** — Codex. **COMPACT SEARCH RESULTS VERTICAL
  RHYTHM (frontend styling/layout only; no search behavior, filters, API,
  backend, schema, query, extraction, or result-data change).** Tightened the
  `/search` workspace from the search heading through the first result card:
  reduced heading-to-input and input-to-example spacing, reduced search-header
  bottom padding while retaining its divider, moved the results workspace
  closer to that divider, and replaced the results header's large inline
  margins with scoped classes for compact title/count/feedback/card spacing.
  Preserved the current sidebar, result cards, typography sizes, dark/teal
  visual system, and responsive layout; the mobile breakpoint receives the
  same proportional tightening. Files changed: `web/app/globals.css`,
  `web/app/search/page.tsx`, `web/components/SearchFeedback.tsx`, and this
  handoff. Verification: `cd web && npm run build` passed; targeted ESLint on
  `app/search/page.tsx` passed; `git diff --check` passed; local
  `/search?q=phospho%20STAT3%20Tyr705` returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. Automated
  browser inspection was unavailable because the in-app browser control tool
  was not exposed in this session; the page was instead verified via the
  production build and live local HTTP route. No environment values or secrets
  were committed.
- **2026-08-26 (session 24)** — Codex. **SEARCH BAR UX/UI REFINEMENT
  (frontend presentation/interaction only; no backend/API/schema/query/filter/
  extraction/evidence data change, no deploy, no cloud DB/Supabase change, no
  production secrets).** Reworked the reusable `SearchInput` and `/search`
  header into one compact scientific search control: cohesive input + teal
  submit button with matching height and coordinated borders, inline accessible
  SVG search icon, improved placeholder (`Search protein, phosphosite,
  antibody, cell line...`), keyboard-accessible clear control, subtle clickable
  example queries that populate the field without submitting, preserved
  submitted query display, and loading/disabled `SEARCHING...` button state
  wired to the existing frontend `loading` flag. Reduced `/search` header/body
  vertical whitespace and widened/aligned the search control to the results
  workspace. Confirmed the search API contract is unchanged: `web/app/search/
  page.tsx` still submits only the query string to the existing `/api/search`
  proxy, URL `q` behavior remains in `handleSearch`, and no backend/filter
  query logic changed. Files changed: `web/components/SearchInput.tsx`,
  `web/app/search/page.tsx`, `web/app/globals.css`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on
  `components/SearchInput.tsx` and `app/search/page.tsx` passed; full
  `npm run lint` still fails only on pre-existing unrelated issues in
  `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`, and
  `web/components/SearchFeedback.tsx` (SearchInput is no longer part of the
  full-lint failure list); local `/search?q=phospho%20STAT3%20Tyr705` returned
  200; local web `/api/search` proxy returned 200; required biology checks
  passed under `.venv`: biology 165/165, reconcile 21/21, loader enrichment
  18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34. The plain
  `python3` biology commands failed on this machine because that interpreter
  lacks `pydantic`; rerunning the same commands with `.venv/bin/python` passed.
  Browser automation was unavailable in this Codex session (`node_repl js` was
  not exposed and Playwright was not installed), so UI QA was limited to build/
  lint, local HTTP checks, and opening the local page for inspection. Local
  gitignored env files may exist for the dev stack; no env values were
  committed.
- **2026-08-25 (session 23)** — Claude Code (Sonnet 5). **COMMIT LONG-STANDING
  LOCAL DEV CONFIG (frontend dev-server config only; no app/backend/schema/
  deploy change, no production secrets).** Committed `web/next.config.ts`'s
  `allowedDevOrigins: ["127.0.0.1"]`, which sessions 17–22 repeatedly noted as
  "existing uncommitted... left untouched." This silences Next.js's dev-server
  cross-origin warning when the local API/web stack is accessed via
  `127.0.0.1`; it has no effect on production builds. No tests affected (no
  code path changed).
- **2026-08-26 (session 22)** — Codex. **HIDE SEARCH-RESULT EVIDENCE PANEL
  INTERACTION (frontend presentation-only; no backend/API/schema/query/filter/
  extraction/evidence data change, no deploy, no cloud DB/Supabase change, no
  production secrets).** Removed the user-facing `View Evidence` interaction
  from `DatabaseResultCard`: no evidence button, no expandable `EvidencePanel`,
  and no visible field-level feedback/provenance controls in the current search
  results experience. The underlying `EvidencePanel.tsx`, record/feedback API
  routes, evidence/provenance fields, extraction pipeline, stored data, and
  backend behavior were left intact. Search result cards still show target,
  modification/status, sample, experiment, treatment, lanes, figure preview,
  chips, antibody/catalog, molecular weight, UniProt, page, and DOI/source.
  Files changed: `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, and this handoff. Verification: `cd web && npm run
  build` passed; targeted ESLint on `components/DatabaseResultCard.tsx` passed;
  search-card path grep found no remaining `View Evidence`/`EvidencePanel`/
  visible evidence-panel strings; full `npm run lint` still fails only on
  pre-existing unrelated lint issues in `web/app/learn/page.tsx`,
  `web/app/page.tsx`, `web/components/Navigation.tsx`,
  `web/components/ResultsCard.tsx`, `web/components/SearchFeedback.tsx`, and
  `web/components/SearchInput.tsx`; local
  `/search?q=phospho%20STAT3%20Tyr705` returned 200; local web `/api/search`
  proxy returned count 18; required biology checks passed again: biology
  165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10, pipeline
  wiring 11/11, benchmark 34/34. Existing uncommitted `web/next.config.ts`
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-26 (session 21)** — Codex. **RESULT CARD SAMPLE/EXPERIMENT +
  COMPACT METADATA REBALANCE (frontend layout-only; no backend/API/schema/
  query/filter/evidence/DOI/image change, no deploy, no cloud DB/Supabase
  change, no production secrets).** Refined `DatabaseResultCard` to remove the
  dedicated large Evidence/Source column from the main card layout. Desktop
  result rows now follow **primary result | sample/experiment | treatment/lanes
  | figure | tags + compact metadata | action**. Primary result now contains
  only the target/modification identity, status, as-printed label, and
  descriptive context. `Sample`, `Experiment`, organism, and IP bait moved into
  their own simple scan column. Treatment/lanes remain in their dedicated
  column. The former source metadata is preserved but compacted into the tags/
  metadata column alongside the existing-data chips (`WB`/`co-IP`, `Phospho`,
  design tag, lane count): antibody/catalog, molecular weight, UniProt, page,
  and DOI still render, but no longer occupy a standalone evidence/source
  column. `View Evidence` behavior is unchanged and still toggles the existing
  `EvidencePanel`. Files changed: `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, and this handoff. Verification: `cd web && npm run
  build` passed; targeted ESLint on `components/DatabaseResultCard.tsx` passed;
  full `npm run lint` still fails only on pre-existing unrelated lint issues in
  `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  local `/search?q=phospho%20STAT3%20Tyr705` returned 200; local web
  `/api/search` proxy returned count 18; required biology checks passed again:
  biology 165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10,
  pipeline wiring 11/11, benchmark 34/34. Existing uncommitted
  `web/next.config.ts` (`allowedDevOrigins`) was present before this task and
  left untouched.
- **2026-08-26 (session 20)** — Codex. **DEDICATED TREATMENT/LANES RESULT
  COLUMN (frontend layout-only; no backend/API/schema/query/filter/evidence
  change, no deploy, no cloud DB/Supabase change, no production secrets).**
  Refined `DatabaseResultCard` so desktop result rows now follow
  **primary result info | treatment + lanes | figure preview | experiment tags
  | evidence/source | action**. Treatment and lane chips moved out of the
  primary identity section into their own adjacent column; all lane chips now
  render and wrap naturally instead of truncating after eight lanes. Primary
  result info keeps target/modification, status, as-printed label, context,
  sample, experiment type, organism/IP bait when present. Figure preview,
  compact existing-data chips, source metadata, and `View Evidence` behavior
  are unchanged except for grid placement; dose/duration display now includes a
  space before units (`10 ng/ml`) as a frontend formatting-only cleanup. Medium
  screens reflow to two rows (**primary | treatment/lanes | figure**, then
  **tags | source | action**); mobile stacks in reading order. Files changed:
  `web/components/DatabaseResultCard.tsx`, `web/app/globals.css`, and this
  handoff. Verification: `cd web && npm run build` passed; targeted ESLint on
  `components/DatabaseResultCard.tsx` passed; full `npm run lint` still fails
  only on pre-existing unrelated lint issues in `web/app/learn/page.tsx`,
  `web/app/page.tsx`, `web/components/Navigation.tsx`,
  `web/components/ResultsCard.tsx`, `web/components/SearchFeedback.tsx`, and
  `web/components/SearchInput.tsx`; local `/search?q=phospho%20STAT3%20Tyr705`
  returned 200; local web `/api/search` proxy returned count 18; required
  biology checks passed again: biology 165/165, reconcile 21/21, loader
  enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34.
  Existing uncommitted `web/next.config.ts` (`allowedDevOrigins`) was present
  before this task and left untouched.
- **2026-08-26 (session 19)** — Codex. **SEARCH RESULTS ROW REFINEMENT
  (frontend-only; no backend/API/schema/query change, no deploy, no cloud
  DB/Supabase change, no production secrets).** Refined the session-18
  `/search` layout so result cards read less like three rigid database columns
  and more like one wide scientific catalog row. The left filter sidebar stayed
  intact and visually secondary; results now dominate the page width. Each
  desktop result row is organized as **primary scientific identity | centered
  figure preview | compact experiment chips | source metadata | action** with
  only one subtle outer card border, wider internal spacing, no heavy vertical
  panel dividers, a larger contained figure preview, compact chips derived only
  from existing result data (`WB`/`co-IP`, `Phospho`, design tag, lane count),
  lighter metadata rows for antibody/MW/UniProt/source, and a compact
  right-aligned `View Evidence` action that still toggles the same
  `EvidencePanel`. The STAT3 temporary image remains frontend-only at
  `/images/STATE3.png` and is labeled "Sample figure preview" so it is not
  presented as confirmed provenance. Files changed:
  `web/components/DatabaseResultCard.tsx`, `web/app/globals.css`,
  `web/app/search/page.tsx`, and this handoff. Verification:
  `cd web && npm run build` passed; targeted ESLint on changed frontend files
  passed; full `npm run lint` still fails only on pre-existing unrelated lint
  issues in `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  local API `/health` returned OK; local `/search?q=phospho%20STAT3%20Tyr705`
  returned 200; local web `/api/search` proxy returned count 18; required
  biology checks passed again: biology 165/165, reconcile 21/21, loader
  enrichment 18/18, extract 10/10, pipeline wiring 11/11, benchmark 34/34.
  In-app browser automation was unavailable in this Codex session, so visual
  QA was limited to local server checks plus opening the page for manual
  inspection. Existing uncommitted `web/next.config.ts` (`allowedDevOrigins`)
  was present before this task and left untouched.
- **2026-08-26 (session 18)** — Codex. **SEARCH RESULTS INFORMATION
  ARCHITECTURE REDESIGN (frontend-only; no backend/API/schema/query change, no
  deploy, no cloud DB/Supabase change, no production secrets).** Rebuilt the
  `/search` results surface around the requested BenchSci/ASCEND-style
  information hierarchy while keeping HiveBlot's existing dark visual system:
  top search bar, persistent left filter sidebar, active filter chips above the
  result list, and desktop result cards split into **Experiment information |
  Figure preview | Evidence / source**. Reused the existing filter concepts
  (protein, site/modification, experiment, cell line, vendor, catalog number,
  needs review) with the same explicit **Apply** action; filters still compose
  a plain query string that the existing deterministic backend parser already
  understands, and `/api/search` still receives only `{query}`. Evidence
  accordion, record-detail fetches, feedback paths, search URL behavior, and
  grouping by `stable_row_key` were preserved. Added/used the provided
  development image at `web/public/images/STATE3.png`; STAT3 cards show it via
  frontend-only `/images/STATE3.png`, with no image API or backend crop-path
  change. Files changed: `web/app/search/page.tsx`,
  `web/components/FiltersBar.tsx`, `web/components/DatabaseResultCard.tsx`,
  `web/app/globals.css`, `web/public/images/STATE3.png`, and this handoff.
  Verification: `cd web && npm run build` passed; targeted ESLint on changed
  frontend files passed; full `npm run lint` still fails only on pre-existing
  unrelated issues in `web/app/learn/page.tsx`, `web/app/page.tsx`,
  `web/components/Navigation.tsx`, `web/components/ResultsCard.tsx`,
  `web/components/SearchFeedback.tsx`, and `web/components/SearchInput.tsx`;
  `curl -I http://127.0.0.1:3000/search?q=phospho%20STAT3%20Tyr705` returned
  200; local web `/api/search` proxy returned 18 rows for
  `phospho STAT3 Tyr705`; required biology checks passed again: biology
  165/165, reconcile 21/21, loader enrichment 18/18, extract 10/10, pipeline
  wiring 11/11, benchmark 34/34. Existing uncommitted `web/next.config.ts`
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-25 (session 17)** — Codex. **LOCAL DEV REQUIREMENTS WIRED +
  LOCAL STACK OPENED (docs/dependency only; no production code path change, no
  deploy, no cloud DB/Supabase change, no production secrets).** Added root
  `requirements-local.txt` for teammates who need local search/results/cards:
  it includes `api/requirements.txt`, `western_blot_miner/requirements.txt`,
  and local-only `pgserver`. Updated `research/team_delegation/ENV_SETUP.md`
  so the setup command installs `requirements-local.txt`; Render/production
  continues to install `api/requirements.txt` only, so `pgserver` stays out of
  the production API dependency surface. Local verification on
  `feature/bio-context-beta`: `python3.12 -m venv .venv`; pip install from
  `requirements-local.txt` succeeded; `scripts/local_db.py up` started embedded
  Postgres at `.localdb/` (local pg_trgm unavailable, index skipped as expected
  per helper); `scripts/local_db.py load eval/demo/*/supabase_rows.json` loaded
  475 rows; `scripts/local_db.py status` confirmed 475 rows; local FastAPI
  `/health` returned 200; local `/search` for `phospho STAT3 Tyr705` returned
  18 rows; existing local Next dev server on `http://127.0.0.1:3000` served 200
  and proxied `/api/search` to the local API with 18 rows. Created gitignored
  local `.env` files only for this machine using local values; no env values
  were committed. Required checks run after setup: biology 165/165, reconcile
  21/21, loader enrichment 18/18, extract 10/10, pipeline wiring 11/11,
  benchmark 34/34. Existing uncommitted `web/next.config.ts` change
  (`allowedDevOrigins`) was present before this task and left untouched.
- **2026-08-24 (session 16)** — Claude Code (Fable 5). **TEAM LOCAL-DEV ENV
  PLAN (docs + .gitignore only; no code, no deploy, no credential rotation,
  no Supabase change, QIB untouched).** `research/team_delegation/
  ENV_SETUP.md`: per-teammate least-privilege env plan for the 6-person team
  (Suhas D, Ananya A+D, Srushti C, Tanvi B+A, Yashvi coordination, Nik
  owner). Core: **the local stack needs ZERO production secrets** —
  `scripts/local_db.py` embedded Postgres + self-generated local
  `INTERNAL_API_KEY`/`AGENT_API_KEYS`; cloud `SUPABASE_*`/`OPENAI_KEY` stay
  empty. Only shared credential: cloud `DB_READONLY_URL` (`hive_readonly`,
  SELECT-only on `western_blot_records`, session-12-audited) to **Suhas
  only**, staged outside the repo at `~/hiveblot-env-handoff/suhas/` (0600)
  for password-manager share or AirDrop — never messaging apps. Forbidden to
  distribute: cloud `DB_FEEDBACK_URL` (write-capable), `SUPABASE_KEY`,
  production `INTERNAL_API_KEY`/`AGENT_API_KEYS`, Nik's model keys,
  Vercel/Render auth. **Gap fixed: `western_blot_miner/.env` was NOT
  gitignored** (api/ and web/ ignore their own; the miner had no rule) —
  root `.gitignore` now ignores `western_blot_miner/.env*` except the
  example. Verified: no `.env` tracked in git (examples only). PR #1
  (branch → main) remains open, unmerged; all work stays on
  `feature/bio-context-beta`.
- **2026-08-18 (session 15)** — Claude Code (Fable 5). **TEAM DELEGATION
  PACKAGE (docs only — no product code, no deploy, no DB change).** The
  founder-walkthrough findings (`/Users/niks/Downloads/
  HiveBlot-Founder-Walkthrough.md`) were turned into
  `research/team_delegation/`: `MASTER_DELEGATION.md` (product state,
  scope guardrails, findings by domain with priorities, 4 workstreams + Nik,
  coordination rules), four role-based handoffs (`BIOLOGY_QA_HANDOFF.md`,
  `SCIENTIFIC_COMMUNICATION_HANDOFF.md`, `PRODUCT_UX_HANDOFF.md`,
  `SEARCH_DATA_HANDOFF.md` — each teaches the concept it touches via a
  "What you should understand before finishing" section), and
  `NIK_FOUNDER_LEARNING.md`. Role-based, not named: project docs identify
  collaborators only by infra actions (Suhas: legacy QIB; Srushti: clean
  Supabase project), insufficient to map specialties — Nik assigns.
  **Priorities: P0 = `/about` fabricated numbers (2.8K/12.4K/520) +
  automated-ingestion claims (only P0).** P1: `/learn`
  Upregulated/Downregulated + densitometry mismatch, homepage first-run
  guidance, needs-review reason not shown in lists, internal values rendered
  as paper quotes (`ambiguous_family`, `{}`, candidate "none", empty WHY
  section), `image_crop_ref` absolute-path leak (plan only — ties to the
  existing relative-ref open question), `GAPDH mouse` organism
  investigation (investigate-only; parser must not hallucinate filters),
  scientific QA re-run vs the 93-experiment grouping, terminology glossary.
  P2: next-action UX exploration, confidence-display question, `RESULTS -`
  dash, cold-start copy, audience statement. Workflow: OBSERVE → UNDERSTAND
  → ASSIGN → then FIX; all fixes deferred to workstreams; Nik alone deploys.
- **2026-08-18 (session 14)** — Claude Code (Opus 5). **P0 IDENTITY FIX + FULL
  HOSTED BETA LIVE.** **Web https://hiveblot-beta.vercel.app · API
  https://hiveblot-api.onrender.com · DB Supabase `zafombwswztvnjikcsdm`.**
  Old QIB untouched (never linked, queried or seeded).
  **ROOT CAUSE.** `_record_id` hashed paper + figure/panel + crop + raw target
  + treatment context but **omitted the biological system**. Crop
  `page_004_cand_0025.png` (PMC12706926) prints **H1792 and A549 side by
  side**, so P62/LC3B/ACTB each collapsed two distinct experiments into one id
  — 12 duplicate keys / 24 of 475 rows; feedback on the H1792 arm could
  rehydrate onto the A549 arm. Diffed every collision field-by-field: **all 3
  groups differed ONLY by `cell_line`/`sample` — one class, one cause.**
  The deeper flaw: **two disagreeing notions of "one experiment"** — search
  grouping had its own composite key.
  **NEW STABLE IDENTITY.** `stable_row_key = <experiment hash>:<lane_index>`;
  hash = sha1(paper doi/pmcid/pmid | figure_label | panel_label | crop filename
  | raw_target | treatment_context | **normalized sample**)[:16], via new
  `record_builder.identity_sample()` (same `sample or cell_line` precedence as
  `_sample_info`; case/whitespace-folded — deliberately NOT applied to target
  labels, where case is semantic: uppercase `P-` is not a phospho marker).
  **Only OBSERVATION data feeds it** — reconciliation outputs
  (modification/experiment_type/ip_bait/protein_status/confidence/needs_review),
  DB serials and display text are excluded and each is pinned by a test, so
  engine improvements can never orphan stored corrections. Lane identity stays
  the reviewed panel's **index**, not its printed condition (immune to the
  display-only lane formatter). **Search grouping now reads that same hash**
  (`stable_row_key` added to the list schema `WesternBlotRecord`), so the card
  boundary and the feedback boundary are one thing.
  **SECOND COLLISION CLASS FOUND (same flaw, opposite direction).** The old
  grouping key carried no treatment context, so on crop `page_005_cand_0034` —
  which holds **two** experiments — it concatenated the 6-lane **Fig 3C (no
  IL-6)** strip and the 7-lane **Fig 3D (with IL-6)** strip into ONE 13-lane
  card for T-Stat3 and β-actin. That is exactly session 7's C1 conflation,
  still live in the UI. **Experiment count 91 → 93 is a CORRECTION, not
  drift**: it splits 2 cards that should never have been one; no flagship query
  changes its card count. Verified in the hosted UI (T-Stat3 now renders 6-lane
  and 7-lane cards with their own Fig 3C / Fig 3D identity lines).
  **UNIQUENESS PROOF.** Artifacts regenerated through the REAL pipeline (not
  patched); diffing each regenerated file against its committed version shows
  **every biological field, provenance envelope and validation flag
  byte-identical, `record_id` the only change**. Corpus + remote DB both:
  **475 rows / 3 papers / 475 distinct `stable_row_key` / 0 duplicate groups /
  93 experiment hashes / 0 null provenance / 21 crop refs valid / 0 legacy QIB
  rows.**
  **FEEDBACK ISOLATION PROOF (real, against cloud).** A = P62/H1792
  (`d95fb4cda43a320f:1`), B = P62/A549 (`8ee3bb5a3555e3cd:1`) — same crop, same
  target, formerly ONE id. Feedback → A: appears on A, **absent on B**. Then a
  full reseed regenerated serials (A 594→1069, B 610→1085): A's feedback
  **rehydrated by stable key onto the new id**, B still clean. Repeated
  end-to-end through the hosted stack. All smoke rows deleted;
  `hiveblot_feedback` back to **0 rows**.
  **DEPLOY.** Render `hiveblot-api` (`srv-da1rbvs9v7es738635ug`), **plan free**,
  Docker, repo `nikhilesh-s/hive`, branch `feature/bio-context-beta`,
  `autoDeploy: false`; deployed commit `bc923bb` → status **live**, `/health`
  200 (~0.15 s warm), and the deployed revision proven new (list rows now carry
  `stable_row_key`). Vercel `hiveblot-beta` production re-pointed to the Render
  origin and redeployed; `ALLOWED_ORIGINS` is the Vercel origin only (never
  `*`). Seeding again used a temporary `hive_seed` role, revoked + DROPped
  after (only `hive_readonly` / `hive_feedback` remain).
  **HOSTED VERIFICATION (all through the public frontend):** `/` and `/search`
  200; `phospho STAT3 Tyr705` 18 rows/3 cards (88.1 expected, reported null —
  distinct; CST 9145), `co-IP PIK3CA` 14/4 with **IP BAIT = PIK3CA** and
  Input/IgG/IP lanes, `CST 9145` 18/3, `P-ERK` 10/2 **Conflicting** with the
  "Why unresolved" sentence and both competing claims and no winner,
  `GAPDH mouse` 31/5 mouse loading-control, `needs review` 20/4,
  `BRCA1 MCF7 olaparib` **0** with scoped copy. Crops served as real PNGs over
  the hosted proxy (442,670 B and 247,631 B, PNG signature verified).
  **15 hosted browser assets scanned: no DSN, no DB user/password, no pooler
  host, no INTERNAL_API_KEY, no Supabase key/JWT, no `NEXT_PUBLIC_*`.**
  Tests: biology **165/165**, reconcile 21/21, loader ok, extract 10/10,
  pipeline 11/11, **stable-row-key 34/34 (NEW suite)**, benchmark 34/34,
  harness 3/3 papers EXACT, api **113/113**, `tsc` clean.
  **Model automation remains future work — the 3/3 EXACT harness is a
  self-consistency check on the reviewed reference set and says NOTHING about
  extraction accuracy on an unseen paper.**
- **2026-08-17 (session 13)** — Claude Code (Opus 5). **ZERO-COST STACK: WEB
  DEPLOYED, API ONE LOGIN AWAY.** Stack is now **Supabase Free + Render Free
  Web Service + Vercel Free**. **Railway is dropped** as the recommended API
  host (kept as a one-line alternative only).
  **WEB IS LIVE: https://hiveblot-beta.vercel.app** — Vercel project
  `hiveblot-beta` (org `nikhilesh-suravarjjalas-projects`), Hobby/free,
  production deploy Ready, HTTP 200 publicly. `API_BASE_URL` +
  `INTERNAL_API_KEY` set on Production/Preview/Development; **neither is
  `NEXT_PUBLIC_*`**. `API_BASE_URL` currently holds a PLACEHOLDER
  (`https://hiveblot-api.onrender.com`) and **must be re-set + redeployed**
  once the real Render host exists — Vercel does not hot-swap env values into
  an existing build.
  **API NOT DEPLOYED — the one blocker is a Render browser login.** Render CLI
  v2.23.0 installed (`brew install render`) but unauthenticated (no
  `~/.render`), so the canonical path is the dashboard Blueprint. Added
  **`render.yaml`** (committed): one web service `hiveblot-api`, `runtime:
  docker`, **`plan: free`**, `dockerfilePath: ./api/Dockerfile`,
  `dockerContext: .`, `healthCheckPath: /health`, `autoDeploy: false`, branch
  `feature/bio-context-beta`; the 4 secrets are `sync: false` (dashboard-only,
  never in git) and `ALLOWED_ORIGINS` is already pinned to the live Vercel
  origin.
  **Render compatibility audited:** CMD already binds `0.0.0.0:${PORT:-8000}`
  so Render's injected `PORT` works and local dev is unchanged; config reads
  pure env vars (no `.env` in the image); `/health` is unauthenticated.
  **Audited and confirmed: the API performs ZERO runtime filesystem writes** —
  Render's ephemeral disk is therefore safe, and Supabase remains the only
  persistence layer (feedback included).
  **`api/crops/` is now TRACKED (21 PNGs, ~6 MB)** — Render builds from the
  GitHub clone, so gitignored crops would have meant no figure evidence in the
  hosted beta; verified all 21 DB `image_crop_ref` values map to a staged file.
  **Supabase re-verified:** still linked to `zafombwswztvnjikcsdm`, 475 rows /
  3 papers / **91 experiment groups**. **Smoke-test feedback rows CLEARED** —
  `hiveblot_feedback` is now **0 rows**, ready for the team.
  **⚠ `stable_row_key` uniqueness is NOT 100% — 463 distinct of 475, 12
  duplicate keys (24 rows).** The session-12 follow-up was never run; this is
  the same pre-existing co-IP defect (the `page_004_cand_0025.png` crop prints
  H1792 and A549 side by side; `_record_id` omits cell line). Feedback on one
  of those rows can surface on its twin. Deploying does not make it worse, but
  it is live in the hosted beta and is disclosed in the team doc.
  Docs: `DEPLOYMENT.md` rewritten around the free stack incl. Render's
  spin-down / cold-start / ephemeral-disk behaviour;
  `research/TEAM_BETA_HANDOFF.md` carries the live web URL and the cold-start
  warning. Tests: biology **165/165**, reconcile 21/21, loader ok, extract
  10/10, pipeline 11/11, benchmark **34/34**, harness **100% EXACT**, api
  **113/113**, web `tsc` clean + production build clean.
- **2026-08-17 (session 12)** — Claude Code (Opus 5). **CLOUD DATABASE LIVE ON
  THE CLEAN BETA PROJECT.** Deployment target is now Supabase
  **`zafombwswztvnjikcsdm`** (`https://zafombwswztvnjikcsdm.supabase.co`,
  us-east-1, PG 17.6). **The old QIB project `belalrbfrndxvdwvjxte` is NO
  LONGER A DEPLOYMENT TARGET** — never link/push/seed to it (empty migration
  history means a `db push` would ALTER Suhas's production tables).
  **Migrations:** repo re-linked; project verified fresh (0 tables, 0
  migrations, no hive roles); `db push --dry-run` showed exactly the canonical
  4-migration chain, no seeds, no `roles.sql`; pre-flight proved all 57 seed
  columns exist in the 73 migration columns; **push applied all 4, all recorded
  in remote history**. **Remote schema verified:** `western_blot_records` 73
  cols, `hiveblot_feedback` 16 cols, **`confidence` = `real`**, `stable_row_key`
  TEXT on both tables, `pg_trgm` 1.6, **17 indexes** (incl. the GIN trigram on
  `target`). **Security verified against `information_schema` + `pg_authid`:**
  `hive_readonly` = SELECT only; `hive_feedback` = INSERT+SELECT on
  `hiveblot_feedback` ONLY with **zero grants on `western_blot_records`** and
  USAGE on only the feedback sequence; neither role is superuser/createrole/
  createdb/bypassrls; both passwords set (SCRAM confirmed — note `pg_roles.
  rolpassword` always reads non-null and proves nothing). Roles are created **by
  the migrations**, not a `supabase/roles.sql`. Seeding needed INSERT, which
  neither restricted role has by design, so a **temporary `hive_seed` role was
  created, used, then revoked and DROPped** (verified: only the two designed
  roles remain). **Seed: 475 rows / 3 papers / 91 experiment groups**, zero
  dropped keys, 0 null `stable_row_key`, 0 null `provenance`, and **zero legacy
  QIB data** (0 `p53` rows, 0 legacy paper_ids). **Cloud verification (local API
  → cloud DB, all green):** `/health`; all 7 flagship searches — `phospho STAT3
  Tyr705` 3 groups/18 lanes, `co-IP PIK3CA` 4 co-IP groups + IP BAIT=PIK3CA,
  `CST 9145`, `GAPDH mouse` 5 groups with DEVELOPMENTAL SERIES on the E14.5/P0/
  P28 panels and correctly **untagged** ligation panels, `needs review`,
  `P-ERK` = MAPK1/MAPK3 **Conflicting** with both claims and no winner,
  `BRCA1 MCF7 olaparib` 0 results with scoped copy; record detail; **crops
  served (1153x909 PNG)**; feedback INSERT + rehydration (2 smoke rows render
  as RESEARCHER FEEDBACK beside the fields); lane-specific durations and
  "varies by lane: 0-60 min"; explicit-submit proven again (30 chars typed +
  2.5 s → **zero** fetches); **21 browser assets scanned: no DSN, no
  INTERNAL_API_KEY, no Supabase key, no `NEXT_PUBLIC_*`**.
  **Deployment prep:** `api/Dockerfile` (+ `Dockerfile.dockerignore`) and
  `scripts/stage_crops.py` (21 crops / 6.2 MB staged into `api/crops/`, so the
  container serves crops with zero code and zero corpus change);
  `DEPLOYMENT.md` rewritten for the new project incl. the **pooler-not-direct**
  rule (`db.<ref>` is IPv6-only; use Supavisor **session mode 5432**, not
  transaction 6543 which breaks asyncpg prepared statements).
  `research/TEAM_BETA_HANDOFF.md` written.
  **NOT DEPLOYED YET — one credential boundary:** Vercel CLI is authenticated
  (`nikhilesh-s`) so web can ship, but no container host is logged in
  (`railway login` needed; no Fly/Render CLI). Web alone is useless without the
  API, so nothing was published.
  **NEW KNOWN ISSUE (pre-existing, not caused by deployment): 12 duplicate
  `stable_row_key` values across 24 of 475 rows.** The co-IP crop
  `page_004_cand_0025.png` prints **H1792 and A549 side by side**; the search
  grouping key includes `cell_line` (so the UI correctly shows 2 cards) but
  `_record_id` does **not**, so P62/LC3B/ACTB collide across the two cell lines
  and feedback on one rehydrates onto its twin. Session 9's "113/113 unique"
  covered the phospho paper only. Fix = add cell line to `_record_id`; that
  rehashes every `stable_row_key` and needs a reviewed reseed, so it is
  deliberately NOT done here. Tests: biology **165/165**, reconcile 21/21,
  loader ok, extract 10/10, pipeline 11/11, benchmark **34/34 (100%)**, harness
  **100% EXACT** on all 3 papers, api **113/113** (incl. migration drift
  guard), web `tsc` clean + production build clean.
- **2026-08-17 (session 11)** — Claude Code (Opus 5). **BETA-TABLE INSPECTION +
  PLAN (READ-ONLY). Nothing altered, in QIB or anywhere.** Suhas created
  `western_blot_records_beta` and `blot_results_beta` inside the QIB production
  database. Full analysis: **`research/supabase_beta_table_plan.md`**.
  **Inspection:** both exist, both **0 rows**, and both are **exact structural
  copies of the legacy production tables** — identical column names, order,
  types, defaults and nullability (diffed field-by-field; only the copied
  functional index is auto-renamed `blot_results_beta_lower_idx`, the signature
  of `CREATE TABLE … (LIKE … INCLUDING ALL)`). So
  `western_blot_records_beta` is 12 columns with **`confidence text`** and a
  pkey-only index — it inherits *every* gap from the legacy audit. Still absent
  project-wide: `hiveblot_feedback` (any form), **`hive_readonly`**,
  **`hive_feedback`**, the trigram index, and any migration history.
  **Gap vs canonical: 61 missing columns** (60 from migration 001 +
  `stable_row_key`), 1 type change (`confidence text → real`, **required** —
  the seed inserts floats and asyncpg is strict), 10 missing indexes, plus a
  whole feedback table. `stable_row_key` itself would port cleanly (plain TEXT
  + b-tree, name-independent). Note numbering: CLI copy `…0004` **is**
  canonical `migrations/003`; there is no fifth migration.
  **RECOMMENDATION — do NOT use the beta tables; wait for Srushti's separate
  HiveBlot project.** The blocker is not effort: `/search` needs the
  `hive_readonly` role and `/feedback` needs `hive_feedback`, and Postgres
  **roles are cluster-level, not table-level**; the trigram index needs
  database-wide `CREATE EXTENSION pg_trgm`. All three land outside the two beta
  tables, against the "do not modify production roles/schema" constraint — so
  Option A **cannot be executed** without a fresh exception from Suhas. Also:
  `supabase db push` is unusable against QIB (empty remote history ⇒ it would
  apply the production-targeted migrations; the only fix writes production
  migration history, also forbidden), so the beta route means hand-pasting a
  ~700-line `_beta` SQL fork that sits **outside** the drift guard, plus code
  edits to `api/app/db.py` (feedback table is hardcoded) and
  `scripts/seed_remote.py` — all of it reverted later. `TABLE_NAME` is already
  env-configurable, so the records table alone would have been config-only.
  **This supersedes session 10's `hive-beta` branch recommendation:** Srushti's
  separate project is the same isolation with no plan upgrade, no per-hour
  branch compute, and HiveBlot ownership. Keep the persistent branch as the
  fallback only if her project stalls. Two items left unverified because they
  need a SQL console (neither changes the recommendation): whether the beta
  `id` default points at production's sequence, and RLS/policy state on the
  beta tables — exact read-only queries are in the plan doc §1.5. Production
  re-verified untouched: 616 + 2 rows. Docs only; api tests 113/113.
- **2026-08-17 (session 10)** — Claude Code (Opus 5). **LEGACY SUPABASE AUDIT
  (READ-ONLY). No production change.** The original hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`, org SuhasKM's-Org, us-west-2, PG 17.6) is now
  linked; CLI 2.113.0, already authenticated. Full findings:
  **`research/supabase_legacy_audit.md`**. Headlines: production `public` holds
  exactly two tables — **`western_blot_records` 616 rows** (5 papers, 64 of
  those rows an exact duplicate of another 64 under a second `paper_id`
  spelling) and **`blot_results` 2 rows** (fabricated demo: `p53 paper 1.pdf`,
  placeholder DOI `10.1234/example.2024`; referenced by no source file).
  **Migration history is EMPTY** — all four local migrations unapplied; prod was
  built by hand, so `db push` must never target it (`create table if not
  exists` would sail past and then ALTER prod). Production's 12 columns are
  exactly `api/db/schema.sql`'s list and order ⇒ **it IS a lineal ancestor of
  the current base table**, with one divergence: **`confidence` is `text`, not
  `real`** (the reviewed seed inserts floats ⇒ asyncpg would hard-fail). Also
  absent: all 60 migration-001 columns, `hiveblot_feedback`, `stable_row_key`,
  the GIN trigram index on `target`, and **both `hive_readonly` and
  `hive_feedback` roles** (verified against the full server role list).
  Legacy data is **not** worth migrating as evidence — it bakes in the banned
  p-prefix heuristic (62 `p53` + 4 `PARP` rows typed `phospho_signaling`), has
  no provenance/UniProt/residue/status, 4 of 6 `paper_id`s are filenames, and
  `confidence` is a constant `'0.9'`. Its one real value is a **5-paper
  shortlist for re-ingestion** through the current pipeline (zero paper overlap
  with the reviewed corpus). **Security finding (no action taken): both tables
  are fully readable with the project's anon key** — RLS is off or not
  restricting anon reads; write exposure deliberately untested (a probe would
  have mutated prod) — verify in the dashboard.
  **Recommendation (NOT implemented): a Supabase branch `hive-beta`, created
  PERSISTENT, not preview** — the beta must outlive any PR because collecting
  `hiveblot_feedback` from UCSF researchers IS the deliverable. Branching is
  available (`supabase branches list` → `[]`). Create **without `--with-data`**,
  re-link to the branch ref, `db push` the four migrations, verify
  `confidence real` (branch-only `ALTER` if the parent's `text` carries over),
  set the two role passwords, then `seed_remote.py` → 475 rows. Fallback if
  branching is plan-gated: a separate standalone project. No files outside
  `research/` + this HANDOFF changed; no tests affected.
- **2026-08-16 (session 9)** — Claude Fable 5. **FINAL INTERNAL-BETA FIX PASS.**
  All reproducible manual-beta findings fixed; no scientific regressions.
  **P0 feedback persistence/rehydration — diagnosed, fixed durably.** The
  manual P-ERK correction HAD persisted (row 6); the gap was (a) no retrieval
  path and (b) a worse latent hazard: reseeds regenerate serial ids, orphaning
  ALL feedback (verified: every stored row pointed at a dead id). Fix at the
  data layer: **migration 003** adds `stable_row_key` (= record-hash:lane_index,
  computed from reviewed observation data, reseed-proof) to both tables;
  `_record_id` strengthened with crop + treatment context so the Fig 3C/3D twin
  records no longer collide (20/20 distinct; 113/113 unique row keys).
  `GET /records/{id}/feedback` rehydrates by serial id OR stable key; the
  evidence panel shows prior feedback as a clearly-labeled RESEARCHER FEEDBACK
  annotation beside (never inside) the extraction. **Proven live: feedback
  submitted on id 4019 rehydrated on id 4494 after a full reseed.** Pre-003
  feedback rows (1–6) lack stable keys and stay orphaned-but-preserved.
  **P0 lane-series representation:** series-derived treatment candidates are
  now tagged `lane_series`; the UI renders "varies by lane: 0–60 min (see
  lanes below)" instead of a false "not reported" + pick-a-winner candidate
  list. **P0 design-tag false positives:** DOSE SERIES now requires explicit
  dose semantics (unit in lanes or context); developmental-stage lanes
  (E14.5/P0/P7/P28M) get their own DEVELOPMENTAL SERIES tag; ligation labels
  (L5d/DL14d) abstain. Verified on GAPDH mouse. **P0 multi-condition summary:**
  TREATMENT now reads e.g. "IL-6 (± CL-E, Bis II, U0126)" — co-conditions taken
  verbatim from the group's own lane labels. **P0 conflict explanation:** a
  generated "Why unresolved: …" sentence built only from the structured
  candidates (never picks a winner). **P1:** co-IP cards render "co-IP" + an
  IP BAIT field (from the panel's printed IP: lane); "DOI:" label; scoped
  zero-result copy ("…in the current HiveBlot beta dataset… does not mean no
  such evidence exists in the literature"). Supabase flow is now 4 migrations
  (docs + CLI copies + drift guard updated). Tests: engine suites green,
  benchmark 34/34, harness 100% EXACT, **api 113/113**, tsc clean. All seven
  flagship queries verified in-browser incl. zero-result and reseed-survival.
- **2026-08-13 (session 8, night sprint)** — Claude Fable 5. **MANUAL-TEST FIXES +
  SUPABASE READINESS.**
  (1) **Search is explicit-submit only** (manual issue 1): typing never fires a
  request; Enter or the new SEARCH button submits; submitted queries land in the
  URL via replaceState (shareable/refresh-safe); `?q=` auto-load unchanged and
  now also populates the input box. Browser-verified: 12 chars typed + 2 s wait
  → zero /api/search requests; button + real-KeyboardEvent Enter both submit.
  (2) **Experiment-card identity** (manual issue 2): each grouped card shows an
  identity line — a deterministic design tag derived ONLY from the group's own
  lane labels (≥3 pure timepoints → TIME COURSE; ≥3 shared-prefix distinct
  trailing numbers → DOSE SERIES) plus the reviewed record's verbatim
  `treatment_context` (truncated). Nothing invented; the Fig 3C/3D records
  carry their figure labels because the reviewed context text starts with them.
  The flagship query's three cards now read: TIME COURSE / "Fig 3D: …
  inhibitor matrix" / DOSE SERIES. Also removed the TREATMENT-field fallback to
  treatment_context (was duplicating the new identity line on co-IP cards).
  (3) **`IL-6 · 3D` RESOLVED — it was a fabricated duration** (manual issue 3):
  the paper never states a 3-day treatment; the case-insensitive duration regex
  parsed the FIGURE REFERENCE "Fig 3D" in the treatment context as "3 D(ays)"
  (same trap: "Fig. 3H" → 3 hours, "3D culture" → 3 days). Engine fix, two
  layers: single-letter units h/d must be lowercase (multi-letter units stay
  case-insensitive via scoped (?i:)), and `is_figure_reference_number()` guards
  every dose/duration/series match against a preceding fig/figure/panel
  reference (a rejected figure-list span is also consumed so its trailing
  number cannot leak back as a single). "Figure 2, 4 h exposure" keeps its real
  4 h. Phospho paper regenerated: Fig 3D records now duration=MISSING (the
  captured context states no duration). 10 new regressions.
  (4) **Lane readability** (manual issue 4): display-only formatter — trailing
  +/− state markers get colons and " / " becomes " · " ("IL-6: + · CL-E: −");
  conjunction "+" ("CL-E + Bis II") untouched; semantics unchanged.
  (5) **Supabase CLI readiness**: `supabase/config.toml` + timestamped
  `supabase/migrations/` copies of the canonical SQL, `scripts/
  sync_supabase_migrations.py`, and a pytest drift guard (byte-equality) so
  `supabase db push` and the SQL-editor flow can never diverge. Role grants
  audited: hive_feedback = INSERT+SELECT on hiveblot_feedback only, zero grants
  on western_blot_records. DEPLOYMENT.md rewritten: exact CLI sequence (login →
  link → db push --dry-run → push → role passwords → seed_remote.py, expect 475
  rows), exact env-var NAMES from api/app/config.py, 8-step smoke checklist.
  Browser-verified end-to-end: flagship query → 3 experiments (18 lanes) with
  distinct identities; co-IP PIK3CA → 4 grouped co-IP experiments, bait/IgG/
  Input intact; evidence panel + crop (1153 px PNG) + 33 feedback controls on
  grouped cards. Tests: **biology 165/165**, api **112/112**, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean. Model creds + cloud Supabase:
  re-checked, still absent (user actions below).
- **2026-08-13 (session 7)** — Claude Fable 5. **REVIEW SWEEP + CROP SERVING +
  RULE HARDENING.** Three parallel review agents ran; main agent implemented.
  (1) **Figure crops now render in the evidence panel**: `GET /records/{id}/crop`
  serves the record's own panel PNG (path from the DB column only, validated
  inside `CROP_BASE_DIR`, .png-only; 404→text fallback in deployments without
  the archive; 5 new API tests incl. traversal). Verified live end-to-end.
  (2) **Band-pattern rules hardened** — the independent probe-driven review
  (`research/band_pattern_scientific_review.md`) found 4 ship-blockers, all
  fixed with regressions: negation now abstains ("no smearing" no longer
  asserts smear); singular "higher-MW band" is not a ladder; caption-derived
  patterns on multi-lane panels are AMBIGUOUS, never per-lane SUPPORTED;
  absent+pattern contradictions raise BAND_PATTERN_STATE_MISMATCH (+ eval
  stamps corrected to present lanes only → 26 doublet lanes). Plus:
  "polyubiquitin smear"→ladder via containment pruning; count guard for
  "Fig. 3 bands"/"n = 3"/"1-2 bands"; parenthetical patterns no longer leak
  across "and".
  (3) **Demo dry-run** (`research/demo_readiness_review.md`): every scripted
  query verified live against the API; demo doc fixed (`needs review P-ERK`
  step, crop beat, 91-experiments close line, 20/min rate-limit warning).
  (4) **`scripts/seed_remote.py`** closes the DEPLOYMENT.md remote-seed TODO.
  (5) **Independent scientific QA delivered and acted on**
  (`research/independent_scientific_qa.md`: 3 Critical / 12 Major / 8 Minor /
  12 verified-correct). All three Criticals FIXED + regression-tested:
  **C1** — one CV crop (phospho paper cand_0034) held TWO experiments (Fig 3C
  + 3D); the collapsed observation asserted IL-6 on the Ser727 arm although
  the legend says Fig 3C ran WITHOUT IL-6. Reference data corrected to the
  printed 6-/7-lane matrices (unverifiable band states → `uncertain`); README
  correction note added. Phospho paper now 20 records / 113 rows; DB 475.
  **C2** — engine bug: an anti-ubiquitin antibody's own antigen name asserted
  `modification_type=ubiquitination` SUPPORTED (same failure class as the
  banned p-prefix rule). detect_modification now treats a mod-word that IS the
  whole target as protein identity; "ubiquitinated EGFR" still claims.
  **C3** — the session-4 self-audit contained false claims; correction banner
  added, independent QA is authoritative. Majors fixed: **M6** (µ-sign doses
  were dropped; series regex fabricated "1 nM" from "BafA1" — both fixed),
  **M7** (ACTB/TUBA1B now loading controls — 81 rows were misclassified),
  **M9** (doubtful BEX2 doublet removed; QA-confirmed Fig 1C LC3B doublet
  added; β-actin Greek-letter now resolves via beta-normalization), **M10**
  (README coverage note: Fig 5A/5B fell below the CV threshold — post-filter
  count ≠ paper content). Still open (documented, next-queue): M5 per-lane
  dose coverage (lane labels carry bare numbers, unit lives in the axis
  label), remaining Majors/Minors listed in the QA file.
  Creds RE-CHECKED: model backend + cloud Supabase both still absent — those
  two user actions remain the only blockers to automated extraction and
  hosted deployment. Tests: **biology 155/155**, api 111/111, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean.
- **2026-08-13 (session 6)** — Claude Code. **M2 CLOSED: descriptive band
  multiplicity / smear representation.** Additive `BandObservation` fields
  `band_pattern` (single|doublet|multiple|smear|ladder|uncertain) + `band_count`
  (only when literally countable/stated) + `band_notes` (verbatim wording), each
  a full EvidenceField envelope. **Additive to `band_state`, never a replacement**
  (a smeared/doublet band is still `present`); null pattern = "source didn't
  say", NOT "single band". Two evidence channels only: (1) deterministic parsing
  of explicit wording (`biology.detect_band_pattern`: doublet, "two/three
  bands", smear(ed), ladder-like, polyubiquitin ladder/conjugates, high-MW
  species, multiple/additional/non-specific bands, single band; hedged wording →
  AMBIGUOUS; conflicting descriptions → uncertain), **clause-scoped to the
  target** so "LC3B resolved as a doublet, while ACTB…" never marks ACTB; and
  (2) explicit observer claims in Stage-2 output (contract updated with strict
  omit-when-in-doubt + no-identity-inference rules). **False-positive audit on
  the real 452-band set: with text-only evidence, zero patterns asserted**
  (correct — no paper states multiplicity wording); observer doublet claims
  were then added ONLY for the 4 targets visibly resolving as two bands in the
  inspected crops (LC3B, BEX2, P-ERK 1/2, T-ERK 1/2 → 30 lanes), each carrying
  image provenance + verbatim note. Phospho+total pairs, loading controls and
  multi-row panels remain pattern-free (multiplicity belongs to ONE band
  observation, never to row count). Exposed in `GET /records/{id}` + evidence-
  panel lane strip with an explicit "descriptive only — no isoform/cleavage
  interpretation" note. LIMITATIONS: no image-based smear/multiplicity detection
  (text/observer evidence only); no isoform/cleavage/dimer assignment ever; the
  no-creds automated model has not been tested against the new contract fields.
  Tests: **biology 124/124** (+30), api 106/106, benchmark 34/34, harness
  self-test 100% EXACT, tsc clean. Demo artifacts + DB regenerated (452 rows).
  Model creds re-checked: still absent. Optional QA sub-agent not spawned (the
  empirical zero-FP audit on all real bands stood in for it; flag for the
  independent pre-UCSF QA pass).
- **2026-08-13 (session 5, hackathon day)** — Claude Code. **RESULT GROUPING + MULTI-DOSE
  REPRESENTATION.** (1) Search results now group into one card per EXPERIMENT
  (paper + panel + target + experiment type + **cell line** + **modification label**)
  instead of one card per lane row: `phospho STAT3 Tyr705` reads "3 experiments
  (15 lane records)". The cell-line component is load-bearing — one real crop
  (PMC12706926 `page_004_cand_0025`) prints **H1792 | A549 side by side**, and the
  first key merged them. Verified against all 374 demo rows: 77 groups, **zero**
  groups containing >1 distinct target / canonical target / modification / residue /
  experiment type / UniProt / figure / cell line / catalog / organism.
  (2) **Multi-dose / time-course representation (QA finding M1 closed).** The old
  scalar took `values[0]`, which reported the **CL-E dose (60 µg/ml) as the IL-6
  dose** and **60 min as THE duration of a 0–60 min time course**. Now:
  enumerations sharing one unit expand (`extract_dose_series` /
  `extract_duration_series`: "10, 30 and 60 µg/ml" → 3 values; "(0, 5, 10, 20, 30,
  60 min)" → 6 timepoints); >1 distinct value ⇒ the panel scalar becomes
  **value=null, status=AMBIGUOUS with every value preserved as a candidate**
  (DB scalar NULL, never a wrong number); per-lane values are parsed from each
  lane's own printed condition into new `BandObservation.lane_dose/lane_duration`
  and served by `GET /records/{id}`. "for the indicated times/doses" is
  kind-specific, so a time course keeps its settled single stimulus concentration.
  Tests: **biology 94/94** (+17), api 106/106, benchmark 34/34, harness self-test
  100% EXACT, tsc clean. Demo artifacts + local DB regenerated (452 rows).
  **Model backend still blocked — no credentials present (re-verified).**
- **2026-08-13 (session 4)** — Claude Code (Opus 4.8). **SCIENTIST-REVIEW BETA COMPLETE.**
  Full provenance + researcher-feedback loop live end-to-end locally:
  `GET /records/{id}` serves curated field-level evidence envelopes (value /
  status / source snippets / competing candidates); the card's evidence panel is
  now a full-width accordion with the normalization chain (raw → canonical →
  UniProt), per-field audit rows + ✓/✗/not-useful/suggest-correction controls,
  equal-weight CONFLICTING candidate display ("Which is right?"), antibody
  roles, lane strip, `+ Missing information?`, result flagging, post-search
  "did HiveBlot understand?" prompt, and a general BETA FEEDBACK widget.
  **Migration 002** adds `hiveblot_feedback` + insert-only `hive_feedback` role:
  human corrections persist BESIDE the AI extraction (model_value snapshot),
  never over it. Verified in the real browser: feedback rows land in Postgres
  from UI clicks. Also: home-page search now routes to /search (legacy table
  retired); advanced-filters bar; `eval/model_comparison/compare_records.py`
  harness (self-test 100% EXACT on all 3 papers); boto3 installed → Bedrock
  path ready pending creds; `DEPLOYMENT.md`; `research/HACKATHON_DEMO_FLOW.md`;
  scientific QA self-audit (`research/demo_scientific_qa.md`: 0 critical open,
  2 major representational). Tests: engine 138 assertions green, benchmark
  34/34, **api 104/104**, web tsc clean. NOTE: two of three planned sub-agents
  (independent QA, eval design) were killed by session limits; QA was done as a
  self-audit and the eval harness written directly — re-run independent QA
  before UCSF.
- **2026-08-12 (session 3)** — Claude Code (Opus 4.8). **LIVE SEARCH LOOP WORKS.**
  `phospho STAT3 Tyr705`, `phospho AKT Ser473`, `co-IP PIK3CA`, `CST 9145`,
  `GAPDH mouse` all return real paper-derived Evidence Records in the running
  HiveBlot frontend. Stood up an **embedded local Postgres** (`scripts/local_db.py`,
  pgserver — no cloud creds needed) with schema + migration 001 + **452 rows from
  3 real papers**; added a **deterministic biological SQL generator**
  (`api/app/bio_query.py`; now the normal search path); fixed a latent sql_guard
  bug (AND/OR rejected with sqlglot≥30); made the Supabase client lazy; processed
  papers 2+3 (mouse standard PMC9559174, co-IP PMC12706926) agent-in-the-loop;
  threaded **organism into UniProt** (mouse accessions correct); fixed 4 more
  structural biology bugs found by real-paper inspection (one-letter phosphosites,
  page-level co-IP bleed, bare-mention fake total claims, page-blob reported-MW).
  Tests: biology 77/77, engine suites green, benchmark 34/34, api 95/95.
- **2026-08-12 (session 2)** — Claude Code (Opus 4.8). **First real paper end-to-end.**
  Built the `.venv` (py3.12) + installed ingestion deps; live UniProt transport
  validated; ran a real phospho-STAT3 paper (PMC12856536) through the full records
  path via **agent-in-the-loop** Stage-2 extraction (no live model backend available).
  Field-by-field inspection found + fixed a **structural identity bug** (`P-ERK 1/2`→
  EPHB2 false-friend; p53/p38/PARP prefix mangling; ambiguous-family-as-SUPPORTED),
  with regression tests. Widened the API model additively; rebuilt the result card;
  wrote `research/RESEARCH_SYNTHESIS.md`. Demo run committed under `eval/demo/`.
- **2026-08-12 (session 1)** — Migrated Phase 2+3 into `/hive`; wired the Evidence
  Record engine into `pipeline.py` behind `WBM_EXTRACTION_MODE`; validated UniProt parsing.

## Product North Star
HiveBlot is a **biologically accurate Western blot evidence search / context
platform**. It turns Western blot figures, captions, methods, and paper context
into structured, searchable, **auditable** experimental evidence, so a researcher
can move between what a blot shows, the conditions that produced it, and
comparable evidence in the literature.

- **Biological validity is the #1 beta priority** — above feature count and UI polish.
- **HiveBlot and AGeneTic are separate projects.** AGeneTic must NOT shape this
  repository, its schema, or its scope.
- **Immediate user target: UCSF wet-lab researchers.**
- This is a **beta** whose explicit purpose is to collect detailed researcher
  feedback. Surface uncertainty; never present a guess as a settled fact.

## Canonical Repository
- **Repo:** `git@github.com:nikhilesh-s/hive.git` (this `/hive` working tree).
- **Branch:** `feature/bio-context-beta` (do NOT build features on `main`).
- **Latest finalized commits:** `beaec0f`, `393ffa6`, `5c54352` (UCSF
  beta-readiness pass, 2026-09-01); this handoff commits on top — run
  `git log -1` for the exact tip.
- The old `Ananya-Jha-code/QBI` repo is **superseded**. Do not build there.

## Current Architecture
- **Frontend** — `web/` (Next.js App Router, TypeScript). Search UI → `web/app/api/search/route.ts` → API.
- **Backend API** — `api/` (FastAPI). Split routers: `internal` (frontend-only, `INTERNAL_API_KEY`)
  and `external` (agent-facing `/v1/search`, `AGENT_API_KEYS`). Security: `sql_guard.py`
  (AST validation of generated SQL) + two scoped Postgres roles (`hive_readonly`,
  `hive_feedback`) behind Row Level Security (migration 004). No PostgREST client.
- **Supabase (Postgres)** — table `western_blot_records` (`api/db/schema.sql`), extended
  additively by `migrations/001` (Evidence Record columns), `002` (feedback table + role),
  `003` (`stable_row_key`), `004` (RLS + least-privilege grants).
- **Literature / PDF ingestion** — `western_blot_miner/` package. Free NCBI E-utilities +
  BioC (`pmc.py`) for literature; local PDF render via PyMuPDF (`pdf_preprocess.py`).
- **Deterministic CV filtering** — `pdf_preprocess.py` (OpenCV): renders pages, scores
  panel candidates (saturation / dark-fraction / horizontal morphology / intensity
  profiles), keeps only above-threshold crops before any model call. This is the cheap
  first stage of the cascade.
- **Biological Evidence Record engine** — `evidence_record.py` (schema), `biology.py`
  (deterministic biology), `reconcile.py` (evidence-hierarchy reconciliation),
  `record_builder.py` (assembly + validation/anomalies), `extract_records.py` (Stage 2→3→4).
- **LLM abstraction** — `llm_client.py`: **Bedrock-first** (`converse`), plus Anthropic /
  OpenAI-compatible / Mock backends. No RunPod dependency.
- **UniProt resolver** — `resolve.py`: live UniProt REST (reviewed, organism-scoped) +
  on-disk cache + local-map fallback. Never guesses an accession.

Cascade (low-compute by design): deterministic Stage 1 → cheap hosted model Stage 2 →
validation Stage 3 → expensive-model escalation Stage 4 only for ambiguous/conflicting.

## Provenance & Feedback (session 4)
- **Record detail**: `GET /records/{id}` (internal auth) → curated `RecordDetail`:
  source identity, biological scalars, `fields{name → {value, confidence, status,
  sources[{type,text}], candidates[]}}` extracted from the provenance JSONB,
  antibodies (role + detection vs association confidence), per-lane bands,
  validation. Shaping: `api/app/record_detail.py`. Web proxy: `/api/record/[id]`.
- **Feedback**: `POST /feedback` (internal auth) → `hiveblot_feedback`
  (**migration 002**) via the **insert-only `hive_feedback` role**
  (`DB_FEEDBACK_URL`) — physically cannot touch `western_blot_records`.
  Scopes: `field` (correct/incorrect/not_useful/missing_context + suggested_value),
  `record` (9 flag types), `missing_field`, `search` (understood yes/partially/no),
  `ui`. `model_value` snapshots the AI claim at feedback time → every row is an
  auditable "AI claim → human correction" pair; corrections are NEVER auto-applied.
  Web proxy: `/api/feedback` (key-allowlisted); anonymous localStorage session id.
- **Frontend**: `EvidencePanel.tsx` (full-width accordion: normalization chain,
  per-field audit + feedback, conflict candidates "Which is right?", antibodies,
  lane strip, missing-info + flag-result forms, DOI link), `SearchFeedback.tsx`,
  `BetaFeedback.tsx`, `FiltersBar.tsx` (persistent sidebar that composes queries
  for the deterministic parser). Home-page search now routes to `/search?q=…`
  (legacy table retired).

## Completed Work
- **Phase 1 — Repository audit / canonical architecture.** Identified the real system
  and canonical components across the messy QBI branches.
- **Phase 2 — Biological schema + phospho classification fix.** `biology.py`; removed the
  `target.startswith("p")` heuristic; additive `migrations/001`. Tests: **test_biology 38**,
  **test_loader_enrichment 18**.
- **Phase 3 — Evidence Record + provenance + reconciliation + resolver + benchmark.**
  Field envelope, evidence hierarchy, conflict handling, UniProt resolver, Bedrock
  abstraction, antibody detection-vs-association, co-IP roles, MW reported-vs-expected,
  validation/anomaly flags. Tests: **test_reconcile 21**, **test_extract_records 10**;
  **eval benchmark 34/34** field-level across 4 seed cases.
- **Migration → /hive**: engine + migrations + eval brought into the canonical repo.
- **Pipeline wiring**: `pipeline.py` now supports `WBM_EXTRACTION_MODE=records`, routing the
  OpenCV panel candidates through the Evidence Record engine (`run_records_stage`); legacy
  path preserved. **113 assertions + 34/34 benchmark verified from `/hive`**
  (test_biology 53, test_reconcile 21, test_loader_enrichment 18, test_extract_records 10,
  test_pipeline_records 11) + **api pytest 81/81**.
- **UniProt resolver live-validated**: parsing checked against the live UniProt API via
  stdlib urllib — STAT3→P40763 (88.1 kDa), AKT1→P31749, TP53→P04637, EGFR→P00533,
  GAPDH→P04406, all exact. **`requests` transport now also live-validated** in the venv.
- **Session 2 — first real paper end-to-end** (`eval/demo/phospho_PMC12856536/`):
  Jang et al. 2026, DOI 10.3892/br.2026.2108, PMC12856536 (phospho-STAT3, Hep3B, IL-6).
  PDF → PyMuPDF → OpenCV (55→9 candidates) → **agent-in-the-loop** Stage-2 → build →
  reconcile → **live UniProt** → validation → **18 Evidence Records / 90 Supabase rows**;
  the 4 bar-chart candidates correctly produced 0 records. Verified correct: phospho vs
  total split, Tyr705/Ser727 residues, loading-control (β-actin), treatment parse
  (IL-6 10 ng/ml, 60 min), expected-MW 88.1 kDa, reported-MW null (never conflated).
  *Transport note:* no live model backend was available, so Stage-2 was performed by
  the agent (real observations in `responses_observed.json`); ALL downstream biology is
  the real production path. Reproducible via `eval/tools/manual_pipeline.py`.
- **Structural bug fixes (session 2, with tests):** `biology._core_symbol` rewritten —
  it stripped a lone `p`/`P` from any p-word (`p53`→`53`, `p38`→`38`, `PARP`→`ARP`),
  ignored total-protein `T-`, and dropped isoform suffixes (`P-ERK 1/2`→`ERK`→ UniProt
  **EPHB2**, a gene-synonym false-friend). Now: separators required for p-/t- stripping,
  glued lowercase-`p` only before uppercase, isoform preserved (`ERK 1/2`→`ERK1/2`).
  Resolver: curated **ambiguous families win over UniProt** (ERK→MAPK1/MAPK3, never one
  wrong accession). `record_builder`: an ambiguous-with-family resolution stays AMBIGUOUS
  (was falsely SUPPORTED) → flips `needs_review`. Tests: **test_biology now 53** (added 15).
- **API widened (additive):** `api/app/schemas.py::WesternBlotRecord` gained the
  migration-001 Evidence Record fields as Optional (Pydantic was silently dropping DB
  columns the frontend never received). The giant `provenance`/`validation` JSONB blobs
  are intentionally kept OUT of list responses. **api pytest 81/81.**
- **Frontend result card rebuilt** (`web/components/DatabaseResultCard.tsx`): biological
  headline (`STAT3 · phospho-Tyr705`) + review badge (Supported / Needs review /
  Conflicting) + antibody/treatment/band/MW (reported≠expected) + an evidence panel
  ("Why HiveBlot says this"). Additive + guarded (legacy rows still render); `tsc` clean.
- **Research tracks delivered** (`research/`): `biologist_western_workflow.md`,
  `biopharma_workflows.md`, `frontend_integration_plan.md`, `benchmark_candidates.md`
  (+ `eval/candidates.json`, 26 verified papers), `real_pipeline_report.md`, and the
  integration `RESEARCH_SYNTHESIS.md`.
- **Session 18 — Search-results IA redesign**: `/search` now keeps the search
  bar on top, moves filters into a persistent left sidebar with explicit Apply,
  shows removable active chips above results, and lays each desktop result card
  out as experiment information, figure preview, and evidence/source. This is a
  frontend-only change; `/api/search`, record detail, evidence feedback, schema,
  and local/production env requirements are unchanged.

## Current Biological Contract
Every important field is an **Evidence Field envelope**: `{value, confidence, status,
sources, candidates}` — **field-level** confidence, not just record-level. Statuses:
- **SUPPORTED** — evidence agrees; value is settled.
- **AMBIGUOUS** — under-supported or resolver returned multiple candidates; value is a
  best-guess flagged unsettled.
- **CONFLICTING** — credible sources disagree. **`value = null`** (never a falsely settled
  scalar); competing **candidates + their evidence are preserved** for review/repair.
- **MISSING** — not reported. Preserved in the record but not given prominent UI treatment;
  surfaces when relevant to a query, evidence review, or feedback.

Other invariants: **raw source wording is always preserved** alongside any normalized value;
**provenance** (which source: antibody / caption / methods / model_target / image / uniprot)
travels with each field; a disputed modification keeps its residue **unsettled** too.

## Known Biological Edge Cases (current gaps)
- **FIXED (session 3) — one-letter phosphosites in row labels.** `p-AKT (S473)`,
  `p-RPS6KB1 (T389)`, `p-EIF4EBP1 (S65)` now yield residue+position (the phospho marker
  and site share one short label, satisfying the one-letter context guard). Bare `S473`
  without a marker still never claims phospho.
- **FIXED (session 3) — page-level co-IP bleed.** co_ip now requires panel-scoped
  evidence (IP-role antibody / co-IP caption / IP:,IgG,input lane labels); a methods-only
  mention becomes a non-settling `co_ip_context` flag. `ip_bait` extraction follows the
  same scoping.
- **FIXED (session 3) — bare mentions are not total claims.** "PI3K/AKT/mTOR signaling"
  no longer manufactures a `MODIFICATION_CONFLICT` against a phospho row; only explicit
  `total X` / `T-X` / `pan-X` wording asserts total, and mixed forms still abstain.
- **FIXED (session 3) — page-blob reported MW.** A kDa figure counts as reported only
  near a mention of the target's core symbol (caption-only fallback when the core is
  absent from a short caption). No more "BEX2 reported 70 kDa" from ladder text.
- **FIXED (session 3) — phospho-specific antibody vs uppercase P- label.** Uppercase
  `P-` is never a phospho *marker* (P-selectin, P-cadherin), but an explicit
  `phospho_specific=true` antibody claim now prevents settling the row as total:
  `P-ERK 1/2` + CST #4370 → modification CONFLICTING, value null, needs_review.
- **NEW (session 3) — organism threading.** `biology.organism_taxon_id` maps explicit
  human/mouse/rat wording → taxon id for the UniProt query (default human 9606, as
  before). Mouse validated live: Stat3→P42227, Gapdh→P16858, Actb→P60710, Tuba1b→P05213.
  Cell-line→organism inference is still NOT used for resolution (only explicit claims).
- **FIXED — ERK/family shorthand false-friend.** `P-ERK 1/2` used to resolve to EPHB2
  (P29323); now resolves to the ambiguous **MAPK1/MAPK3** family (status AMBIGUOUS,
  `needs_review=true`, no single accession). Curated ambiguous families now beat a
  UniProt synonym hit.
- **P-ERK 1/2 is NOT classified as phospho** (mod=`-`, experiment=`standard_western`)
  because there is no explicit site and `P-` alone isn't accepted as phospho evidence.
  Conservative-correct, but the phospho-specific antibody (rank-1) is a hint we don't yet
  use for site-less phospho labels — candidate improvement.
- **Non-human UniProt resolution ordering** — resolver defaults to `organism_id=9606`;
  mouse/rat targets can resolve wrong or expected-MW wrong until organism is threaded in.
- **Unusual phospho notation** far from the target mention (e.g. glued `STAT3(pY705)`, or
  "phosphorylated at Y705" across a clause) can be missed → falls back to antibody/model.
- **Antibody-to-panel association ambiguity** — "which antibody detected which row" in a
  dense reagents paragraph is *flagged* via `association_confidence`, not fully solved.
- **Dual modifications** (e.g. cleaved AND phospho on one target) → treated as a conflict,
  not yet represented as co-occurring.
- **FIXED (session 5) — multi-dose / time-course collapse.** Enumerated series now
  expand; a panel with >1 distinct dose/duration keeps `value=null` + AMBIGUOUS +
  candidates instead of asserting one lane's value (which had cross-attributed the
  CL-E dose to IL-6). Per-lane values live on `BandObservation.lane_dose` /
  `lane_duration`, parsed only from that lane's own printed condition.
- **IP-bait heuristic** (`_first_gene_after`) is best-effort; robust for "anti-EGFR", brittle in messy methods.

## Current Technical Blockers
- **RESOLVED — real paper end-to-end**: done (session 2, `eval/demo/phospho_PMC12856536/`).
- **RESOLVED — ingestion deps**: `.venv` (py3.12) at repo root has PyMuPDF, opencv-headless,
  numpy, requests, pydantic, anthropic. Recreate with
  `python3.12 -m venv .venv && .venv/bin/pip install -r western_blot_miner/requirements.txt`.
- **RESOLVED — `requests` / UniProt transport**: installed + live-validated in the venv.
- **RESOLVED — representative PDFs**: 3 real open-access PDFs in `research/papers/`
  (standard PMC9559174, phospho PMC12856536, co-IP PMC12706926); gitignored (fetch via
  the PMCIDs in `research/real_pipeline_report.md`).
- **OPEN — no live model backend** (unchanged, re-verified session 3: no `~/.aws`, no
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`WBM_LLM_*`). All three real papers used
  **agent-in-the-loop** Stage-2 (honest, documented per demo README). For an automated
  run set `WBM_LLM_BACKEND` + matching creds, then diff against
  `eval/demo/*/responses_observed.json` + `evidence_records.json` as reference.
- **WORKED AROUND — cloud Supabase still not provisioned** (`SUPABASE_URL`/`KEY` empty
  in `api/.env`), but the live loop no longer needs it locally: `scripts/local_db.py`
  runs an embedded Postgres (pgserver, data in gitignored `.localdb/`), applies the
  SAME `api/db/schema.sql` + `migrations/001` (pg_trgm index skipped locally — not
  bundled), creates `hive_readonly`, and loads the demo rows. `api/.env`'s
  `DB_READONLY_URL` points at it. `/search` runs asyncpg-only, so against this DB the
  search path is the real production path; PostgREST-only endpoints (`/proteins`, `/`)
  still need real Supabase. **Cloud Supabase remains a user action for the hosted
  beta**: create the project, run schema+migration, load `eval/demo/*/supabase_rows.json`,
  fill `SUPABASE_URL`/`SUPABASE_KEY`/`DB_READONLY_URL`.
- **NOTE — /search SQL generation**: /search uses the deterministic biological
  parser (`api/app/bio_query.py`) — protein,
  phospho-site (Tyr705/S473), vendor+catalog, co-IP, loading-control, needs-review,
  cell-line terms — through the same `sql_guard` + read-only role. The legacy
  OpenAI NL→SQL branch was removed for B-9 because its prompt described an older
  schema and `bio_query.py` is the supported HiveBlot search generator.

## Immediate Next Task
~~Provenance detail endpoint + researcher feedback system + evidence UI~~ — **DONE (session 4)**.
~~Result grouping + multi-dose/time-course representation~~ — **DONE (session 5)**.
~~Manual-test fixes (search submit, card identity, IL-6·3D, lanes) + Supabase CLI prep~~ — **DONE (session 8)**.

~~Legacy Supabase production audit~~ — **DONE (session 10)**,
`research/supabase_legacy_audit.md`.
~~Beta-table inspection + plan~~ — **DONE (session 11)**,
`research/supabase_beta_table_plan.md`.

~~Wait for Srushti's clean Supabase project~~ — **DONE (session 12)**: linked,
migrated, seeded, verified on `zafombwswztvnjikcsdm`.

~~Deploy the web app~~ — **DONE (session 13)**: https://hiveblot-beta.vercel.app

~~Create the Render service, re-point Vercel~~ — **DONE (session 14)**.
~~Fix the duplicate `stable_row_key`~~ — **DONE (session 14)**, 475/475 distinct.
~~Search-results information architecture redesign~~ — **DONE (session 18)**,
frontend-only, using the provided `/images/STATE3.png` preview asset for STAT3
cards.
~~Search-results row refinement~~ — **DONE (session 19)**, frontend-only:
lighter wide rows, centered preview, compact existing-data chips, lighter
source metadata, compact right-aligned evidence action.
~~Dedicated treatment/lanes result column~~ — **DONE (session 20)**,
frontend layout-only: treatment and all lane chips now occupy their own
desktop column immediately after primary identity, with medium/mobile reflow.
~~Sample/experiment column + compact metadata rebalance~~ — **DONE (session
21)**, frontend layout-only: removed the large evidence/source column from the
main card, moved sample/experiment into their own column, and kept source
metadata compact beside tags.
~~Hide search-result evidence panel interaction~~ — **DONE (session 22)**,
frontend presentation-only: `View Evidence` and the expandable evidence/
feedback panel are no longer shown from result cards; underlying evidence code
and routes remain.

~~Team delegation package + P0 `/about` overclaims + Supabase public-table
exposure~~ — **DONE (session 31, 2026-09-01)**: workstreams consolidated and
executed; see CURRENT STATE above and `research/UCSF_BETA_READINESS.md`.

**The hosted beta is READY FOR UCSF WITH KNOWN LIMITATIONS.** The one
outstanding deployment step is the Render API redeploy (Nik).

**NEXT, in order:**
0. **Nik: `render login`, deploy the branch tip to `hiveblot-api`, run the
   presentation-day checklist (readiness report §J).**
1. Distribute to the team / UCSF reviewers and collect feedback. Warn them
   about the free-tier cold start (~30–60 s on the first request after ~15 min
   idle) so it is not reported as a bug.
2. Watch `hiveblot_feedback` fill up. It starts at **0 rows** — every row from
   here is real researcher signal. Corrections are stored BESIDE the
   extraction and are never auto-applied.
3. **Model credentials** (Bedrock `AWS_*` or `ANTHROPIC_API_KEY`) → run the
   staged automated-extraction evaluation. Harness already scores EXACT /
   ACCEPTABLE / PARTIAL / WRONG / MISSING / HALLUCINATED; protocol in
   `research/automated_extraction_eval_protocol.md`. **Until that runs, no
   claim about arbitrary-paper accuracy is defensible.**
4. ~~Independent scientific QA re-run against the corrected 93-experiment
   grouping~~ — **DONE (session 31)**; findings QA-1…QA-5 await a founder
   decision on a reviewed reseed.
5. `image_crop_ref`: public responses now expose the filename only (session
   31). Making the STORED refs relative to `CROP_BASE_DIR` remains cosmetic
   (removes the Dockerfile path line) and needs a reseed.

## Next After That
- Live Bedrock + UniProt validation (real credentials + network).
- Phase 4: expand anomaly/validation rules + tests.
- Phase 5: advanced structured search (safe parameterized filters + NL→filter routing).
- Phase 6: Evidence Record UI (only after the biology is trusted).
- Phase 7: researcher feedback system.
- Phase 8: larger biological benchmark (10–20 wet-lab-annotated cases).

## Files That Matter Most
| Path | What it does |
|------|--------------|
| `western_blot_miner/biology.py` | Deterministic biology: modification/site detection, experiment type, loading control, protein core symbol. |
| `western_blot_miner/evidence_record.py` | Field envelope + EvidenceRecord + `to_supabase_rows()` projection. |
| `western_blot_miner/reconcile.py` | Evidence-hierarchy reconciliation; conflict handling. |
| `western_blot_miner/record_builder.py` | Builds an EvidenceRecord from model claims + biology; validation/anomalies. |
| `western_blot_miner/extract_records.py` | Stage 2→3(→4) panel extraction; `records_to_supabase_rows`. |
| `western_blot_miner/resolve.py` | UniProt resolver + cache + local fallback. |
| `western_blot_miner/llm_client.py` | Bedrock-first model abstraction + Mock. |
| `western_blot_miner/pdf_preprocess.py` | OpenCV candidate filtering (cheap stage). |
| `western_blot_miner/pipeline.py` | PDF ingestion orchestrator (**still old VLM path — to be wired**). |
| `western_blot_miner/supabase_loader.py` | Flatten/enrich rows + PostgREST upload. |
| `migrations/001_evidence_record.sql` | Additive Evidence Record columns (+ rollback). |
| `eval/score.py`, `eval/cases.json`, `eval/gold.json` | Biological benchmark (seed gold). |
| `api/app/` | FastAPI backend (routers, sql_guard, auth, search_service). |
| `api/app/bio_query.py` | Deterministic biological query→SQL for normal search (same guard). |
| `scripts/local_db.py` | Embedded local Postgres (pgserver): up / load / status / stop. |
| `eval/tools/` | Agent-in-the-loop harness + per-paper observation builders. |
| `eval/demo/` | 3 real papers: Evidence Records + Supabase rows + observations + READMEs. |
| `api/db/schema.sql` | Base `western_blot_records` table + `hive_readonly` role. |
| `web/app/`, `web/components/` | Next.js frontend. |

## Tests / Commands
```bash
# Biological tests (need python3 + pydantic; run from repo root)
python3 western_blot_miner/tests/test_biology.py
python3 western_blot_miner/tests/test_reconcile.py
python3 western_blot_miner/tests/test_loader_enrichment.py
python3 western_blot_miner/tests/test_extract_records.py
python3 western_blot_miner/tests/test_pipeline_records.py   # ingestion wiring (mock model)

# Biological benchmark (offline; writes eval/out/)
python3 eval/score.py

# API tests (install deps once: .venv/bin/pip install -r requirements-local.txt)
cd api && ../.venv/bin/python -m pytest
# + the RLS access matrix against the embedded local Postgres
.venv/bin/python scripts/local_db.py up
HIVE_DB_TEST_URL=$(.venv/bin/python scripts/local_db.py test-url) .venv/bin/python -m pytest api/tests/test_db_access_matrix.py -v

# Frontend
cd web && npm install && npm run dev

# Backend
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload

# Ingestion — legacy VLM path (default) or new Evidence Record path
python3 -m western_blot_miner.pipeline path/to/paper.pdf                 # legacy
WBM_EXTRACTION_MODE=records python3 -m western_blot_miner.pipeline paper.pdf --mode records
```

## Environment Variables / Services  (NAMES ONLY — never put values here)
- **API (`api/.env`):** `DB_READONLY_URL`, `DB_FEEDBACK_URL`, `OPENAI_KEY`,
  `INTERNAL_API_KEY`, `AGENT_API_KEYS`, `ALLOWED_ORIGINS`, `AGENT_RATE_LIMIT`, `SEARCH_RATE_LIMIT`;
  `SUPABASE_URL`/`SUPABASE_KEY` optional and unused since migration 004.
- **Web (`web/.env`):** `API_BASE_URL`, `INTERNAL_API_KEY`.
- **Ingestion engine (`western_blot_miner/.env`):** `ANTHROPIC_API_KEY`, `NCBI_API_KEY`,
  `NCBI_EMAIL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_TABLE`, `SUPABASE_IDEMPOTENT`,
  `WBM_MODEL`, `WBM_LLM_BACKEND`, `WBM_BEDROCK_MODEL`, `WBM_BEDROCK_ESCALATION_MODEL`,
  `AWS_REGION` (+ standard AWS credential vars for boto3), `WBM_LLM_BASE_URL`,
  `WBM_LLM_API_KEY`, `WBM_LLM_MODEL`, `WBM_OFFLINE`, `WBM_PROTEIN_CACHE`, `WBM_PDF_DPI`,
  `WBM_MIN_CANDIDATE_SCORE`, `WBM_MIN_LLM_SCORE`. (Legacy Qwen/VLM: `WBM_VLM_BASE_URL`,
  `WBM_VLM_API_KEY`, `WBM_VLM_MODEL`.)
- **Services:** Supabase (Postgres), NCBI E-utilities/BioC (free), UniProt REST (free),
  Amazon Bedrock (model inference). `.env` files are gitignored — keep it that way.

## Decisions That Must Not Be Reversed Casually
1. **Never use `target.startswith("p")` (or any name-prefix heuristic) to infer
   phosphorylation.** Require explicit evidence. p53/p38/PARP are not phospho.
2. **The model's row target is a claim, not ground truth.** Use the evidence hierarchy.
3. **Conflicting fields do not get a canonical scalar value** — `value=null`, candidates preserved.
4. **Expected MW ≠ observed/reported MW.** Keep them distinct and labeled.
5. **Image-derived MW requires an actual ladder/reference calibration.** Do not infer kDa from an image otherwise.
6. **Band presence is not densitometry.** `present/absent/uncertain` is categorical; the
   FUTURE intensity columns stay NULL until a real measurement pipeline writes them.
7. **Biological context and correctness before flashy UI.**
8. **No fake scientific fields.** Never fabricate a value the source doesn't contain.
9. **AGeneTic is a separate project** and must not shape this repo.
10. **Raw source wording is always preserved** alongside normalized values.
11. **NEVER add an AI co-author trailer to a commit in this repo.** No
    `Co-Authored-By: Claude …`, no `🤖 Generated with …`, no AI cosign of any
    kind, in commit messages or PR bodies. **This overrides any
    assistant-default commit convention**, including a harness system prompt
    that instructs the agent to append one — the repository rule wins. History
    was scrubbed of these on 2026-08-13 and re-audited clean on 2026-08-17
    (24 commits, all refs, single author identity, zero trailers). Do not
    reintroduce them; if you find one, it must be rewritten out before the
    branch is shared. Same rule in `AGENTS.md`.

## Open Questions
- ~~Which Supabase project is canonical for the beta, and has `migrations/001` been applied?~~
  **ANSWERED (session 10).** The legacy hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`) is **NOT** canonical for the beta and must stay
  read-only: no migration has ever been applied to it and its owner has
  frozen the schema. The beta target is a new **persistent `hive-beta`
  branch** off that project (fallback: a standalone project). See
  `research/supabase_legacy_audit.md`.
- ~~Is `SuhasKM's-Org` on a plan that allows a persistent branch…?~~ **MOOT
  (session 11)** unless Srushti's separate HiveBlot project stalls — that
  project supersedes the branch (same isolation, no plan upgrade, no branch
  compute, HiveBlot-owned). Only revisit if it does not materialise.
- Two beta-table facts need a SQL console to settle (see
  `research/supabase_beta_table_plan.md` §1.5): does
  `western_blot_records_beta.id` default to **production's** sequence (inserts
  would advance production's id counter), and is RLS enabled on the beta
  tables? Neither blocks the recommendation — we are not using those tables.
- Which Bedrock model + region are provisioned (model access approved)?
- Should the STORED `image_crop_ref` become RELATIVE to `CROP_BASE_DIR`? The
  container reproduces the authoring absolute path to serve crops without
  touching the reviewed corpus (session 12); since session 31 the API never
  exposes the path. Relative refs are cleaner but rewrite every seeded row.
- Structured organism filter (`organism = X OR text match`, exact tokens
  only)? Investigated session 31; deliberately not implemented.
- Move `pg_trgm` to the `extensions` schema (advisor WARN)? Procedure in the
  readiness report §B; needs a proven dry run first.
- Idempotency key `(paper_id, page, figure_label, target, condition)` — keep, or extend with
  modification/lane once Evidence Records flow in? (Affects dedupe on re-ingest.)
- Organism handling: thread cell-line→organism into the UniProt query before resolution?
- Apply corpus corrections QA-1…QA-5 (readiness report §C) via a reviewed reseed?

## Recent Commits (rolling)
- `5c54352` Complete consolidated researcher and biology QA fixes
- `393ffa6` Resolve UCSF beta P0 communication issues on About and Learn
- `beaec0f` Harden Supabase table access with RLS and scoped roles
- `0653fbd` Add professor orchestration brief and ignore .serena local state
- `987c4aa` Add light and dark theme system
- (this HANDOFF update commits on top of `5c54352`)

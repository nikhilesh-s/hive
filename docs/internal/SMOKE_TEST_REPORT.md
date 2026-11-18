# HiveBlot beta: smoke test report

**Date/time tested:** 2026-09-20, approx. 15:20 to 15:35 America/Los_Angeles

**Environment:**
- Web: https://hiveblot-beta.vercel.app
- API: https://hiveblot-api.onrender.com
- Repo worktree read (read-only): `/Users/niks/hive-beta`, branch `feature/bio-context-beta`, commit `e0d2089e4e0f838f69a55daa750c030c0e9b465c`
- Tooling: `curl` (API + Next.js route handlers), Playwright (`playwright-skill`, headless Chromium) for browser flows. Screenshots saved under the session scratchpad (`smoke/01_homepage.png` … `smoke/11_learn.png`).
- Render free tier did **not** show a cold start during this run; the API was already warm (`/health` returned in 0.12 s, first `/api/search` call in 0.79 s). No 30 to 60 s wake-up was observed or needed to be worked around.

## Summary verdict

The hosted beta works end to end and the copy is honest. Search, the evidence/provenance panel, figure crops, and feedback submission all function correctly through the real user-facing paths (not just the API). The most notable positive finding: ambiguity is preserved. A `P-ERK` search returns records still marked `CONFLICTING`/`AMBIGUOUS` rather than being silently resolved to "phospho" just because the query used a `P-` prefix, and the UI shows the competing claims side by side. No secrets, no CORS errors, no broken images, no console/network errors were found. The one thing I could not verify is whether the hardcoded "3 papers · 93 experiments · 475 evidence rows" copy still matches the live database, because no endpoint reachable from the web tier reports a live count. This is a low-severity drift risk, not an observed inaccuracy.

**Counts: 11 Pass / 0 Fail / 1 Not verified** in the agent run (see table). The orchestrator then checked the corpus stat directly against the database as the project owner: 3 distinct DOIs and 475 rows with 475 distinct stable row keys, matching the copy. The 93 experiment-group figure was not recounted. Treat flow 12 as Pass for papers and rows, Not verified for the experiment count.

## Test table

| Flow | Expected | Actual | Pass/Fail/Not verified | Notes |
|---|---|---|---|---|
| 1. API health `GET /health` | `{"status":"ok"}` | `{"status":"ok"}`, HTTP 200, 0.12 s | Pass | No cold start hit this run. |
| 2. Web loads (homepage) | Renders without obviously broken UI | HTTP 200, hero/search box/nav render, background video+poster load, no console errors, no failed asset requests | Pass | `smoke/01_homepage.png` |
| 3. Search `phospho STAT3 Tyr705` | Relevant STAT3 phospho-Tyr705 results | 3 experiments / 18 lane records, all `STAT3` canonical target, modification `phosphorylation`, residue `Tyr705`, `SUPPORTED` status | Pass | Verified via web's `/api/search` (0.79 s) and in-browser render (`smoke/02_search_results.png`, `03_evidence_panel.png`) |
| 4. Search `co-IP PIK3CA` | co-IP related results | 4 experiments / 14 lane records: PIK3CA/p85/BEX2 co-IP with IP-bait vs detection antibody distinction, IgG control lane shown | Pass | `smoke/04_coip_pik3ca.png` |
| 5. Search `GAPDH mouse` | Loading-control related results | 31 lane records, mouse tissue GAPDH loading-control rows | Pass | `smoke/05_gapdh_mouse.png` |
| 6. Search `P-ERK` (ambiguity check) | Ambiguity/conflict preserved, not over-resolved by the `P-` prefix | 2 experiments / 10 lane records, all `MAPK1/MAPK3`, `protein_status=AMBIGUOUS`, `modification_status=CONFLICTING`, `modification_type=None` server-side; UI shows "MODIFICATION: unsettled, sources disagree" with both competing claims ("phosphorylation via antibody" vs "no modification (total protein) via row label") displayed, neither picked | Pass | Strongest result of the run; confirms the no-guessing design actually holds under a leading query. `smoke/06_p_erk.png`, `06b_p_erk_evidence.png` |
| 7. Search `BRCA1 MCF7 olaparib` | Likely 0 results with clear scoped-beta copy | `count: 0`; UI: "No matching Western blot evidence was found in the current HiveBlot beta dataset (3 reviewed papers). This does not mean no such evidence exists in the literature; the beta corpus is deliberately small." | Pass | `smoke/07_brca1_zero_results.png` |
| 8. Open evidence/provenance panel | Source type, quote, confidence appear | "Evidence & sources" toggle on each card opens a panel with the normalization chain (raw→canonical→UniProt), per-field source ("via UniProt", "via antibody", "via caption"), quoted snippets, and prior-feedback annotations | Pass | `smoke/03_evidence_panel.png` |
| 9. Crop/figure evidence | Crop image loads or clean fallback | `/api/record/{id}/crop` returned PNG (HTTP 200, `image/png`), image rendered in-page with `naturalWidth` 1422px | Pass | Confirmed via DOM (`img.naturalWidth`), not just HTTP status |
| 10. Feedback path | Harmless test feedback submittable, or limitation clearly noted | Used the "+ Missing information?" control on record id **1189** (STAT3 phospho-Tyr705, Hep3B, IL-6 time course, `10.3892/br.2026.2108`), submitted field name `smoke test 2026-09-20`, comment `smoke test 2026-09-20 - QA smoke test, please ignore/delete`. UI showed "✓ recorded, thank you" | Pass | `smoke/08_feedback_form.png`, `09_feedback_submitted.png`. **Record touched: id 1189.** Not tested: the per-field ✓/✗ correct/incorrect buttons and the "Flag this result" / homepage-level "Beta feedback" widget. One harmless submission was made per instructions, not all feedback surfaces. |
| 11. Browser console/network: no CORS errors, no secrets, headers clean | Clean | Zero console errors/warnings across all pages tested; zero non-2xx network responses; zero direct browser calls to `hiveblot-api.onrender.com` (all API calls correctly proxy through the Vercel `/api/*` route handlers); grepped homepage HTML and all `/api/*` response headers for `INTERNAL_API_KEY`, `AGENT_API_KEY`, Postgres connection strings, `sk-` tokens, bearer tokens; none found | Pass | Matches the code: `INTERNAL_API_KEY`/`API_BASE_URL` are read only in server-side Next.js route handlers (`web/app/api/**/route.ts`), never sent to the client |
| 12. Copy accuracy (home / empty state / about / learn) | No overclaiming on corpus size, coverage, or production readiness | Home, search empty-state, and About page all consistently state "3 papers · 93 experiments · 475 evidence rows"; About page has an explicit "What this beta proves, and what it does not" section explicitly disclaiming literature-wide coverage, extraction accuracy on unseen papers, and precision/recall numbers; a "Beta hosting note" explains the free-tier cold start plainly | Pass (copy is consistent and appropriately conservative) / **stat freshness Not verified** | No endpoint reachable from the web tier reports a live row/paper/experiment count (`/proteins` and `/search` are internal-key-gated and query-scoped, not a full count). The "3/93/475" numbers are hardcoded copy (`web/app/about/page.tsx`, `web/app/search/page.tsx`), not fetched live, so I could not independently confirm they still match the current database, only that they're internally consistent across pages. |

## Issues found

1. **Low severity, informational.** The corpus-size claim ("3 papers · 93 experiments · 475 evidence rows") is hardcoded in frontend copy (`web/app/about/page.tsx`, `web/app/search/page.tsx`) rather than sourced live from the database. If the underlying data changes (e.g. a fourth paper is added) without a copy update, the site will understate/overstate the corpus. No live discrepancy was observed; this is a maintenance risk, not an observed inaccuracy.
2. **Low severity, observation only.** Prior feedback already exists on record 1189 (all fields marked "✓ marked correct" on 2026-09-16), presumably from earlier internal testing. Not a bug, but record 1189's feedback trail is not pristine. The "smoke test 2026-09-20" row this run created (feedback_id 42) was deleted by the orchestrator right after the run, as the project owner, and the deletion was confirmed with a count query.

3. **Low severity, informational.** The API's FastAPI auto-docs are public at `https://hiveblot-api.onrender.com/docs` (found by the hosting check in `HOSTING_STATUS.md`). They expose route names and schemas only; every data route still requires the internal key. Fine for a beta, but easy to disable in `api/app/main.py` (`docs_url=None`) if the route list should not be public.

No functional, security, or data-integrity defects were found. A separate orchestrator pass with a second browser confirmed the `P-ERK` conflict rendering, an empty console, no direct browser calls to the Render origin, and no credential-shaped strings in the served JS bundles (~670 KB scanned).

## Recommended fixes before UCSF sharing

- None are blocking. Optionally: derive the "3 / 93 / 475" corpus stats from a small live count query (or a build-time generated constant checked against the DB) instead of hand-maintained copy, so the numbers can't silently drift from reality as the corpus grows.
- Decide whether the 2026-09-16 "marked correct" feedback on record 1189 should stay visible to UCSF testers. The evidence panel shows all prior feedback inline. The 2026-09-20 smoke row is already gone.

## Unknowns / not tested

- Live experiment-group count (93). Papers (3) and rows (475) were verified directly in the database after the run; no web-reachable count endpoint exists (see Issue 1).
- The per-field ✓ (correct) / ✗ (incorrect, with suggested-value form) / "not useful" buttons in the evidence panel, the candidate-picker buttons under CONFLICTING/AMBIGUOUS fields, the record-level "⚑ Flag this result" flow, and the homepage/search-page "Beta feedback" (Yes/Partially/No) widget. Only the "+ Missing information?" path was exercised, per instructions to submit one harmless feedback item.
- True cold-start behavior (the "30 to 60 s wake-up" UI copy and `slow` state in `web/app/search/page.tsx`). The API was warm throughout this session, so the `slow` banner and the actual wake-up latency were not observed live, only read in code.
- Mobile/responsive layout, other browsers (WebKit/Firefox), and accessibility were not in scope for this pass and were not tested.
- `/v1/search` (the external agent-facing endpoint, `AGENT_API_KEYS`) was not tested. It is out of scope per the task (web-facing flows only) and requires a separate agent key.

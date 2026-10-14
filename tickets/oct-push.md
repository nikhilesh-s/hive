# October push tickets (written 2026-10-11)

Tracks: **R** release (Nik + Nik's Claude, needs credentials), **W** web/product
(Srushti + Codex), **Q** bio QA (Tanvi, no code), **G** growth and outreach (Yashvi +
Claude). The rules for working a ticket are in [`README.md`](README.md).

Context: wave 1 was 27 emails (Yashvi 13 on 9-30, Tanvi 14 on 10-05). There were
0 replies, and Supabase shows almost no outside visits since 9-28. Srushti's Oct 1-3
work is on `main` but not deployed: the Vercel web build is from 9-26.

---

## R-1 · Merge PR #12 and push the pending migrations — Nik + Claude
- Do: merge PR #12, then `supabase db push --linked`. It plans exactly
  `20261011000008/9/11`: hive_feedback grants and policies on `saved_results`, the
  upsert index, and the ingest_jobs indexes.
- Acceptance: `supabase migration list --linked` shows no local-only or remote-only
  versions, and `hive_feedback` has SELECT/INSERT/DELETE on `saved_results`. Without this,
  Saved Results fails in production, because Render uses `DB_FEEDBACK_URL`.

## R-2 · Web auth configuration — Nik + Claude
- Do: add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` to
  Vercel production (see `web/AUTH.md`). Add
  `https://hiveblot-beta.vercel.app/auth/callback` to the Supabase Auth redirect
  allow-list.
- Acceptance: on production, Nik signs in with Google, the session survives a refresh,
  and sign-out works.

## R-3 · Deploy web and run the hosted smoke test — Nik + Claude (after R-1, R-2)
- Render already runs main's API code; PR #12 has no API changes. Run
  `vercel deploy --prod` from `web/`, then move `release/hosted` to the deployed commit.
- Smoke: search STAT3; anonymous save and unsave; sign in, save, `/saved` shows it, sign
  out; Search and About show live counts; `/?lab=smoke_test` then a search writes a
  `search_history` row with `lab_tag = smoke_test` (delete the smoke rows afterwards);
  the research page opens through an access link.
- Acceptance: every smoke item passes, and HANDOFF records the deployed SHAs.

## R-4 · Review and merge PR #11 — Nik (Tanvi checks one paper)
- PR #11 changes live ingestion to metadata, then relevance, then access, then
  retrieval. Papers with no retrievable PDF end as `awaiting_full_text` with an
  institutional-access link instead of failing.
- After merging, deploy Render (autoDeploy is off). Submit two DOIs, one open access and
  one paywalled. Tanvi checks the open-access paper's records.
- Acceptance: the paywalled job ends `awaiting_full_text` with the link shown; the
  open-access job extracts as before.

---

## W-5 - Dynamic corpus counts and recovery - Srushti - P1
- Problem: homepage totals were hardcoded, and a transient statistics failure
  left Home/Search/About unavailable until refresh.
- Scope: use the existing database-backed statistics hook on Home; retry
  transient failures with bounds and abort cleanup; never substitute fake totals.
- Acceptance: independent Supabase totals agree with the API; Home/Search/About
  reflect changed API values; transient recovery, cache/pagination, readonly
  database integration and frontend/browser tests pass.
- Limitations: backend cache remains 60 seconds; no Realtime subscription.
- No access-label changes, migrations, production data writes or deployment.

## W-1 · `?doi=` deep link that opens an already-extracted paper — Srushti (Codex) · P1
- Why: follow-up 2 should take each researcher straight to their own extracted paper.
  Today `/experimental/research` reads no URL parameters. The promised link format
  (`outreach/PREEXTRACT_CHECK.md`) is
  `/experimental/research?doi=<DOI>&lab=<lab_tag>&access=<code>`.
- Do: on load, normalize `doi` (strip `https://doi.org/`, trim, lowercase). Look it up
  among the already-extracted live papers, using the same data as the "Already extracted
  in this stack" section. If found, open that paper's extracted-evidence view. If not,
  prefill the DOI box and say it has not been extracted yet. Make sure the access gate
  keeps `doi` and `lab` through its redirect.
- Don't: start an extraction automatically. Jobs count against the daily cost cap.
- Acceptance: tests for normalization, found and not found. Manual check: a wave-1 DOI
  link opens its evidence after a fresh access-code visit, and a bad DOI shows the
  not-extracted state.

## W-2 · Open the B-3 PR — Srushti · P1
- B-3 ("not stated" vs "not recovered") is 17 commits on `feature/saved-results`
  (2026-10-03), with no PR.
- Do: after PR #12 merges, merge `main` into the branch and open "B-3: not stated vs not
  recovered". Put a screenshot of the record-detail view in the PR body and ask Tanvi to
  review the wording.
- Acceptance: CI green, Tanvi approves the wording in a PR comment, and the B-3 status in
  `bio-qa.md` is updated.

## W-3 · Phone and Safari pass — Srushti · P2 (after R-3)
- Check iPhone Safari and desktop Safari: search, result card, record detail, save,
  `/saved`, sign-in, the research page from an access link, and the feedback buttons.
- Acceptance: a pass/fail list under this ticket. Each failure becomes a new W ticket
  here, with steps and a screenshot.

---

## Q-1 · Sign off the wave-1 pre-extracted papers — Tanvi · P1, by Wed 10/14
- The sheet is `outreach/PREEXTRACT_CHECK.md` on branch `outreach/oct20`. Run the five
  15-minute checks on each of the 9 extracted papers and mark ✅ or ❌ with one line.
- Only ✅ papers get a "your paper" link in follow-up 2.
- Acceptance: every row has ✅ or ❌ and a reason.

## Q-2 · ImageJ spot-check of lane readouts — Tanvi · P1, by Fri 10/16
- Why: nothing independent checks that HiveBlot's lane readouts match the figure.
- Honest scope: figure crops are compressed, and often clipped or saturated. ImageJ here
  checks **band presence and lane ordering only**, not amounts. No number from this goes
  on the site.
- Do: pick 10 panels across at least 5 papers, mixing easy, faint and crowded ones. For
  each lane, use Analyze → Gels lane profiles (or a background-subtracted rectangle
  measure) to record whether a band is present, its intensity rank within the panel, and
  whether it is saturated. Compare with HiveBlot's readout.
- Log one row per lane in a shared sheet with these columns: `date, doi, record_id, panel,
  lane, hiveblot_band, imagej_band, hiveblot_rank, imagej_rank, saturated, agree, note`.
  Yashvi's or Srushti's agent commits it as `qa/imagej/2026-10-16.csv`.
- Acceptance: 10 panels logged, the agreement rate posted in chat, and each disagreement
  filed as a one-line B ticket in `bio-qa.md`.

## Q-3 · Expected target names for B-12 — Tanvi · P2
- List 30 names researchers actually type: aliases, phospho forms (for example
  `p-STAT3 Tyr705`) and loading controls. Give each its gene symbol and UniProt
  accession. Add them under B-12 as "Expected mappings", or send them to Srushti.
- Acceptance: 30 rows, used by the B-12 tests.

## Q-4 · Non-western panel examples for B-13 — Tanvi · P2
- While doing Q-1 and Q-2, note every panel that is a Northern, gel stain, Ponceau,
  microscopy or similar: DOI, panel, and what it is.
- Acceptance: at least 5 examples under B-13 as "Examples".

---

## G-1 · Outreach and grants log — Yashvi (Claude) · P1
- Branch `yashvi-outreach` from `outreach/oct20`, not from `main`, so the prospect ledger
  stays in one place.
- `outreach/yashvi/LOG.md`: dated entries (who, what, outcome, next step).
- `outreach/grants.md`: name, link, deadline, amount, fit, status.
- Open a PR into `outreach/oct20` every Friday.
- Acceptance: entries for the UCSF Tally follow-up, Gina (journal access) and Seiji
  (Stanford referral, internships); every grant being considered is listed.

## G-2 · Email v2 and spam check — Yashvi (Claude) · P1, by Tue 10/13
- Why: wave 1 was 27 emails with 0 replies, and almost no visits.
- Do:
  - Plain text, under 120 words, sent to the paper's first author (grad student or
    postdoc), not the PI.
  - Open with their paper and one concrete thing HiveBlot pulled from it.
  - One link: the W-1 link once it ships, until then the research page with `?access=`
    embedded. One yes/no ask, such as "Did we read lane 3 right?"
  - Two variants: own-paper (Q-1 ✅ papers) and generic.
  - Send one copy from each sending account to mail-tester.com.
- Acceptance: drafts in `outreach/emails_v2.md`, mail-tester scores noted (aim for 8/10
  or better), and Nik approves.

## G-3 · Batch 2, about 100 prospects — Yashvi (Claude) · P2, after G-2 is approved
- Who: first authors of 2024–2026 open-access western blot papers. Use the same columns
  as `outreach/prospects.csv`, dedupe against batch 1 and opt-outs, and give each lab a
  `lab_tag`. Prefer publishers that resolve: PLOS, the Nature family, microPublication
  (see O-2 for blocked ones).
- Pre-extract each paper on hosted `/experimental/research` before its email goes out.
  The cap is 30 extractions a day, so spread them over several days.
- Acceptance: 100 rows, each with a pre-extracted paper or a reason why not; Tanvi
  spot-checks 10 using the Q-1 method.

## G-4 · Stale share-pack line — Yashvi (Claude) · P3
- `UCSF_BETA_HANDOFF_MESSAGE.md`, line 12, still says live search is not hosted. It has
  been hosted, behind the access code, since 9-27. Fix the line in a PR to `main`.

## G-5 · Upload the 8 blocked wave-1 papers — Yashvi · P2, after O-2
- Eight papers in `PREEXTRACT_CHECK.md` are blocked by publisher bot checks. Download
  each open-access PDF in a browser and upload it on the research page. Tanvi then runs
  Q-1 on them.
- Acceptance: all 8 are in the live tier, or each has a stated reason.

## W-4 · Stop trusting browser-sent paper metadata on `/ingest` — Srushti (Codex) · P2
- Found in the PR #11 review. The ingest request now accepts title, abstract, authors,
  journal, pmid, pmcid, `access_*` and `relevance_*` from the browser, with no length
  limits. `paper_metadata` keeps a browser-sent title or pmcid ahead of OpenAlex/NCBI, and
  `check_access` trusts the sent pmcid, so a wrong one can make it check the wrong paper.
  The access and relevance values are recomputed on the server, but they are still accepted.
- Do: drop `access_*` and `relevance_*` from the request model. Cap the lengths (title 500,
  abstract 5000, authors 50 × 200, journal 300). Require pmid to be digits and pmcid to match
  `PMC\d+`. Prefer OpenAlex/NCBI values, using browser values only to fill gaps.
- Acceptance: tests that an oversize field returns 422, a bad pmcid returns 422, and a
  browser-sent title is replaced by the OpenAlex title when one exists.

# Team log

Dated updates from the team, newest first. Facts only: who did what, when, and what is open.
Tickets live in [`README.md`](README.md).

## 2026-10-20

- **Paused**: HiveBlot development is paused after today. See the top of `HANDOFF.md`.
- **Benchmark done**: merged as #43 (`d3fb82c`). Precision of assertions 512/553 (92%), coverage
  512/895 (57%), raw pre-registered 78%. Claims wording: `eval/blind_2026_10/report/CLAIMS.md`.
- **Tanvi**: blind labels for the benchmark (8 panels, 47 target rows, 950 lane calls) and her
  confirmation of the adjudications (A8). Thank you.
- **Yashvi**: the crop map (57/57 crops: 30 mapped to figure panels, 27 not Western blots).
- **Srushti**: groundwork for O-2, W-1, W-5 and W-6, finished by agents and deployed (O-2, W-3, W-4
  10-19; B-3, B-12, B-13 10-20).
- **Deployed**: Render and Vercel at `7e26710`. Zenodo DOI `10.5281/zenodo.23491677` is reserved
  (unpublished draft). `UNPAYWALL_EMAIL` is set.
- **Feedback**: 2 Tally responses (one internal test, one UCSF postdoc, 10-3).

## 2026-10-19

- **Srushti**: no response since 10-14. Her tickets were taken over by agents, with Nik's OK:
  - O-2: the security review fixes were re-reviewed, then merged and deployed.
  - W-3 and W-4: merged and deployed.
  - B-12 and B-13: draft PRs on hold until the benchmark is scored.
- **Yashvi**: on 10-18 she pushed G-1 (outreach log and grants list) and G-2 (email v2 draft) to
  `yashvi-outreach`. Claude made two honesty fixes to v2; mail-tester scores and Nik's approval
  are next. Crop map due Mon 10-19 21:00.
- **Tanvi**: benchmark labels tonight per Nik (due Tue 10-20 12:00).
- **Release prep**: PR #31 (draft) adds the MIT license, CITATION.cff, a public README and a
  Zenodo archive script. Before it merges, Nik needs to confirm the author list and get each
  teammate's OK to release under MIT.
- **Deploys**: Render and Vercel are at `363f19e`. Migration 012 is applied.

## 2026-10-18

- **Priority change**: the blind extraction benchmark (P0, E-1 to E-7) comes before every other
  ticket until Tue 10-20. Tanvi annotates; Yashvi maps crops; Q-1 to Q-4 are paused.
- **Nik / Claude**:
  - Merged Srushti's W-5 (#20), W-6 (#21) and W-1 (#19). W-6 and W-1 needed review fixes first;
    agents pushed them to her branches with tests, and CI is green.
  - Merged O-3 (#25) and G-4 (#26), opened the B-3 PR (#24, draft), closed Copilot PR #2, and
    moved O-2 (#22) onto main.
  - Benchmark: pre-registered and drew 4 unseen papers. Froze the PDFs, ran Stage 1, and started
    the model stage with the production model.
- **Srushti**: 10-14 PRs #19 to #22 (W-1, W-5, W-6, O-2). Nothing has been deployed since 10-11
  (R-5).
- **Tanvi, Yashvi**: no commits or recorded updates since 10-11. Status of these is unknown:
  - Q-1 and Q-2
  - follow-ups 1 and 2
  - the Tally follow-up
  - G-1 and G-2
- **Usage (production DB, read-only)**:
  - 16 searches in 8 anonymous sessions since 9-27, no lab tags, mostly the team's smoke queries.
  - No feedback since 9-16.
  - Details: `research/ADOPTION_STATUS_2026-10-18.md` on the benchmark branch.
- **Security**: the `hive_ingest` password was printed in an agent session; rotation is O-9.

## 2026-10-11

- **Tanvi**: read, fixed and sent her 14 wave-1 emails one at a time on Mon 10-05. Zero replies.
  Follow-up 1 was due about Fri 10-09 and is not reported sent. Follow-up 2 is due about 10-16.
  Her sends are not in `outreach/prospects.csv` yet.
- **Yashvi**: 13 wave-1 emails sent 09-30 (logged). Follow-up 1 sent (date not given). The Tally
  form to UCSF testers is scheduled for Mon 10-12 08:00. She followed up with Gina, who will check
  and get back to her. Seiji will ask whether his lab is open for internships; Yashvi also asked him
  for Stanford labs that might try HiveBlot. She is prioritizing HiveBlot and grant applications
  and will log grants and outreach on a `yashvi-outreach` branch.
- **Srushti**: Oct 1-3 she built Saved Results (anonymous and Google-account), Google sign-in,
  live corpus counts, `?lab=` / `?utm_source=` attribution, paper access badges on search results
  and the B-9 deletion, pushed straight to `main`. B-3 is on `feature/saved-results` (no PR yet).
  PR #11 (metadata-first ingestion) was merged. All of it went live
  10-11. She asked for edit access to the Tally responses.
- **Nik / Claude**: shipped Srushti's work and PR #11 (R-1 to R-4):
  - PR #12 fixed main CI (lockfile, `saved_results` migration, Supabase history).
  - Supabase migrations were pushed and the Vercel keys added; web and API are deployed.
  - Two PR #11 bugs were found live and fixed: buttons stuck after "awaiting full text"
    (#15), and job saves failing past the first step (#16).
  - Nik verified Google sign-in and Save on the live site.
  - Ticket board merged (#14); duplicate #13 closed.
  - Render and `release/hosted` are at `3839ee3`.
- **Usage since 09-28**: 12 searches (one session a day), 0 feedback, 0 extraction jobs.

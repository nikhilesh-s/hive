# Team log

Dated updates from the team, newest first. Facts only: who did what, when, and what is open.
Tickets live in [`README.md`](README.md).

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

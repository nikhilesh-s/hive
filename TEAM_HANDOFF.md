# HiveBlot team handoff (2026-10-11)

This file is for Nik, Srushti, Tanvi and Yashvi. It is the short version of `HANDOFF.md`.
**Open work lives on the ticket board, [`tickets/README.md`](tickets/README.md).** Dated
team updates go in [`tickets/team-log.md`](tickets/team-log.md).

## 1. Status

HiveBlot is a search engine for published Western blots. It turns each blot in a paper into a
structured record: target, antibody, dilution, cell line, and what each lane shows. Every field
carries the quote from the paper behind it. It is live at https://hiveblot-beta.vercel.app,
with the API on Render's free tier.

On 2026-10-11 Srushti's Oct 1-3 work and PR #11 went live. Render and `release/hosted` are at
`3839ee3`; the Vercel web build is at `ffc54a0`, and there have been no web changes since.
Nik checked Google sign-in and Save on the live site.

Outreach: wave 1 was 27 emails (Yashvi 13 on 09-30, Tanvi 14 on 10-05). There have been
0 replies and almost no outside visits since 09-28.

## 2. Features

**Live**
- Reviewed search (3 papers, 475 rows, live counts), with an evidence panel, figure crops and
  per-field ✓/✗ feedback.
- Saved Results for anonymous visitors and Google accounts; Google sign-in; search history.
- Outreach attribution: `?lab=` and `?utm_source=` are stored on searches and feedback.
- Paper access badges (open access, paywalled, unknown) on search results and the research page.
- The research page finds papers and checks metadata, relevance and access first. Paywalled or
  unretrievable papers end as "awaiting full text", with an institutional-access link.
  Downloadable papers extract (PLOS ONE test: 25 experiments, 158 lanes).
- Paper Q&A with citations. Band reading v0.3.0.
- Feedback F-1 to F-6.
- Guards: a beta access code on `/experimental/*`, daily caps, per-researcher limits, and
  hidden API docs.

**Not done**
- `?doi=` deep link (W-1).
- Upload-your-own-PDF (O-2).
- B-3 "not stated" vs "not recovered": built, but no PR yet (W-2).
- Accuracy numbers on unseen papers.
- Calibrated densitometry.

## 3. Bugs and risks (worst first)

- **Most open-access papers can't be downloaded automatically.** Publisher bot checks and
  PMC/Europe PMC block scripts, so these papers end as "awaiting full text". Upload (O-2) fixes it.
- **Free Render.** A 30-60 s cold start means the first request can return 503. A restart kills
  running extractions (O-1).
- **The research page gives up on a job after a few 429s.** It shows "Lost track of this job"
  while the job keeps running (O-8).
- **Extraction quality.** Target-name misses (B-12), Northern blots stored as westerns (B-13),
  and unresolved targets not flagged for review (B-14).
- **Browser-sent paper metadata is trusted too far** on `/experimental/ingest` (W-4).
- Live rows can't be corrected on the site; corrections come by email reply.
- `UNPAYWALL_EMAIL` is unset (O-7). There is a stale share-pack line (G-4). Record 1189 shows
  internal feedback (O-6, Nik decides).

## 4. Tickets

Everything is on [`tickets/README.md`](tickets/README.md), with owners, priorities, statuses and
the rules for agents. P1 this week:
- Srushti: W-1, O-2, W-2
- Tanvi: Q-1, Q-2
- Yashvi: G-1, G-2
- Nik: O-7

## 5. Ideas still on the table

- Search-driven growth: extract and add papers automatically when someone searches (UCSF meeting).
- UCSF network access for journals the institution licenses (the "green flag" idea).
- Organism threading into UniProt, so mouse blots resolve correctly.
- Antibody validation and controls fields; ladder-based MW estimation, then QC flags. Densitometry last.
- Reseed the hosted 475 rows once B-5 has measured the new pipeline (founder decision D-2).
- Escalating ambiguous panels to a stronger model, only if B-5 shows it helps (D-3).


## 6. Outreach to Oct 20

- The hook: **"We extracted the westerns from your paper. Tell us what we got wrong."**
- **What happened:**
  - Yashvi sent 13 on 09-30, plus follow-up 1.
  - Tanvi sent 14 on 10-05; her follow-up 1 was due 10-09 and follow-up 2 is due 10-16.
  - 0 replies, and almost no visits.
- **Changes:**
  - Batch 2 waits for email v2 (G-2): plain text, sent to the first author, opening with their
    own paper, one link, after a spam check.
  - Warm channels: lab-meeting demos through UCSF and Seiji (Stanford), and core facilities.
  - `?lab=` tracking is now live, so clicks count.
- **Rules:** at most ~20 new emails a day, three touches then stop, opt-outs removed the same day.

Top 10 of 84 prospects (43 schools, 70 with a public email). Full sheet:
`git show outreach/oct20:outreach/prospects.csv`.

| Name | School | Persona | Score | Why |
|---|---|---|---|---|
| Julea Vlassakis | Rice | Early-career PI | 90 | Her field is western blot quantification |
| Aldrin V. Gomes | UC Davis | Rigor advocate | 88 | Publicly champions western blot rigor |
| Brianna Bibel | Loyola Marymount | Rigor advocate | 88 | New lab, writes about lab techniques |
| Ana Sachetto | UNC Chapel Hill | Rigor advocate | 88 | Postdoc writing on method pitfalls |
| Cornelius Taabazuing | UPenn | Early-career PI | 88 | Young lab, caspase/gasdermin fragment blots |
| Carrie House | San Diego State | Early-career PI | 86 | Blot-heavy lab; runs the CMB PhD program |
| Robert Banh | NYU | Early-career PI | 86 | Small new lab still setting up workflows |
| Lillian J. Eichner | Northwestern | Early-career PI | 86 | Scaling now; new techs choosing antibodies |
| Jennifer M. Spangle | Emory | Early-career PI | 85 | Uses LI-COR and ChemiDoc quantification |
| Kevin Janes | UVA | Rigor advocate | 85 | Wrote the reference paper on immunoblot quantification |


## 7. Who does what this week

- **Nik:** decisions (section 9), approving email v2, Monday and Thursday check-ins, merges.
- **Srushti + Codex:** W-1, O-2 and W-2, then B-14, B-12, B-13, O-8, W-3 and W-4.
- **Tanvi:** follow-up 1 now and follow-up 2 on 10-16. Q-1 by 10-14, Q-2 (ImageJ) by 10-16,
  then Q-3 and Q-4. Review the B-3 wording.
- **Yashvi + Claude:** UCSF Tally email 10-12 08:00, follow-up 2, Gina and Seiji, G-1 to G-5,
  and O-3.
- Everyone posts done, open and blocked in the chat on Thursday and Sunday.

## 8. Branches

- `main`: source of truth. PRs only, CI must be green, and Nik merges.
- `release/hosted` (`3839ee3`): what Render runs. The Vercel web build is `ffc54a0`.
- `outreach/oct20`: outreach plan, prospect sheet and `PREEXTRACT_CHECK.md`. Yashvi's
  `yashvi-outreach` branches from it.
- `feature/saved-results`: the B-3 work; W-2 turns it into a PR.
- `archive/*` tags: old branches, already merged.

## 9. Nik's decisions needed

1. Move Render to a paid plan (O-1)?
2. Which mailbox for `UNPAYWALL_EMAIL` (O-7)?
3. Record 1189 feedback: keep (recommended) or delete (O-6)?
4. Densitometry page name. Recommendation: "Band reading (experimental)".
5. What lab number to announce on Oct 20. Recommendation: no public number, internal goal of 5.
6. Approve email v2 before batch 2 (G-2).
7. Close Copilot PR nikhilesh-s/hive#2.

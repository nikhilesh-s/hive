# HiveBlot team handoff (2026-09-24)

For Nik, Srushti, Tanvi, Yashvi. Short version of `HANDOFF.md` plus the outreach plan.

## 1. Status

HiveBlot is a search engine for published Western blots. It turns each blot in a paper into a
structured record (target, antibody, dilution, cell line, what each lane shows) with the quote
from the paper behind every field. It is live at https://hiveblot-beta.vercel.app (API on Render
free tier). The live site has reviewed search (3 papers, 475 rows), a research page that finds
and extracts new papers (about 4.5 min each), paper Q&A, and a band-reading tool. The feedback
work (F-1..F-6) is merged to `main` but **not deployed**. Work has been paused since 2026-09-20.
The UCSF follow-up email and Tally form promised for 2026-09-16 were **not sent**.

## 2. Features

**Done**
- Reviewed search: evidence panel, figure crops, per-field ✓/✗ feedback (live).
- Research page: Valency search, PMC fallback, live extraction proven on the hosted site (live).
- Paper Q&A with citations (live).
- Band reading v0.3.0: drawn lanes, saturation refusal, ranges instead of decimals,
  loading-control pairing, export (live).
- Feedback upgrades F-1..F-6: export script, zero-result capture, useful / not relevant,
  3-question survey, opt-in contact, separate rate limit, honest failures (merged, not deployed).
- CI now runs on `main` and `release/**` (commit `273412b`, passing).

**Not done**
- Deploy of F-1..F-6 (needs migration 006 first).
- Daily cap or any auth on paid endpoints.
- `?doi=` deep link on `/experimental/research` (search already supports `?q=`).
- Journal-access flag promised at the UCSF meeting.
- Accuracy numbers on papers we have not seen. None exist yet.
- Calibrated densitometry. There is no ladder calibration; intensity columns stay empty.

## 3. Bugs and risks (worst first)

- **No auth on paid endpoints.** Anyone with the link can start model jobs. `/experimental/ingest`
  is limited to 6/minute but has no daily cap.
- **Deploying the API before migration 006 breaks every feedback submit** (500 error).
- **Paper access is fragile.** Europe PMC and PMC block scripted downloads. We depend on OpenAlex
  finding a publisher PDF. `UNPAYWALL_EMAIL` is not set, so Unpaywall is skipped.
- **Free Render kills jobs.** 30-60 s cold start; a 15-minute idle spin-down kills extractions in
  progress. Jobs run inside the API process. Two people extracting at once is untested.
- **One shared rate-limit bucket.** All Vercel traffic reaches Render from one IP, so every user
  shares search 20/min, feedback 120/min, band reading 60/min. A lab session can hit 429.
- **Live rows cannot be corrected.** Feedback on the live (unreviewed) tier is read-only by design.
  The outreach hook asks authors to click ✗ on their own extracted paper, so this must change or
  the email must say "reply to this email" instead.
- **Stale copy.** The docs pack at repo root (`UCSF_BETA_*.md`, `BETA_EMAIL_*.md`,
  `HOSTING_STATUS.md` and others) still says live search is "not yet in this link". Corpus counts
  are hardcoded in `web/app/about/page.tsx` and `web/app/search/page.tsx`.
- **B-9 closed on `feature/saved-results`:** the stale `api/app/nlp.py` OpenAI NL-to-SQL path was deleted.
  Normal search now always uses deterministic `api/app/bio_query.py` plus `sql_guard.py`.
- Smaller: record 1189 shows internal feedback to testers; API `/docs` is public; reviewed crops
  are baked into the Docker image. Not tested hosted: per-field ✓/✗ after F-6, mobile, other browsers.

## 4. Tickets left

| ID | What | Owner | Blocker / next step |
|---|---|---|---|
| F-8 | Deploy F-1..F-6 and smoke test hosted | Nik | Migration 006 first, then Render, then Vercel. Steps in `HANDOFF.md` |
| F-7 | Weekly feedback triage | Tanvi | Needs F-8 so new feedback lands |
| W-0.2 | Daily cap on ingest and ask | Nik | None. Do before any outreach |
| W-0.4 | `/experimental/research?doi=` deep link | Srushti | None |
| J-1 | Journal-access flag (OA / no OA / may need institution) | Srushti | Deferred ticket `tickets/journal-access-later.md` |
| D-7 | Real ground truth: dilution series, Source Data survey | Yashvi + Tanvi | Needs one lab to agree |
| D-name | Name of the densitometry page | Nik | Decision only |
| B-3 | `not_stated` vs `not_recovered` for empty fields | Nik + Srushti + Tanvi | None |
| B-4 | Recall/precision script (inventory part done) | Tanvi + Nik | Tanvi fills the panel inventories |
| B-5 | `compare_records.py`, 3 repeats per paper | Nik | None; needed before B-7 |
| B-7 | Escalation that merges instead of replaces | Nik | After B-5 |
| B-8 | Sample normalization and tissue routing | Nik + Tanvi | `record_id` must not change |
| B-9 | Delete OpenAI NL-to-SQL | Srushti | Done on `feature/saved-results`; search uses `bio_query.py` |
| B-10 | External adjudicators | Yashvi + Tanvi | Outreach replies can supply them |
| B-11 | Band pattern and lane dose as columns | Nik | Stretch |

## 5. Ideas still on the table

- Search-driven growth: extract and add papers automatically when someone searches (UCSF meeting).
- UCSF network access for journals the institution licenses (the "green flag" idea).
- Organism threading into UniProt, so mouse blots resolve correctly.
- Antibody validation and controls fields; ladder-based MW estimation, then QC flags. Densitometry last.
- Reseed the hosted 475 rows once B-5 has measured the new pipeline (founder decision D-2).
- Escalating ambiguous panels to a stronger model, only if B-5 shows it helps (D-3).

## 6. Outreach to Oct 20

- The hook: **"We extracted the westerns from your paper. Tell us what we got wrong."** Replies,
  evaluation labels and corpus growth all come from one email.
- Fallback for people who will not review: "send a protein and cell line, we send back every
  published western we can find." Done by hand.
- Week 0 (09-24 to 09-27) blocks everything: deploy, daily cap, Render Starter, deep link, stale
  copy, `UNPAYWALL_EMAIL`, UCSF follow-up.
- Before sending, extract one paper per 70+ prospect. Tanvi checks each one. Never link an
  extraction nobody has checked.
- Waves: 0 = UCSF testers (09-28); 1 = score 80+, ~20 (09-29 to 10-01); 2 = 65-79, ~30
  (10-06 to 10-08); 3 = the rest, ~30 (10-13 to 10-15); readout 10-19 to 10-20.
- Targets: 80 sent, 20 replies, 12 users, 8 papers corrected by authors, 150 field labels,
  3 design partners, 1 dilution-series commitment.
- Max ~20 new emails a day, three touches then stop, opt-outs removed the same day.
  **Nothing has been sent. Every email is sent by hand, one at a time, from Nik's mailbox.**

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

- **Nik:** deploy (migration 006, Render, Vercel, F-8 smoke test). Daily cap on ingest and ask.
  Move Render to Starter. Set `UNPAYWALL_EMAIL`. Pre-extract papers Mon-Tue, then all sending and replies.
- **Srushti:** `?doi=` deep link on the research page. Journal-access flag. Any bug a tester reports.
- **Tanvi:** fix stale copy in the docs pack and hardcoded corpus counts. Spot-check every extracted
  paper before it goes in an email. Weekly F-7 triage (extraction bugs become B tickets).
- **Yashvi:** send the overdue UCSF follow-up (Tally form + research page). Own the prospect sheet
  (status per row). Handle concierge requests.

## 8. Branches

- `main`: source of truth. All work lands here. CI runs on it.
- `release/hosted` (`0aa5fdf`): exactly what Vercel and Render run today.
- `outreach/oct20`: outreach plan and prospect sheet.
- `archive/*` tags: 7 old branches, fully merged into `main`, then deleted (2026-09-24).

## 9. Nik's decisions needed

1. Pay for Render Starter ($7/mo)?
2. Which real mailbox for `UNPAYWALL_EMAIL` and for sending outreach?
3. Let authors correct live rows, or ask for corrections by email reply?
4. Daily cap only, or also a shared beta key, before strangers get the link?
5. Densitometry page name. Recommendation: "Band reading (experimental)".
6. B-9 is closed on `feature/saved-results`; normal search no longer depends on `OPENAI_KEY`.
7. Delete the internal feedback on record 1189?
8. Hide API `/docs` (`docs_url=None`)?
9. Close Copilot PR nikhilesh-s/hive#2.
10. Approve the outreach plan and the wave 1 send date (09-29).

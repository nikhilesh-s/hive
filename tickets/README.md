# Ticket board

This board is the single list of open work. Every ticket lives in one track file
in this folder; the board says who owns it, how urgent it is, and where it
stands. The 2026-09-16 sprint plan that used to be here is now
[`sprint-2026-09-16.md`](sprint-2026-09-16.md).

## How to work a ticket (people and coding agents)

Point Codex or Claude at this file and the ticket ID, e.g. *"Work ticket W-1 from
tickets/README.md."* The agent follows these rules:

1. **Read first, and only this:** [`AGENTS.md`](../AGENTS.md) (biology rules that
   cannot be broken), this board, and the ticket. Read `HANDOFF.md` only from the top
   down to the first older dated section; it is long.
2. **One ticket, one branch, one PR.** Branch from `main` as
   `<ticket-id>-<short-slug>` (e.g. `w-1-doi-deep-link`). PR title starts with the
   ticket ID. Never push to `main`. Never merge your own PR. Nik merges.
3. **Claim it.** In your first commit, set the ticket's board row to
   `doing (<name>, <date>)`. In the PR, set it to `PR #<n>`. Nik sets `done` on merge.
4. **Done means** the ticket's *Acceptance* is met, new behavior has a test, and CI is
   green. Run the CI checks locally before you push:
   ```bash
   cd api && python -m pytest -q
   ```
   ```bash
   python -m pytest -q western_blot_miner/tests --ignore=western_blot_miner/tests/test_densitometry.py
   ```
   ```bash
   cd web && npm ci && npx tsc --noEmit && npm run lint && npm run build
   ```
5. **Hands off:** live Supabase, Render and Vercel (no deploys, no `supabase db push`,
   no dashboard edits). Also secrets and `.env` files, and the reviewed
   `western_blot_records` data. Schema changes go in `migrations/NNN_*.sql`, then run
   `python scripts/sync_supabase_migrations.py`. Nik applies them.
6. **Never invent scientific values.** An empty field stays empty, with its reason
   (see B-3). Do not work around publisher bot checks.
7. **Stuck for more than 30 minutes, or the ticket is unclear?** Add a `Questions:`
   line under the ticket, push it, tell Nik, and move on to the next ticket.
8. **PR body:** what changed, how it was tested, and what is left.

**Team updates** go in [`team-log.md`](team-log.md), dated, facts only.

**Accountability:** owners post in the team chat every Thursday and Sunday:
tickets closed, PRs open, anything blocked.

## Board (updated 2026-10-11, end of day)

P1 = this week, P2 = next, P3 = when free. Track files:
[oct-push](oct-push.md) (R, W, Q, G), [bio-qa](bio-qa.md) (B),
[ops](ops-2026-09-27.md) (O), [feedback](feedback.md) (F),
[densitometry](densitometry.md) (D).

### Release (Nik + Nik's Claude; these need credentials)
| Ticket | What | Pri | Status |
|---|---|---|---|
| R-1 | Merge PR #12 (red-CI fix) and push pending Supabase migrations | P1 | done 10-11 (36569fa) |
| R-2 | Supabase keys in Vercel, prod auth callback, Google sign-in test | P1 | done 10-11 (Nik verified sign-in + Save) |
| R-3 | Deploy web, hosted smoke test | P1 | done 10-11 (web ac85a6e, smoke passed) |
| R-4 | Review and merge PR #11 (metadata-first ingestion), deploy API | P1 | done 10-11 (3839ee3) |
| O-7 | `UNPAYWALL_EMAIL` on Render | P1 | needs a team mailbox from Nik |
| O-6 | Record 1189 feedback: keep or delete | P2 | Nik decides (recommend keep) |
| O-1 | Render paid plan | P2 | Nik decides |

### Srushti (+ Codex)
| Ticket | What | Pri | Status |
|---|---|---|---|
| W-1 | `?doi=` deep link opens an extracted paper | P1 | todo |
| O-2 | Upload-your-own-PDF on the research page (API + web) | P1 | todo |
| W-2 | Open the B-3 PR from `feature/saved-results` | P1 | todo |
| B-14 | Unresolved target must set needs_review | P2 | todo |
| B-12 | Target normalization misses (uses Tanvi's Q-3 list) | P2 | todo |
| B-13 | Non-western blots stored as westerns (uses Tanvi's Q-4 list) | P2 | todo |
| O-8 | Research page gives up on transient 429s | P3 | todo |
| W-3 | Phone and Safari pass on the hosted site | P2 | todo (site is deployed) |
| W-4 | Stop trusting browser-sent paper metadata on `/ingest` (from PR #11 review) | P2 | todo |
| W-6 | Honest access labels and independent access-metadata selection | P1 | PR #21 |

### Tanvi (bio QA; no code)
| Ticket | What | Pri | Status |
|---|---|---|---|
| Q-1 | Sign off the 9 wave-1 pre-extracted papers | P1 | todo, by Wed 10/14 |
| Q-2 | ImageJ spot-check of lane readouts, 10 panels | P1 | todo, by Fri 10/16 |
| Q-3 | 30 expected target names for B-12 | P2 | todo |
| Q-4 | 5+ non-western panel examples for B-13 | P2 | todo |
| B-3 | Review "not stated" vs "not recovered" wording on the W-2 PR | P1 | waits on W-2 |
| F-7 | Weekly feedback triage | P3 | ongoing (no new rows since 9-16) |

### Yashvi (+ Claude)
| Ticket | What | Pri | Status |
|---|---|---|---|
| G-1 | Outreach and grants log on `yashvi-outreach` | P1 | todo |
| G-2 | Email v2 plus spam check, for Nik's approval | P1 | todo, by Tue 10/13 |
| G-3 | Batch 2: about 100 first authors, papers pre-extracted | P2 | after G-2 approved |
| G-4 | Fix the stale "live search isn't hosted" line | P3 | todo |
| G-5 | Upload the 8 blocked wave-1 PDFs | P2 | after O-2 |
| O-3 | `export_feedback.py --since` drops same-day rows | P3 | todo |

### Done (recent)
B-1, B-2, B-6, B-9 (bdd5410), F-0 to F-6, F-8 (release of 2026-09-27), Ticket C saved
results (on main; ships with R-3), `?lab=` attribution (47d4071), live corpus
counts (b9e9c04), reviewed-results access flags (2a7d0b8). O-4 and O-5 are accepted
as-is.

### Parked (not this push)
B-4 (scaffold landed, review pending), B-5, B-7, B-8, B-10, B-11, all of D-1 to D-7
(see the status block in `densitometry.md`), and `journal-access-later.md`.

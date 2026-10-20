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

## Board (updated 2026-10-18)

P0 = before anything else, P1 = this week, P2 = next, P3 = when free. Track files:
[oct-push](oct-push.md) (R, W, Q, G), [bio-qa](bio-qa.md) (B),
[ops](ops-2026-09-27.md) (O), [feedback](feedback.md) (F),
[densitometry](densitometry.md) (D).

### P0: blind extraction benchmark (due Tue 10-20)
Branch `eval/blind-benchmark-2026-10`, folder `eval/blind_2026_10/`. Read `TEAM_TASKS.md` there.
Until it is scored, **do not merge or deploy anything under `western_blot_miner/`**. The
benchmark measures commit `f77d311`, which is what production runs.

| Ticket | What | Owner | Status |
|---|---|---|---|
| E-1 | Pre-register, draw 4 papers, freeze PDFs, Stage 1 | Nik + Claude | done 10-18 (`38bf0a6`, `5ba7945`) |
| E-2 | Model stage on the frozen papers, then seal outputs | Nik + Claude | papers 1, 2 and 4 done 10-18; paper 3 running |
| E-3 | Browser download of PMC7948984 (or log the skip) | Nik | done 10-18 (rank 3 replaces rank 8) |
| E-4 | Blind annotation of 4 papers (`ANNOTATOR_GUIDE.md`) | Tanvi | shared 10-18 (Drive folder + Sheet); due Mon 10-20 12:00 PT |
| E-5 | Map 57 crops to figure and panel (`TEAM_TASKS.md`) | Yashvi | shared 10-18 (Drive folder + Sheet); due Sun 10-19 21:00 PT |
| E-6 | Second annotator on paper 1 (optional) | Nik picks | todo |
| E-7 | Score, adjudicate, report (`RUNBOOK.md` steps 5-7) | Nik + Claude | after E-4, E-5 |

### Release (Nik + Nik's Claude; these need credentials)
| Ticket | What | Pri | Status |
|---|---|---|---|
| O-9 | Rotate the `hive_ingest` DB password (it was printed in an agent session on 10-18) | P0 | done 10-18 (role, Render, `api/.env`, DSN file; new login verified) |
| O-10 | Rotate the gswitch `FASTMCP_SERVER_AUTH_GOOGLE_JWT_SIGNING_KEY` (also printed 10-18); re-authorize the ChatGPT connector afterwards | P1 | Nik decides |
| R-5 | Deploy W-1, W-5, W-6, O-3, O-8, W-7 (API first, then web), then a hosted smoke test | P1 | done 10-18: Render and Vercel at `edd95f5`; health, Home, Search, About and corpus stats checked |
| O-7 | `UNPAYWALL_EMAIL` on Render | P1 | needs a team mailbox from Nik (still unset 10-18) |
| O-6 | Record 1189 feedback: keep or delete | P2 | Nik decides (recommend keep) |
| O-1 | Render paid plan | P2 | Nik decides (still free 10-18) |

### Srushti (+ Codex)
| Ticket | What | Pri | Status |
|---|---|---|---|
| O-2 | Upload-your-own-PDF on the research page (API + web) | P1 | PR #22: 7 security-review items fixed 10-19 (finished for Srushti, Nik approved); apply migration 012 before uploads work; Nik reviews/merges |
| W-2 | Open the B-3 PR from `feature/saved-results` | P1 | PR #24 (draft, opened 10-18); hold the merge until E-7 |
| B-14 | Unresolved target must set needs_review | P2 | probably covered by `4cbbaa8` in PR #24; check after E-7 |
| B-12 | Target normalization misses (uses Tanvi's Q-3 list) | P2 | held until E-7 (extraction code) |
| B-13 | Non-western blots stored as westerns (uses Tanvi's Q-4 list) | P2 | held until E-7 (extraction code) |
| W-7 | W-5 review follow-ups (non-retryable config/401, old-Safari abort, standalone DB test) | P3 | done 10-18 (#29) |
| O-8 | Research page gives up on transient 429s | P3 | done 10-18 (#28) |
| W-3 | Phone and Safari pass on the hosted site | P2 | todo (R-5 deployed 10-18) |
| W-4 | Stop trusting browser-sent paper metadata on `/ingest` (from PR #11 review) | P2 | todo (labels are safe since W-6; job metadata is still trusted) |

### Tanvi (bio QA; no code)
| Ticket | What | Pri | Status |
|---|---|---|---|
| E-4 | Blind benchmark annotation (see P0) | P0 | todo, due Mon 10-20 12:00 PT |
| B-3 | Review "not stated" vs "not recovered" wording on PR #24 | P1 | after E-4 |
| Q-1 | Sign off the 9 wave-1 pre-extracted papers | P1 | paused for E-4 (was due 10/14; no sign-off recorded) |
| Q-2 | ImageJ spot-check of lane readouts, 10 panels | P2 | paused for E-4 (was due 10/16; nothing recorded) |
| Q-3 | 30 expected target names for B-12 | P2 | paused |
| Q-4 | 5+ non-western panel examples for B-13 | P2 | paused |
| F-7 | Weekly feedback triage | P3 | ongoing (no new rows since 9-16) |

### Yashvi (+ Claude)
| Ticket | What | Pri | Status |
|---|---|---|---|
| E-5 | Crop mapping for the benchmark (see P0) | P0 | todo, due Sun 10-19 21:00 PT |
| G-1 | Outreach and grants log on `yashvi-outreach` | P1 | todo (branch not pushed as of 10-18) |
| G-2 | Email v2 plus spam check, for Nik's approval | P1 | no update since 10-11 (was due 10/13) |
| G-3 | Batch 2: about 100 first authors, papers pre-extracted | P2 | after G-2 approved |
| G-5 | Upload the 8 blocked wave-1 PDFs | P2 | after O-2 |

### Done (recent)
- 10-18:
  - W-1 `?doi=` deep link (#19, `d01f08d`)
  - W-5 dynamic corpus counts (#20, `69c3737`)
  - W-6 honest access labels (#21, `1319f9a`; review fixes: unverified jobs can't set labels,
    PostgREST quoting, http(s)-only links)
  - O-3 `--since` same-day rows (#25)
  - G-4 share-pack line (#26)
  - Copilot PR #2 closed (obsolete)
- 10-11: R-1 to R-4.
- Earlier: B-1, B-2, B-6, B-9 (bdd5410), F-0 to F-6, F-8 (release of 2026-09-27), Ticket C saved
  results, `?lab=` attribution (47d4071), live corpus counts (b9e9c04), reviewed-results access
  flags (2a7d0b8). O-4 and O-5 are accepted as-is.

### Parked (not this push)
B-4 (scaffold landed, review pending), B-5, B-7, B-8, B-10, B-11, all of D-1 to D-7
(see the status block in `densitometry.md`), and `journal-access-later.md`.

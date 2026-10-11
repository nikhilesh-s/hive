# Ticket board

This is the single list of open work. Reminders and chat point at ticket IDs here.
Each ID has a spec in the file linked in its row. The old 09-16 sprint plan is in
[`sprint-2026-09-16.md`](sprint-2026-09-16.md), kept for history.

## How to work a ticket (people, Claude, Codex)

1. Pick a row whose **Owner** is you (or `Agent`, if you are running Claude or Codex) and whose
   **Status** is `ready`. Change its status to `in progress (<name>)` in the PR that does the work.
2. Open one branch per ticket, named `t/<ID>-<short-slug>` (for example `t/W-0.4-doi-deep-link`).
   Never push to `main`.
3. Read the spec, `AGENTS.md` (biological rules) and the top of `HANDOFF.md` before you change code.
4. Open a PR into `main` titled `<ID>: <what changed>`. CI must be green before you ask Nik to
   merge. In the PR, list the checks you ran and what you could not check.
5. In the same PR, set the ticket's spec heading to `— DONE <date> (<short sha>)` and its row
   here to `done`. Add a short dated entry at the top of `HANDOFF.md`.
6. Deploys, Supabase migrations and production env vars belong to Nik or Claude only (see O-9).
   Never commit secrets; refer to them by name only.

Owners: `Agent` = whichever agent picks it up (Claude in Nik's repo, or Srushti's Codex). A named
person means it needs that human.

## Open tickets (2026-10-11)

### Ship and ops
| ID | What | Owner | Status | Spec |
|---|---|---|---|---|
| O-9 | Put the Oct 1-3 work live: migrations, Vercel Supabase keys, web deploy, smoke test | Agent (Claude) + Nik | blocked: merge PR #12 | [ops](ops-2026-09-27.md) |
| O-1 | Render is still on the free plan (cold starts, killed jobs) | Nik | ready: add a card | [ops](ops-2026-09-27.md) |
| O-7 | Set `UNPAYWALL_EMAIL` on Render | Nik picks mailbox, Agent sets it | blocked: mailbox | [ops](ops-2026-09-27.md) |
| O-6 | Keep or delete the 11 feedback marks on record 1189 | Nik | decision | [ops](ops-2026-09-27.md) |
| O-2 | Upload your own PDF when automatic download fails | Srushti (Codex) | ready | [ops](ops-2026-09-27.md) |
| O-8 | Research page gives up on slow jobs after 10 s of 429s | Srushti (Codex) | ready | [ops](ops-2026-09-27.md) |
| O-3 | `export_feedback.py --since` drops same-day rows | Srushti (Codex) | ready | [ops](ops-2026-09-27.md) |
| O-10 | Phone and Safari check of the hosted site | Agent, then Srushti on a real iPhone | blocked: O-9 | [ops](ops-2026-09-27.md) |
| O-11 | Extract the 9 publisher-blocked wave-1 papers | Nik or Tanvi download, Agent extracts, Tanvi signs off | ready | [ops](ops-2026-09-27.md) |

### Product
| ID | What | Owner | Status | Spec |
|---|---|---|---|---|
| W-0.4 | `/experimental/research?doi=` opens an already-extracted paper directly | Srushti (Codex) | ready | [product](product.md#w-04) |
| B-3 | "Not stated" vs "not recovered" for empty fields: built, needs a PR | Agent opens PR, Tanvi reviews wording, Nik merges | ready | [bio-qa](bio-qa.md) |
| PR #11 | Paper access and relevance in the ingestion flow (Srushti) | Nik | review: updated 10-11 | GitHub |

### Bio QA
| ID | What | Owner | Status | Spec |
|---|---|---|---|---|
| B-15 | Check 10 extracted panels by hand with ImageJ | Tanvi | ready | [bio-qa](bio-qa.md) |
| B-12 | Target normalization misses common protein names | Agent | ready | [bio-qa](bio-qa.md) |
| B-13 | Northern blots get extracted as westerns | Agent | ready | [bio-qa](bio-qa.md) |
| B-14 | An unresolved target does not set needs_review | Agent | ready | [bio-qa](bio-qa.md) |
| F-7 | Weekly feedback triage | Agent pre-sorts, Tanvi judges | ready (0 new rows) | [feedback](feedback.md) |
| B-4, B-5, B-7, B-8, B-11 | Recall measurement, repeat runs, escalation, sample routing, extra columns | Agent | backlog | [bio-qa](bio-qa.md) |

### Outreach
| ID | What | Owner | Status | Spec |
|---|---|---|---|---|
| OUT-1 | Rewrite the follow-up and batch-2 email; spam check | Agent drafts, Tanvi and Yashvi test | ready | [outreach](outreach.md#out-1) |
| OUT-2 | Research batch 2 (~100 prospects) | Agent | blocked: OUT-1 | [outreach](outreach.md#out-2) |
| OUT-3 | Fix the stale "live search is not in this link" copy in the docs pack | Agent | ready | [outreach](outreach.md#out-3) |
| OUT-4 | Warm intros and lab-meeting demos | Yashvi + Nik | ready | [outreach](outreach.md#out-4) |

## Team updates

Dated updates from Tanvi, Yashvi and Srushti go in [`team-log.md`](team-log.md).

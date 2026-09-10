# Post-UCSF sprint — ship Wednesday 2026-09-16

Written 2026-09-09 after the UCSF meeting. Three tracks, each with its own
ticket file:

- [`feedback.md`](feedback.md) — Track F: researcher feedback we can pull and analyze (**priority 1**, cheapest, and the founder's direct question)
- [`densitometry.md`](densitometry.md) — Track D: band reading with honest uncertainty and refusal
- [`bio-qa.md`](bio-qa.md) — Track B: scientific validity of extraction (Tanvi's questions, unparked)

Meeting notes from UCSF are not in the repo yet. When Nik dispatches them,
add a `ucsf-notes.md` here and turn each concrete request into a ticket on
the matching track; do not rewrite the plan around them until then.

## Decisions Nik has to make first (Thursday morning)

| # | Decision | Recommendation |
|---|---|---|
| D-0 | **Release vehicle for the 09-16 beta.** The hosted beta is frozen at `7d80b8b` (`feature/bio-context-beta`, API `96678c8`). The demo branch carries the experimental stack with `experimental_enabled` defaulting to true, the densitometry route and the local-only research page. | Cut `release/beta-2026-09-16` from `feature/bio-context-beta`, cherry-pick only F-2..F-6 (+ B-9 if done), deploy that. Experimental work stays on `experimental/*` and local. Do not ship the experimental branch to Vercel/Render. |
| D-1 | **What to call the densitometry page.** There is no calibration in the repo and most reviewed crops are clipped. | "Band reading (experimental)" with the refusal policy in D-3/D-6. Reserve the word densitometry for a calibrated feature. |
| D-2 | **Reseeding the hosted 475 rows** after B-1 / B-2 / B-8 change extraction output. | Not this week. Measure first (B-5), Tanvi reviews the diff, reseed in week 2. `record_id` stability is a hard test in B-8. |
| D-3 | **Is a 20 s escalation call per ambiguous panel acceptable** on `claude_cli`? | Defer B-7 to week 2 unless B-5 shows it buys something. |

## Definition of shipped, 2026-09-16

**Hosted beta (what UCSF researchers touch):**
- F-2 zero-result capture, F-3 useful / not-what-I-needed, F-4 three-question survey, F-5 opt-in contact + real `app_version`, F-6 separate rate limit and honest failure state, all deployed (F-8), each verified with one hosted row read back through the F-1 export.
- `scripts/export_feedback.py` works against production; the first F-7 triage has been run on whatever rows exist.

**Experimental stack (local, demo-able):**
- D-1 region reaches the API, D-2 researcher-defined lanes, D-3 saturation refusal, D-4 ranges instead of decimals, D-6 refusal card + method block + JSON export, page renamed per D-1. The 59.7% is retired with a written baseline (D-5 header).

**Extraction validity:**
- B-1 caption/methods separation and B-2 antibody backstop landed on the experimental branch with tests; B-6 stale L1 table fixed; B-4 panel inventory checked in for all three papers.
- B-5 first `compare_records.py` run published if time allows; otherwise Monday of week 2.

**Explicitly not shipped this week:** loading-control ratios, anything stored for densitometry, B-3 null provenance, B-7 escalation, B-8 sample routing, B-9, unseen-paper accuracy claims of any kind.

## Timeline

Working days: Thu 10, Fri 11, Mon 14, Tue 15, Wed 16 (ship by end of day).
Half-days per person: Nik 10, Srushti 10, Tanvi 8, Yashvi 6. Weekend is
buffer, not plan.

| Day | Nik | Srushti | Tanvi | Yashvi |
|---|---|---|---|---|
| **Thu 10** | D-0..D-3 decisions; cut release branch; F-1 export script (0.5); F-6 limit (0.5); B-6 L1 fix (0.5) | F-2 zero-result (0.5); D-1 region proxy (0.5) | B-4 panel inventory, paper 1 of 3 (1) | F-4 survey wording (0.5); send UCSF thank-you + ask for the eval papers and lab contacts (0.5) |
| **Fri 11** | B-1 caption/methods (1.5); F-3 api half (0.5) | F-3 web half (0.5); D-2 lane dividers, web (2) | B-4 inventory papers 2–3 (1); D-3 threshold study on the Butler set (0.5) | B-10 adjudicator outreach (1) |
| **Mon 14** | D-2 api (1); B-2 antibody backstop (1) | F-4 survey build (1); F-5 checkbox + F-6 UI (0.5); D-2 finish (0.5) | B-2 spot-check recovered catalogs (0.5); D-5 author LC3B:ACTB values, first pass (1) | D-7 dilution-series ask to one lab (0.5); collect any UCSF replies into `ucsf-notes.md` (0.5) |
| **Tue 15** | D-3 saturation gate (1.5); F-5 migration + api (0.5) | D-6 refusal card, method block, export (2) | D-5 author values, finish (0.5); F-7 first triage on live rows (0.5); D-7 protocol draft (0.5) | Buffer / follow-ups |
| **Wed 16** | D-4 ranges (2, morning); **F-8 deploy + hosted smoke** (1, afternoon); HANDOFF | B-9 OpenAI path (0.5); D-6 polish; release QA on the hosted beta (1) | B-10 annotation brief (0.5); review D-6 copy for overclaims (0.5) | Confirm survey reaches researchers; note who to follow up with |

Nik is at 10.5 half-days against 10. The release valve is D-4: if Tuesday
slips, D-4 moves to week 2 and Wednesday morning goes to deploy and smoke.
Nothing on the hosted-beta path depends on D-4.

## Week 2 backlog (2026-09-17 onward), in order

1. B-5 `compare_records.py` three-repeat run, then B-1/B-2 before-vs-after.
2. B-3 null provenance (`not_stated` vs `not_recovered`).
3. B-8 sample normalization and tissue routing, then D-2 reseed decision.
4. B-7 escalation that escalates and merges.
5. D-5 synthetic recovery study (error vs clip fraction, vs box jitter).
6. D-7 / B-10 follow-through: dilution series, external adjudicators.
7. Loading-control pairing data model (record ↔ strip position). Not
   before the reseed decision.
8. Supabase pausing questions in `super-based-ticket.md` (project is active
   today; the 7-day inactivity risk stays while traffic is low).

## Ticket index

| ID | Title | Owner | Half-days | This week |
|---|---|---|---|---|
| F-0 | Supabase awake, feedback writes end to end | Nik | done | ✓ |
| F-1 | `scripts/export_feedback.py` | Nik | 0.5 | ✓ |
| F-2 | Capture zero-result searches | Srushti | 0.5 | ✓ |
| F-3 | Result-level useful / not what I needed | Srushti + Nik | 1 | ✓ |
| F-4 | Three-question end-of-session survey | Yashvi + Srushti | 1 | ✓ |
| F-5 | Opt-in contact + real `app_version` (migration 006) | Nik + Srushti | 1 | ✓ |
| F-6 | Separate feedback rate limit; honest failure state | Nik + Srushti | 0.5 | ✓ |
| F-7 | Weekly feedback triage | Tanvi | 0.5/pass | first pass ✓ |
| F-8 | Beta release + hosted smoke | Nik | 1 | ✓ |
| D-1 | Forward `region` to the API | Srushti | 0.5 | ✓ |
| D-2 | Researcher-defined lanes | Srushti + Nik | 3 | ✓ |
| D-3 | Saturation gate on the band core | Nik + Tanvi | 2 | ✓ |
| D-4 | Ranges, not point values | Nik | 2 | ✓ (valve) |
| D-5 | Retire D1; synthetic study; author-value comparison | Nik + Tanvi | 3 | header + author values only |
| D-6 | Refusal card, method block, export, storage decision | Srushti + Nik | 2 | ✓ |
| D-7 | Real ground truth (dilution series, Source Data survey) | Yashvi + Tanvi | 1 + weeks | start |
| B-1 | Caption / methods separation in live extraction | Nik | 1.5 | ✓ |
| B-2 | Deterministic antibody backstop | Nik + Tanvi | 1 | ✓ |
| B-3 | Null provenance `not_stated` / `not_recovered` | Nik + Srushti + Tanvi | 2.5 | week 2 |
| B-4 | Panel inventory + CV recall measurement | Tanvi + Nik | 2 | inventory ✓, script week 2 |
| B-5 | `compare_records.py` three repeats per paper | Nik | 2 | if ahead |
| B-6 | Correct the stale L1 report | Nik | 0.5 | ✓ |
| B-7 | Escalation that escalates and merges | Nik | 1.5 | week 2 |
| B-8 | Sample normalization + tissue routing (record_id stable) | Nik + Tanvi | 1.5 | week 2 |
| B-9 | Fix or delete OpenAI NL→SQL | Srushti | 0.5 | ✓ |
| B-10 | External adjudicators for week 2 | Yashvi + Tanvi | 1 | ✓ |
| B-11 | Band pattern / lane dose columns | Nik | 1 | stretch |

## Rules that do not move this week

Reviewed corpus stays human-reviewed and unchanged on the hosted beta. Live
tier stays badged `LIVE · UNREVIEWED`. Conflicting stays unresolved. Band
presence ≠ densitometry; the reserved intensity columns stay NULL. No
accuracy number for unseen papers anywhere. No secrets in tickets or HANDOFF.

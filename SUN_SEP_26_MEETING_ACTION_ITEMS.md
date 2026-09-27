# Sun Sep 26 Meeting Action Items

HiveBlot, push to **Tue 2026-10-20**. Owners: Nik (worst bugs, deploy, running the team),
Srushti (development and tickets), Tanvi and Yashvi (outreach; Tanvi also owns bio QA checks).
Background: [`TEAM_HANDOFF.md`](TEAM_HANDOFF.md). Outreach plan, prospect sheet and email drafts:
branch `outreach/oct20`, folder `outreach/`.

## The goal

By 10-20, Nik can say: **"X unique labs, beyond our two UCSF labs, are using the HiveBlot beta."**
Recommended target: **20 labs** (stretch 30). Every lab in that number has evidence behind it.

### What counts as a lab "using" HiveBlot

A lab counts once when anyone in it (PI, postdoc, student, tech) has done at least one of:

- run a search or extraction through a link carrying their `?lab=` tag,
- opened a result we prepared for them and replied about it,
- submitted feedback (in-app or the Tally form).

Record it in the ledger columns of `outreach/prospects.csv` (`used_on`, `evidence`: a feedback
row id, a search-history row, or the email). Opening an email, replying "no", and the two UCSF
labs do not count. Beta use counts.

## How to get the most labs (the plan in six lines)

1. **Do the work for them.** Most searches on the 3-paper corpus return nothing, and live
   extraction takes minutes. So every email offers: "reply with a protein, we'll send back what
   HiveBlot pulls out of the published westerns for it." We run it, Tanvi checks it, we send the link.
2. **Aim at multipliers.** Core facilities, PhD program directors and lab-course instructors
   each reach many labs. Every thread ends with a referral ask for one more colleague.
3. **Volume.** 84 prospects at about 20% reply and half of those trying it gives roughly 8-10
   labs. Twenty labs needs about 200 contacts, so a second batch of ~100 prospects gets built
   in week 2 (Nik runs the research agents; same criteria as the first 84).
4. **Make the link survive strangers first.** Nik's bug list ships before wave 1.
5. **Bio QA is the credibility.** No extraction reaches a researcher unchecked. Every
   correction is a label. Author-checked papers become the first honest accuracy table.
6. **Count honestly.** Lab tags plus the ledger. Say "X labs tried the beta" only with evidence.

## Timeline

| Date | What happens |
|---|---|
| Sun 9/27 | Team call, reminders handed out |
| Mon 9/28 - Tue 9/29 | Nik: release + worst bugs. Srushti: lab tag + deep link. Yashvi: UCSF follow-up. Tanvi: stale copy |
| Tue 9/29 - Thu 10/1 | **Wave 1** (27 emails, score 80+), starts once lab tags and the daily cap are live |
| Tue 10/6 - Thu 10/8 | **Wave 2** (35) + follow-up 1 for wave 1; second prospect batch ready |
| Tue 10/13 - Thu 10/15 | **Wave 3** (22) + batch 2 + remaining follow-ups |
| Fri 10/16 | Ledger count, chase every half-finished conversation |
| Mon 10/19 - Tue 10/20 | Readout: lab count, quotes, author-checked accuracy table |

---

## Reminders (paste-ready)

Format: heading reminder, then subtasks. Paste a block into Apple Reminders (each line becomes a
reminder), select the subtask lines and press `Cmd ]` to indent them under the heading.

### Nik

**Ship Pending Release**
- Apply migrations 006 and 007 with supabase db push dry-run first
- Deploy API on Render, then web on Vercel, from main
- Smoke test feedback, survey, history on hosted site, then delete rows
- Move release/hosted branch to the deployed commit and note the SHA

**Fix Worst Bugs**
- Add daily cap on ingest and ask so strangers can't burn credits
- Upgrade Render to Starter so cold starts stop killing extractions
- Key rate limits on real client IP, not the shared Vercel proxy
- Set UNPAYWALL_EMAIL to a team mailbox so more papers resolve
- Hide public API docs and delete internal feedback on record 1189
- Run two simultaneous extractions on hosted site and confirm neither dies

**Pre-extract Wave 1 Papers**
- Pick one open-access western paper per wave 1 PI from sheet
- Run extractions locally with concurrency four into the hosted live tier
- Hand each paper to Tanvi; only checked ones get the variant email
- Paste deep links into the email drafts once Srushti ships them

**Run The Team**
- Hold 15-minute check-ins Monday and Thursday; unblock people same day
- Review every Srushti PR; nothing merges to main with red CI
- Count unique labs every Friday from the ledger, post number in chat
- Update HANDOFF.md and TEAM_HANDOFF.md every Friday, then push to main
- Close stale Copilot PR and delete merged feature branches on GitHub
- Run the second prospect batch of about 100 during week two

**Make This Week's Decisions**
- Decide whether authors can correct live rows in the site itself
- Name the densitometry page; recommendation is Band reading (experimental) for now
- Approve wave 1 send date and the sender signatures for Tanvi, Yashvi
- Decide the public lab goal we announce, recommend twenty by October 20

### Delegated to Srushti

**Delegated to Srushti**
- Capture ?lab= tag and attach it to search history, feedback rows
- Add ?doi= deep link that opens an already-extracted paper directly
- Ship Ticket C saved results from your spec, behind passing CI
- Add journal-access flag: open access versus may need institutional login
- Replace hardcoded corpus counts with live numbers from the API
- Delete the stale OpenAI NL-to-SQL path, ticket B-9, keep tests green
- Build B-3: show not stated versus not recovered for empty fields
- Test hosted site on phone and Safari; file anything broken
- Work on feature branches, open PRs, and never push straight to main

### Delegated to Tanvi

**Delegated to Tanvi**
- Read each wave 1 email, fix anything untrue, then send individually
- Answer every target request within 24 hours using the research page
- Spot-check every extraction before its link goes to any researcher
- Check Nik's wave 1 pre-extracted papers: target, antibody, lane readout
- Send follow-up one after four business days, follow-up two a week later
- Log every send, reply, and use in the prospects sheet ledger
- Triage feedback weekly: valid, invalid, unclear; extraction bugs become B tickets
- Fix stale share-pack copy that says live search isn't hosted
- Ask every responder for one colleague who runs a lot of westerns

### Delegated to Yashvi

**Delegated to Yashvi**
- Send overdue UCSF follow-up with Tally form and research page link
- Read each wave 1 email, fix anything untrue, then send individually
- Answer every target request within 24 hours using the research page
- Send follow-up one after four business days, follow-up two a week later
- Own the lab ledger: who used it, when, and the evidence
- Ask core facilities and PhD program directors to forward to their labs
- Collect referral names and add them to the sheet with source
- Remove opt-outs the same day and never contact those people again
- Collect three quotable reactions, with written permission to quote them

---

## Details an agent needs (by owner)

### Srushti: development, in priority order

1. **Lab tag (P0, needed before wave 1).** Every outreach link carries `?lab=<tag>` (neutral
   tags like `rice_university_1`, never a surname). On any page, read `lab`, accept only
   `^[a-z0-9_]{1,40}$`, keep it in localStorage, and send it with search-history writes and
   feedback submits. Store it in a nullable column (new additive migration) and make
   `scripts/export_feedback.py` able to count distinct tags. Touches `web/lib/history.ts`,
   `web/lib/feedback.ts`, `api/app/routers/internal.py`, `api/app/db.py`, `migrations/`.
2. **Deep link (P0).** `/experimental/research?doi=<doi>` opens an already-extracted paper
   (the page already has an "open extracted paper" path). Concierge replies and the "your
   paper" email variant depend on it. `web/app/experimental/research/page.tsx`.
3. **Ticket C saved results.** Your spec: `research/team_delegation/NIKHILESH_TICKET_C_SAVED_RESULTS.md`
   (the expanded version is on branch `docs/expand-search-history-ticket`; open a PR for it).
4. **Journal-access flag** promised at the UCSF meeting: `tickets/journal-access-later.md`.
5. **Live corpus counts** instead of hardcoded copy in `web/app/about/page.tsx` and
   `web/app/search/page.tsx`.
6. **B-9** (delete `api/app/nlp.py` path) and **B-3** (null provenance) from `tickets/bio-qa.md`;
   Tanvi reviews B-3 wording.

Notes: your search-history merge (`ca1150d`) turned CI red on main. The cause was a test, not
the feature: `_as_role` rolls back after each statement, so the read-back SELECT saw 0 rows.
Fixed in `8885a7b`. Migration `20260925000007_search_history.sql` ships with Nik's release.
From now on: branch, PR, green CI, then merge.

### Tanvi and Yashvi: outreach

- Your emails are drafted: `outreach/emails_tanvi.md` and `outreach/emails_yashvi.md` on
  branch `outreach/oct20`. 42 prospects each, split by school so each school hears from one
  person. Tanvi has the technical personas (rigor researchers, core facilities).
- Send from your own mailbox, one email at a time, 10-15 a day, Tue-Thu mornings in the
  recipient's time zone. Read every email before sending and fix anything that isn't true.
- Concierge loop: a researcher replies with a target, you run it on
  `/experimental/research`, Tanvi checks the result, you reply with the link. Target: 24 hours.
- Wave 1 "your paper" variants are only for papers Nik pre-extracted and Tanvi checked.
- Ledger: `owner`, `wave`, `lab_tag`, `status`, `used_on`, `evidence` columns in
  `outreach/prospects.csv`. Status values: `sent`, `fu1`, `fu2`, `replied`, `used`, `no`, `bounced`.

### Rules that do not move

Nothing unchecked goes to a researcher. Live rows stay `LIVE · UNREVIEWED` until checked. No
accuracy claims for new papers until the author-checked table exists. Opt-outs are removed the
same day. No secrets in any file.

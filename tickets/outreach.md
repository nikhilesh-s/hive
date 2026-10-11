# Outreach tickets (to Oct 20)

State on 2026-10-11: 27 wave-1 emails had been sent: Yashvi 13 on 09-30, Tanvi 14 on 10-05.
There were zero replies. Since 09-28 the site shows 12 searches (one session a day, probably
internal), 0 feedback rows and 0 extraction jobs, so recipients are not clicking either. `?lab=`
capture is not live until O-9, so clicks cannot be attributed yet. Plan and prospect sheet:
branch `outreach/oct20`.

## OUT-1

**Rewrite the follow-up and batch-2 email, then spam-check it.** Agent drafts; Tanvi and Yashvi test.

- Lead with the researcher's own paper. Give one concrete finding from it (a target and a lane
  readout) and ask one yes/no question, such as "Did we read lane 3 right?"
- Plain text, one link, no access code in the visible text, under 120 words. Send to first or
  corresponding authors who run blots (grad students, postdocs), not only PIs.
- Write the drafts into `outreach/emails_*.md` on `outreach/oct20`: follow-up 2 for wave 1 and the
  batch-2 first email.
- Spam check: each sender mails one draft to mail-tester.com from their real mailbox and records
  the score in `team-log.md`. A score under 8/10 blocks batch 2.

## OUT-2

**Research batch 2 (~100 prospects).** Agent. Blocked by OUT-1.

Use the same columns and scoring as `outreach/prospects.csv`. Prefer people with an open-access
western-blot paper from the last two years, so O-11's path can pre-extract it. Bay Area labs
(UCSF, Stanford, Berkeley) go first, because a demo can follow (OUT-4). Mark every row's source.

## OUT-3

**Fix the stale copy in the docs pack.** Agent.

`UCSF_BETA_HANDOFF_MESSAGE.md` (line 12) and the other `UCSF_BETA_*.md`, `BETA_EMAIL_*.md` and
`HOSTING_STATUS.md` files still say live search is "not yet in this link". Make them match what
is hosted after O-9. Only state what is actually deployed.

## OUT-4

**Warm intros and lab-meeting demos.** Yashvi + Nik.

Ask each warm contact for one 10-minute slot at a lab meeting, or one named lab that runs a lot
of westerns. Log each ask and its answer in `team-log.md`, and the lab in the prospect sheet with
its source. Open threads (10-11): Gina (follow-up sent, waiting); Seiji (asked about Stanford labs
that might try HiveBlot); UCSF testers (Tally form goes out 10-12 08:00).

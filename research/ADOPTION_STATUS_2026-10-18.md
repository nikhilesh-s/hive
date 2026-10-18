# UCSF adoption status (verified 2026-10-18)

**Bottom line:** no record shows that researchers in two UCSF labs have actively used HiveBlot.
What can be verified is one UCSF demo and a beta link shared with one UCSF-connected group. One
anonymous session of expert feedback (2026-09-16) may come from that group, but it cannot be
attributed.

**Sources:**
- Read-only queries on the production Supabase project (`search_history`, `hiveblot_feedback`,
  `saved_results`, `ingest_jobs`, `western_blot_records_live`, and `auth.users` counted by
  domain)
- The repository
- The outreach branch

Not checked: email inboxes, the Tally form and Vercel analytics.

## What exists, by category

| Category | Evidence | Source |
|---|---|---|
| **Product demo** | UCSF meeting 2026-09-09. Nik demonstrated the hosted beta. No attendee list or lab names were recorded. | `meeting_notes:1-61`, `research/UCSF_DEMO_2026-09-09.md` |
| **Beta testing (offered)** | "A live beta link has been shared with Paul and his team for unstructured testing." The file does not give a surname or a lab. | `meeting_notes:61` |
| **Unattributed expert feedback** | One browser session on 2026-09-16, 14:30-14:52 PT (21:30-21:52 UTC). It left 24 "correct" and 6 "incorrect" field marks on 4 records, plus 1 UI comment. The comments read like a biologist, for example "The numbers below kDa on the image are molecular weight standards…" and "AKT, not AKT1". No lab tag and no contact. `app_version` is `beta-local`. | `hiveblot_feedback` ids 18-41 |
| **Unattributed searches** | 16 searches in 8 anonymous sessions (2026-09-27 to 2026-10-16), none with a `lab_tag` or `utm_source`. Almost all are the team's standard smoke-test queries ("phospho STAT3 Tyr705", "co-IP PIK3CA", "GAPDH mouse", "CST 9145", "needs review"). | `search_history` |
| **Internal development** | <ul><li>37 saved results (13 anonymous on 10-01; 18 and 6 from accounts on 10-03 and 10-11), from Srushti's build and Nik's 10-11 check.</li><li>2 Google accounts, both `gmail.com`, created 10-02 or later.</li><li>All 33 extraction jobs (9-20, 9-27, 10-11) were run by the team.</li></ul> | `saved_results`, `auth.users`, `ingest_jobs` |
| **Planned outreach** | Wave 1 was 27 emails (Yashvi 13 on 9-30, Tanvi 14 on 10-05), with 0 replies. 84 prospects, with the `used_on` and `evidence` columns empty. | `TEAM_HANDOFF.md:18-19`, `outreach/prospects.csv` |
| **Active use by a UCSF lab** | **None recorded.** | n/a |

The phrase "two UCSF labs" appears only as an assumed baseline in a planning document
(`SUN_SEP_26_MEETING_ACTION_ITEMS.md:10,22`). The same document's own rule is "Say 'X labs tried
the beta' only with evidence."

## What you can truthfully say today

- "Demoed to UCSF researchers; beta shared with a UCSF lab." Use the last part only if Paul's
  group is a UCSF lab.
- Do **not** say "2 UCSF labs use it" or "used by UCSF labs".

## Written confirmation that would make "used by researchers in two UCSF labs" true

You need one email from a named researcher in **each** lab. It should state all of the following:
1. Their name, role and lab/PI.
2. That they personally used HiveBlot (hiveblot-beta.vercel.app) on their own research question,
   with approximate dates and what they did (searched, extracted a paper, gave feedback).
3. Whether they still use it, or plan to.
4. Permission for you to describe this as "used by researchers in the [PI] lab at UCSF".

Template to send (Nik sends it; nobody sends it for him):

> Hi [name], thanks again for trying HiveBlot after the September demo. I'm writing it up and want
> to describe your lab's use accurately. Could you reply with (1) your role and lab, (2) roughly
> when and how you used it (searches, a paper extraction, the feedback buttons), and (3) whether
> it's OK for me to say "used by researchers in the [PI] lab at UCSF"? Also: was it someone on
> your team who left detailed field feedback on Sept 16 around 2:30 pm (the note about the kDa
> ladder and "AKT, not AKT1")? Thanks!

If they confirm the 9-16 session, that is the strongest adoption evidence on record. It is
substantive expert review of the extraction, not just a visit.

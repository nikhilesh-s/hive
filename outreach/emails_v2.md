# Email v2 (batch 2) — DRAFT, ticket G-2

Status: drafted 2026-10-18 by Yashvi + Claude. **Not approved.** Still needed before any send:
mail-tester.com score from each sending account (aim 8/10+) and Nik's approval.

Rules from G-2: plain text, under 120 words, sent to the paper's **first author** (grad
student or postdoc), not the PI. Open with their paper and one concrete thing HiveBlot
pulled from it. One link. One yes/no ask. No attachments, no tracking pixels, one
recipient per email. Replace `ACCESS_CODE` once, privately, with the code from Nik.

Fields: `{first_name}`, `{year}`, `{journal}`, `{topic}`, `{target}`, `{doi}`,
`{lab_tag}`, `{sender_name}`. Never fill a field with something you haven't checked.

---

## Variant A — own paper (only for papers with a Q-1 ✅ sign-off)

Subject: `lane {lane_number} in your {topic} paper`

> Hi {first_name},
>
> We ran your {year} {journal} paper on {topic} through HiveBlot, a student-built tool that
> turns published western blots into structured records. From {figure_ref} it pulled:
> {one_concrete_extraction}.
>
> Did we read {panel_or_lane} right? A one-word yes/no is plenty. Nobody has checked this
> record yet; fields taken from your text show the sentence they came from:
> https://hiveblot-beta.vercel.app/experimental/research?doi={doi}&lab={lab_tag}&access=ACCESS_CODE
>
> {sender_name}
> HiveBlot (student team) · hiveblot-beta.vercel.app
> If this isn't useful, reply "no" and I won't write again.

`{one_concrete_extraction}` example shape: "STAT3 pTyr705 in HEK293 cells, band present in
lanes 2 and 4, antibody quoted from your methods". Copy it from the checked record, never
from memory.

## Variant B — generic (paper not pre-extracted, or not signed off)

Subject: `westerns for {target}`

> Hi {first_name},
>
> I'm on a small student team building HiveBlot, which turns published western blots into
> searchable records (antibody, dilution, cell line, lane readout), showing the source
> sentence wherever the paper states it. I read your {year} paper on {topic}.
>
> Would you reply with one protein and cell line you're blotting next? I'll send back what
> HiveBlot finds for it in open-access papers, usually within a day. A "yes" and a target is
> enough.
>
> Or look around yourself: https://hiveblot-beta.vercel.app/experimental/research?lab={lab_tag}&access=ACCESS_CODE
>
> {sender_name}
> HiveBlot (student team) · hiveblot-beta.vercel.app
> If this isn't useful, reply "no" and I won't write again.

## Follow-ups (both variants, reply in the same thread)

**Follow-up 1 — 4 business days later, no reply**

> Hi {first_name}, one more try with a smaller ask: is there a single lane or band in your
> paper you'd expect an automatic reader to get wrong? Even "lane 3" helps us.
>
> {sender_name}

**Follow-up 2 — 7 days after that, last one**

> Hi {first_name}, last note from me, and thanks for reading. If a labmate runs more westerns
> than you do, I'd be grateful for a name or a forward.
>
> {sender_name}

Opt-outs: mark `opted out` in the sheet the same day and never write again.

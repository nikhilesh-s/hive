# UCSF HiveBlot beta — Tally feedback form spec

**Target send:** Wednesday, 2026-09-16
**Build surface:** Tally, built manually
**Audience:** UCSF researchers testing or evaluating HiveBlot
**Normal-path completion:** ~4–5 minutes (path A: 21 questions, 8 required; ~8 s per select, ~15 s per multi-select, ~40 s per long text; confirm in the timed team test in §7)
**Deep correction / validation path:** ≤7 minutes

This document is the source spec for the external beta feedback form. It does **not** replace the in-product correction controls; it collects session-level product, scientific-trust, and validation feedback that is easier to analyze across labs.

## Product boundary

Add this near the top of the form:

> Please do not paste unpublished, confidential, patient, or proprietary lab data into this form. Public paper DOIs/PMCIDs and general workflow feedback are ideal.

The form should be easy to forward within a lab without requiring respondents to identify themselves.

---

## 1. What we need to learn

The form must answer five questions:

1. Is experiment-level Western blot search useful in a real researcher workflow?
2. Which biological fields and evidence surfaces actually matter?
3. Where is HiveBlot biologically wrong, incomplete, misleading, or hard to trust?
4. What would make `LIVE · UNREVIEWED` evidence acceptable for exploratory use?
5. Is experimental band reading worth building, and can UCSF researchers help us obtain public evaluation / ground-truth data?

Do not optimize for a generic NPS score. Optimize for reproducible product and science decisions.

---

## 2. Tally capabilities / build rules

Use:
- multi-page form;
- conditional logic to show/hide questions and skip irrelevant pages;
- hidden fields populated through URL parameters;
- optional contact collection only after explicit follow-up consent;
- a custom thank-you page or redirect after completion.

Official Tally docs:
- Conditional logic: https://tally.so/help/conditional-form-logic
- Hidden fields: https://tally.so/help/hidden-fields
- Redirect on completion: https://tally.so/help/redirect-on-completion

**Do not use a progress bar for this version.** Tally documents that page-jump logic can make progress indicators confusing because the form cannot know the respondent's future branch.

---

## 3. Hidden tracking fields

Create these hidden fields:

| Field | Purpose | Example values |
|---|---|---|
| `ref` | who/channel generated this link | `direct`, `lab_forward`, `team_followup` |
| `lab` | distribution cohort, not necessarily respondent identity — use neutral labels (`lab_a`, `lab_b`), never a PI surname | `lab_a`, `lab_b`, `other_ucsf`, `unknown` |
| `cohort` | intended tester cohort | `wetlab`, `computational`, `pi`, `mixed` |
| `beta_version` | product version under test | `2026-09-16` |
| `source` | outreach channel | `email`, `meeting`, `slack`, `forward`, `qr` |

Example pattern:

```text
https://tally.so/r/FORMID?ref=lab_forward&lab=lab_a&cohort=wetlab&beta_version=2026-09-16&source=email
```

Do not encode personal emails, private researcher identifiers, or unpublished project names in the URL.

---

# PAGE 1 — Researcher context

## Q1. Did you try the HiveBlot beta before filling this out?
- **Type:** single select
- **Required:** yes
- **Options:**
  - Yes, I used it
  - I opened it but did not really test it
  - No, not yet
- **Why:** separates product-use evidence from expectations.

### Conditional Q1a. What stopped you from testing it more?
- **Show if:** Q1 is not `Yes, I used it`
- **Type:** multi-select + Other
- **Required:** no
- **Options:**
  - I did not have time
  - I was not sure what to search
  - The current dataset was too small for my work
  - I hit a technical/loading problem
  - The workflow did not feel relevant to me
  - I wanted more explanation first
  - Other

If Q1 = `No, not yet`, skip detailed extraction-correctness questions later. Keep the respondent on the short product-expectation path.

## Q2. Which best describes your role?
- **Type:** single select
- **Required:** yes
- **Options:** PI / faculty; Staff scientist; Postdoctoral researcher; Graduate student; Research assistant / technician; Computational biologist / data scientist; Other

## Q3. How often does your work involve Western blot data or Western blot literature?
- **Type:** single select
- **Required:** yes
- **Options:** Daily / almost daily; Weekly; Monthly; Occasionally; Rarely / never

If `Rarely / never`, skip detailed band-reading questions on Page 4.

## Q4. What research area or workflow best describes your work?
- **Type:** short text
- **Required:** no
- **Placeholder:** `e.g., kinase signaling, cancer biology, antibody validation, literature review`

Do not require lab name.

---

# PAGE 2 — What they tried

Only show Q5–Q8 in full if Q1 = `Yes, I used it`.

## Q5. What were you trying to find or do in HiveBlot?
- **Type:** long text
- **Required:** yes for users; optional otherwise
- **Placeholder:** `e.g., find phospho-STAT3 blots in a liver cancer cell line, check whether an antibody catalog has worked in published experiments`
- **Help text:** `One or two sentences is enough.`
- **Why:** gives the real job-to-be-done rather than forcing our taxonomy.

## Q6. How useful were the results for that task?
- **Type:** single select
- **Required:** yes for users
- **Options:**
  - Very useful — I found evidence I could act on
  - Somewhat useful
  - Relevant, but not enough to act on
  - Mostly not what I needed
  - I could not find a relevant result

## Q7. Which parts of a HiveBlot record are most valuable to you?
- **Type:** multi-select, `pick up to 3` (do not use ranking — 11 items to rank is the slowest question on the form)
- **Required:** no
- **Options:**
  - Protein / normalized target identity
  - Modification / phosphosite
  - Cell line / sample / organism
  - Treatment / dose / duration
  - Antibody vendor / catalog / dilution
  - Lane conditions and band presence
  - Expected vs reported molecular weight
  - Figure crop
  - Figure caption / methods evidence
  - DOI / link to the paper
  - Supported / Needs review / Conflicting status
  - Other

## Q8. Did anything feel missing from the workflow after you found a useful result?
- **Type:** multi-select + Other
- **Required:** no
- **Options:**
  - More results / broader paper coverage
  - More from the same paper
  - Related experiments
  - Save / bookmark
  - Export
  - Citation / reference formatting
  - Better explanation of why a field is unsettled
  - Better search/filtering
  - Nothing major
  - Other

---

# PAGE 3 — Scientific trust and correctness

Skip the specific-correction branch for respondents who did not use the beta.

## Q9. How easy was it to verify where HiveBlot's information came from?
- **Type:** 5-point scale
- **Required:** no
- **Anchors:** `Very difficult` → `Very easy`

## Q10. Which evidence made you trust or distrust a result?
- **Type:** multi-select
- **Required:** no
- **Options:** Figure crop; Caption text; Methods text; Antibody details; UniProt normalization; Lane pattern; DOI/source paper; Status label; I did not inspect provenance; Other

## Q11. Do these statuses communicate the right thing to you?
Show a short reminder:
- **Supported** — available evidence agrees
- **Needs review** — something remains uncertain/ambiguous
- **Conflicting** — credible evidence disagrees and HiveBlot refuses to choose

- **Type:** single select
- **Required:** no
- **Options:** Yes, clear as written; Mostly clear; The names should change; The meanings should change; I am not sure

### Conditional Q11a. What would you change about the statuses?
- **Show if:** Q11 is not `Yes, clear as written`
- **Type:** long text
- **Required:** no

## Q12. Did you notice any result that was biologically wrong, misleading, or missing important information?
- **Type:** single select
- **Required:** yes for active users
- **Options:** Yes; No; Not sure

### Conditional correction branch — show if Q12 = Yes

#### Q12a. Public paper reference
- **Type:** short text
- **Required:** yes (on this branch only)
- **Prompt:** `DOI or PMCID — it is shown on the HiveBlot record`

#### Q12b. Figure / panel / result
- **Type:** short text
- **Required:** no
- **Prompt:** `e.g., Fig 3D, phospho-STAT3 Tyr705 card`

#### Q12c. Which field was wrong or missing?
- **Type:** multi-select + Other
- **Required:** yes
- **Options:** target identity; modification/site; cell line/sample; treatment; dose/duration; antibody; molecular weight; lane condition/band state; figure/caption provenance; status/conflict handling; other

#### Q12d. What should the result have said, or why is the current result misleading?
- **Type:** long text
- **Required:** yes
- **Help text:** `What HiveBlot showed, and what the paper actually reports (the expected value).`
- **Reminder:** `Please use public paper information only.`

This branch must collect enough information for the team to reproduce the correction without contacting the respondent.

## Q13. For `LIVE · UNREVIEWED` evidence from a newly extracted paper, what would you need before using it for exploratory research?
- **Type:** multi-select + Other
- **Required:** no
- **Options:**
  - Exact figure crop and source text
  - Field-level confidence / uncertainty
  - Clear `unreviewed` badge
  - A human-reviewed subset
  - Agreement between multiple extraction methods/models
  - Ability to correct the record
  - Comparison against the original PDF
  - I would not use unreviewed extraction
  - Other

---

# PAGE 4 — Experimental band reading

Skip if Q3 = `Rarely / never`.

Intro copy:

> We are exploring an experimental **band-reading aid**. It is not calibrated densitometry. The tool should refuse to give a quantitative read when an image is clipped, saturated, or otherwise cannot support one.

## Q14. Which band-reading tasks would be useful to you?
- **Type:** multi-select + Other
- **Required:** no
- **Options:**
  - Mark lane boundaries
  - Present / absent / uncertain band calls
  - Rank lanes by relative signal
  - Detect likely saturation / overexposure
  - Compare a target against a loading control
  - Export a reproducible measurement record
  - None of these
  - Other

## Q15. If an image is too saturated or unstable to quantify, what should HiveBlot do?
- **Type:** single select
- **Required:** no
- **Options:**
  - Refuse quantification and explain why
  - Show only qualitative present/absent/uncertain
  - Show a broad range with a warning
  - Still provide a numeric estimate
  - Not sure

### Optional block — experimental densitometry page (`/experimental/densitometry`)

Only the gate (Q15a) is on the normal path; Q15b–c appear only on `Yes`. Do not describe your own unpublished blots here — answer about the tool's behaviour only.

#### Q15a. Did you try the experimental densitometry page (draw a strip and lanes, get a within-image relative band signal)?
- **Show if:** Q1 = `Yes, I used it`
- **Type:** single select
- **Required:** no
- **Options:** Yes; No; I did not know it existed

#### Q15b. When it refused or warned (clipped/saturated image, near-tie reference lane, text row), did the reason make sense?
- **Show if:** Q15a = Yes
- **Type:** single select
- **Required:** no
- **Options:**
  - Yes — I understood why and what to change
  - Partly — I saw the state but not what to do about it
  - No — I did not understand it
  - It never refused or warned on my image
  - I did not notice those states

#### Q15c. Would you trust a within-image relative band number reported with a range (e.g., lane 3 ≈ 0.6× reference, range 0.5–0.7) for exploratory use?
- **Show if:** Q15a = Yes
- **Type:** single select
- **Required:** no
- **Options:**
  - Yes, as reported
  - Only if I can see the strip/lanes I drew next to the number
  - Only relative to a loading control on the same blot
  - No — I would redo it in ImageJ/Fiji
  - Not sure

## Q16. Would you be willing to suggest a **publicly available** paper/source-data example that would be useful for evaluating this feature?
- **Type:** single select
- **Required:** no
- **Options:** Yes; Maybe; No

### Conditional Q16a. Public DOI / PMCID / source-data link
- **Show if:** Yes or Maybe
- **Type:** short text
- **Required:** no

## Q17. Would your lab ever be interested in helping evaluate band reading with a known dilution series or another controlled reference?
- **Type:** single select
- **Required:** no
- **Options:** Yes, potentially; Maybe / ask me later; No

Do not ask for unpublished measurements in this form. This only records willingness to discuss a controlled validation study later.

---

# PAGE 5 — Overall value and follow-up

## Q18. If HiveBlot covered the literature relevant to your work, where would it save you the most time?
- **Show if:** Q1 is not `Yes, I used it` (users already answered this concretely in Q5/Q6; keeps the normal path short)
- **Type:** single select + Other
- **Required:** no
- **Options:**
  - Finding whether a protein was blotted in a specific model/condition
  - Evaluating an antibody before purchasing/using it
  - Comparing conditions across papers
  - Checking phosphosites / modified proteins
  - Verifying a figure while reading a paper
  - Building a literature review / evidence table
  - It would not meaningfully save me time
  - Other

## Q19. Roughly how valuable could this be in your workflow if the coverage and extraction quality were strong enough?
- **Type:** single select
- **Required:** no
- **Options:**
  - Core tool I would use regularly
  - Useful for specific projects
  - Occasionally useful
  - Interesting, but not part of my workflow
  - Not useful for me

## Q20. What is the single most important thing we should improve next?
- **Type:** long text
- **Required:** yes
- **Help text:** `One sentence is fine.`

## Q21. May we contact you to follow up about your feedback or a validation example?
- **Type:** single select
- **Required:** yes
- **Options:** Yes; No
- **Note:** no preselected option; contact is collected only after an explicit `Yes`. Do not add an email field anywhere else on the form.

### Conditional Q21a. Contact
- **Show if:** Yes
- **Type:** email or short text
- **Required:** yes only on this branch
- **Consent copy:** `We'll use this only to follow up about HiveBlot feedback or validation and will not publish it.`

---

## 4. Thank-you page

Suggested copy:

> Thank you — this is exactly the kind of feedback we need. We are using this beta to learn which fields researchers actually rely on, where our extraction is wrong or incomplete, and what evidence is necessary for trust.

Optional button: **Return to HiveBlot beta**.

---

## 5. Manual Tally build checklist

1. Create the form with the title/introduction above.
2. Add the five hidden fields first and verify URL-parameter capture.
3. Build the five pages in order.
4. Add the conditional branches only after every question exists.
5. Keep Q12's correction branch hidden by default; show only on `Yes`.
6. Skip Page 4 for Western-blot `Rarely / never` respondents.
7. Make Q21a required only if follow-up = Yes.
8. Do not enable a progress bar while page-jump logic is active.
9. Preview and test at desktop and mobile widths.
10. Submit at least six test responses covering the paths below.
11. Export responses and verify `ref`, `lab`, `cohort`, `beta_version`, and `source` appear correctly.
12. Delete/label test responses before sending the live link.
13. Prepare the base link plus parameterized distribution links.

### Required logic test cases

- **A — active wet-lab tester, no correction, Q15a = No, follow-up No:** normal path, 21 questions, timed <5 minutes. If the timed test fails, cut in this order before adding anything: Q17 (fold into a Q21 `Yes` branch), Q4, Q13.
- **B — active tester, wrong extraction:** Q12a–d appear and capture reproducible detail.
- **C — opened but did not test:** blocker question appears; detailed correctness is skipped.
- **D — did not use beta:** short expectations path.
- **E — rare/never Western user:** band-reading page skipped.
- **F — follow-up yes:** contact appears and becomes required; follow-up no keeps contact hidden.
- **G — densitometry user:** Q15a = Yes shows Q15b–c; Q15a = No/unknown shows nothing extra.

No path should dead-end or require an irrelevant answer.

---

## 6. Distribution setup

Build one canonical form, not separate forms per lab. Use hidden fields to distinguish distribution.

Recommended link families:
- direct follow-up from the current UCSF contacts;
- forwarded within a wet-lab group;
- computational / data-biology tester;
- PI/faculty reviewer;
- QR/link used in a future meeting.

Ask current researchers to forward the same beta + feedback link to **2–3 labmates who actually inspect Western blots**, rather than broadly spamming UCSF. Try to cover postdoc, graduate student, staff scientist, PI, and at least one computational researcher across the first wave.

Separate respondents conceptually into three cohorts when analyzing:
1. **Product tester** — evaluates usefulness/workflow.
2. **Biology adjudicator** — can judge extraction correctness against papers.
3. **Band-reading ground-truth collaborator** — can help with controlled validation later.

---

## 7. First-wave success criteria

The Wednesday form is ready only if:

- normal path completes in <5 minutes in a timed team test;
- wrong-extraction path captures enough information to reproduce the issue from a public paper;
- non-user and non-Western-user paths stay short;
- hidden source fields survive submission/export;
- no question requests unpublished or sensitive lab data;
- team can separate usefulness feedback from biological-correction feedback;
- copy never implies unseen-paper extraction accuracy or calibrated densitometry.

After the first 5–10 real responses, revise the form based on abandonment and low-information questions rather than adding more questions by default.

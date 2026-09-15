# UCSF HiveBlot beta — multi-lab distribution plan

**Target first wave:** Wednesday, 2026-09-16 onward  
**Goal:** get useful feedback from multiple researcher types and labs without turning the beta into indiscriminate cold outreach.

This is an internal distribution plan. It prepares the referral structure; it does not authorize sending messages automatically.

## Principle

The beta is more valuable if ten respondents represent different workflows than if ten respondents all sit in one lab and use the same assay the same way.

Use the current UCSF contacts as a **referral graph**. Ask each engaged researcher to forward one beta + Tally link to 2–3 people who genuinely inspect Western blots or make decisions from Western blot literature.

Do not mass-email UCSF. Optimize for relevant testers, not raw response count.

---

## 1. Three tester cohorts

### A. Product testers
People who can answer: *would this save me time, and where?*

Recruit across:
- graduate students;
- postdocs;
- staff scientists / research associates;
- PIs;
- at least one computational/data-biology researcher who consumes experimental literature.

### B. Biology adjudicators
People comfortable checking a HiveBlot record against the actual figure/caption/methods and saying whether a field is wrong, missing, ambiguous, or correctly abstained.

Ideal ask: **one public paper or panel each**, not a huge annotation job.

### C. Band-reading validation collaborators
People who routinely generate/interpret Western blots and could eventually help with controlled validation — for example a dilution-series dataset or a public source-data example with known quantitative values.

Do not request unpublished lab data through the feedback form. Record willingness first, then discuss a validation protocol separately.

---

## 2. First-wave target mix

Aim for approximately 8–15 real testers in the first wave, spread across several labs/workflows.

Desired mix:
- 2–4 current-contact / directly introduced researchers;
- 3–6 forwarded labmates who actively inspect Western blots;
- 1–2 senior researchers / PIs for product-level trust and workflow judgment;
- 1–2 computational researchers for search/data representation feedback;
- 2–4 respondents capable of biological adjudication;
- at least 1 potential band-reading ground-truth collaborator.

These categories can overlap. Do not chase quotas if the people are not relevant.

---

## 3. Distribution mechanics

Use **one canonical Tally form** from `tickets/tally-ucsf-beta-feedback.md` and one beta link. Do not fork forms by lab.

Parameterize the Tally URL with hidden fields:
- `ref`
- `lab`
- `cohort`
- `beta_version`
- `source`

Examples:

```text
?ref=direct&lab=known_ucsf_group&cohort=wetlab&beta_version=2026-09-16&source=email
?ref=lab_forward&lab=known_ucsf_group&cohort=wetlab&beta_version=2026-09-16&source=forward
?ref=direct&lab=other_ucsf&cohort=computational&beta_version=2026-09-16&source=email
```

Use cohort labels, not personal identifiers, in URLs.

---

## 4. The referral ask

When the team follows up with an engaged researcher, the most useful request is:

- try one or two searches relevant to your actual work;
- fill out the short feedback form;
- if possible, forward the same beta + form to 2–3 labmates who regularly inspect Western blots;
- optionally suggest one **public** paper that represents a workflow HiveBlot should be able to handle.

This creates a chain of relevant testers while keeping the product inside warm introductions.

---

## 5. What to measure

Do not judge the first wave by number of form submissions alone.

Track:
- completion count by `ref` / `lab` / `cohort`;
- how many respondents actually used the beta;
- useful / not-useful task outcomes;
- specific reproducible biological corrections;
- most-valued fields;
- top missing workflow actions;
- trust requirements for `LIVE · UNREVIEWED` records;
- public evaluation-paper suggestions;
- willingness to follow up;
- willingness to help with band-reading validation.

Separate **product feedback** from **biological correction signal** when summarizing.

---

## 6. Weekly feedback loop

For each feedback pass:

1. Export Tally responses and in-product feedback separately.
2. Remove/mark test submissions.
3. Group Tally responses by cohort/source.
4. Route reproducible extraction corrections into bio-QA review; do not auto-edit the reviewed corpus.
5. Route search/UX friction into product tickets.
6. Route band-reading examples into the validation queue.
7. Write a short findings summary: repeated signal, one-off requests, and decisions.
8. Update `HANDOFF.md` only when work actually lands or a product/scientific decision becomes authoritative.

---

## 7. Anti-patterns

Do not:
- cold-spam a large UCSF list;
- ask testers to upload unpublished data just to make the beta look useful;
- treat all respondents as equally qualified to adjudicate biology;
- promise calibrated densitometry;
- use the reviewed three-paper corpus to imply literature coverage;
- turn every single respondent request into a feature ticket;
- make the form longer every time a new question occurs to the team.

The first-wave objective is to discover **repeated, high-information signal** from varied real workflows.

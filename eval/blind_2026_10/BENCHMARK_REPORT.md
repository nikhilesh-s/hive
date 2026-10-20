# HiveBlot blind extraction benchmark, October 2026: final report

**Status (2026-10-20): final.**
- Every number below is copied from `report/RESULTS.md`, which `score_blind.py` generates. None is
  typed by hand.
- Every change made after pre-registration is in `DEVIATIONS.md` (A1-A8).

## 1. Bottom line

| Tier | ALL FIELDS precision of assertions | ALL FIELDS accuracy (coverage) |
|---|---|---|
| (i) Pre-registered raw | 222/285 (78%) | 222/992 (22%) |
| **(ii) Adjudicated (headline)** | **512/553 (93%)** | **512/895 (57%)** |
| (iii) Plus post-hoc label corrections | 536/549 (98%) | 536/900 (60%) |

- **Precision is high.** On 3 papers and 8 labeled panels, when the system asserts a value it is
  usually right: 93% in the headline tier.
- **Coverage is much lower.** The system declines to name a canonical gene symbol for about half the
  targets (identity abstained 22/47). It also misses repeated loading-control strips (10 of the 11
  NOT_FOUND rows are extra GAPDH strips).
- **Raw differs from adjudicated mostly because of the join, not the system.** Notation and alignment
  between the labels and the records account for most of the gap (`report/AUDIT.md`).
- **This is a small benchmark.** Three papers, one annotator. It is not a literature-wide accuracy
  figure.

## 2. Design (pre-registered 2026-10-18, `PREREGISTRATION.md`)

- **System under test:** `western_blot_miner/` frozen at `f77d311`, the same extraction code
  production runs. Settings:
  - DPI 350, candidate score 0.35, model score 0.65
  - escalation off, concurrency 1
  - live UniProt resolver
- **Model and transport:** `claude-opus-5` through the local `claude_cli` transport. It uses the same
  model and prompts as production, but hands off the image differently (A1.5).
- **No database writes.** Outputs went to a private directory and were sealed by SHA-256 before any
  annotation was received.
- **Reference labels:** one wet-lab annotator (Tanvi), working from the PDF only, with no AI tools and
  blind to system output.
- **Crop mapping:** a separate person (Yashvi) mapped each crop sent to the model onto a figure panel.
  She saw only the images and page numbers.
- **Scoring:** fields are aligned to annotated target rows by printed label or gene symbol. Each field
  is scored CORRECT, INCORRECT, ABSTAINED, NOT_FOUND, CORRECT_SILENCE or UNSUPPORTED (§8).

## 3. Papers

The pool was 26 candidates; 15 were eligible. They were drawn with seed 20261018 (`draw.py`), and the
PDFs were frozen by SHA-256 (`papers.json`).

| Draw rank | PMCID | Paper | Status |
|---|---|---|---|
| 1 | PMC9283986 | Lopez-Toledo et al. 2022, *Front Aging Neurosci*: PSEN1-mutant patient fibroblasts | scored |
| 2 | PMC5328321 | Yang et al. 2017, *Onco Targets Ther* | excluded: retracted (eligibility rule; found during annotation, before scoring; outputs never opened) (A4) |
| 3 | PMC7948984 | *J Biol Chem* 2021: 89-kDa PARP1 fragment and AIF-mediated apoptosis | scored (PDF downloaded manually, A2) |
| 4 | PMC4393234 | Bojovic et al. 2015, *PLoS ONE*: immediate-early genes in rat spinal cord | scored |

- **No replacement for rank 2.** It was not replaced, because of annotator time (A4). The benchmark
  is 3 papers.
- **Hard pool.** The candidate pool was built to be diverse and adversarial (patient fibroblasts,
  tissue, cleavage products), so it is likely harder than an average paper.

## 4. What was measured

**Annotated sample:**
- **Panels.** Tanvi inventoried 11 Western panels and labeled 8 of them, her own choice made blind to
  the system:
  - PMC9283986: 4/4
  - PMC7948984: 3/5
  - PMC4393234: 1/2
- **Rows and lanes.** The 8 panels hold 47 target rows and 950 lane calls.

**Fields scored:**
- protein identity (gene symbol)
- modification type
- phospho site
- cell line or sample
- treatment
- band present/absent per lane

**Metrics, each reported with its denominator:**
- accuracy (coverage) = CORRECT / annotated values
- precision of assertions = CORRECT / (CORRECT + INCORRECT + UNSUPPORTED)
- abstained
- not found

## 5. Results: three tiers

- **(i) Pre-registered raw** is the frozen scorer on the locked labels, kept unchanged in
  `report/raw_preregistered/`.
- **(ii) Adjudicated (headline)** is the pre-registered adjudication rule, which allows notation only.
  It adds:
  - A7 matching corrections:
    - molecular-weight tags are ignored in labels
    - `none` counts as total
    - lane-count mismatches are left unscored
  - the annotator's confirmed notation:
    - 13 alignment aliases
    - 19 `EQUIVALENT_NOTATION` verdicts
- **(iii) Post hoc** is tier (ii) plus 62 label corrections Tanvi accepted *after seeing system
  output*. Examples:
  - treatment `none` changed to staurosporine
  - faint AIF bands
  - re-filed lane strips

  Treat (iii) as an upper reference, not a blind result.

| Field | (i) raw: precision | (i) raw: coverage | **(ii) precision** | **(ii) coverage** | (iii) precision | (iii) coverage |
|---|---|---|---|---|---|---|
| protein_identity | 9/11 (82%) | 9/47 (19%) | **11/14 (79%)** | **11/47 (23%)** | 11/14 (79%) | 11/47 (23%) |
| modification_type | 4/21 (19%) | 4/47 (9%) | **34/35 (97%)** | **34/47 (72%)** | 34/35 (97%) | 34/47 (72%) |
| phospho_site | n/a (0) | n/a (0) | **7/7 (100%)** | **7/7 (100%)** | 7/7 (100%) | 7/7 (100%) |
| cell_line | 10/21 (48%) | 10/47 (21%) | **28/36 (78%)** | **28/47 (60%)** | 29/36 (81%) | 29/47 (62%) |
| treatment | 0/10 (0%) | n/a (0) | **0/11 (0%)** | **n/a (0)** | 10/11 (91%) | 10/12 (83%) |
| band_call | 199/222 (90%) | 199/851 (23%) | **432/450 (96%)** | **432/747 (58%)** | 445/446 (100%) | 445/740 (60%) |
| **ALL FIELDS** | 222/285 (78%) | 222/992 (22%) | **512/553 (93%)** | **512/895 (57%)** | 536/549 (98%) | 536/900 (60%) |

**Other counts in the headline tier (ii):**

| Count | Value | Note |
|---|---|---|
| abstained | 76/895 (8%) | |
| not found | 277/895 (31%) | |
| incorrect assertions | 46 | includes 5 spurious records on non-Western crops, 4 of them immunofluorescence rows |
| lane calls left unscored | 104 | lane-count mismatch (A7) |
| records on uninventoried Western panels | 27 | not scored |

**How to read the treatment row.** In tier (ii), all 11 system treatments are UNSUPPORTED:
- On PMC7948984, Tanvi labeled the treatment `none`. The audit and Tanvi both agree the paper used
  staurosporine there, so the system was right. That is why (iii) jumps to 10/11.
- The remaining tier-(iii) error on treatment is "CS (conditioning stimulation of the sciatic nerve)"
  against her corrected "sciatic nerve conditioning stimulation". The scorer's exact matching treats
  these as different, and no verdict covers that pair.

**Panel recall: 10/11 (91%).** Read it with its caveat:
- What it counts: 10 of the 11 panels Tanvi chose to inventory got a crop sent to the model. The miss
  is the faint Arc blot (PMC4393234 Fig 3B).
- Why it is not literature recall: the inventory is an annotator-selected partial list. The crop map
  shows at least 13 more Western panels in PMC7948984 alone (A5, A6, audit §3; confirmation row 28).

**Timing.** The two figures measure different tasks in different units, so they are not a like-for-like
speed-up:

| Side | Time | Per panel |
|---|---|---|
| Manual | 123 min for 8 labeled panels | 15.4 min per labeled panel |
| Automated (Stage 1 + model, wall-clock, 3 papers) | 19.8 min for 29 panels sent to the model | 40.9 s per panel sent |

- **Different units.** The time log does not separate inventory from full annotation. The system
  processes every crop it detects, including non-target crops, while the human labels the panels she
  chose.

Per-paper tables for tiers (ii) and (iii) are in `report/RESULTS.md`.

## 6. What the annotator confirmation changed (A8)

Tanvi answered all 29 confirmation questions. Classification, in
`annotations/tanvi/confirmation_classification.csv`:

| Class | Count | What it means |
|---|---|---|
| A, NOTATION | 14 | same thing written differently |
| B, LABEL_CORRECTION | 9 | label was wrong; tier iii only |
| C, SYSTEM_WRONG | 3 | HSP70 vs HSPA9; 4 GAPDH strips omitted; full-length PARP1 called in a lane holding only the fragment |
| D, N/A | 3 | no scoring action |

The locked label files were not edited. Notation enters through `aliases.csv` (alignment only) and
`adjudications.csv`. Corrections enter through `corrections.csv`, in tier iii only.

**Left as scored (pending):**
- 7 PMC9283986 panel 1 sample cells, where the system text differs from the confirmed pair
- AKT1 against printed "PAKT" / "AKT total" (2 cells; she confirmed "AKT", not the isoform)
- the PMC4393234 treatment pair above
- the unscored cleaved-PARP1 strip and Fig 2D GAPDH lanes
- duplicate lane keys in Fig 2A row 3 in tiers (i) and (ii)

## 7. Limitations

- **Small sample.** 3 papers and 8 labeled panels (47 target rows). Denominators are small. Each
  paper is a different kind of experiment, so pooled numbers are dominated by PMC9283986 (760 of the
  895 headline cells).
- **Single annotator.** There was no second annotator, so there is no agreement figure.
- **Post-hoc matching fixes.** A7 and A8 were made after unsealing. Each is logged and symmetric, and
  raw is always reported alongside. Tier (iii) used corrections the annotator accepted after seeing
  system output.
- **Incomplete inventory.** Panel recall covers only the panels the annotator chose. 27 records on
  Western panels outside the inventory are unscored (they are not errors).
- **Lane-count mismatches unscored.** 104 lane calls are unscored where the annotator counted physical
  lanes and the system counted samples (A7). These are PMC9283986 Fig 4A (93 calls) and PMC7948984 Fig 2A
  PARP1 (11 calls, scored in tier iii after the strip was re-filed).
- **Lab notation.** Non-standard labels (misread symbols, `none` for total, free-text samples) moved
  raw accuracy far more than system behaviour did.
- **Model transport.** The run used `claude_cli`, not production's `anthropic` API transport (A1.5).
- **Scope.** Only main-text panels are included. Supplementary figures are out of scope.

## 8. Integrity

- **Seal.** The seal was verified on the final run: every one of the sealed files listed in
  `SEALED_OUTPUTS.sha256` matches.
- **Frozen code.** System code is unchanged against `f77d311`: `git diff` under `western_blot_miner/`
  and `api/` is empty, and the scorer checks this on every run.
- **Unchanged inputs.** The locked labels (`targets.csv`, `lanes.csv`, `crop_map.csv`) and the
  pre-registered raw output are unchanged.
- **Scorer self-test.** `score_blind.py self-test` passes, including the A8 cases.
- **Reproduce.** `RUNBOOK.md` steps 6 and 7.

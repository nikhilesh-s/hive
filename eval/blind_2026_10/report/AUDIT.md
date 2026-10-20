# Independent audit of the raw blind-benchmark numbers

Auditor read-only on annotations, scorer, papers.json and sealed outputs. Inputs: `report/results.json`, `RESULTS.md`, `adjudication_sheet.csv`, the three `evidence_records.json`, the PDFs and crops. The scorer's alignment was re-implemented and reproduces every total in `results.json` (82 incorrect assertions; 26 NOT_FOUND rows; 607 NOT_FOUND lanes).

## 1. Bottom line

The raw 22% is mostly not a measurement of the system. Most non-CORRECT outcomes come from how labels were written and from the join, not from wrong system values. Classes:

- (a) ANNOTATION_NOTATION: non-standard label text for the same thing (SOSTMI, LC31, PSMBS, `none` = total, long sample text).
- (b) JOIN_OR_ALIGNMENT: the system has a matching record or lane, but the scorer's join failed.
- (c) SYSTEM_ERROR: system asserted a wrong value.
- (d) SYSTEM_OMISSION: system has no record.
- (e) ANNOTATION_ERROR: the label looks wrong against the PDF (figure cited below).

| Field / outcome | (a) notation | (b) join | (c) system error | (d) omission | (e) annotation error | Total |
|---|---|---|---|---|---|---|
| protein_identity NOT_FOUND | 5 | 10 | 0 | 11 | 0 | 26 |
| protein_identity INCORRECT | 1 (AIF vs AIFM1) | 0 | 1 (HSP70 vs HSPA9) | 0 | 0 | 2 |
| modification_type NOT_FOUND | 5 | 10 | 0 | 11 | 0 | 26 |
| modification_type INCORRECT | 16 (`none` vs total) | 0 | 1 (c-casp3 said total) | 0 | 0 | 17 |
| cell_line NOT_FOUND | 5 | 10 | 0 | 11 | 0 | 26 |
| cell_line INCORRECT | 11 (free text) | 0 | 0 | 0 | 0 | 11 |
| treatment UNSUPPORTED | 0 | 0 | 0 | 0 | 10 (staurosporine labelled `none`) | 10 |
| band_call NOT_FOUND | 96 | 267 | 0 | 244 | 0 | 607 |
| band_call INCORRECT | 0 | 5 | 1 | 0 | 17 | 23 |
| spurious records | 5 | 10 | 4 (IF micrograph rows) | 0 | 0 | 19 |

Not in the table (not wrong, not requested): 10 identity and 22 band ABSTAINED. The identity abstentions are the system declining to give a canonical symbol (`canonical_target` not SUPPORTED). That is a real weakness: identity reaches only 13/47 even with perfect notation and join.

How the 26 NOT_FOUND rows split:
- 5 are misread or non-standard symbols (SOSTMI, LC31, PSMBS, "pGSK3a/B", "total GSK3a/B.").
- 10 are cases where the printed label equals the system's "label + kDa" (`printed()` at `score_blind.py:247`).
- 11 are real omissions. 10 are repeated GAPDH strips where the system emitted one GAPDH per crop (Fig 2A has 5, Fig 3A 3, Fig 4A 3, Fig 9A 3). 1 is the Arc blot (PMC4393234 Fig 3B), which Stage 1 never cropped.

Findings behind the classes:
- **Lane granularity (PMC9283986).** Blots in Figs 2A, 3A and 4A have duplicate lanes per sample (24 physical lanes, 12 samples).
  - The system's `lane_index` k is sample k. The Fig 4A crop has 12 bands with `lane_condition` NA1 to AD6.
  - Tanvi's `lane_index` is the physical lane.
  - Joining on index compares different lanes. Lanes 13-24 become NOT_FOUND, and the 5 APP INCORRECT lanes compare AD1-AD4 against NA4/NA5 duplicates.
- **Misfiled lane rows (PMC7948984).** PARP1 was split into two strips (full-length and cleaved) in `lanes.csv` but not in `targets.csv`.
  - Panel 2 (Fig 2A): row 1 has 11 lanes, row 2 starts with a stray lane 12 and holds the cleaved-PARP1 pattern, row 3 has 24 lanes (casp3 then c-casp3).
  - Panel 3 (Fig 2D): row 2 (Histone H3) holds the cleaved-PARP1 pattern, row 3 (GAPDH) holds the Histone H3 pattern, row 4 (set aside in ERRATA) holds GAPDH.
  - Result: 14 band INCORRECT cells from the shift, all (e).
- **AIF, Fig 1G.** A zoomed crop shows a faint band in all four nuclear lanes. Labels give lane 2 present and lanes 1, 3, 4 absent. 3 cells, borderline, classed (e) and sent to Tanvi.
- **Treatments.** Every PMC7948984 panel is a staurosporine experiment (Fig 1G caption; Fig 2A and 2D labels). The guide says to list every agent, so `none` is an annotation error. The 10 UNSUPPORTED cells are true system output and the system is right.
- **PMC4393234.** Tanvi filed the GAPDH row under panel 1 (Fig 3B). The caption says GAPDH is Fig 3C, which is inventory panel 2, where the system's one record lives. Joined, that row would be CORRECT on identity, CORRECT on modification after notation, and ABSTAINED on bands (the crop shows only lane labels).
- **Spurious records.** 14 unaligned records are the system's correct records for rows in classes (a)/(b), the same strips counted as NOT_FOUND. Of the 5 on non-Western crops, 4 are IF micrograph rows (AIF, Tom20, DAPI, merge; Fig 6F) and are real false positives. The fifth, GAPDH, is a cut-off strip of Fig 6G (mapper judgment call).

## 2. Spot-check of CORRECT cells (seed 20261020, 22 of 222)

All 22 hold against records and labels: annotated value equals system value, and the record is the right strip. No wrong CORRECT found.

Caveats:
- 6 of the 22 are band calls on PMC9283986 Fig 4A (12 system lanes vs 24 annotated). They match only because the strips (GAPDH, total tau, ptau) are present in every lane. The 36 CORRECT band cells on that panel are correct by coincidence of uniform strips, not by validated lane correspondence.
- The 15 CORRECT and 6 ABSTAINED on PMC7948984 panel 2 row 3 are double-counted, because each lane index appears twice in `lanes.csv`.

## 3. Inventory completeness and panel recall

| Paper | Inventoried | WB panels visible in crop map (lower bound) | Not inventoried |
|---|---|---|---|
| PMC9283986 | 4 (2A, 3A, 4A, 9A) | 4 | 0 |
| PMC7948984 | 5 (1G, 2A, 2D, 2E, 4B) | 18 (1E, 1G, 2A, 2D, 2E, 4A, 4B, 4D, 5A, 5B, 6C, 6G, 7A, 7D, 7E, 7F, 7G, 7H) | 13 |
| PMC4393234 | 2 (3B, 3C) | 1 seen (3C); 3B exists but was never cropped | 0 |
| Total | 11 | at least 24 | at least 13 |

The crop map only covers crops Stage 1 sent to the model, so these are lower bounds. Panels Stage 1 missed are invisible here.

What "10/11 (91%)" can claim: Stage 1 produced a crop for 10 of the 11 panels Tanvi chose to inventory. The miss is the faint Arc blot (PMC4393234 Fig 3B).

What it cannot claim: the inventory is a partial, annotator-selected list (A5/A6), so 91% is not literature-level recall and not a sample estimate. The system actually processed at least 23 Western panels. 27 records on the 13 uninventoried panels are unscored (not errors).

## 4. Raw numbers and the notation-corrected ESTIMATE

Raw, pooled: protein_identity 9/47, modification_type 4/47, cell_line 10/47, band_call 199/851.

**ESTIMATE, pending Tanvi's confirmation. This is not a benchmark result and must not replace the raw numbers.** It assumes the proposed answers in `confirmation_sheet.csv` are confirmed, fixes (a), (b) and (e) in labels and join, and leaves real system omissions and errors.

| Field | Raw | Estimate if all proposed answers confirmed |
|---|---|---|
| protein_identity | 9/47 (19%) | 13/47 (28%); 22 abstained, 11 omitted, 1 wrong |
| modification_type | 4/47 (9%) | 34/47 (72%); 11 omitted, 1 wrong, 1 abstained |
| cell_line | 10/47 (21%) | 35/47 (74%); 11 omitted, 1 wrong (paper 4 `Unknown`) |
| treatment | 0 of 10 supported | 10 of 10 supported, if labels become staurosporine etc. |
| band_call | 199/851 (23%) | about 522/833 (63%); 244 omitted, 59 abstained, 8 wrong |

The band estimate expands 12 sample lanes to 24 physical lanes and re-files the misfiled PMC7948984 rows. It excludes the 12 cleaved-PARP1 lanes, which have no system strip. The remaining shortfall is real: 11 omitted rows, identity abstentions, and band abstentions. Even corrected, this is 3 papers and 8 labeled panels with single-annotator labels.

## 5. Scorer and data issues (nothing was edited)

1. `score_blind.py:247-248` (`printed`) and `:270` (symbol fallback). Alignment needs exact normalized equality with the system's `raw_target_name`, which often ends in a "NN kDa" suffix. The fallback compares against Tanvi's `gene_symbol` column, which holds printed text rather than an official symbol (the guide asked for official symbols). 10 rows and 14 records fail. This follows A1 to the letter, so it is a design weakness, not a coding bug.
2. `score_blind.py:141-159` (`score_lanes`) and `:234-235`. Lanes join on bare `lane_index`, with no check for duplicate keys, agreement with `n_lanes`, or sample-vs-physical-lane granularity. PMC7948984 panel 2 row 3 has every index twice, and panel 2 row 2 starts with lane 12. `n_lanes` in `targets.csv` is 6 for panels 1 and 2, but Fig 1G has 8 lanes and Fig 2A has 12.
3. `score_blind.py:74` (`annotated_mod`) and `:128`. `none` is not mapped to `total`, and "proteolytic cleavage" becomes `other`, so all 16 `none` cells are INCORRECT. `:315-324` (`apply_adjudication`) can only turn INCORRECT or UNSUPPORTED cells into CORRECT. It cannot rescue NOT_FOUND rows or lane joins. The `was` choice at `:321` looks at the field's counter, not the cell's own category.
4. `score_blind.py:230` (`found`). A panel counts as found if any crop maps to it, regardless of records produced. Recall is about crops only.
5. `annotations/tanvi/targets.csv`, PMC4393234 panel 1 row 2: GAPDH (Fig 3C) is filed under Fig 3B.

## 6. Next step

`report/confirmation_sheet.csv` has 29 rows with `tanvi_verdict` empty. It covers every ANNOTATION_NOTATION item and all 63 rows of `adjudication_sheet.csv`, grouped by identical question. No labels, scorer or results were changed.

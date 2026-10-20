# Deviations and amendments

Every change to `PREREGISTRATION.md` after its commit (`38bf0a6`) goes here, dated. Each entry
says whether any annotation or extraction output existed when it was made.

## A1. 2026-10-18, before any annotation or model output existed (Stage 1 only)

At this point, only Stage 1 had run: OpenCV panel candidates, with no model call. No annotation
had started.

1. **Alignment (section 7).** Order-based fallback matching of target rows is dropped.
   - A system record aligns to an annotated target row only when one of these holds:
     - the printed names are equal after normalization, or
     - the gene symbol equals one of the annotator's symbols.
   - Everything else counts as NOT_FOUND (annotated row) or as a spurious record (system).
   - Reason: system records carry no row position, so ordering would pair unrelated rows by
     accident. Both versions count the same error. This one is deterministic.
2. **Crop mapping (section 7).**
   - The mapper writes the figure number and panel letter(s) for each crop instead of
     inventory panel IDs. `score_blind.py` joins these to the inventory.
   - This lets mapping run in parallel with annotation. The mapper still sees only crop images
     and page numbers.
   - The crops given to the mapper are every crop Stage 1 sent to the model, not only the ones
     that produced records.
3. **Field formats (section 6).**
   - Modification is written as `total`, `phospho`, `phospho:Y705` or `phospho:T202/Y204`,
     `cleaved`, `other:<text>`, or `NOT_STATED`. It is scored as two fields:
     - `modification_type`
     - `phospho_site`, only for annotated phospho rows with a stated site. A system site counts
       as correct if it is one of the annotated sites.
   - Treatments use `none` when no agent was applied. `none` and `NOT_STATED` are both treated
     as "no value expected".
   - Synonyms are allowed with `|`, and several items are separated with `;`.
   - Cell line falls back to the system's `sample` field when `cell_line` is not asserted.
4. **Band calls.**
   - Lanes the annotator calls `uncertain` are not scored. They are counted in the lanes CSV.
   - A system `uncertain` on a lane the annotator called present or absent is ABSTAINED.
5. **Model transport.** Production calls `claude-opus-5` through the `anthropic` backend. This
   laptop has no API key, so extraction will run either:
   - through the `claude_cli` backend with `WBM_MODEL=claude-opus-5` (same model, same prompts,
     the image passed as a file), or
   - with the production backend, if Nik runs it with the key himself.

   Whichever is used gets recorded in each paper's `timing.json` (`environment`) and in the
   report.

## A2. 2026-10-18: PDF acquisition

The system fetcher got draw ranks 1, 2 and 4. Rank 3 (PMC7948984) failed every source. Under
section 4 step 2, a person must try a browser download before rank 3 can be skipped. Until that
is done, rank 8 (PMC7757890) is in the frozen list provisionally.
- **If rank 3 is obtained:** it replaces rank 8.
- **If not:** rank 8 stays, and ranks 3, 5, 6 and 7 are logged as access failures.

This depends on access only. Rank 8's Stage 1 output was produced while it was provisional.

**A2 resolved, 2026-10-18.** Nik downloaded rank 3 (PMC7948984) in a browser. Its DOI was
checked against the PDF text, and the file is frozen with SHA-256 `ee043119b233…`. Rank 3
replaces rank 8 (PMC7757890), which is dropped from the frozen list:
- Rank 8's Stage 1 output was produced and is not used.
- Its model stage was never run.

Final papers: ranks 1, 2, 3 and 4.

## A3. 2026-10-18: scorer fixes from a dry run (before any benchmark output was viewed)

The full scorer was dry-run on a paper that is **not** in the benchmark: the reviewed STAT3
paper, 10.3892/br.2026.2108. The annotations for it were synthetic, and the benchmark's sealed
outputs were not opened. These are general bookkeeping fixes, not tuning:
1. **Multi-symbol targets.**
   - The system writes ERK1/2 as `MAPK1/MAPK3`, while annotators write `MAPK3|MAPK1`.
   - Protein identity is now correct when every system symbol is one the annotator listed.
2. **Crops.**
   - **Every crop counts.** A panel's records now come from every crop mapped to it. Before,
     only the first crop group was used.
   - **Overlapping crops.** Extra records for an already-aligned target are counted as
     `duplicate_records`. They are reported and are neither scored nor counted as incorrect
     assertions.
   - **Spurious records.** A record counts as spurious only if its target matches no annotated
     row in its fully annotated panel(s).
3. **Alignment order.**
   1. Every annotated row is matched by printed label first.
   2. Remaining rows are matched by gene symbol, preferring a record with the same modification
      and site. This stops a Ser727 record from taking a Tyr705 row.
4. **Adjudication verdicts** are keyed by paper as well as panel. Panel IDs restart in every
   paper, so the old key let one paper's verdict apply to another.

Self-test cases were added for 1-3. The dry run exercised the seal check, the crop-map join,
panel recall, the report and adjudication (raw 3/4 → adjudicated 4/4 on an injected notation
mismatch).

## A4. 2026-10-19: retracted paper excluded; benchmark is 3 papers

During annotation, Tanvi found a RETRACTED watermark on draw rank 2 (PMC5328321, Yang et al.
2017, Onco Targets Ther). The eligibility rule in section 3 excludes retracted papers. The
candidate file had not flagged it, so it was drawn by mistake.
- **Exclusion.** It is excluded on that rule. The decision was made before any scoring; its
  sealed outputs were never opened and are not scored.
- **No replacement.** Section 4 would take the next paper in draw order (rank 5, PMC12022650).
  It was not added, because of annotator time before the deadline. The benchmark therefore has
  **3 papers** (ranks 1, 3 and 4) instead of 4.
- **What this changes.** The sample is smaller and the denominators will show it. Neither
  decision depended on any result.

## A5. 2026-10-20: annotation coverage and clerical fixes (before scoring; outputs still sealed)

- **Coverage.** The guide asked for every panel to be labeled when a paper has 6 or fewer. Tanvi
  labeled 8 of 11 inventoried panels:
  - paper 1: 4/4
  - paper 3: 3/5
  - paper 4: 1/2

  The panels she labeled were her own choice, made blind to all system output. Field metrics use
  the 8 labeled panels. Panel recall uses all 11.
- **Clerical fixes,** each logged in `annotations/tanvi/ERRATA.csv` and confirmed with Tanvi:
  - inventory panel numbers changed to per-paper numbering
  - one duplicate `row_order` typo fixed
- **Set aside.** 24 lane calls had no matching target row: paper 3 panel 4 (3 strips) and paper 3
  panel 3 strip 4. Nobody filled them in, to keep the labels human-only, so they are not scored.

## A6. 2026-10-20: scorer fixes after unsealing (no metric changed)

The first scoring run stopped on Tanvi's free-text time log ("1:32 hour"). Three mechanical fixes
were made. Re-scoring produced identical metrics, and the pre-fix output is kept for comparison:
1. Durations are now parsed from free text (time log only).
2. Supplementary figure labels ("S1") are no longer read as Figure 1 in the crop-map join.
3. The report's paper count is computed, not hard-coded.

Separately, the raw numbers are strongly affected by annotation notation:
- gene symbols written non-standardly (SOSTMI, LC31, CatD)
- `none` written for `total`
- free-text cell-line descriptions

That gets settled only through Tanvi's adjudication and confirmation sheet, never by changing the
scorer to fit the results. The inventory lists only the panels she labeled, not every Western
panel, so panel recall is not a valid literature-level number and will be reported only with that
caveat.

## A7. 2026-10-20: matching corrections from the independent audit (after unsealing)

The auditor (`report/AUDIT.md`) found that most non-CORRECT outcomes came from joining labels to
records, not from wrong system values. Three mechanical corrections follow from its diagnosis and
are applied symmetrically:
1. Printed labels are compared without molecular-weight tags ("LC3B (14 kDa)" equals "LC3B").
2. An annotated modification of `none` means total protein, which is what the guide's `total` means.
3. When the annotator and the system counted a strip's lanes differently (for example 24 physical
   lanes against 12 samples), its lane calls are reported as `LANE_COUNT_MISMATCH` and left
   unscored, instead of being counted as misses. 104 lane calls are affected.

The pre-registered scorer's output is kept unchanged in `report/raw_preregistered/`. Every report
shows both. Gene-symbol notation (SOSTMI, LC31, CatD), cell-line notation, and the treatment labels
on PMC7948984 (a staurosporine study labeled `none`) go to Tanvi's confirmation sheet; they are
not fixed in the scorer.

## A8. 2026-10-20: annotator confirmation applied; three reported tiers (after unsealing)

Tanvi answered the auditor's 29-row confirmation sheet (`annotations/tanvi/confirmation.csv`): 26 `yes`,
1 `no` (HSP70 vs HSPA9), 1 `present (faint)` (AIF nuclear lanes 1, 3, 4) and 1 blank (Fig 4A lanes 13-24,
already `LANE_COUNT_MISMATCH`). Each row is classified in `annotations/tanvi/confirmation_classification.csv`:
- **A, NOTATION** (her label and the system's are the same thing written differently): rows 1-7, 9, 10,
  12-15, 26.
- **B, LABEL_CORRECTION** (after seeing system output she agrees her label was wrong): rows 16-18, 21,
  22, 24, 25, 27, 29.
- **C, SYSTEM_WRONG** (label stands): rows 8, 11, 23.
- **D, N/A** (no scoring action): rows 19, 20, 28.

The locked label files (`targets.csv`, `lanes.csv`, `crop_map.csv`) are not edited. Three inputs are
read by `score_blind.py` and applied to in-memory copies:
1. **`annotations/tanvi/aliases.csv`** (notation, tiers ii and iii; 13 rows). New mechanism, because
   the pre-registered `EQUIVALENT_NOTATION` verdict can only rescue an INCORRECT/UNSUPPORTED cell, not a
   row that never aligned:
   - `alias_label`: a second spelling of the printed label, used **only for alignment** (SOSTMI ->
     SQSTM1, LC31 -> LC3I, PSMBS -> PSMB5, a/B -> alpha/beta for two GSK3 rows, and the two ERK rows whose
     system label ends in "42/44 kDa", which the A7 rule does not strip). The fields are still scored
     against the locked label.
   - `alias_modification`: the phospho site written out from her own printed label (7 rows,
     confirmation row 14). This adds `phospho_site` cells, which could score either way.
   - `alias_panel_id`: the PMC4393234 GAPDH row (and its 4 lanes) belongs to Fig 3C, inventory panel 2,
     not Fig 3B (row 26). Panel 2 therefore counts as a labeled panel in tiers ii and iii (9 panels).
2. **`annotations/tanvi/adjudications.csv`** (notation, tiers ii and iii): 19 `EQUIVALENT_NOTATION`
   verdicts, keyed to `report/adjudication_sheet.csv` from a fresh score with the aliases in place.
   - A verdict is applied only to cells whose (annotated, system) pair is exactly the pair she confirmed:
     AIF vs AIFM1 (1 cell), and the PMC9283986 sample text vs "fibroblast protein extracts from control (6)
     and FAD (6) individuals" (18 cells in panels 2-4; panel 2 has the identical pair although the sheet
     listed panels 3-4).
   - The scorer stops if any verdict matches no cell.
3. **`annotations/tanvi/corrections.csv`** (label corrections, tier iii only; 62 rows):
   - treatments for PMC7948984 (staurosporine) and PMC4393234 (sciatic nerve conditioning stimulation);
   - PMC4393234 sample (spinal cord dorsal horn);
   - AIF lanes 1, 3, 4 (present);
   - the re-filed Fig 2A and Fig 2D strips, one call per lane;
   - `n_lanes` (not scored);
   - the Fig 6G crop (`NOT_WB` -> `WB_NOT_IN_INVENTORY`).

**Scorer bug fixed:** `apply_adjudication` chose INCORRECT or UNSUPPORTED from the field's counter rather
than from the cell's own category (`AUDIT.md` §5.3). It now uses the cell's category. No applied verdict
falls in a field that has both categories, so no number changed.

**Not applied (pending; disclosed in the report):**
- **PMC9283986 panel 1 sample cells (7).** The system text there ("Fibroblast ... (NA1-NA6, AD1-AD6)")
  is not the pair she was shown. They stay INCORRECT.
- **AKT1 against printed "PAKT (Ser473)" / "AKT total" (2 cells).** The question confirmed "AKT", not
  the isoform AKT1. They stay INCORRECT.
- **PMC4393234 GAPDH treatment in tier iii.** Her corrected text is "sciatic nerve conditioning
  stimulation"; the system wrote "CS (conditioning stimulation of the sciatic nerve)". No verdict exists
  for this pair, so it scores INCORRECT.
- **Fig 2A cleaved-PARP1 strip.** It has no target row and stays unscored.
- **Fig 2D GAPDH lane calls.** They were in the set-aside row, which is not in the locked `lanes.csv`,
  so they stay unscored in tier iii.
- **Duplicate lane keys.** In tiers (i) and (ii), PMC7948984 Fig 2A row 3 still holds duplicate lane keys
  (24 entries for 12 lanes), as locked.

**Reported tiers** (`report/RESULTS.md`, generated):
- (i) Pre-registered raw, unchanged in `report/raw_preregistered/`.
- (ii) Adjudicated, the headline: A7 matching plus notation (aliases and `EQUIVALENT_NOTATION`).
- (iii) Tier (ii) plus label corrections. This tier is post hoc: the annotator saw system output.

The A7-only intermediate is also shown, for transparency. Nothing under `western_blot_miner/` or `api/`
changed. Self-test cases cover alias alignment, alias panel re-filing, corrections, duplicate-lane
removal and the crop-map correction.

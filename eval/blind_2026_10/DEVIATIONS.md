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

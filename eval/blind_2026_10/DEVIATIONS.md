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

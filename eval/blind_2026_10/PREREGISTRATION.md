# Blind extraction benchmark, October 2026: pre-registration

Written 2026-10-18, before any paper was drawn, downloaded, annotated or extracted. This file is
committed first. Every later change is a new commit, and any deviation goes in `DEVIATIONS.md`.

## 1. Question

Take open-access papers that HiveBlot has never processed. The goal is to measure how well the
existing extraction system recovers these items from their Western-blot figures, against labels
an independent human made from the paper alone:
- protein identity
- modification
- cell line
- treatment
- lane-level band calls

This is a small evaluation of 4 papers. It is not a literature-wide accuracy figure, and the
report must say so next to every number.

## 2. System under test (frozen)

- **Code.** `western_blot_miner/` at commit `f77d311` (main, 2026-10-11).
  - The production API (Render, `3839ee3`) runs the same extraction code. The only difference
    between `3839ee3` and `f77d311` is in docs and tickets.
  - The worktree must show no diff under `western_blot_miner/` or `api/` against `f77d311`
    when extraction runs and when scoring runs. The scorer checks this.
- **Path.** This is the same path production live ingestion takes:
  1. `pdf_preprocess.preprocess_pdf` with defaults: DPI 350, candidate score 0.35, model score 0.65.
  2. `pipeline.run_records_stage(summary, use_cache=False)`.
  3. The UniProt resolver live.
  4. Escalation off (`WBM_ESCALATE` unset).
  5. `WBM_CONCURRENCY=1`.
- **Model.** `claude-opus-5`, which is the production default (`WBM_MODEL` is unset on Render).
  - Production calls it through the `anthropic` backend.
  - If this run has to use another transport (the local `claude_cli` backend), that goes in
    `DEVIATIONS.md` before extraction.
- **No database writes.** No row goes to the production database, and no DOI below is entered
  into hosted HiveBlot.
- **No code changes.** Nothing that could change accuracy is altered between pre-registration
  and the final report: no prompt, threshold, rule or normalization in the system. A crash is
  recorded as a failure, not fixed and re-run. The one exception is when the crash is
  infrastructure (expired login, network timeout before any model output). Then the same frozen
  code is re-run and the event is logged.

## 3. Paper pool and eligibility (fixed before the draw)

**Pool.** The pool is the 26 papers in `eval/candidates.json`, assembled 2026-08-12 for future
human annotation. None has been run through HiveBlot extraction.
- I checked this against every DOI in:
  - the reviewed table
  - the live table
  - `ingest_jobs`
  - local `pdf_runs`
- I checked it against the repository: the only mention outside the candidate files is
  PMC6360618 in `tickets/densitometry.md`, which is a densitometry note, not an extraction
  fixture.

**Eligibility rule.** A paper is eligible only if all of the following hold:
- `is_western` is true.
- The license string contains "CC BY".
- It is not a protocol or methods-chapter publication (Bio-protocol, STAR Protocols, Methods
  Mol Biol).
- It is not retracted.
- It has not been processed before.

**Eligible papers (15):** PMC5328321, PMC5225179, PMC8332585, PMC4393234, PMC12022650, PMC8632698,
PMC6406374, PMC7333534, PMC7948984, PMC6794468, PMC9283986, PMC3941594, PMC7757890, PMC6242874,
PMC6360618.

**Excluded (11):**
- PMC3139001, PMC2820294, PMC5778823, PMC7250321: no explicit CC BY.
- PMC3631761, PMC7842739, PMC8784402: protocol or methods publication.
- PMC4087434, PMC5472695, PMC1867154: not Western blots.
- PMC2542845: retracted.

**Note on difficulty.** The pool was built to cover diverse and adversarial Western-blot cases,
so it is likely harder than an average paper. The report states this.

## 4. Draw

`draw.py` sorts the 15 PMCIDs and shuffles them with `random.Random(20261018)`. Papers are taken
in that order until **4** have a usable PDF.

**PDF acquisition, in order:**
1. The system's own `fulltext.fetch_pdf(doi)`.
2. If that fails, a person downloads the publisher or PMC PDF in a browser. This is the same file
   a researcher would supply through the upload path.
3. If no PDF can be obtained, the paper is skipped, logged in `papers.json` with the reason, and
   the next one is taken.

A skip can depend only on access, never on content or results. Each frozen PDF is identified by
its SHA-256. Only the main article PDF counts; supplementary files are out of scope for both the
system and the annotators.

## 5. Sealing

- Extraction output goes to a private directory outside the repository. Only its SHA-256
  manifest (`SEALED_OUTPUTS.sha256`) is committed, and it is committed before any annotation is
  received.
- Annotators and the crop mapper never see extracted values.
- Annotations are committed with their own hashes before the outputs are unsealed for scoring.

## 6. Reference labels (independent human annotation)

**Who.** Annotators are people with wet-lab Western-blot experience.

**Rules for annotators:**
- Label from the frozen PDF only.
- No AI tools.
- Do not use HiveBlot.
- Do not read `eval/candidates.json`. Its `annotation_fields` were written by AI agents, so they
  are not ground truth.

**Units.**
- **Inventory.** List every Western-blot panel in the main PDF, in reading order: figure number,
  then panel letter, then top-left to bottom-right inside unlettered figures. Numbering
  1..N defines the panel IDs. Each entry gives the page, the figure and panel, and every target
  printed beside the blot rows.
- **Full annotation.** Fully annotate the panels chosen by the paper's pre-generated sampling
  sequence in `papers.json`. Go through the sequence in order, keep each number that is ≤ N, and
  stop at 6 panels. If N ≤ 6, annotate every panel.
- **Fields per target row:**
  - printed target name
  - official gene symbol
  - modification: a phospho site, "total", or "not stated"
  - cell line or sample
  - treatment(s)
- **Fields per lane:** lane index (1 = leftmost), the lane label as printed, and the band call
  (`present`, `absent` or `uncertain`).
- **"Not stated."** Where the paper does not state a value, the annotator writes `NOT_STATED`.
- **Timing.** Each annotator logs start and end clock times per paper, separately for the
  inventory and the full annotation.

**Second annotator.** If one is available, they independently annotate the same sampled panels
of one paper, chosen as the first paper in draw order. That gives an agreement figure. The
primary annotator's labels are the reference.

## 7. Alignment

- **Crop mapping.** After annotation is committed, a person who is neither annotator maps each
  system panel crop to inventory panel IDs, or marks it `NOT_WB` or `WB_NOT_IN_INVENTORY`.
  - The mapper is shown only the crop images and their page numbers (`mapper_pack/`), never
    extracted values.
  - One crop can map to several panel IDs.
- **Target rows.** Within a mapped panel, a system record aligns to an annotated target row when
  either:
  - the gene symbols are equal, ignoring case, or
  - the printed names are equal after normalization (case, whitespace and punctuation removed).

  Unaligned rows are matched in listed order.
- **Lanes.** Lanes align by lane index.

## 8. Scoring (fields: protein identity, modification, cell line, treatment, band call)

**Categories:**

| Category | Meaning |
|---|---|
| `CORRECT` | The system asserts the annotated value. Equality is after the normalizations in `score_blind.py`. |
| `INCORRECT` | The system asserts a different value. |
| `ABSTAINED` | The system gives no value, or a status of MISSING, AMBIGUOUS or CONFLICTING, for a field the annotator filled. |
| `NOT_FOUND` | The annotated target row or panel produced no aligned record. |
| `CORRECT_SILENCE` | The annotator wrote `NOT_STATED` and the system gave no value. |
| `UNSUPPORTED` | The annotator wrote `NOT_STATED` and the system asserted a value. This counts as an incorrect assertion. |

**Reported per field, per paper and pooled, always with denominators:**
- **Accuracy** = CORRECT / annotated values
- **Precision of assertions** = CORRECT / (CORRECT + INCORRECT + UNSUPPORTED)
- **Abstention rate** = ABSTAINED / annotated values
- **Not-found rate**

**Panel recall.** The share of inventoried Western-blot panels with at least one aligned system
record. It is computed over the full inventory, not the sample.

**Incorrect assertions.** INCORRECT plus UNSUPPORTED field values, plus spurious records. A
spurious record is one on a crop mapped to `NOT_WB`, or one that aligns to no annotated target
in a fully annotated panel.

**Adjudication.**
- After scoring, the primary annotator reviews every INCORRECT and UNSUPPORTED cell and may mark
  it `EQUIVALENT_NOTATION`. This covers only the same entity written differently, such as an
  alias or a formatting difference.
- Reference labels may change only to fix a logged clerical error (`ERRATA.csv`).
- Both raw and adjudicated numbers are reported.

**Timing.**
- Manual: minutes per fully annotated panel, measured.
- Automated: wall-clock per paper, for preprocessing and model extraction separately, plus
  minutes per panel sent to the model.

Both are reported as measured. Extrapolations are labeled as estimates.

**No exclusions after the draw.** Every drawn paper with a frozen PDF is reported, including any
where extraction fails. A failed paper counts as panel recall 0.

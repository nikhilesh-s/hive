# UCSF push session log — 2026-09-14

## Canonical execution state

- **Active branch:** `experimental/ucsf-demo-2026-09-09`
- **Do not use `main` as current state.** It is stale relative to the beta/experimental lineage.
- **Founder hard stop for the multi-window push:** Tuesday, 2026-09-15 at 7:00 PM America/Los_Angeles.
- **Startup launcher:** `CLAUDE_RUN_2026-09-14.md`
- **Full orchestration plan:** `research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md`
- **Deferred access ticket:** `tickets/journal-access-later.md`

## Founder decisions locked for this push

1. Densitometry is the highest-priority product track because it was promised to UCSF researchers.
2. Build a real first-generation experimental densitometry workflow, not only categorical band reading.
3. Preserve scientific honesty: relative within-image pixel measurements may be shown when supported; clipped/invalid/unstable cases must warn or refuse instead of returning fake precision.
4. B-1 caption/methods separation and B-2 deterministic antibody backstop are the highest-priority biology fixes.
5. Valency is only the paper-discovery layer. Do not create a separate Valency workstream unless the research route is currently broken.
6. Journal/paywall access visibility is deferred to week 2+.
7. Use one active integration branch. Existing experiment branches should become historical pointers; experiments belong behind `/experimental/*` routes.
8. Claude should recursively continue choosing the highest-value safe unfinished task through each allowance window, checkpointing before cutoff, and resume across subsequent windows instead of restarting planning.

## Branch graph already established

The active UCSF branch already contains the histories of:

- `experimental/densitometry`
- `experimental/paper-qa`
- `experimental/valency-live-ingest`
- `experimental/demo-day`

Do not merge them again.

`feature/bio-context-beta` diverges by a small documentation/HANDOFF-only delta relative to the active branch. Inspect/port only genuinely useful current-state information.

`copilot/fix-whitespace-and-secret-scan` has a tiny unique fixture/CI-related delta relative to stale `main`; inspect whether the current hygiene false-positive still makes it useful before porting anything.

## Planning commits immediately before execution

- `2f1e48ffd0fd5c1ee2896294c8beca12b5184661` — refocus orchestration on densitometry + branch convergence.
- `a80f063cc1bf7c4a61465422ca5ed97d71383e95` — defer journal access indicator.
- `0038497b2a2fe71e0eb0e49c314c154685df7491` — add resumable multi-window Claude launcher.
- `0fb6b538889eef5651db79a29450b801aa195c71` — make root `CLAUDE.md` point to the active launcher.
- this commit — establish the resumable session checkpoint.

## Exact next task

Start execution, not another broad planning pass:

1. pull the active branch and verify working tree/test baseline;
2. open the current densitometry frontend proxy/API/analyzer path;
3. fix researcher `region` propagation end-to-end with a regression test;
4. immediately continue into researcher-defined lane boundaries and quality/refusal behavior according to the launcher/orchestration plan;
5. after each coherent block, test, commit, push, update this log and `HANDOFF.md`, then recursively choose the next highest-value task.

The next Claude window should not spend time re-deriving this plan unless repository state materially contradicts it.

## Window 1 execution log (2026-09-14 night)

Baseline verified at `b287b7b`: densitometry 20/20 (old contract), api 160/11 skipped, tsc clean.

### Block 1 — commit `7238a8f` (pushed)
- Densitometry v0.2: region propagation fixed (proxy dropped it); `lane_bounds`/`lane_labels`
  first-class; equal-width/auto = diagnostics; explicit contract; clip / SNR / geometry gates;
  refusal states with `relative: null`; deterministic perturbation envelope; method + threshold
  metadata; sha256 of the image; UI rebuilt (drag region, dividers, labels, overlay, quality
  card, ranges, JSON/CSV export). Tests 61/61 + API 10 (164 total).
- B-1 caption/methods split (`_split_text_context`, 2 tests). B-2 antibody backstop (4 tests).
- Browser-verified on the local stack (API :8010 upload path, web :3000): clipped reference lane
  → "Quantification refused" card, no relative column; 4 clean lanes → ranges 1.0 / 0.5 / 0.2–0.3 / 0.0,
  ranking stable, overlay matches returned geometry.
- Sub-agents used: Biology lead (B-1/B-2), Densitometry UI lead (page/proxy/css); orchestrator
  owned analyzer/router/tests/git.

### Block 2 — validation docs (this commit)
- `scripts/experiments/densitometry_clip_study.py` → `research/experiments/D2_clip_threshold_study.md`
- `scripts/experiments/densitometry_real_crops.py` → `research/experiments/D5_real_crops_refusal.md`
  (21/21 crops have a clipped row past the gate; 78/112 rows refused, 15 ok, 19 warning; 1 refused for
  reference instability). Auto geometry is diagnostic; ~0.5 s per analysis on the largest crop.
- D1 report retired with a header; architecture doc experiment table updated; HANDOFF top block added.
- Adversarial reviewer (Lead Q) running on densitometry + B-1/B-2; findings land in the next block.

## Window 2 (2026-09-15, after the usage reset)

- Lead Q sub-agent died on the rate limit; the orchestrator ran the probes itself
  (`scratchpad/adv*.py`, not committed). Findings: P1 B-2 multi-antibody attribution (fixed,
  `6e7911d`); everything else held (0 invariant violations / 30 fixtures, deterministic JSON,
  clamped region echo, 400/422 at the API boundary, no protein-amount copy).
- `6e7911d` — B-2 target scoping + CI hygiene `@localhost` exclusion.
- Browser check of the record path on the local DB (record 4455) exposed the polarity bug
  (region mean) and a false "printed text" warning on a tightly boxed strip; both fixed in
  `5ccac69` together with the near-tie warning (values kept) vs severe-flip refusal split.
- Real-crop gate checks (73 checks total) + `research/overnight/2026-09-14-summary.md`
  (densitometry state, limitations, branch audit, Nik's manual steps) — this commit.
- Lead P (Tally / distribution review) running as a sub-agent; result folded in when it returns.
- `94b9840` demo_check product-path check (record 4455), Lead P Tally/distribution review folded in,
  L1 stale header (B-6).
- Tight-box probe found the background kernel scaling with the box (ratios 0.5/0.25/0.1 read
  0.62/0.54/0.56 in an 18 px box, state ok). Fixed in `2ff1b0f` (kernel from the whole image) together
  with explicit `band_row` (API + UI select), overlay PNG export (UI sub-agent), 40 px floor on the
  text-row test, run-of-show step 9 rewritten with concrete records (4455 valid / near tie, 4686 refused).
  Browser-verified on record 4455 after an API restart.
- Weak-lane flag reworded (a lane showing 0.4 was labelled "no signal"); summary updated — this commit.
- `8d2a1aa` multi-strip full-box warning; About/Learn name the experimental route.
- `19afe21` row buttons re-box the chosen strip; multi-strip box = warning.
- Browser check of the re-box path showed the 3-strip box compressing ratios (0.6 → 0.8) because the
  opening's background hits white space inside the box and membrane grey becomes signal. Method
  **v0.3.0**: per-lane flank baseline (median of membrane rows one band-height above/below the band,
  lower of the two) + flank MAD noise. Synthetic unclipped error 7.4% → ≤1.8%; tight vs re-boxed real
  strip agree within 0.04; adversarial set all within 0.01. Box with no flank rows warns. — this commit.
- `f1022a4` printed-text test = short dark runs (a clipped ACTB strip was being called text); run-of-show
  4686 box corrected and browser-rehearsed (refused, clipped cores 30–56%).
- Per-lane vertical profile in the response + sparkline column in the table (band row shaded, flank
  rows faint, dashed baseline); browser-verified on record 4455 — this commit.
- TIFF uploads (imager exports) via `POST /experimental-densitometry/preview` → 8-bit PNG data URL;
  measurement on the preview equals the TIFF (test); rate limit 60/min; browser-verified with a 16-bit
  synthetic TIFF.
- Third adversarial pass on the flank baseline: opening kernel floored at 61 px (`6901354`); all
  cases within 0.04. `next build` clean with the dev server stopped; `scripts/demo_check.py` on the
  restarted stack: 19 PASS · 2 WARN (Valency token absent) · 0 FAIL.
- D-5 author-value comparison closed with the allowed outcome: `scripts/experiments/
  densitometry_author_values.py` → `research/experiments/D5_author_values.md`, 12 of 93 detected rows on
  the ten LC3B/ACTB crops pass the gates and no crop has a passing LC3B + ACTB pair ("n too small").
  Final browser rehearsal of run-of-show step 9 (4455 valid, 4686 refused) passed on the restarted stack.
- Loading-control pairing: `pair_ratio` + `POST /experimental-densitometry/pair` (`e0d1239`), nine
  synthetic checks, real record 4455 P-STAT3 ÷ β-actin normalized 0.69/1.0/0.31/0.04/0.04/0.33; UI
  section 4 built by the UI sub-agent (verified below when it lands). `local_db.py up` re-run is clean.

## Window 3 (2026-09-15, Opus 5 after the Fable limit)

- The pairing UI sub-agent hit the usage limit mid-edit. Its first half had already been swept into
  `e0d1239`; the remaining section-4 edit typechecked and linted clean, so it was kept and pushed as
  `1017a11` together with the side-tab fix on the quality card (design hook finding).
- Browser-verified the full pairing flow on record 4455 (P-STAT3 target, β-actin control): table
  matches the analyzer, caveat first, target/control overlay labels, both pair exports, no console
  errors. All suites green (densitometry 94, api 167/11 skipped, miner 56).
- Design hook: two other side-tab borders (globals.css ~1454, ~1638) are pre-existing beta styles
  from 2026-09-01 / 09-05; left standing, not suppressed.
- New rule from Nik: checkpoint commit + push after every coherent block and tell him; sub-agent
  prompts must require an early progress report.
- Re-rehearsed record 4686 refusal after the v0.3 / text-row changes: refused, clipped 30–56%, no
  false printed-text warning.
- B-4 scaffold: `scripts/experiments/panel_inventory_review.py`, blank inventory templates for the
  three reviewed papers, review report; recall/precision blocked on the human inventory; crop-gate
  visibility limit stated in the report.

## Window 4 (2026-09-15 afternoon, Opus 5) — hardening / adversarial QA

- `8c6ba44` CI hygiene: trailing Markdown spaces + B-4 report EOF blank line (the only failing CI step).
- Property harness (`scratchpad/fuzz/fuzz_dens.py`, 300 random fixtures: refusal invariant, JSON safety,
  determinism, envelope bracketing, confident-wrong, padding / polarity / mirror metamorphic, self-pair):
  all held once the harness's own ground truth accounted for unequal band widths.
- Read-only attack children (API boundaries; biology/provenance) + hostile fuzz found and we fixed:
  - `7ccf754` refused strips still exposed per-lane stability ranges; refused pair lanes still exposed
    target/control relatives; empty / undecodable base64 and int16/float64 colour TIFFs were HTTP 500;
    transparent PNGs read as dark background; no decoded-pixel cap; control-only labels dropped;
    labels silently cut at 40 chars; pair errors did not name the strip.
  - `01719c0` antibody backstop stole neighbours' catalog/dilution (unprefixed lists, `;` inside
    parentheses, substring target match ERK/ERK5, single fragment naming another protein); catalog regex
    matched "indicated 1000"; pVHL / pRB / P-glycoprotein / P-gp read as phospho, p-p38 missed;
    core_symbol stripped P-cadherin / t-PA; two-site captions assigned the first site; reported MW always
    labelled caption with synthesized text; caption/methods split fooled by quoted/repeated headers; IP
    lane markers labelled caption.
  - `684b27f` geometry caveats (no membrane margin, diagnostic lanes, text-like row) sat under a "valid"
    card; now they downgrade to warning.
  - `e594c7c` pairing warns on offset control lanes / differing labels; lane-count mismatch rejected early.
- Known limit (not gated, documented): strips closer than ~3 band sigmas merge into one row; centroid
  spread and profile-shape distance both overlap real single strips, so a gate would warn on valid demo
  strips. The per-lane profile sparkline shows the merged shape.
- Frontend stale-state (this block): request sequence numbers so a late Measure / pair / TIFF-preview
  response cannot paint onto a new image or geometry; row-index change invalidates; target uses the row
  the result was measured with; errors clear on geometry change; CSV labels neutralised against formula
  injection.
- `ec8218d` lane conditions / lane doses-durations / lane-text band patterns are image evidence, not
  figure_caption (unfixed remainder of the IP-marker fix).
- `68f1c7c` single lane downgraded to warning (relative 1 by definition); thin explicit band-row
  refusal names the cause.
- Verified without defects: export JSON -> rebuilt request reproduces identical lanes/state; record vs
  upload path identical (same sha256); top/left padding shifts coordinates and profiles exactly
  (120 fixtures); random pairings never expose numbers on refused lanes; 24 three-pixel lanes and
  lanes touching image edges behave.
- Post-fix hostile fuzz (250): confident-wrong valid strips 22 -> 11, remaining are the documented
  adjacent-strip merge limit plus one 9-DN JPEG noise-limited case (not gated: one point, error 0.16).

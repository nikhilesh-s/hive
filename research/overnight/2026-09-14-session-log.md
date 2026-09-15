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
- `079124d` real-corpus provenance sweep (child, read-only): today's backstop truncated catalog numbers
  (20200728 -> 2020072, 5174s -> 5174), cut dilutions at the comma (1:100,000 -> 1:100) and offered a
  second anti-PIK3CA antibody's catalog/vendor as candidates; fixed and verified on the sweep.
- `4c98e6e` page error line visible before an image loads (corrupt TIFF on a fresh page), readable
  FastAPI validation errors, lead copy no longer says "not loading-control normalized" above the pairing.
- `c42f1ee` pre-existing source typing fixed (child): a Source is typed methods / figure_caption only
  when its text is verbatim there (whitespace, soft hyphen, dash variants folded), else model_target;
  backstop only over verbatim text. Sweep: caption-not-substring 75 -> 0, snippet-lacks-value 113 -> 0,
  methods-not-substring 418 -> 40 (U+2011 hyphen variants, verbatim under the new rule). No value,
  status or candidate changed on the three papers.
- `e6e86ad` conflict probe: "pVHL" / "pRB" in a caption read as a glued phospho prefix, creating a false
  phospho-vs-total conflict; fixed. Caption Ser727 vs antibody Tyr705 and caption total vs phospho
  antibody correctly stay CONFLICTING with candidates.
- `0396aee` evidence panel / Learn / About label model_target as "model reading", not "row label".
- Checked clean: 128 stored context blobs have line-start headers (no split leaks); 81 MP bomb PNG is a
  400 in 0.1 s; overlay PNG strokes land on returned lane/region coordinates; property harnesses rerun
  after the caveat changes (150 + 80 fixtures) hold; first fully green CI run on `7d92dfa`.
- `9080341` treatment dose/duration parsed from the model's own wording are model readings, not
  deterministic evidence.
- `8f766fe` + `1d6c431` co-IP bait from printed lane labels typed image (not caption), and image quotes
  windowed on the lane-label text only. Real-corpus sweep after all source-typing fixes: caption classes
  0; only 40 U+2011 hyphen variants flagged by the sweep's stricter normaliser.
- Browser state machine (pairing): new record clears the target and section 4; lane-count change after
  setting a target gives "target has 6 lanes, control has 5"; diagnostic mode disables pairing with a hint.
- `29bf167` CI lint failure on 9080341 (unescaped apostrophes from 0396aee). Cause of the miss: local lint
  was piped through `tail`, hiding the exit code. Lint is now always run with pipefail.
- `f329bc2` CI gap: the pytest-style miner regression suites never ran in CI (only a fixed script list);
  added a CI step (green on f329bc2) and a local corpus rebuild test (record_ids stable, deterministic,
  caption/methods quotes verbatim). Rebuild is byte-identical across PYTHONHASHSEED values; 93/93 ids stable.
- Checked clean: no API / web / loader consumer selects evidence by source type (only the panel label map),
  so the model-reading retyping cannot drop evidence; local stack restarted on HEAD, demo_check 19 PASS /
  2 WARN / 0 FAIL.
- Soft-saturation probe (not a code defect, documented limit): a tanh exposure knee compresses ratios
  (0.5 / 0.25 / 0.1 -> 0.67 / 0.37 / 0.17) with 0% clipped pixels and a "valid" card; core flatness does
  not separate it from clean or real strips, so no gate. Only a dilution-series calibration (D-7) can bound it.
- Live (non-replay) extraction of the demo panel (claude_cli / sonnet, one model call, cached): biology
  correct (Ser727 / Tyr705 phospho, T-Stat3 total, beta-actin unmodified), 0 provenance violations, but
  every antibody catalog empty. Root cause was retrieval, not the backstop: the context blob was cut once
  at 12000 chars with methods last, so 50/128 stored contexts had no methods snippets; reagent sentences
  were never targeted; extract_panel sent only 4000 methods chars.
- `8dd8735` per-section context budgets, reagent snippets first, methods snippets ahead of the preamble,
  8000-char methods prompt, backstop over verbatim methods with dash-variant folding.
- Follow-up (this block): the reagent sentence was retrieved twice (overlapping keyword windows), so the
  backstop abstained as if two antibodies; identical / prefix scopes now count once and overlapping
  retrieval windows merge. Replaying the cached live output on the rebuilt context: beta-actin rows recover
  CST #4967, 1:2000, Cell Signaling with a deterministic source quoting "beta‑actin (1:2,000; CST #4967)";
  phospho and total STAT3 rows abstain (one sentence names both). Stored-corpus sweep: 0 value changes.
  This is B-2's original acceptance case, now met on the live path.
- Backstop agreement audit (no model calls, `scratchpad/live_one/strip_replay.py`): blanked vendor /
  catalog / dilution / clone in the stored reviewed claims and replayed them on contexts rebuilt with the
  current builder. Recovered 92 values, 92 agree with the reviewed claims, 0 disagreements, 0 fills where
  the reviewed claim was empty; abstained on 24/60 (STAT3 paper), 5/60 (SMG paper), 99/100 (co-IP paper,
  whose methods list many antibodies in one sentence). Agreement with reviewed claims, not accuracy.
- Final-code checks on the restarted stack: demo_check 19 PASS / 2 WARN / 0 FAIL; step-9 rehearsal
  (4455 valid 0.5-0.6 / 1.0 / 0.3 / 0.0 / 0.0-0.1 / 0.3; beta-actin pairing warning; 4686 refused) all
  requests 200 (the only 4xx in the tab were the deliberate probes); /experimental/research opens an
  already-extracted paper with 17 LIVE · UNREVIEWED cards and a working evidence panel. CI green on adfcf81.
- In progress: read-only paper-QA grounding/citation attack child.
- Live-ingestion row conversion on today's code: rebuilt records for the three reviewed papers convert to
  475 rows (the reviewed corpus count), all JSON-safe, carrying model_target / deterministic /
  figure_caption / methods / image source types through the provenance JSON. CI green on 06cb4ff.
- Paper-QA grounding attack (read-only child, mocked DB + model) confirmed five defects in
  `api/app/experimental/ask.py`, all fixed in `d056c83` with 7 regression tests (each failed on the old
  code): (D1) record fields were interpolated raw, so a newline + "[E1] ... QUESTION: ..." in a field
  forged a record and a question; fields are now folded to one line with `[]<>` neutralised inside
  `<record ref>` tags and the system prompt says record text is data. (D2) a reviewed-table or guard
  failure was reported as "No matching evidence"; it is now "Retrieval failed" (live-table failure still
  tolerated). (D3) capitalised prose ("Show", "Compare") became AND terms; dropped, and single-capital
  words (Akt) go last so back-off drops them before proteins. (D4) a question with no filterable term
  ran an unfiltered SELECT over the whole table; now no query. (D5) `[E1, E2]` was not a citation and
  phantom refs (E0, E99) were silently ignored; grouped refs parse, phantom refs land in `invalid_cited`
  and the note; both answer renderers link grouped refs. Also: a non-string model reply was a 500;
  modification MISSING rendered "none stated" (reads as total protein), now "not stated"; rows without a
  stable_row_key merged on the "doi:" prefix.
- Open gap (not fixed, documented): citations are validated for existence only. A cited answer can still
  contradict the cited record's status (e.g. assert phospho-Ser727 while citing a CONFLICTING record);
  there is no per-claim status check. api 177 passed / 11 skipped; tsc and lint clean; the restarted local
  stack answers the STAT3 question with 12 blocks and no note, "Show GAPDH" returns the 5 GAPDH blocks.
- Browser: /experimental/ask "Is ERK phosphorylation settled in the IL-6 time course?" answered "Not
  settled ... [E2][E3]" on claude-sonnet-5 with no phantom citations. CI green on d056c83.
- `da0f5c9` search false positives (core search, not only experimental): '%MYC%' matched Rapamycin /
  Bafilomycin treatments, so MYC returned 90 local rows of which 4 were MYC. Terms of <= 4 characters that
  end in a letter now use `lower(col) SIMILAR TO '%term([^a-z]%)?'` (the guard rejects regex operators;
  SIMILAR TO needs no new allowlisted function). Local corpus, 31 short terms, both tiers: 336 off-target
  rows dropped, 0 lost whose name fields start with the term. Ceiling: left side is still substring
  (ERK matches PERK). demo_check 19 PASS / 2 WARN / 0 FAIL after the change.
- Second read-only attack child (experimental live / research / ingest routes and pages) found:
  DOI searched as substring terms (a truncated DOI showed another paper's 384 rows; '(00)' parsed as a
  Ser92 site; '_' stripped), failures rendered as empty lists, stale responses landing on a newer
  selection in the research page, 500 on an oversized record id, DELETE without the ingest DB = 500,
  deleting a running job, job status 404 after an API restart, invalid JSON to proxies = 500. Held: auth
  on every route, key never reaches the browser, proxy paths allowlisted, no SQL injection, live rows
  badged everywhere, Valency/PMC failures surfaced.
- `e4936f3` API side: a DOI (bare, doi:, doi.org URL) is extracted first and filtered exactly; every
  DOI in both local tiers returns exactly its paper's rows. Record ids bounded to bigint on all record
  routes and densitometry / feedback bodies (422, was 500). DELETE job: 503 without ingest DB, 409 while
  running. Job status falls back to persisted jobs. api 182 passed / 11 skipped. Browser: truncated DOI
  -> 0 rows (was another paper's 384), doi.org URL in capitals -> the paper's 384 rows, main search MYC
  -> 8 rows (BEX2 co-IP + MYC), oversized record id -> 422.
- `035bbb1` web side (implementation child, reviewed and adjusted by the lead): request tokens on the
  research page (rows, extraction start, job poll, ask) and live page (live-tier search); visible alerts
  for failed live-papers listing, record load, paper search and extraction start; job poll stops on 404
  or after ~10 s of backend errors (the child's version failed the job on one transient error; changed);
  all seven experimental proxies answer invalid JSON with 400 (the lead extended the child's three to
  densitometry, pair, preview and ask). Browser: opening two papers back to back shows only the second
  paper's rows/scope/count; with the API stopped the research page alerts "Could not list
  already-extracted papers: Failed to reach backend" and the live page alerts "Live tier search failed".
  tsc and lint clean. API restarted on HEAD: demo_check 19 PASS / 2 WARN / 0 FAIL. CI green on d056c83,
  da0f5c9, e4936f3.
- Third read-only attack child (main search, evidence panel, feedback) confirmed: (1) the web proxy sent
  no limit, so results were cut at 100 lane rows mid-experiment with no notice ("loading control" 175
  rows -> 100, one card 2 of 5 lanes); (2) vendor + catalog found only numeric catalogs (Sigma A1978,
  abcam ab108629, Santa Cruz sc-398486, 5174s all 0 rows); (3) notation gaps (pSTAT3, beta-actin,
  SQSTM1, ERK1/2, 4E-BP1) and `_esc` stripping kappa/alpha ("IκBα" -> "ib", matching -ib drug names);
  (4) "STAT3 expression" 0 rows, "T24" parsed as Thr24, "HEK 293 CST" / "CST 1:1000" parsed as
  catalogs; (5) main search page had no stale-response guard; (6) /api/search and /api/feedback gave
  502 for invalid JSON, a NUL byte in feedback passed validation and fails in Postgres, and a record_id
  with another record's stable_row_key was accepted and rehydrated on both records. Held: DOI rule, site
  notation, short-symbol rule, CONFLICTING rows included and badged, MW always labelled expected,
  categorical bands, review reasons present.
- Fixes (this block): the proxy asks for 500 rows and the API drops the trailing partial experiment and
  returns `truncated`, shown as a note on the page; a catalog is read only directly after a vendor (any
  "ab"/"sc-"/letter prefix and suffix), `antibody_catalog_number` is a term column, dilutions are not
  terms; T24/Y79 stay terms; letters of any script survive `_esc`; expression/level/protein/knockdown
  words are stopwords; search page request token (implementation child); proxies 400 on invalid JSON;
  feedback rejects NUL and mismatched record keys; rehydration matches a keyed row only by its stable key.
  Local corpus: Sigma A1978 50, abcam ab108629 31, Santa Cruz sc-398486 53, 5174s 31, CST 9145 18,
  STAT3 expression 59, CST 1:1000 no catalog filter. Not fixed (synonym expansion would be a new
  feature): pSTAT3 / beta-actin / SQSTM1 / ERK1/2 / 4E-BP1 notation gaps, and protein terms matching
  treatment text ("MEK/ERK inhibitor") by design.
- `8cd3f88` verification: api 186 passed / 11 skipped; DB access matrix 11 passed against the local
  scratch Postgres (`HIVE_DB_TEST_URL` from `scripts/local_db.py test-url`); the new rehydration WHERE
  clause run on real Postgres inside a rolled-back transaction: record 42 + its key gets keyed + legacy
  rows, record 42 with a different (reseeded) key gets only the legacy row, a caller without a key
  matches by id, a key follows its record to a new id. Browser: /search?q=loading control shows
  "Found 30 experiments (175 lane records)" (was 100 rows), no console errors; demo_check 19 PASS /
  2 WARN / 0 FAIL. (CI on 8cd3f88 was cancelled by the next push; ec395b9 and later carry it.)
## Final pre-demo hardening window (2026-09-15 16:00-19:00 PT), from 811e94c

- Track A (paper-QA status grounding, `cb4caeb`): citations were checked for existence only. `status_warnings()`
  now compares each sentence's wording with the structured statuses of the records that sentence cites and
  adds a labelled note (lexical, not a verification): CONFLICTING/AMBIGUOUS stated as settled; a supported
  phosphorylation denied, or a phosphorylation no cited record holds; a not-stated modification called
  total/unmodified; certainty words on a needs-review record; a sentence naming a target only uncited
  records carry; intensity/regulation language; live records cited without the word "unreviewed". Nine
  adversarial fixtures + faithful-answer fixtures in api/tests/test_experimental_ask.py. On six real
  claude_cli answers to the demo questions it raised zero warnings. NOT detectable and documented: partial
  support inside one sentence. Also: evidence blocks no longer fall back to legacy `western_blot_type`,
  which reads "total_protein" for any non-phospho row (a MISSING modification would have reached the model
  as total protein).
- Model output was being shaped by the operator's own Claude Code user settings (`85b20b2`): a user-level
  output-style hook turned paper-QA answers into clipped non-grammatical prose ("E1 mark modification
  CONFLICTING"). `claude -p` now runs with `--setting-sources project` (login unaffected, unlike `--bare`);
  demo_check's probe too. A/B on the production call path confirmed normal prose after the change, and the
  image path still reads a crop through the Read tool (all six printed row labels recovered).
- Track B (search false positives, read-only child): 106 symbol-table runs over both tiers (475 reviewed +
  861 live rows), 1975 on-target vs 326 off-target matches. Every off-target row is a symbol named in
  treatment / context / sample / catalog text (design), not a symbol matched inside a longer word: "MEK/ERK
  inhibitor U0126", "siATG5", "siBEX2#1", "LC3B siRNA", "Bisindolylmaleimide II", catalog "ab108629".
  A left-boundary rule removes 0 of them and loses 0 on-target rows, cannot separate pERK from PERK under
  lower(), and would newly drop KRAS/BRAF/siMYC. Decision: documented as a limit in `_term_clause`, no code
  change. KIT/MET/RAF/RB/VHL/JUN/FOS/RAS/p53/PTEN/mTOR/GSK3/CDK1 match no rows at all in this corpus.
- Track E (provenance sweep, read-only child): 93 records, 2931 sources, 475 flattened rows rebuilt from
  stored claims with current code. 0 violations: caption sources verbatim in caption (307), methods sources
  verbatim after dash folding only (40, all U+2011 artefacts), image sources quote lane labels or the
  model's band notes, no model reading typed as caption/methods, CONFLICTING/AMBIGUOUS keep candidates and
  null scalars, expected MW only from UniProt, bands categorical. Determinism: two in-process rebuilds and
  PYTHONHASHSEED 0 vs 1 subprocesses identical; record_id sets equal the stored sets (20/20, 20/20, 53/53);
  475 stable_row_keys identical and unique per (record, lane).
- Regression found by Track E and fixed (`afc9f19`): the "caption" channel is the retrieval's figure-text
  section, which on PMC12706926 is the same results paragraph for 11 of 15 panels. Its one
  "Immunoprecipitation (IP) assays with either PIK3CA or BEX2" sentence classified 47 expression records as
  co_ip and set ip_bait_protein to "IP". co_ip now settles only on panel evidence (IP-role antibody, or
  co-IP / IP: / IgG markers printed on the lanes); caption-channel wording joins methods-only wording as the
  non-settling co_ip_context flag, and the bait lookup skips IP/IB/WB/IgG/input/WCL. After the fix the
  co-IP paper rebuilds to exactly the stored records: 6 co_ip, bait PIK3CA, 0 records differing on
  (experiment_type, bait). Benchmark unchanged at 34/34. The stored demo DB was never affected (it is
  loaded from the stored records); a LIVE extraction would have reproduced the error.
- Track D (bounded local fuzz): 631 requests over the web proxies and the API (empty/invalid JSON, null
  fields, oversized and negative ids, huge strings, NUL and control characters, malformed lane arrays and
  regions, mismatched labels, malformed DOIs, Unicode biology text, dash variants, Greek symbols, empty
  terms) plus 33 malformed-image and geometry cases (truncated PNG, header-only, GIF/SVG/PDF bytes, 1x1,
  1x4000, RGBA, 16-bit TIFF, inverted/zero-area/NaN regions, reversed and overlapping lane bounds, 400
  bounds, label/bound mismatch, lanes 0 and 1000, band_row 1e9, pair geometry mismatches): zero 5xx, all
  rejected as 400/422. Note for anyone re-running this: `api/.env`'s INTERNAL_API_KEY is NOT the key the
  demo launcher uses (it takes it from `.env.cloud`, same as the web proxy), so direct API calls with the
  former return 401.
- Track F (export / reproducibility, read-only child): rebuilding a request from the exported JSON alone and
  re-POSTing gives 0 diffs for the valid 4455 strip, the beta-actin warning, the 4686 refusal and the
  target/control pair (image sha256, region, lane bounds, band row, method + version, thresholds, per-lane
  values, quality, refusal reasons all identical). CSV formula injection is impossible for the OWASP set
  (`=`, `+`, `-`, `@`, tab, CR, DDE `=cmd|...` all prefixed with `'`; leading-space and Unicode-minus
  variants are inert in Excel / LibreOffice / Sheets); refusal rows carry empty relatives with the clipping
  reason intact. Overlay PNG geometry matches the returned lane bounds and band row with 0.00 px centre
  offset (max 1 px anti-aliasing).
  Three real gaps, two fixed here: (G2) a diagnostic equal-width measurement replayed from its export as
  explicit lanes and its quality rose warning -> ok; (G3) the stability flag was not exported, so a replay
  could warn or refuse where the original did not; both fixed by echoing the request in the response
  (`result["request"]`, image bytes excluded) - verified on the live stack, the diagnostic case now replays
  identical including lane_mode, band row and the diagnostic warning. (G1b) a TIFF is measured through its
  PNG preview, so the export held no hash of the researcher's own file: the page now keeps
  `uploaded_file: {name, source_sha256}`. (G1, documented not fixed) an upload's bytes are not in the
  export, so an upload is only reproducible if the operator keeps the file; the export now at least names
  it and carries both hashes.
- Same cap defect in paper QA: `_rows_for` capped rows at 300, so a paper-scoped question on a 384-row
  live paper handed the model a partial lane strip for the last experiment. The partial trailing
  experiment is now dropped there too (shared `_experiment_key`); regression test; api 187 passed.

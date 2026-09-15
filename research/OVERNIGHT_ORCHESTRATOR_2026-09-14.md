# HiveBlot overnight orchestrator — densitometry-first push — 2026-09-14 → 2026-09-15

**Target ship:** Wednesday, 2026-09-16  
**Single active working branch for this push:** `experimental/ucsf-demo-2026-09-09`  
**Primary objective:** make the next UCSF package feel like a meaningful product step, led by a real first-generation experimental densitometry workflow, while fixing the two highest-leverage biology plumbing issues and simplifying the repository around one active integration branch.

This brief is intentionally aggressive. It should use roughly 80% of one active five-hour Claude window on useful work and preserve ~20% for Nik's review/fixes. It is not permission to fabricate scientific confidence, silently mutate the reviewed corpus, or deploy irreversible production changes.

---

## 0. Wednesday win condition

By Wednesday, HiveBlot should no longer feel like several disconnected experiments living on several branches.

The package should demonstrate one coherent product with multiple routes:

- `/search` — reviewed reference corpus / trust anchor.
- `/experimental/research` — live paper discovery + extraction + paper-scoped QA.
- `/experimental/densitometry` — experimental relative densitometry on a researcher-selected blot region and researcher-defined lanes.
- `/experimental/ask` and `/experimental/live` may remain as diagnostic routes, but `/experimental/research` is the preferred live-research surface.

The Wednesday package should show four concrete forms of progress:

1. **Densitometry actually starts becoming a product.** A researcher can select the relevant blot strip, define lanes, get deterministic relative measurements from the same strip, see quality/refusal checks, and export enough method metadata to reproduce what happened.
2. **Biology extraction gets safer.** Fix B-1 and B-2: preserve real figure-caption evidence separately from methods, and use the existing deterministic antibody parser as a safe backstop when the model omitted antibody identity.
3. **Repository/architecture gets simpler.** One active development/integration branch; experiments live primarily behind routes, not long-lived per-feature branches.
4. **The UCSF feedback package is build-ready.** External Tally spec + distribution plan are reviewed, not reinvented.

The journal-access/paywall indicator is explicitly deferred. See `tickets/journal-access-later.md` once present. Do not spend this overnight window on it.

---

## 1. Read order and authority

Read only what is needed to execute:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `HANDOFF.md`
4. `meeting_notes`
5. `tickets/densitometry.md`
6. `tickets/bio-qa.md`
7. `tickets/feedback.md`
8. `tickets/tally-ucsf-beta-feedback.md`
9. `tickets/ucsf-beta-distribution.md`
10. this file

Then inspect the actual current code before assuming any ticket still describes current behavior exactly.

Historical research docs are reference material, not a new backlog. Open them only when they can change an implementation or validation decision.

---

## 2. Important current-state facts — do not waste the night rediscovering these

### Branch graph

As of this plan, `experimental/ucsf-demo-2026-09-09` already contains the histories of:

- `experimental/densitometry`
- `experimental/paper-qa`
- `experimental/valency-live-ingest`
- `experimental/demo-day`

Do **not** merge those branches again. Treat them as historical branch pointers.

`feature/bio-context-beta` has diverged with one unique HANDOFF-only commit relative to the current UCSF branch. Inspect whether its information is already represented; port only useful current-state documentation, not the whole branch.

`copilot/fix-whitespace-and-secret-scan` has a small unique change relative to stale `main`; inspect the exact `api/conftest.py` delta and re-implement/cherry-pick only if it is still relevant. Do not merge stale `main` into the active branch.

### Valency — what it is and what it is not

Valency is **paper discovery**, not HiveBlot's biology engine and not the extraction model.

Its job is:

`research topic -> candidate papers/DOIs -> open-access resolution -> HiveBlot extraction`

The current live-research path already has Valency integration plus PubMed Central fallback. If a Valency token is absent or Valency is unavailable, PMC discovery still works. The Valency contract was already live-smoked previously.

Therefore:

- do not create a new Valency workstream tonight;
- do not block densitometry or biology work on Valency;
- keep Valency on `/experimental/research` as the preferred discovery source when available;
- only touch Valency if a current regression blocks the research route.

---

## 3. Branch convergence and repository structure

Nik wants fewer experiments-as-branches. Adopt this operating model:

### One active branch

For this push, work directly on:

`experimental/ucsf-demo-2026-09-09`

Do **not** create a new branch per feature or per sub-agent tonight unless there is an actual concurrent-human conflict that requires isolation.

At the end of the run:

- `HANDOFF.md` must explicitly name this as the one active development/integration branch for the Wednesday package;
- old experimental branch names should be described as historical/archival, not places new work should land;
- produce a branch-cleanup recommendation listing which old refs are safe to delete later after Nik reviews them;
- do not delete shared branches automatically during this overnight run.

### Experiments live behind routes

New experiments should default to route-level isolation, not branch-level isolation:

- frontend: `web/app/experimental/<experiment>/`
- server proxy: `web/app/api/experimental/<experiment>/`
- backend: `api/app/experimental/`
- scientific/algorithm module: `western_blot_miner/`
- reproducible experiment outputs: `research/experiments/`
- active tickets: `tickets/`

This keeps Vercel capable of exposing multiple experimental workflows from one coherent deployment/preview branch.

### Repository-improvement pass

Agent R should identify obvious structural debt that directly slows execution: duplicated current-state docs, misleading historical instructions, stale route names, dead experimental navigation, or tests that no longer map to the product surface. Fix only low-risk/high-leverage items. Do not perform a mass file move or documentation purge during the 80% window.

---

## 4. Usage governor — aggressive, adaptive, no fake precision

Nik wants approximately 80% of a five-hour Claude window used on useful work.

If first-party usage telemetry is available, record it and re-check after major phases. If not, use roughly four active hours as the proxy and say clearly that exact percentage could not be verified.

Suggested checkpoints:

- **~15% used:** branch/repo audit complete; densitometry implementation already underway.
- **~35%:** densitometry wiring + first quality gate working with narrow tests.
- **~50%:** densitometry UI/API/algorithm path integrated; B-1/B-2 underway or complete.
- **~65%:** validation/stability work + repository convergence + packaging.
- **~72%:** scope freeze. No new product track.
- **~78%:** stop spawning sub-agents; integration, QA, docs, test matrix only.
- **~80%:** stop model-intensive work; finish deterministic tests/commit/handoff.

Never burn tokens just to hit a meter.

---

## 5. Orchestration topology

Use **one primary orchestrator + four execution leads + one adversarial reviewer**. Keep recursion bounded: a lead may spawn at most two focused children when parallel work is genuinely independent, and children do not recursively create a swarm.

The orchestrator owns branch state, scope, usage, integration, and the next-task decision.

Expected effort weights are guidance, not quotas:

- **D — Densitometry:** 45–50%
- **B — Biology QA:** 20–25%
- **R — Repo/integration/structure:** 10–15%
- **P — Packaging/feedback:** 5–10%
- **Q — Adversarial review:** ~10%

After every meaningful checkpoint, the orchestrator asks:

1. What completed work most increases Wednesday demo value?
2. What is the highest-risk scientific or integration failure still open?
3. Given remaining usage, should we deepen densitometry, fix biology, simplify integration, or stop adding scope?
4. What would a UCSF researcher distrust immediately if we demoed right now?

The answers determine the next task; do not mechanically execute every ticket.

---

## 6. Lead D — experimental densitometry (highest priority)

This is the main push.

### Product framing

The route and product may be called **Experimental densitometry**. Be precise about what the current version measures:

- pixel-derived, background-corrected integrated signal;
- relative **within one selected published figure strip**;
- no physical units;
- not comparable across separate images/exposures;
- not automatically equal to protein quantity;
- not loading-control-normalized unless a future explicit pairing/normalization feature exists.

Do not retreat to presence/absence only. We are starting densitometry. The scientific safety feature is that the system must refuse or downgrade measurement when the pixels cannot support a defensible relative read.

### D0 — make the existing path honest and controllable

1. **Fix region propagation end-to-end.** The current Next proxy destructures `record_id`, `live`, `image_base64`, `lanes`, `row_index` and drops `region`; fix the UI -> Next route -> FastAPI -> analyzer contract and test it.
2. **Add explicit lane-boundary input**, not only a lane count. Researcher-defined x boundaries should be first-class. Equal-width slicing may remain a diagnostic fallback, not the default researcher path.
3. Ensure returned coordinates map correctly back to the full image after a selected region is used.

### D1 — define the first real measurement contract

Current algorithm already does grayscale/inversion, morphological-opening background estimation, corrected signal, band-row selection, and integrated corrected intensity.

Turn that into a documented API contract rather than a demo number dump:

Per lane return at minimum:

- lane index/name when supplied;
- x bounds + selected y/band bounds;
- raw integrated signal;
- estimated background contribution;
- background-corrected integrated signal;
- relative signal inside the same strip;
- saturation/clipping diagnostics;
- measurement quality/refusal state;
- method/version metadata.

Do not round to presentation-friendly pseudo-precision before stability is understood.

### D2 — quality gates and refusal states

Implement deterministic quality checks before showing a quantitative-looking result.

At minimum test:

- clipping/saturation in the selected band area;
- effectively no signal above estimated background;
- invalid/tiny selected region;
- overlapping/reversed/impossible lane bounds;
- lane bounds that extend outside the selected region/image;
- unstable measurement under small reasonable boundary perturbations when D3 is available.

Use explicit states such as:

- `ok`
- `warning`
- `quantification_refused`

If refused, do **not** return/display a normalized quantitative ratio as though valid. Return the reason and diagnostics.

Thresholds must be tied to reproducible fixtures/experiments. Do not invent a magic cutoff and call it scientific.

### D3 — repeatability / sensitivity envelope

The next major credibility step is to answer: **if the researcher moves the box slightly, does the conclusion survive?**

Build a deterministic perturbation study around selected region/lane boundaries. Choose the perturbation scale based on image dimensions and documented rationale; do not hard-code arbitrary pixel jitter without checking crop sizes.

Report a sensitivity envelope/range (e.g. min/median/max or equivalent deterministic stability summary), not a statistical confidence interval unless there is an actual statistical model.

Use this to suppress false precision and to flag lane rankings that flip under tiny geometry changes.

### D4 — researcher-facing workflow on `/experimental/densitometry`

Target interaction:

1. choose/load a HiveBlot crop or upload an image;
2. draw/select the blot strip;
3. define lane boundaries visually;
4. optionally label lanes;
5. run analysis;
6. show per-lane relative signal + quality state + warnings;
7. overlay selected region/lane boundaries so the researcher can verify geometry;
8. export JSON, and CSV if low-cost, including method/version/region/bounds/quality diagnostics.

The page should make it obvious whether the result is:

- a valid within-image relative measurement;
- a warning/unstable measurement;
- refused because the image is clipped/invalid.

### D5 — validation ladder

Do not judge this feature by whether the graph looks plausible.

Run progressively stronger checks:

1. **Synthetic fixtures with known signal ratios/order** — verify recovery direction and rough proportional behavior.
2. **Geometry perturbation** — measure sensitivity to region/lane changes.
3. **Reviewed real crops** — primarily identify/refuse clipping and geometry failures; do not call the reviewed categorical band labels densitometry ground truth.
4. **Public dilution-series/source-data benchmark** if a usable one can be located quickly from existing repo research or primary literature. If not available, leave a precise benchmark task rather than fabricating validation.

Retire the old `59.7%` D1 number as a quality metric. It compared an immature automatic-placement system against categorical band presence and is not a defensible densitometry score.

### D6 — future, not required before Wednesday

Only after D0–D5 are stable:

- loading-control pairing;
- target/loading-control normalized ratios;
- raw-source-data calibration;
- cross-image normalization;
- storing quantitative measurements in a dedicated artifact model.

Do not silently put these values into the existing reviewed Evidence Record intensity columns.

### Densitometry child agents

If useful, Lead D may spawn at most two children:

- **D-A Algorithm/validation:** metrics, quality gates, synthetic/stability tests.
- **D-U UX/API integration:** region/lane editor, proxy/API contract, overlays/export.

They must not edit the same files concurrently without explicit partitioning.

---

## 7. Lead B — biology QA: B-1 and B-2 only until they are green

### B-1 — caption/methods separation

**What it means:** the live extraction path currently collapses source context so the biology layer can receive an empty figure caption while caption text is effectively carried under methods. That disables the intended evidence hierarchy and can mislabel provenance.

Goal:

- real figure legend/caption text reaches the caption channel;
- methods text remains methods;
- source snippets labeled `figure_caption` are actual source text, not model paraphrase;
- tests prove the distinction survives the live extraction path.

### B-2 — deterministic antibody backstop

**What it means:** the repo already has deterministic antibody parsing, but the live record-building path does not consistently call it when the model leaves vendor/catalog identity empty.

Goal:

- if the model returned no antibody identity and target-scoped source text contains a deterministic antibody match, recover it;
- preserve deterministic provenance;
- never overwrite an existing model/source value;
- never silently settle a conflict;
- test empty-model recovery + non-overwrite + conflict behavior.

After B-1/B-2 pass, return effort to densitometry unless a regression blocks the research route.

B-3/B-7/B-8/reseed remain deferred unless the orchestrator has completed all Wednesday-critical work and still has useful budget.

---

## 8. Lead R — integration, branch convergence, and repository improvement

Lead R runs an early audit and a final integration pass.

### Early audit

Record:

- current HEAD;
- current uncommitted work;
- branch graph;
- which historical experiment branches are fully contained in the active branch;
- the one unique `feature/bio-context-beta` documentation delta;
- the small `copilot/fix-whitespace-and-secret-scan` delta;
- current route map;
- current test baseline.

Create/update:

`research/overnight/2026-09-14-session-log.md`

### Single-active-branch outcome

By end of run, document:

- `experimental/ucsf-demo-2026-09-09` = active integration branch for Wednesday;
- `experimental/densitometry`, `experimental/paper-qa`, `experimental/valency-live-ingest`, `experimental/demo-day` = historical branch pointers already contained by active branch;
- whether the beta/copy/security unique deltas were ported or intentionally left out;
- recommended branches Nik can delete/archive after review.

Do not merge stale branches just to make the branch list look clean.

### Route architecture check

Ensure experiments remain reachable from one Vercel preview/deployment through routes, with a coherent experimental nav. Prefer route isolation over branch isolation.

### Small repo-quality fixes

Fix only things that directly reduce confusion or broken CI: stale active-branch instructions, a known false secret-scan fixture, misleading route naming, or duplicated current-state claims. No giant reorganization tonight.

---

## 9. Lead P — packaging and researcher feedback

This is deliberately lighter than densitometry.

Review, do not rebuild:

- `tickets/tally-ucsf-beta-feedback.md`
- `tickets/ucsf-beta-distribution.md`

Acceptance:

- normal path under ~5 minutes;
- captures usefulness/workflow fit/trust, not just bug reports;
- wrong extraction path captures public DOI/figure/field/expected value;
- asks for public evaluation papers when appropriate;
- no request for unpublished/confidential data;
- optional follow-up contact is explicit opt-in;
- distribution favors multiple UCSF labs/roles through warm referrals.

Existing in-product feedback remains the field/record-level correction layer. Tally is the session-level evaluation layer.

Journal-access/paywall UI is deferred and must not steal this budget.

---

## 10. Lead Q — adversarial scientific/product review

Run after the main integration pass. Do not build a new feature unless fixing a P0/P1 finding.

Attack the current product:

### Densitometry

- Can a saturated black band still receive a clean-looking ratio?
- Can moving the region a few pixels flip the ranking without a warning?
- Can lane boundaries overlap or drift between browser and API coordinates?
- Does auto-lane behavior accidentally remain the default?
- Are values being compared across different images?
- Does the UI imply protein amount rather than within-image pixel signal?

### Biology

- Can caption text still arrive as methods?
- Can deterministic antibody recovery overwrite stronger evidence?
- Can model paraphrase masquerade as a source quote?
- Can `LIVE · UNREVIEWED` look reviewed?

### Repo/product

- Did a sub-agent create another long-lived feature branch unnecessarily?
- Do current docs disagree about the active branch or routes?
- Did Valency accidentally become a blocker despite PMC fallback?
- Did any page start implying unseen-paper extraction accuracy?

Return P0/P1/P2. Fix P0/P1 or explicitly mark the Wednesday package PARTIAL/BLOCKED.

---

## 11. Dynamic priority stack

### P0 — must dominate the 80% window

1. D0 region propagation.
2. D0 researcher-defined lane boundaries.
3. D1 explicit densitometry measurement contract + method metadata.
4. D2 saturation/clipping + invalid-measurement refusal.
5. D4 integrated `/experimental/densitometry` workflow.
6. B-1 caption/method separation.
7. B-2 antibody backstop.
8. integration tests + adversarial review.

### P1 — deepen the product once P0 is green

1. D3 geometry sensitivity/ranges.
2. D5 stronger validation fixtures/benchmark search.
3. D4 JSON/CSV export and UX polish.
4. branch-convergence documentation + low-risk repo/CI cleanup.
5. Tally/distribution final polish.
6. stale L1/report cleanup if still relevant.

### P2 — defer unless everything above is genuinely done

- loading-control normalization;
- cross-image quantitative comparisons;
- quantitative storage schema;
- reviewed-corpus reseed;
- broad schema expansion;
- escalation redesign;
- sample/tissue routing;
- journal/paywall-access indicator;
- production deployment;
- unseen-paper accuracy claims.

---

## 12. Evaluation gates

### Densitometry gate

Required before calling it Wednesday-ready:

- region round-trip test;
- explicit lane-boundary contract test;
- coordinate correctness with cropped regions;
- synthetic known-order/known-ratio behavior test;
- saturation/clipping case that refuses quantitative output;
- no-signal/invalid geometry cases;
- at least one real reviewed crop that demonstrates a valid warning/refusal path;
- sensitivity envelope if D3 lands;
- web typecheck/lint/build for changed UI;
- API/miner tests for changed code;
- exported method metadata identifies algorithm/version/region/lane bounds/quality state.

### Biology gate

- real caption reaches caption channel;
- methods remains methods;
- source text is real source text;
- deterministic antibody recovery fills only missing identity;
- existing/conflicting identity is not overwritten;
- relevant biology/record-builder/pipeline tests green.

### Integration gate

- `git diff --check`;
- required test suites green or source-branch failure reproduced/documented;
- no secrets/generated junk;
- one active working branch identified;
- route map documented;
- no production mutation;
- Q review complete.

---

## 13. Stop-time deliverables

Leave Nik with:

1. the strongest tested densitometry implementation achievable within the window;
2. B-1/B-2 landed if feasible;
3. one coherent active branch with route-based experiments;
4. reviewed Tally/distribution specs;
5. `research/overnight/2026-09-14-session-log.md`;
6. `research/overnight/2026-09-14-summary.md` containing:
   - densitometry state and exact limitations;
   - what changed in biology accuracy;
   - active branch + route map;
   - test commands/results;
   - commit SHAs;
   - what is Wednesday-ready;
   - what Nik must manually do Tuesday/Wednesday;
   - P0/P1/P2 remaining work;
7. updated `HANDOFF.md`;
8. pushed commits on `experimental/ucsf-demo-2026-09-09`.

Do not deploy production automatically.

---

## 14. Final report format

```text
STATUS: COMPLETE / PARTIAL / BLOCKED

USAGE:
- Start:
- End:
- Exact usage telemetry available? yes/no
- Review reserve preserved:

ACTIVE BRANCH:
- Branch:
- Start SHA:
- End SHA:
- Historical branches confirmed contained:
- Unique deltas still outside active branch:

DENSITOMETRY:
- Region selection:
- Lane definition:
- Measurement method:
- Quality/refusal gates:
- Stability/range:
- UI route:
- Export:
- Validation completed:
- Known scientific limitations:

BIOLOGY QA:
- B-1:
- B-2:

VALENCY / LIVE RESEARCH:
- Current status:
- Any regression touched? yes/no

PACKAGING:
- Tally spec:
- Distribution spec:

TESTS:
- command -> result

ADVERSARIAL REVIEW:
- P0:
- P1:
- P2:

WEDNESDAY-READY:
- ...

NIK MANUAL ACTIONS:
1. ...

DEFERRED:
- journal/paywall access indicator
- ...

NEXT BEST TASK:
- ...
```

A coherent, tested partial implementation beats five unfinished experiments.
# HiveBlot overnight FABLE orchestrator — 2026-09-14 → 2026-09-15

**Target ship:** Wednesday, 2026-09-16  
**Working source:** `experimental/ucsf-demo-2026-09-09`  
**Overnight goal:** convert the current post-UCSF plans into a tested, reviewable Wednesday package while preserving biological validity and ~20% of the active Claude five-hour usage window for Nik's next-day review.

This is the primary overnight execution brief. It is not permission to deploy production, reseed the reviewed corpus, or invent scientific ground truth.

---

## 0. Start here — authority and read budget

Read in this order:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `HANDOFF.md`
4. `research/OVERNIGHT_SOURCE_MAP_2026-09-14.md`
5. `meeting_notes`
6. `tickets/README.md`
7. `tickets/feedback.md`
8. `tickets/densitometry.md`
9. `tickets/bio-qa.md`
10. `tickets/tally-ucsf-beta-feedback.md`
11. `tickets/ucsf-beta-distribution.md`

Then stop broad reading and execute.

Do **not** ingest every file in `research/` at startup. Many August delegation/QA documents are historically useful but superseded as current task lists. Open a Tier 2/3 document from `OVERNIGHT_SOURCE_MAP` only when it can change a concrete implementation or validation decision.

Before any edit, verify branch/HEAD and whether a ticket was already implemented after it was written.

---

## 1. Mission

By stop time, leave Nik with a **tested Wednesday package**, not a pile of prototypes.

Highest-value outcomes:

1. **Band reading:** improve the existing experimental path until it behaves like a defensible research aid: researcher-defined region/lanes, saturation/clipping refusal, honest uncertainty, no fake calibrated quantitation.
2. **Biological QA:** land the highest-leverage extraction-plumbing fixes already identified in `tickets/bio-qa.md`, especially caption/methods separation and deterministic antibody recovery, with provenance-safe tests.
3. **Feedback readiness:** review/polish the already-created Tally spec and multi-lab distribution plan; do not rebuild them from scratch.
4. **Integration:** clean commits, exact tests, adversarial QA, and a concise Tuesday/Wednesday handoff.

Latest binding product context comes from `meeting_notes`: a structured feedback form and the band-reading/densitometry direction were promised for the next Wednesday follow-up.

### Product vocabulary

Until real calibration exists, user-facing language is **Band reading (experimental)**, not calibrated densitometry.

A refusal is a valid successful result when pixels cannot support quantification.

---

## 2. Non-negotiables

Repository rules in `AGENTS.md` and `HANDOFF.md` win over this file.

In particular:

- biological validity is priority #1;
- never infer phosphorylation from a protein-name prefix;
- a model claim is not ground truth;
- `CONFLICTING` never silently picks a winner;
- missing source evidence never becomes a guessed value;
- expected MW ≠ observed/reported MW;
- band presence ≠ densitometry;
- reviewed and `LIVE · UNREVIEWED` tiers stay visibly distinct;
- the reviewed 475-row corpus is not silently reseeded tonight;
- agreement with the reviewed corpus is not unseen-paper accuracy;
- no secrets in commits/docs/logs;
- no AI co-author trailers;
- no production deploy or irreversible production DB change in this run.

Do not touch `main`.

---

## 3. Branch protocol

From the newest remote UCSF demo branch:

```bash
git switch experimental/ucsf-demo-2026-09-09
git pull --ff-only
git switch -c overnight/ucsf-2026-09-14
```

If that task branch already exists, inspect it first; do not recreate or overwrite it.

Use coherent commits by track. Never force-push shared history.

At the end, update `HANDOFF.md` according to repository rules and push the task branch.

---

## 4. Usage governor — target 80%, preserve 20%

Nik wants roughly **80% of one active five-hour Claude usage window consumed on useful work**, leaving ~20% for review/fixes.

This is a **ceiling + target**, not an instruction to waste tokens.

### If first-party usage telemetry is available

At startup, record:
- current usage/remaining allowance;
- the estimated 80% stop point;
- whether the five-hour window reset time is visible.

Re-check after every major phase.

Operational checkpoints:

- **~15–20% used:** recon complete; first implementation underway.
- **~35–40%:** at least one P0 track implemented + narrow tests green.
- **~55–60%:** both core engineering tracks should be active or one should be clearly blocked; stop general exploration.
- **~70–72%:** scope freeze. No new feature track.
- **~77–78%:** stop spawning sub-agents; integration, tests, adversarial review, docs only.
- **80%:** stop model-intensive work. Finish deterministic commands already running, write handoff, commit/push.

### If exact usage telemetry is not available

Do not claim exact control. Use **~4 hours of active orchestration inside the five-hour window as the proxy**, preserve the remaining hour, and log that the 80% figure could not be verified.

Never burn context or run useless literature review just to hit 80%.

---

## 5. FABLE recursive loop

The orchestrator and every sub-agent repeat this loop until acceptance criteria are met, the next pass is lower-value than another track, or the usage governor freezes scope.

### F — Frame
Ask:
- What exact researcher/engineering problem am I solving?
- What is the smallest defensible Wednesday outcome?
- What scientific/product invariant could I accidentally violate?

### A — Audit
- Read the relevant ticket, code, tests, and **only** the research note needed for this task.
- Reproduce the current failure when practical.
- Distinguish code bug vs missing data vs missing validation vs misleading metric.
- Check whether an older Markdown finding was already fixed in `UCSF_BETA_READINESS.md` or later commits.

### B — Build
- Implement the smallest coherent improvement.
- Add/update tests in the same pass.
- Preserve provenance and abstention.
- Prefer removing a misleading output over polishing it.

### L — Learn
After each meaningful pass answer, briefly:

1. **How can this project/process be improved without adding complexity for its own sake?**
2. **How can this be more biologically accurate or scientifically honest?**
3. **What must I learn next, and what is the best primary source?**
4. **What is the highest-value next action given the remaining usage budget?**

Primary-source order:
- source paper figure/caption/methods/supplement;
- existing repo QA + reproducible fixtures;
- UniProt / NCBI/PMC/BioC docs;
- peer-reviewed methodology already catalogued by the repo;
- only then broader external material.

Do not turn `Learn` into unlimited research.

### E — Evaluate
- narrow tests first, then required broad suites;
- positive + abstention/conflict case for biology changes;
- clean + clipped/saturated + misboxed cases for band reading;
- happy + failure state for UI/API work;
- ask: **What would make a UCSF researcher distrust this output?**

Fix the highest-severity answer before recursing.

---

## 6. Sub-agent topology

Use sub-agents if supported; otherwise execute roles sequentially. The main orchestrator owns scope, git state, budget, and integration.

Never let two agents modify the same files concurrently.

### Agent R — Repo/release integrator

Owns:
- branch/commit map;
- whether Sept. tickets are still current;
- session log;
- integration and conflict resolution;
- final test matrix;
- final handoff.

Create:
`research/overnight/2026-09-14-session-log.md`

The first log entry should state authoritative HEAD, branch, existing uncommitted work, and current ticket reality.

### Agent D — Band-reading engineer

Read first:
`tickets/densitometry.md`

Then inspect the actual current code/tests before assuming the audit is still exact.

Priority:

1. **D-1** — forward researcher `region` end-to-end.
2. **D-2** — explicit researcher-defined lane boundaries on the user path; retire equal-width whole-crop slicing as the default user path.
3. **D-3** — saturation/clipping refusal gate on the actual band core.
4. **D-6** — honest refusal card + method metadata + JSON export, no DB storage.
5. **D-4** — uncertainty/ranges only if D-1..D-3 are stable and tested.
6. D-5 cleanup/study only if budget remains.

Rules:
- no loading-control-normalization claim;
- no DB write for measurements tonight;
- no two-decimal pseudo-precision on unstable values;
- no numeric ratio when saturated/clipped/unstable;
- old D1 `59.7%` is historical failure context, never a product-quality claim.

For algorithmic thresholds, cite the fixture/data/method that justifies them. Do not choose a magic number and call it scientific.

### Agent B — Biological QA engineer

Read first:
`tickets/bio-qa.md`

Priority:

1. **B-1** — restore real caption vs methods separation in the live extraction path.
2. **B-2** — deterministic antibody backstop in the record path when the model returned empty; never overwrite an existing/conflicting claim.
3. **B-6** — correct/delete stale L1 reporting.
4. **B-5** — existing `compare_records.py` three-repeat harness only if code is stable and budget remains.
5. B-4 measurement scaffolding only if the trusted panel inventory already exists.

Defer B-3/B-7/B-8 and reseeding unless all Wednesday P0 work is genuinely complete.

For each changed field verify:
- source type is correct (`figure_caption` vs `methods` etc.);
- verbatim source text is real source text, not model paraphrase;
- `SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING` semantics remain honest;
- no parser fallback converts paper silence into a value.

Historical QA (`independent_scientific_qa.md`) is valuable for **failure classes**, but its old counts/status are not current truth. Check the Sept. readiness report before resurrecting any old finding.

### Agent F — Feedback/product reviewer

Do **not** recreate the form. Review and improve:
- `tickets/tally-ucsf-beta-feedback.md`
- `tickets/ucsf-beta-distribution.md`

Use current Tally capabilities only if a form mechanic matters. Keep the form short and branch-heavy.

Acceptance:
- normal path under ~5 minutes;
- wrong-extraction path captures enough public-paper detail to reproduce;
- non-user/non-Western paths are short;
- hidden `ref/lab/cohort/beta_version/source` fields are coherent;
- no unpublished/confidential data requested;
- form separates product usefulness, biological corrections, and validation-collaboration signal;
- distribution strategy favors warm multi-lab referrals over cold-spam response count.

If specs are already good, stop quickly and return budget to engineering.

### Agent Q — Adversarial scientific/product reviewer

Runs after integration. Do not build major features.

Try to break the result:
- can clipped/saturated signal still produce fake-looking quantitation?
- can region/lane coordinate state desync across browser/proxy/API?
- can captions still be mislabeled as methods?
- can antibody recovery overwrite model/source disagreement?
- can a live row look reviewed?
- can a correction or form solicit unpublished data unnecessarily?
- are zero-result/coverage messages scoped honestly?
- did any doc/UI start implying unseen-paper accuracy?
- did any change remove provenance to simplify UX?

Return P0/P1/P2 findings. P0/P1 must be fixed or explicitly block completion.

---

## 7. Priority stack

### P0 — Wednesday-critical

1. D-1 region forwarding, with tests.
2. D-2 user-defined lane path, with API/UI contract tests.
3. D-3 saturation/clipping refusal, with no numeric output when refused.
4. B-1 caption/methods separation, with provenance tests.
5. B-2 deterministic antibody backstop, with non-overwrite/conflict tests.
6. Tally + multi-lab specs reviewed and build-ready.
7. integrated regression/adversarial review + founder handoff.

### P1 — only after P0 is green

- D-6 refusal/method/export UX.
- D-4 ranges / stability instead of point precision.
- F-1 feedback export script.
- F-2 zero-result search feedback capture.
- F-3 result-level useful/not-useful.
- B-6 stale L1 cleanup.
- B-5 existing comparison-harness run.

### P2 — explicitly defer unless everything above is done

- calibrated densitometry claims;
- loading-control normalization;
- reviewed-corpus reseed;
- null-provenance redesign B-3;
- escalation redesign B-7;
- sample/tissue routing B-8;
- broad schema expansion;
- literature-scale claims;
- unseen-paper accuracy claims;
- production deployment.

---

## 8. Evaluation gates

`HANDOFF.md` commands are authoritative. Discover the current test commands instead of inventing a parallel suite.

### Band-reading gate

Must include:
- region round-trip test;
- explicit lane-boundary API test;
- real-crop boundary sanity on multiple reviewed crops if fixtures are available;
- clipped/saturated case returns `quantification_refused` with **no numeric ratio**;
- clean synthetic case retains expected qualitative ordering;
- web typecheck/lint on changed route/page;
- honest method metadata/export if D-6 lands.

### Bio-QA gate

Must include:
- non-empty real figure-caption context reaches the record builder when source has a legend;
- methods context remains typed as methods;
- known empty-model antibody case recovers expected catalog/vendor from target-scoped source text;
- existing/conflicting model/source antibody evidence is not overwritten;
- biological engine tests + benchmark required by repo rules.

### Integration gate

- relevant API tests;
- web typecheck/lint/build as practical;
- `git diff --check`;
- no secrets/generated junk;
- no production change;
- Agent Q review complete;
- any unrelated pre-existing failure reproduced on source branch and documented rather than hidden.

---

## 9. Wednesday feedback package

The external form already lives as a build spec in:
`tickets/tally-ucsf-beta-feedback.md`

The distribution/referral strategy lives in:
`tickets/ucsf-beta-distribution.md`

Do not spend engineering time reproducing those questions in-app tonight. The existing in-product feedback system remains useful for field/record/search corrections; Tally is the session-level instrument.

For the first UCSF wave, optimize for varied workflows across multiple labs/roles rather than maximum submissions. Ask warm contacts to forward to 2–3 relevant labmates and request public evaluation papers when appropriate.

---

## 10. Deliverables at stop time

Must leave:

1. tested P0 engineering changes that were feasible;
2. reviewed/polished Tally + multi-lab distribution specs;
3. `research/overnight/2026-09-14-session-log.md`;
4. `research/overnight/2026-09-14-summary.md` with:
   - what changed;
   - what is biologically safer now;
   - what is demo/Wednesday-ready;
   - what is not ready and why;
   - exact manual Tuesday/Wednesday actions;
   - test commands/results;
   - commit SHAs;
   - P0/P1/P2 blockers;
5. updated `HANDOFF.md`;
6. clean pushed task branch.

Do not deploy production.

---

## 11. Stop conditions

Stop/hand off when:
- usage hits the 80% ceiling;
- ~4 active hours elapse if usage cannot be measured;
- continuing needs production credentials/irreversible mutation;
- biology cannot be established from evidence;
- proceeding requires invented ground truth;
- a P0 regression becomes the highest-value task;
- remaining tasks are lower-value than preserving the review reserve.

A tested partial result is better than unfinished breadth.

---

## 12. Final Claude report format

```text
STATUS: COMPLETE / PARTIAL / BLOCKED

USAGE:
- Start:
- End:
- Exact 80% measurable? yes/no
- Reserve preserved:

SOURCE STATE:
- Source branch/head:
- Task branch/head:

SHIPPED ON TASK BRANCH:
- ...

BIOLOGICAL SAFETY IMPROVEMENTS:
- ...

BAND-READING STATUS:
- ...

TALLY / UCSF FEEDBACK PACKAGE:
- ...

TESTS:
- ...

ADVERSARIAL REVIEW:
- ...

NOT DONE / DO NOT CLAIM:
- ...

TUESDAY/WEDNESDAY MANUAL ACTIONS FOR NIK:
1. ...
2. ...
3. ...

COMMITS:
- ...

NEXT SINGLE BEST TASK:
- ...
```

Report facts only. Never call a plan "implemented" or an agreement metric "accuracy".

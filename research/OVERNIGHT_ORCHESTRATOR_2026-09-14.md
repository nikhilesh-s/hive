# HiveBlot overnight FABLE orchestrator — 2026-09-14 → 2026-09-15

**Target ship:** Wednesday, 2026-09-16  
**Source branch:** `experimental/ucsf-demo-2026-09-09`  
**Purpose:** use one long Claude Code session to convert the post-UCSF notes and ticket backlog into a Wednesday-ready beta package without sacrificing biological validity.

This file is an execution brief, not a product claim. Read `CLAUDE.md`, `AGENTS.md`, and `HANDOFF.md` before doing anything. The repository's biological non-negotiables override this file if they conflict.

---

## 0. Mission

By the end of this run, leave Nik and the team with a **tested, reviewable Wednesday package**, not a pile of speculative code.

The package has four outcomes:

1. **UCSF feedback package:** a complete Tally form specification that Yashvi/Srushti/Nik can build manually, optimized for distribution beyond the current two researchers and across multiple UCSF labs.
2. **Experimental band-reading improvement:** make the existing experimental densitometry path scientifically defensible as a *band-reading aid* — user-defined region/lanes, saturation refusal, uncertainty/ranges where justified, honest copy, no fake quantitation.
3. **Biological-accuracy improvement:** land the highest-leverage plumbing fixes already identified in `tickets/bio-qa.md`, especially caption/methods separation and deterministic antibody recovery, with tests.
4. **Release handoff:** one concise status document, clean commits, green relevant tests, and a precise Wednesday checklist. Do **not** deploy production or run irreversible production migrations unless Nik explicitly does that later.

The latest meeting note (`meeting_notes`) is now binding product context: researchers were promised a structured feedback form by Wednesday and the team discussed a densitometry direction. The existing `tickets/` plan remains useful, but this brief changes one product choice: **the structured end-of-session survey for Wednesday will be external Tally, not an in-app survey.** Do not spend this overnight run rebuilding F-4 inside the app unless it is needed for another acceptance test.

---

## 1. Current state to assume, then verify

Before editing, verify each statement against the branch and current HEAD. If any is stale, write the corrected fact into the session log and adapt.

- `main` is stale and must not be touched.
- `feature/bio-context-beta` is the stable hosted-beta lineage; the experimental UCSF branch contains newer live-ingest, QA, and band-reading work.
- `experimental/ucsf-demo-2026-09-09` is the current UCSF/demo lineage and contains the newest meeting note.
- The reviewed corpus is ~475 rows / 93 experiment groups / 3 papers and must not be silently reseeded during this run.
- Live rows remain clearly badged `LIVE · UNREVIEWED`.
- Existing post-UCSF tracks are:
  - Track F: feedback (`tickets/feedback.md`)
  - Track D: band reading / densitometry (`tickets/densitometry.md`)
  - Track B: biological QA (`tickets/bio-qa.md`)
- The current quantitative densitometry output is **not calibrated** and has known clipping, lane-placement, and reproducibility problems. Do not rescue it by better wording alone; fix the failure modes or refuse quantification.
- The most important bio-QA plumbing gaps are already documented: caption/methods separation, deterministic antibody backstop, unmeasured panel recall, and stale/limited evaluation.

Run a short `git log`, inspect the files above, and produce a 10–20 line `research/overnight/2026-09-14-session-log.md` before implementation begins.

---

## 2. Branch and safety protocol

Create a task branch from the current UCSF demo branch if one does not already exist:

```bash
git switch experimental/ucsf-demo-2026-09-09
git pull --ff-only
git switch -c overnight/ucsf-2026-09-14
```

If the task branch already exists, inspect it before continuing. Never force-push. Never rebase shared branches. Never touch `main`.

Commit in coherent phase-sized commits. Prefer one commit per track plus a final integration/handoff commit. Do not add AI co-author trailers.

**No production side effects during this overnight run:**
- no production deployment;
- no destructive DB changes;
- no hosted-corpus reseed;
- no secrets committed or printed into docs;
- no sending emails/forms/messages on Nik's behalf.

The desired endpoint is PR-ready / cherry-pick-ready work that Nik can inspect and deploy tomorrow.

---

## 3. Usage governor — target 80% of the active five-hour Claude window

Nik wants this session to use approximately **80% of one five-hour usage window while preserving a 20% reserve**.

Treat 80% as a **hard spending ceiling and target, never as a reason to manufacture useless work**.

### If Claude exposes usage telemetry

At startup:
1. Read the current window usage / remaining quota using whatever first-party usage indicator is actually available.
2. Write the starting value and the 80% stop point to the session log.
3. Re-check at major checkpoints.

Checkpoints:
- ~20% used: recon and first implementation should be underway.
- ~40% used: at least one high-value code path should be implemented and tested.
- ~60% used: stop broad exploration; finish chosen work.
- ~72% used: freeze scope; no new feature tracks.
- ~78% used: stop spawning new sub-agents and begin final integration, deterministic tests, docs, and commits.
- **80% used: stop model-intensive work.** Only finish deterministic commands that are already in progress, then write the handoff.

### If exact usage telemetry is not available

Do **not** pretend exact 80% control exists. Use **four hours of active orchestration inside the five-hour window as a conservative proxy**, keep the same phase checkpoints, and record that the percentage could not be verified.

Never burn tokens solely to hit a number. The reserve exists so Nik can inspect/fix the output after the run.

---

## 4. FABLE recursive loop

The orchestrator and every sub-agent use the same loop. Repeat it until the assigned acceptance criteria are met, the next improvement is lower-value than another track, or the usage governor tells the agent to stop.

### F — Frame
- What exact researcher or engineering problem am I solving?
- What is the smallest defensible outcome that moves Wednesday forward?
- Which repository rule or scientific claim could this accidentally violate?

### A — Audit
- Read the relevant code, ticket, tests, and existing research note before proposing new architecture.
- Reproduce the current failure when possible.
- Distinguish a real bug from missing validation, missing data, or a misleading metric.

### B — Build
- Implement the smallest coherent improvement.
- Preserve provenance, abstention, conflict handling, and reviewed/unreviewed separation.
- Add or update tests with the implementation, not later.

### L — Learn
Ask all four questions explicitly after each meaningful pass:
1. **How can I improve this project/process without increasing complexity for its own sake?**
2. **How can I make this more biologically accurate or scientifically honest?**
3. **What do I need to learn next, and which primary resource should I use?** Prefer the paper itself, figure/caption/methods, UniProt, NCBI/PMC/BioC documentation, and peer-reviewed methodology already cited in `research/` over generic summaries.
4. **How do I produce the best product while staying inside the remaining usage budget?**

Write one short answer to each in the sub-agent handoff. Do not turn learning into endless literature review.

### E — Evaluate
- Run the narrowest relevant tests first, then the broader required suite.
- For biological changes: test both a positive case and an abstention/conflict case.
- For image analysis: test clean + clipped/saturated + misboxed/edge cases.
- For UI: test failure states, not just the happy path.
- Ask: "What would make a UCSF researcher distrust this?" and address the highest-severity answer.

Then recurse only if the next pass is still among the highest-value uses of the remaining budget.

---

## 5. Orchestrator topology

Use sub-agents if the environment supports them. If it does not, run the same roles sequentially. The orchestrator owns scope, branch state, integration, and budget; sub-agents do focused work and return concise handoffs.

Do not allow two agents to edit the same files simultaneously.

### Agent R — Release/repo integrator
**Role:** source-of-truth keeper.

First tasks:
- map the current branch/commit graph relevant to `feature/bio-context-beta`, `experimental/ucsf-demo-2026-09-09`, and the overnight task branch;
- confirm what has actually been implemented since the 09-09 tickets were written;
- create/update the session log;
- maintain a live checklist of changed files, tests, and blockers;
- integrate other agents' work and resolve conflicts.

Do not redesign features. Do not deploy production.

### Agent T — Tally feedback-product spec
**Role:** turn researcher feedback into a manual form Nik's team can build tomorrow.

Primary deliverable:
- create `tickets/tally-ucsf-beta-feedback.md` following the acceptance criteria in section 7 below.

Use Tally's current capabilities conservatively: multi-page form, conditional logic, hidden fields / URL parameters, progress bar, and completion redirect are appropriate. The actual Tally form must be built manually outside this run.

Optimize for a broad UCSF researcher cohort, not just the current two contacts. The form should work for wet-lab researchers, computational biologists, postdocs, graduate students, staff scientists, and PIs without becoming generic.

### Agent D — Experimental band-reading engineer
**Role:** execute the highest-value subset of Track D.

Priority order:
1. D-1 — forward researcher `region` end-to-end.
2. D-2 — explicit researcher-defined lane boundaries on the user path.
3. D-3 — saturation/clip refusal gate.
4. D-6 — honest refusal card + method/export block.
5. D-4 — uncertainty/range output **only if** D-1..D-3 are stable and tested.
6. D-5 research cleanup only if budget remains.

Non-negotiables:
- page/product language says **Band reading (experimental)**, not calibrated densitometry;
- no numeric ratio when saturation/instability makes it indefensible;
- no DB storage this week;
- never treat loading-control normalization as solved;
- the old 59.7% agreement number is not a quality claim and must not appear in product copy.

A refusal is a successful output when the image cannot support quantification.

### Agent B — Biological QA engineer
**Role:** improve correctness of the extraction path before adding breadth.

Priority order:
1. B-1 — restore caption / methods separation.
2. B-2 — deterministic antibody backstop without overwriting model evidence.
3. B-6 — correct/delete stale L1 reporting.
4. B-5 — run the existing `compare_records.py` harness only after the code path is stable and only if budget permits.

Optional only after those:
- B-4 measurement scaffolding if the required panel inventory is already present and trustworthy.

Do not tackle B-3/B-7/B-8/reseed during this overnight unless all Wednesday-critical items are complete and the usage governor has ample room.

For every biological field changed, verify provenance and the `SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING` behavior. Never convert a paper-silent null into a guessed value.

### Agent Q — Adversarial QA / scientific reviewer
**Role:** attack the integrated result after implementation.

Do not write major features. Review diffs and try to falsify claims.

Checklist:
- can a clipped blot still produce a fake-looking quantitative number?
- can the region/lane UI send coordinates inconsistent with the API?
- can a caption claim be mislabeled as methods?
- can deterministic antibody parsing overwrite conflicting model/paper evidence?
- can a live unreviewed row look reviewed anywhere?
- can feedback copy solicit unpublished/sensitive lab data unnecessarily?
- do failure states tell the user the truth?
- are docs claiming any unseen-paper accuracy?

Return a severity-ranked list. The orchestrator fixes P0/P1 issues before final handoff.

---

## 6. Priority stack for this run

### P0 — Wednesday blockers

1. Complete `tickets/tally-ucsf-beta-feedback.md`.
2. Implement and test D-1 region forwarding.
3. Implement the D-2 researcher-defined lane path far enough that automatic equal-width whole-crop slicing is no longer the default user path.
4. Implement D-3 quantification refusal for saturated/clipped signal.
5. Implement B-1 caption/methods separation.
6. Implement B-2 deterministic antibody backstop.
7. Produce an integration/handoff report with exact tests and remaining manual Wednesday steps.

### P1 — high-value if P0 is green

- D-6 refusal/method/export UX.
- D-4 uncertainty ranges instead of fake precision.
- F-1 feedback export script.
- F-2 capture zero-result searches.
- F-3 result-level useful / not useful.
- B-6 stale L1 cleanup.
- B-5 existing comparison harness run.

### P2 — explicitly defer unless everything above is done

- calibrated densitometry claims;
- loading-control normalization;
- hosted-corpus reseed;
- B-3 null provenance redesign;
- B-7 escalation redesign;
- B-8 sample/tissue routing;
- unseen-paper accuracy claims;
- major schema expansion;
- autonomous production deployment.

---

## 7. Tally spec acceptance criteria

Agent T must create a builder-ready spec, not vague survey ideas.

The spec must include:

### A. Goal and audience
- Goal: measure **usefulness, trust, biological correctness, missing fields, workflow fit, and demand for band-reading tools**.
- Audience: UCSF researchers across multiple labs and seniority levels.
- Core completion target: ~4 minutes; deep-feedback branch ≤7 minutes.
- Explicit note: do not paste unpublished/confidential lab data.

### B. Form structure
Use 5 short sections/pages:
1. Researcher context
2. What they tried in HiveBlot
3. Scientific trust/correctness
4. Band-reading interest and ground-truth collaboration
5. Overall value + follow-up

### C. Branching logic
At minimum:
- did not use beta → skip detailed correctness questions and ask what blocked testing;
- found an incorrect extraction → reveal DOI/figure/field/detail follow-up;
- does not work with Western blots → skip detailed band-reading questions;
- willing to follow up → reveal contact field + consent language;
- willing to contribute a public evaluation paper → reveal DOI/PMCID field;
- willing to help with a dilution-series ground truth → reveal lab/protocol follow-up question.

### D. Hidden fields / tracking
Define URL parameters such as:
- `ref`
- `lab`
- `cohort`
- `beta_version`
- `source`

These must track distribution without requiring respondents to identify themselves. Include example link patterns, but do not put real private contact data in the repo.

### E. Questions
Include exact wording, answer type, required/optional state, and rationale for every question.

Must cover:
- role / lab type / frequency of Western blot use;
- whether they actually used the beta;
- what task/search they attempted;
- whether results were relevant/useful;
- field-importance ranking or matrix;
- specific wrong/missing data with a reproducible public reference when possible;
- whether `Supported / Needs review / Conflicting` communicates the right thing;
- trust threshold for `LIVE · UNREVIEWED` evidence;
- usefulness of provenance/crop/caption/methods;
- band-reading use cases and acceptable refusal behavior;
- interest in providing public evaluation papers or a known dilution series;
- top missing feature;
- estimated time saved / workflow value;
- permission for follow-up + optional contact.

### F. Manual build checklist
Include exact Tally builder actions, logic test cases, mobile/desktop QA, test submissions, export check, and final share-link preparation.

### G. Distribution plan
Prepare one base link and parameterized links by channel/lab/cohort so Nik can measure where feedback came from. Make the form easy to forward inside a lab.

### H. Wednesday success metric
A successful first wave means:
- form builds without logic dead-ends;
- one team member can complete the normal path in <5 minutes;
- one "wrong extraction" path captures enough detail to reproduce the issue;
- one "not a Western blot user" path stays short;
- exported responses preserve the hidden source fields;
- the team can separate product feedback from biological-correction feedback.

---

## 8. Broader UCSF researcher distribution — prepare, do not send

The current beta should not depend on feedback from one lab or two people. Produce a short internal note (`tickets/ucsf-beta-distribution.md`) that turns the current contacts into a **referral graph** rather than a closed beta list.

The note should propose:
- ask current contacts to forward one single Tally + beta link to 2–3 labmates who actually inspect Western blots;
- intentionally recruit different roles: postdoc/grad student/staff scientist/PI and at least one computational researcher;
- include Verba/Jura-network researchers already connected to the project, then expand through their introductions rather than cold-spamming UCSF;
- use hidden `ref`/`lab`/`cohort` parameters to measure response source;
- ask for one public paper each that represents a real workflow they care about;
- separate "general product tester" from "biology adjudicator" and "band-reading ground-truth collaborator" cohorts.

Do not scrape emails or send outreach in this run.

---

## 9. Scientific learning queue

Learning is allowed only when it resolves a current implementation or validation question. Use primary sources first.

### For extraction / biology
1. The source paper itself: figure, caption, methods, supplementary/source data.
2. UniProt reviewed records for protein identity/aliases, without guessing across ambiguous families.
3. NCBI/PMC/BioC docs for retrieval semantics.
4. Existing repository scientific QA and known failure examples before external browsing.

### For band reading
1. `tickets/densitometry.md` and the real-crop failures already documented.
2. The Butler/Misleading Westerns evaluation material already catalogued in `eval/candidates.json`.
3. Published source data / author-provided quantification from the reviewed papers where available.
4. A real dilution-series dataset before claiming calibrated quantitation.

For every source used to justify an algorithmic threshold or biological rule, record the citation or repository path in the relevant research note.

---

## 10. Test and evaluation gates

The exact commands in `HANDOFF.md` are authoritative; discover and use them rather than inventing a parallel suite.

At minimum, before final handoff:

### Band-reading changes
- unit tests for region forwarding;
- explicit lane-boundary API tests;
- at least five real reviewed crops for boundary sanity if fixtures permit;
- clipped/saturated fixture returns `quantification_refused` and no numeric ratio;
- clean synthetic case still returns expected qualitative ordering;
- web typecheck/lint for the changed page/proxy.

### Bio-QA changes
- pipeline test proving non-empty caption reaches the record builder where a figure legend exists;
- test proving methods remain methods rather than being relabeled;
- antibody backstop recovers a known catalog on an empty-model case;
- backstop does not overwrite an existing/conflicting model value;
- biological test suite + benchmark required by `AGENTS.md`.

### Integration
- relevant API suite;
- web typecheck/lint/build as practical;
- no new secrets or generated artifacts in git;
- review `git diff --check`;
- Agent Q adversarial review with P0/P1 resolved.

If a broad test fails for a pre-existing unrelated reason, reproduce it on the source branch and document it. Do not hide failures.

---

## 11. Deliverables at stop time

The orchestrator should leave all of the following:

1. `tickets/tally-ucsf-beta-feedback.md` — complete manual Tally specification.
2. `tickets/ucsf-beta-distribution.md` — multi-lab distribution/referral plan.
3. Implemented/tested P0 code changes that were feasible within the budget.
4. `research/overnight/2026-09-14-session-log.md` — starting state, usage checkpoints, decisions, agent handoffs, tests.
5. `research/overnight/2026-09-14-summary.md` — founder-facing concise summary:
   - what changed;
   - what is biologically safer now;
   - what is demo-ready;
   - what is not ready and why;
   - exact manual steps Nik/Yashvi/Srushti must do Tuesday/Wednesday;
   - commit SHAs;
   - test commands/results;
   - remaining blockers ranked P0/P1/P2.
6. Updated `HANDOFF.md` following repository rules.
7. Clean pushed task branch. No production deploy.

---

## 12. Stop conditions

Stop early if any of these happen:
- usage reaches the 80% ceiling;
- a change requires production credentials or irreversible migration to validate;
- biological correctness cannot be established from available evidence;
- continuing would require inventing ground truth;
- integration tests expose a P0 whose fix is more valuable than remaining feature work.

When stopping, prefer an honest, tested partial completion over a broad unfinished implementation.

---

## 13. Final orchestrator report format

End the Claude session with this exact structure:

```text
STATUS: COMPLETE / PARTIAL / BLOCKED

USAGE:
- Start:
- End:
- 80% target measurable? yes/no
- Reserve preserved:

SHIPPED ON TASK BRANCH:
- ...

BIOLOGICAL SAFETY IMPROVEMENTS:
- ...

TALLY / UCSF FEEDBACK PACKAGE:
- ...

BAND-READING STATUS:
- ...

TESTS:
- ...

NOT DONE / DO NOT CLAIM:
- ...

TUESDAY/WEDNESDAY MANUAL ACTIONS FOR NIK:
1. ...
2. ...
3. ...

BRANCH + COMMITS:
- ...

NEXT SINGLE BEST TASK:
- ...
```

The report must be factual. Never label "implemented" when only a plan or spec exists.

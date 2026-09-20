# HiveBlot overnight source map — 2026-09-14

Purpose: keep an overnight Claude run from wasting context and usage rediscovering the repository or treating superseded August notes as current requirements.

## Tier 0 — process rules; read first

1. `CLAUDE.md`
2. `AGENTS.md`
3. `HANDOFF.md`

These govern branch discipline, biological non-negotiables, tests, handoff behavior, and the current implementation state. If anything below conflicts with these, verify the newer fact before acting.

## Tier 1 — current Wednesday requirements

Read these next, in this order:

1. `meeting_notes` — latest UCSF meeting outcome; structured feedback form + band-reading/densitometry direction are explicit action items.
2. `tickets/README.md` — Sept. 16 sprint scope and current release strategy.
3. `tickets/feedback.md` — what feedback the product already captures and the concrete gaps.
4. `tickets/densitometry.md` — current band-reading implementation audit, failure modes, and ordered D tickets.
5. `tickets/bio-qa.md` — current biological QA audit and ordered B tickets.
6. `tickets/tally-ucsf-beta-feedback.md` — builder-ready external Tally spec added 2026-09-14.
7. `research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md` — overnight execution / FABLE orchestration brief.

These are the primary planning sources for the overnight task.

## Tier 2 — current technical/scientific evidence

Consult only when a task needs it:

- `research/UCSF_BETA_READINESS.md` — authoritative Sept. 1 consolidated beta audit; useful for what was already fixed and what was deliberately deferred.
- `research/UCSF_DEMO_2026-09-09.md` and `DEMO.md` — exact demo architecture, claims language, and fallbacks.
- `research/PROFESSOR_ORCHESTRATION_BRIEF.md` — concise architecture/orchestration description and measured-vs-unmeasured caveats.
- `research/automated_extraction_eval_protocol.md` — evaluation protocol; use instead of inventing a new accuracy metric.
- `research/experiments/L1_live_ingest_eval.md` — limited/stale live-ingest evaluation; never present as unseen-paper accuracy.
- `research/experiments/D1_densitometry_vs_bands.md` — old densitometry-vs-band-state experiment; use as a failure/benchmark history, not a quality claim.
- `research/real_pipeline_report.md` — source-paper facts and why the three reviewed papers stress standard/phospho/co-IP paths.
- `research/independent_scientific_qa.md` — historical independent audit that found serious failure classes. Many specific issues were subsequently fixed; use the failure classes and reproducible examples, not its old row counts/status as current state.

## Tier 3 — useful product/research context, mostly historical

Read selectively, not as current tickets:

- `research/biologist_western_workflow.md` — wet-lab verification workflow and field priorities.
- `research/ucsf_beta_ux_review.md` — strong first-run/product critique and experiment-grouping reasoning; many blockers were subsequently addressed.
- `research/RESEARCH_SYNTHESIS.md` — product/research synthesis and wedge use cases.
- `research/band_pattern_scientific_review.md` — background on band patterns / scientific caution.
- `research/benchmark_candidates.md` — candidate evaluation material.
- `research/biopharma_workflows.md` — broader future-use context, not Wednesday scope.
- `research/frontend_integration_plan.md` — historical frontend integration plan; verify before using.
- `research/supabase_beta_table_plan.md` and `research/supabase_legacy_audit.md` — DB history and security context; do not reopen resolved security work without current evidence.
- `super-based-ticket.md` — current Supabase status/parking issues; not a Wednesday feature track unless infrastructure becomes a blocker.

## Tier 4 — superseded delegation package

`research/team_delegation/*` is explicitly historical. `MASTER_DELEGATION.md` says the August workstreams were superseded by the Sept. 1 beta-readiness pass.

The files are still valuable for reasoning and teaching:
- `NIK_FOUNDER_LEARNING.md` — concise product/biology mental model.
- `PRODUCT_UX_HANDOFF.md` — first-run UX and researcher-value reasoning.
- `SCIENTIFIC_COMMUNICATION_HANDOFF.md` — honesty/positioning principles.
- `SEARCH_DATA_HANDOFF.md` — search/data integrity concerns.
- `BIOLOGY_QA_HANDOFF.md` — prior QA method.

Do **not** resurrect their task lists blindly. First check `UCSF_BETA_READINESS.md`, `HANDOFF.md`, and the September tickets for whether the issue was already closed.

## High-value lessons that still apply

1. **The representation + auditability are the product.** A field should trace to figure/caption/methods/UniProt evidence; provenance must not be removed to simplify UI.
2. **Abstention is a feature.** `CONFLICTING` keeps no winner. `MISSING` should not become a guess. A band-reading refusal is a correct output when the pixels cannot support quantification.
3. **The sharpest current user wedges:** exact-antibody evidence before buying/using it; finding whether a target has been blotted in a model/condition; verifying whether a record is trustworthy.
4. **Group around biological experiments, not database rows.** The old UX audit demonstrated how lane-level rows can become unusable if shown as independent results; never fuse biologically distinct panels just to make the UI cleaner.
5. **Historical QA found orchestration errors, not just model errors.** Panel conflation, bad grouping identity, source-label errors, and unsupported context can create confident biological falsehoods even with a decent model.
6. **Never confuse agreement with the reviewed set for unseen-paper accuracy.** The reviewed corpus is useful for regression/self-consistency; external accuracy requires independently adjudicated unseen papers.
7. **Band presence is not densitometry.** Until calibration/ground truth exists, the experimental feature is a band-reading aid with qualitative outputs, ranges where defensible, and refusal gates.
8. **The current feedback system is strong on corrections but weak on session-level usefulness and cohort tracking.** The external Tally form fills that gap; do not duplicate every Tally question in-product during the Wednesday sprint.

## Overnight read-budget rule

Do not read every Markdown file end-to-end at startup.

Start with Tier 0 + Tier 1. Then let each sub-agent open only the Tier 2/3 document needed for its task. The orchestrator should periodically ask: "Is another document likely to change the implementation decision, or am I reading for completeness?" If the answer is completeness, stop reading and execute.

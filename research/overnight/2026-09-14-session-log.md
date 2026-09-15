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

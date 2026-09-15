# Claude run launcher — UCSF densitometry push

**Active branch:** `experimental/ucsf-demo-2026-09-09`\
**Founder hard stop:** Tuesday, 2026-09-15 at 7:00 PM America/Los_Angeles\
**Primary execution plan:** `research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md`

This file is the short launcher for every Claude Code window used on this push. It exists so a fresh window can resume immediately instead of re-planning the repository.

## 1. Startup sequence

At the beginning of every Claude window:

1. `git fetch --all --prune`
2. switch to `experimental/ucsf-demo-2026-09-09`
3. pull with `--ff-only`
4. read `CLAUDE.md`
5. read `AGENTS.md`
6. read `HANDOFF.md`
7. read this file
8. read `research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md`
9. inspect the latest commits and `research/overnight/2026-09-14-session-log.md` if it exists
10. begin execution immediately from the highest-value unfinished task; do not repeat broad repository recon unless current state contradicts the handoff

Repository rules and biological non-negotiables still outrank this launcher.

## 2. Priority order

The founder promised UCSF researchers a densitometry direction. **Densitometry is the highest-priority product track until a real first-generation researcher workflow exists.**

Default order:

1. **Experimental densitometry** — region selection, researcher-defined lane boundaries, deterministic relative measurements, quality/refusal states, geometry overlay, reproducible export, stability/sensitivity checks, and validation.
2. **B-1** — restore real figure-caption vs methods separation in live extraction.
3. **B-2** — deterministic antibody recovery only when model/source output is empty; never overwrite or silently resolve conflict.
4. **Integration / repository structure** — one active branch, experiments behind routes, coherent experimental navigation, fix low-risk CI/repo debt that blocks execution.
5. **Feedback packaging** — polish the external Tally spec and distribution plan; do not rebuild the same session survey in-app.
6. **Deeper validation / P1 work** after the Wednesday-critical path is green.

Valency is a paper-discovery provider, not a separate product track. Touch it only if a current regression blocks `/experimental/research`.

`tickets/journal-access-later.md` is deferred. Ignore it during this push unless the founder explicitly reprioritizes it.

## 3. Recursive grind rule

Do **not** stop because one planned task is complete. After every meaningful implementation/test checkpoint, recursively choose the next highest-value safe task and continue.

Use this loop:

1. **Inspect** — what is actually unfinished or failing now?
2. **Choose** — which next task most increases Wednesday demo quality, densitometry usefulness, biological trust, or integration reliability?
3. **Execute** — implement the smallest coherent improvement; use bounded sub-agents when parallelism is real.
4. **Validate** — narrow tests first, then the relevant broader suite; test failure/refusal states, not just happy paths.
5. **Integrate** — resolve overlaps, update docs/contracts if behavior changed, commit and push coherent work.
6. **Record** — update the session log and `HANDOFF.md` with exact state, tests, blockers, and next task.
7. **Repeat immediately.**

If the current highest-priority task is blocked by credentials, unavailable external data, or an unsafe scientific assumption, document the blocker and move to the next highest-value task rather than ending the window.

## 4. Usage / limit behavior — use the window hard

The earlier orchestration file describes an ~80% target. **For this multi-window founder push, this launcher supersedes that usage target.** The goal is to extract as much useful work as possible from every Claude allowance window through the founder hard stop.

### If reliable first-party usage telemetry is visible

- Continue useful model-intensive work through roughly **90–95%** of the current allowance.
- Reserve only the final **5–10%** for integration, tests that need interpretation, `HANDOFF.md`, session-log update, commit, and push.
- Do not begin a large new feature once there is not enough allowance left to checkpoint it safely.
- Never intentionally hit a hard cutoff with uncommitted work.

### If exact usage telemetry is not visible

- Do not invent a percentage.
- Keep working through useful tasks until the platform gives a credible near-limit signal or the window is practically exhausted.
- Because the exact cutoff is unknown, **checkpoint frequently**: commit/push after each coherent acceptance block and keep `HANDOFF.md` current enough that an abrupt limit does not erase project state.

### Important

- Do not waste tokens merely to consume allowance.
- Do not stop early because the initial P0 list is complete. If P0 is green, deepen densitometry validation/UX, run adversarial QA, fix P1 scientific/integration issues, improve tests, and simplify high-leverage repository debt.
- If work becomes speculative or scientifically unsupported, choose another task instead of manufacturing output.
- A forced Claude usage cutoff is expected; the next window resumes from Git + handoff rather than starting over.

## 5. Multi-window continuation protocol

Nik may run multiple Claude allowance windows before the hard stop.

At each reset/new window:

1. resume the same active branch;
2. pull latest remote state;
3. read the newest `HANDOFF.md` + session log + last commits;
4. identify what the previous window actually completed;
5. skip completed recon and completed tasks;
6. continue the recursive grind from the highest-value unfinished task;
7. preserve the same scientific rules and route-based architecture.

Do not create a new long-lived feature branch merely because a new Claude allowance window started.

## 6. Sub-agent policy

Use the topology in `research/OVERNIGHT_ORCHESTRATOR_2026-09-14.md`:

- primary orchestrator/integrator;
- Densitometry lead;
- Biology QA lead;
- Repo/integration lead;
- Packaging/feedback lead;
- adversarial reviewer after tangible implementation exists.

Densitometry may use two bounded children when useful:

- algorithm / quality / validation;
- UI / API / interaction.

Do not spawn recursive swarms. File ownership must be explicit before parallel edits.

## 7. Densitometry success condition

A strong Wednesday state means a researcher can:

1. open/load a blot image or HiveBlot crop;
2. select the relevant blot strip;
3. define lane boundaries;
4. run deterministic analysis;
5. see the exact selected geometry;
6. receive per-lane background-corrected relative measurements **when pixels support them**;
7. receive a clear warning/refusal instead of a fake number when clipping, bad geometry, no signal, or instability makes quantification unreliable;
8. export enough method/geometry/quality metadata to reproduce what HiveBlot did.

This is a first-generation experimental densitometry workflow. Do not claim calibrated protein abundance, cross-image comparability, or loading-control-normalized protein quantity unless those capabilities are actually implemented and validated later.

## 8. Commit / checkpoint discipline

- Work directly on `experimental/ucsf-demo-2026-09-09` for this push.
- Make coherent commits by completed acceptance block.
- Push frequently enough that a usage cutoff cannot strand substantial local work.
- Never force-push shared history.
- Never merge stale `main` into the active branch.
- Historical experiment branches already contained by the active branch do not need to be merged again.
- Do not delete old shared branches automatically; leave Nik a cleanup recommendation.
- No secrets or AI co-author trailers.

## 9. End conditions

Before the founder hard stop, a Claude window should end only when one of these is true:

1. the current Claude allowance is near exhaustion and remaining budget is needed to checkpoint safely;
2. the platform hard-limits the window;
3. a task requires an unavailable credential/external resource **and** all other useful in-scope work is exhausted;
4. continuing would require invented biological ground truth or an unsafe/irreversible production action;
5. the founder hard stop of Tuesday, 2026-09-15 at 7:00 PM America/Los_Angeles has been reached.

If the window ends for reasons 1 or 2, leave the repository immediately resumable.

## 10. End-of-window report

Keep the user-facing report short. Include:

- what shipped this window;
- tests/results;
- current branch + latest commit;
- densitometry status;
- B-1/B-2 status;
- top unresolved blocker;
- **exact next task for the next Claude window**.

Then stop. The next allowance window should be able to restart from this file and `HANDOFF.md` without Nik having to explain the project again.

# HiveBlot Team Assignments

> **STATUS (2026-09-01, UCSF beta-readiness pass): the five teammate
> workstreams below are CONSOLIDATED.** They were absorbed into one pass owned
> by Nik + the primary Claude engineering agent, and that pass is complete:
> see `research/UCSF_BETA_READINESS.md` (findings, fixes, verdict) and
> `HANDOFF.md` (current state). **Future agents must not wait for Ananya,
> Suhas, Srushti, Tanvi or Yashvi deliverables — none are pending.** The
> personal handoff files in this directory remain as historical specification
> and backlog only. Srushti's frontend work landed directly on
> `feature/bio-context-beta` (14 commits, 2026-08-25/26) and is canonical.

Current beta: **3 reviewed papers · 93 experiments · 475 evidence rows**.

Historical assignment index for the August 2026 internal beta pass (see status above).

| Person | Primary role | Handoff |
|---|---|---|
| **Ananya** | Biology QA + search support | `ANANYA_HANDOFF.md` |
| **Suhas** | Search, data integrity, API / infra | `SUHAS_HANDOFF.md` |
| **Srushti** | Product / UX | `SRUSHTI_HANDOFF.md` |
| **Tanvi** | Scientific communication + biology support | `TANVI_HANDOFF.md` |
| **Yashvi** | Coordination, feedback synthesis, team communication | `YASHVI_HANDOFF.md` |
| **Nik** | Product direction, integration, evaluation strategy, final decisions | `NIK_FOUNDER_LEARNING.md` + `MASTER_DELEGATION.md` |

## Shared rules

- Work on `feature/bio-context-beta`, never `main`.
- Observe and understand before fixing.
- Do not touch legacy QIB.
- Do not deploy unless Nik explicitly owns/approves the deploy.
- Do not change the reviewed corpus without Nik's sign-off.
- Preserve raw wording and provenance.
- Never silently resolve scientific conflicts.
- Reviewed beta does not equal arbitrary-paper automated extraction accuracy.
- No model automation in this workstream pass.

## Coordination overlaps

- **Ananya ↔ Tanvi:** biology-checked glossary and scientific wording.
- **Srushti ↔ Suhas:** `needs review` reason display and minimal API support.
- **Ananya ↔ Suhas:** what a safe organism-aware query should mean biologically vs technically.
- **Yashvi:** track these overlaps so no duplicate implementation happens without coordination.

## Founder decisions that stay with Nik

- Final `/about` positioning and any public capability claims.
- Whether/when organism filtering changes search semantics.
- Whether API path sanitation requires a reseed.
- Which next-action UX ideas become roadmap items.
- Confidence display direction.
- Any reviewed corpus correction/reseed.
- Model credentials and automated-extraction evaluation.
- Integration, merge, and deploy decisions.

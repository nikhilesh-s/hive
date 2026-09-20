# Later ticket — journal / full-text access indicator

**Status:** DEFERRED — not part of the 2026-09-16 Wednesday push.\
**Priority:** Week 2+ only after densitometry, B-1/B-2, feedback packaging, and active-branch consolidation are stable.

## Why this exists

The 2026-09-09 UCSF follow-up notes included a request to make paper access clearer, including whether HiveBlot can obtain an open-access PDF and whether a researcher may need institutional access for a journal.

This is useful product work, but it is not currently more important than densitometry, biological extraction correctness, or the structured researcher-feedback loop.

## Current capability to preserve

The experimental research route already distinguishes papers where HiveBlot can resolve a legal open-access PDF and refuses live extraction when it cannot obtain one through the supported OA path. Valency/PMC discovery and the OA-resolution layer should remain separate from any future claim about a researcher's institutional entitlement.

## Future goal

Expose a small, honest access status on paper discovery/results, such as:

- **Open-access PDF available** — HiveBlot can legally acquire the PDF through its supported OA sources.
- **No open-access PDF found** — HiveBlot cannot currently acquire full text through its OA path.
- **Institutional access may be required** — informational only unless a future UCSF/library integration can verify entitlement.

Do **not** claim that a UCSF researcher can access a paywalled paper merely because the journal is commonly available at universities. Institutional access must be verified by an actual supported resolver/integration before presenting it as fact.

## Acceptance criteria when this is eventually worked

1. Paper discovery response has one explicit access-status contract rather than UI inference from scattered fields.
2. OA status comes from the existing acquisition/resolution logic.
3. UI distinguishes HiveBlot acquisition ability from the user's possible institutional access.
4. No scraping or bypass of paywalls.
5. Unknown access remains unknown; no optimistic guessing.
6. Tests cover OA available, OA unavailable, and unknown/institutional cases.
7. The indicator works from the single active integration branch and appears on `/experimental/research`; no new long-lived feature branch is created just for this.

## Not this week

Do not spend the 2026-09-14 overnight Claude window on this ticket unless every Wednesday-critical densitometry, B-1/B-2, integration, and feedback deliverable is complete and Nik explicitly re-prioritizes it.
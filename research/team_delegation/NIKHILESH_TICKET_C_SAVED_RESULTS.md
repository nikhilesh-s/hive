# Ticket C: Save Experiments and Saved Results

**Product:** HiveBlot
**Handoff to:** Nikhilesh (Nik), for implementation with Claude
**Target branch:** `experimental/ucsf-demo-2026-09-09`
**Date:** 2026-09-25
**Status:** Saved Results specification only; Search History companion is implemented.
**Repository inspection baseline:** `511d7b6`.

## 1. Goal

Add a **Save** button to experiment cards in HiveBlot Search and a dedicated **Saved** page where researchers can return to their saved experiments.

The core workflow is:

```text
Search for evidence
  -> Save an experiment
  -> Button shows Saved
  -> Open SAVED in the navigation
  -> Review the same experiment and its grouped lanes
  -> Remove it from Saved when no longer needed
```

## Related Feature: Search History

Search History is a separate companion feature, not another form of Saved
Results:

```text
History = searches the researcher has performed
Saved   = evidence experiments the researcher intentionally bookmarked
```

Search History is implemented through the existing Next.js -> FastAPI ->
Supabase architecture at `/history`. Successful submitted searches are
deduplicated by anonymous browser session, normalized query, and structured
filters; the History page supports rerun through `/search?q=...`, individual
removal, and explicit clear-all. It uses the existing `hive_feedback` scoped
database role and is intentionally separate from the future `saved_results`
model described in this ticket.

Authentication is not currently implemented in HiveBlot, so this history is
browser-session scoped through the existing anonymous localStorage session ID.
It persists across refreshes and app sessions in that browser, but is not an
account-level or cross-device identity. Do not reuse this mechanism as secure
ownership for Saved Results without the ownership decision below.

**Search History completion:** Done. The implementation includes migration 007,
session-scoped FastAPI and Next.js data access, successful-submit recording with
normalized deduplication, `/history`, rerun links through `/search?q=...`,
individual deletion, clear-all confirmation, empty/loading/error states, and
database/API test coverage. TypeScript, lint, production build, Python syntax,
and migration parity checks pass. Saved Results remains unimplemented.

This is a bookmarking feature. Saving or removing a bookmark must never modify or delete the underlying scientific evidence.

## 2. Current Search Behavior

The Search page calls `POST /api/search` and receives lane-level rows typed as `DatabaseResult[]`. It groups them with `groupResults(results)` and renders experiment-level cards:

```tsx
{groups.map((g) => (
  <DatabaseResultCard
    key={g.first.id}
    data={g.first}
    lanes={g.lanes}
  />
))}
```

One card represents one experiment. Multiple lane rows are displayed together inside that card.

**Save the experiment represented by the card, not its first row alone and not each lane separately.** A six-lane experiment must create one saved item and count as one saved experiment.

## 3. Scope

Implement:

- A Save control on every experiment card rendered by Search.
- Save, Saved, loading, and failure states.
- Removal from saved results.
- Persistent saved-result storage in the existing Supabase project/database.
- Restoration of Saved state on Search.
- A `/saved` page using the existing experiment cards.
- A SAVED navigation item immediately after SEARCH.
- Loading, empty, error, and unavailable-evidence states on Saved.
- Tests covering the complete workflow and experiment identity.

Do not implement collections, tags, notes, exports, saved-result filters, collaboration, or an unrelated authentication redesign. Do not change scientific extraction, evidence interpretation, search ranking, or the existing card information hierarchy.

## 4. Save Button: Appearance and Placement

Add a compact Save control in a consistent position within the existing card's action area. Use the existing HiveBlot button styling, typography, colors, spacing, and focus treatment.

- Do not redesign the card or move the experiment title, lane display, image, or evidence metadata to accommodate it.
- Use the visible label **Save** when the experiment is not saved.
- Use **Saved** after a successful save, with a restrained selected treatment that fits the current theme.
- Keep the control's height and reserved width stable across states so the card does not jump.
- Keep it usable on desktop, tablet, and mobile without overlapping card content.
- Match both existing light and dark themes.
- An icon is optional; use existing project conventions rather than adding an icon dependency for this feature alone.

## 5. Save Button: Interaction States

| State | Visible behavior | Interaction |
| --- | --- | --- |
| Saved status being checked | Neutral checking/loading state | Do not falsely present the item as unsaved; disable mutation until ownership/status is known. |
| Not saved | Save | Clicking saves the experiment. |
| Saving | Saving... or existing equivalent loading treatment | Disable repeat clicks for that experiment only. |
| Saved | Saved | Clearly expose removal as described below. |
| Removing | Removing... or equivalent | Disable repeat clicks until the request finishes. |
| Save failed | Return to Save; show an error | Preserve the ability to retry. |
| Remove failed | Retain Saved and the saved card; show an error | Do not pretend removal succeeded. |
| Status lookup failed | Show an unavailable/retry state | Do not silently treat an unknown state as Save. |

Prefer confirmed server success before changing the persistent Saved state. If using optimistic updates, implement rollback and test failure cases.

Use keyboard-accessible buttons, meaningful accessible names, visible focus, and accessible loading/error announcements. If Save/Saved is a toggle, expose its state with `aria-pressed` and make the removal action clear to keyboard and touch users, not just on hover.

## 6. Removing a Saved Experiment

Researchers must be able to remove a saved experiment from Search and from `/saved`.

Use a consistent interaction that makes clear this removes only a bookmark:

- A Save/Saved toggle is acceptable when the Saved state clearly communicates that activating it removes the bookmark.
- If that would be ambiguous, retain the Saved status and offer an explicit **Remove from saved** action using the existing action pattern.
- Do not label the action simply **Delete**.
- On successful removal, Search shows Save, the Saved page removes that item, and the experiment count updates.
- On failure, keep the previous state and card visible, with a retryable error.
- When the last item is removed, show the intentional empty state.

Do not require a large confirmation modal for an ordinary reversible bookmark action. Return focus sensibly when a card disappears.

## 7. Saved Page and Navigation

Add `/saved` and update the existing navigation to:

```text
SEARCH   SAVED   ABOUT   LEARN   RESEARCH
```

Keep the current navigation layout and styling. Indicate the current page accessibly with `aria-current="page"`; reuse existing active styling if present, otherwise add only a minimal consistent treatment. Do not redesign the navigation.

The Saved page should visually belong to the existing Search experience. Suggested content hierarchy:

```text
SAVED
Western blot evidence

Your saved experiments
12 saved experiments

[Existing experiment card, marked Saved]
[Existing experiment card, marked Saved]
```

Reuse `DatabaseResultCard` instead of building a separate saved-card design. Preserve grouped lanes, experiment metadata, crop behavior, evidence access, uncertainty labels, and any review-tier labels already provided by the component.

Count saved experiments, not lane records. Use singular/plural correctly. Default to newest saved first with a deterministic tie-breaker; a sorting control is not required.

The researcher must be able to reach all saved experiments. Pagination or Load more is acceptable if needed; paginate bookmarks/experiments, not raw lane rows, and never split an experiment across pages.

## 8. Saved Page States

**Loading:** Show the existing loading pattern while bookmarks and evidence are fetched. Do not briefly show the empty state during loading.

**Empty:** Show:

```text
No saved experiments yet.
Save Western blot evidence from Search to collect it here.
[Go to Search]
```

**Error:** Explain that saved results could not be loaded and provide Retry. A failed request must not be reported as zero saved experiments.

**Unavailable evidence:** If a saved experiment can no longer be retrieved, keep its bookmark visible as unavailable with a removal action. Do not fabricate its evidence, silently discard it, or attach it to a different record that reused a numeric ID. The saved count includes retained bookmarks; distinguish available and unavailable items if necessary.

## 9. Persistence and Ownership

Use the existing Supabase project/database. Do not create another database and do not make React state or localStorage the authoritative saved-results store.

Saved state must survive:

- Page refreshes.
- Search -> Saved -> Search navigation, including browser Back.
- A different search that returns the same experiment.
- Closing and reopening the app under the same supported owner identity.

Bookmarks must be private to their owner. Do not create one shared saved list for all researchers. Do not trust a request body's arbitrary `user_id` or `owner_id` as authorization.

**Ownership decision for Nikhilesh:** Repository inspection found internal/agent API-key authentication, but no researcher-account login. The feedback localStorage session ID is anonymous correlation data, not a secure identity. Before implementing private persistence, confirm the smallest approved ownership mechanism with Nik. Do not quietly add a large login system or reuse the feedback ID as authorization.

If browser-specific ownership is approved, document that persistence is limited to that browser identity and does not promise cross-device access or recovery after clearing cookies. Account-based ownership can support those behaviors, but requires an explicitly approved authentication scope. This decision does not change the requested Save/Saved UI.

## 10. Experiment Identity

Use one canonical experiment identity consistently for grouping, saved-status lookup, save, storage, retrieval, and removal.

`stable_row_key` normally has this shape:

```text
<experiment hash>:<lane index>
```

Rows sharing the experiment-hash portion belong to the same experiment under the current card-grouping rules. The full lane key must not become the bookmark identity.

- Do not use an array index, `g.first.id`, or a volatile numeric row ID as the sole persistent identity.
- For legacy rows without a stable key, preserve the existing frontend grouping semantics: paper, crop or page fallback, target, experiment type, cell line/sample, and modification label.
- Centralize the frontend helper and types in the existing `web/lib/results.ts` where practical. Search currently duplicates definitions already present there.
- Backend identity and retrieval must agree with the frontend contract. The current backend truncation helper's legacy paper/row-ID fallback differs from frontend grouping; do not reuse it unmodified for bookmarks.
- Use shared fixtures to verify cross-language parity, including null versus empty strings, crop-path normalization, delimiters, and multiple cell lines within a panel.
- Validate client-supplied identity against database evidence before saving. Do not accept a row ID paired with a key belonging to another experiment.
- If ambiguity remains in a legacy group, report it explicitly rather than inventing a confident match.

The shared card is also used for live/unreviewed evidence. Confirm with Nik whether those surfaces are included in Ticket C. Do not accidentally expose a working-looking Save control that stores the wrong corpus or uses colliding IDs. If live saves are included, carry source-tier identity through save, lookup, retrieval, and removal, preserve unreviewed labels, and handle re-ingestion/deletion explicitly. If deferred, document that scope rather than silently claiming every shared-card surface is supported.

## 11. Storage Requirements

Inspect the deployed schema read-only before deciding that a new table is needed. Repository inspection found no existing saved-results migration; this is not proof that the deployed database has no such table.

A conceptual record is:

```text
saved_results
  id
  owner identity
  experiment_key
  source tier, if required by supported scope
  created_at
```

The exact table/column names and owner type should follow the approved identity mechanism and repository conventions.

- Store a stable reference, not an unnecessary copy of the complete experiment payload.
- Enforce uniqueness for owner + canonical experiment identity, including the source namespace where applicable.
- Make repeated saves idempotent at the database boundary, including concurrent requests. A duplicate save should not create another row or change the original save date.
- Make removal idempotent and owner-scoped. Removing an already-removed bookmark is a successful no-op.
- A representative row reference may be useful, but must not replace the stable identity or cause bookmarks to disappear on a corpus reseed.
- Add appropriate indexes for owner-scoped listing, status lookup, and evidence retrieval.
- Do not grant the search role write access, expose browser credentials, weaken existing RLS, or use a privileged role as a shortcut around ownership checks.

Use an additive migration and documented rollback if a new table/role is required. Keep canonical migrations and Supabase CLI copies synchronized through the existing migration-sync tooling and tests. Do not apply live migrations or change hosted services without Nik's approval.

## 12. API and Data-Access Behavior

Preserve the current architecture:

```text
Search / Saved page
  -> Next.js API route
  -> FastAPI endpoint
  -> scoped PostgreSQL data-access layer
  -> existing Supabase database
```

Provide these capabilities using repository-consistent routes; the exact route names are implementation details:

| Capability | Required behavior |
| --- | --- |
| Batched saved status | Accept a bounded set of displayed experiment identities; return this owner's saved identities only. |
| Save | Validate the experiment, derive trusted ownership, and persist one idempotent bookmark. |
| Remove | Remove only this owner's bookmark for that experiment. |
| List saved results | Return an owner-scoped experiment count and ordered bookmarks with all evidence rows needed for the cards, or an explicit unavailable status. |

Use parameterized database operations, bounded inputs, predictable error responses, and the existing internal API authentication boundary. Do not forward a browser-supplied owner header as trusted identity. Cookie-based mutations need appropriate CSRF/origin protection. Private responses must not enter shared caches.

Keep database calls out of `DatabaseResultCard`. Let the page or a reusable hook/data-access module own saved state and mutation handlers. Extend shared TypeScript contracts rather than introducing conflicting copies.

## 13. Search and Saved Synchronization

When Search returns results:

1. Group the rows into experiments with the canonical helper.
2. Deduplicate the displayed experiment identities.
3. Fetch saved status in one batched request, or a bounded number of batches for size limits.
4. Populate each card's Save/Saved state without one request per card.
5. Update the relevant experiment state after a successful save/remove.

Keep saved-status requests tied to the current search/owner. Late responses from an earlier search must not overwrite newer results or a successful mutation. Preserve the Search page's existing stale-response protection. Disable only the affected card during a write.

Revalidate appropriately when navigating back from Saved, after removal, or when the owner changes. Do not leave stale React state that contradicts database persistence.

When loading `/saved`, retrieve full experiment evidence by identity, not by repeating the original search query and not by reading only the representative row. Search filters can match only some lanes; that must not become a permanent partial bookmark. Reuse the existing grouping and lane-display semantics, with deterministic lane ordering.

## 14. Acceptance Criteria

- [ ] Search for `phospho STAT3 Tyr705` and see a Save control on every displayed experiment card.
- [ ] Saving one multi-lane card creates one bookmark and shows Saved after success.
- [ ] Repeated/concurrent saves do not create duplicates.
- [ ] Another search returning the same experiment shows Saved correctly.
- [ ] SAVED appears immediately after SEARCH and opens `/saved`.
- [ ] Saved displays the existing experiment card with its full grouped lanes and metadata.
- [ ] The count reflects experiments, not lane rows.
- [ ] Refreshing and reopening under the same supported identity retain bookmarks.
- [ ] Removal from Search or Saved is clear, owner-scoped, and does not delete evidence.
- [ ] Returning to Search after removal shows Save.
- [ ] Save/remove failures retain the correct prior state and expose Retry.
- [ ] Loading, empty, error, and unavailable-evidence states are distinguishable.
- [ ] Numeric ID reuse or reseeding cannot attach a bookmark to unrelated evidence.
- [ ] Different owners cannot list, save into, or remove from each other's collections.
- [ ] Keyboard, touch, narrow-screen, and light/dark-theme checks pass without card layout shifts.
- [ ] No unrelated scientific, search, or layout behavior changes.

## 15. Verification

Add focused tests for:

- Stable-key and legacy grouping, plus frontend/backend identity parity.
- One bookmark for many lanes; complete lane reconstruction from a partially matching search.
- Save/list/status/remove, duplicate and concurrent writes, repeated delete, and sorting/counts.
- Ownership isolation, forged owner/record-key inputs, RLS/grant boundaries, and private-response caching.
- Failed writes, failed saved-status lookup, late responses, refresh/navigation, and unavailable evidence.
- Reviewed/live namespace isolation if live saves are supported.
- Corpus reseeding and numeric row-ID reuse.

Run the repository's relevant API tests, database access-matrix tests, migration-sync checks, TypeScript, lint, production build, and required scientific regression tests/benchmark. Use the existing test setup; do not invent passing test counts or report database integration tests as passing when skipped.

Current frontend commands, from `web/`:

```sh
npx tsc --noEmit
npm run lint
npm run build
```

Use the API and database verification commands documented in `HANDOFF.md`. Manually verify the acceptance workflow in a browser, including failure states and mobile layout. Do not use live database writes as a substitute for isolated tests.

## 16. Files to Inspect and Likely Touch

| Path | Relevance |
| --- | --- |
| `web/app/search/page.tsx` | Search state, duplicated grouping, saved-status lookup, and card callbacks. |
| `web/lib/results.ts` | Existing shared result types and grouping; preferred consolidation point. |
| `web/components/DatabaseResultCard.tsx` | Save/Saved control; preserve existing evidence display. |
| `web/components/Navigation.tsx` | SAVED link and current-page indication. |
| `web/app/saved/page.tsx` | New Saved page. |
| `web/app/api/` | Existing server-side proxy pattern; new bookmark routes as needed. |
| `api/app/auth.py` | Existing service-key boundary; not researcher authentication. |
| `api/app/db.py`, `api/app/config.py` | Scoped database pools and configuration. |
| `api/app/search_service.py`, `api/app/schemas.py` | Identity parity, serialization, and existing search contracts. |
| `migrations/`, `supabase/migrations/` | Additive schema/permissions changes if needed. |
| `scripts/sync_supabase_migrations.py`, `api/tests/` | Migration synchronization and integration/security tests. |
| `HANDOFF.md` | Final implementation status, limitations, verification, and next actions. |

These are pointers, not instructions to modify every file. Reinspect the branch before implementation and keep the diff focused.

## 17. Completion Report for Nikhilesh

Report the changed files, exact Save/remove interaction, approved ownership scope, experiment identity used, reviewed/live scope, migration and permission changes, tests/build results, and any deployment steps not performed.

Update `HANDOFF.md` with what actually shipped and any remaining blockers. Do not describe this ticket itself as a completed feature. Verify the remote branch before sharing: the inspected local checkout reports its configured upstream as `[gone]`; this has not been checked against the live remote.

## Claude Execution Brief

Implement Ticket C on the approved HiveBlot branch: a compact Save/Saved control on Search experiment cards and a `/saved` page that reuses those cards with full grouped lanes. Follow the behavior and acceptance criteria above. Reuse existing API/database patterns and the current Supabase database. Confirm the missing researcher-ownership mechanism and live-result scope with Nikhilesh before making those product/security decisions. Do not alter unrelated search or scientific behavior, expose secrets, or apply production migrations without approval. Verify the end-to-end workflow, run the required checks, and update the handoff with accurate results.

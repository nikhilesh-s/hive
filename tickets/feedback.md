# Track F — researcher feedback we can actually analyze

Source: code audit 2026-09-09 (post-UCSF meeting). Hosted beta = Vercel web +
Render API + Supabase `zafombwswztvnjikcsdm`. Env variable names only in this
file; never values.

## Where we stand (verified live 2026-09-09)

- Supabase project **ACTIVE_HEALTHY**, RLS on both tables, Security Advisor
  0 errors / 1 deferred WARN (`pg_trgm` in public). The September 1 alerts
  are resolved (see `super-based-ticket.md`).
- `public.hiveblot_feedback` holds **1 row** (2026-08-18, a pre-launch
  test). Everything from the UCSF meeting onward is real signal.
- Nik can pull all of it today with one command (runs as `postgres`, sees
  everything):

  ```bash
  supabase db query --linked --output-format json "select * from public.hiveblot_feedback order by created_at" | jq '.rows'
  ```

  Second path: `psql "$DB_FEEDBACK_URL"` (the `hive_feedback` role has
  SELECT; `hive_readonly` was deliberately revoked). No API path exists.

## What a beta user can submit today

| Entry point | Writes | File |
|---|---|---|
| Per-field ✓ correct / ✗ incorrect (+ suggested value, comment) / not useful, inside "Evidence & sources" | `scope=field`, `model_value` snapshot next to the human correction | `web/components/EvidencePanel.tsx:287-312` |
| "Which is right?" candidate pick on CONFLICTING / AMBIGUOUS fields | `scope=field`, `type=incorrect`, `suggested_value` = chosen candidate | `EvidencePanel.tsx:307-312` |
| "+ Missing information?" and "⚑ Flag this result" (nine flag types + comment) | `scope=missing_field` / `scope=record` | `EvidencePanel.tsx:565-604` |
| "Did HiveBlot understand what you were looking for?" Yes / Partially / No, with "what did you expect" on Partially/No | `scope=search`, `search_query` | `web/components/SearchFeedback.tsx:49-70` |
| Bottom-right BETA FEEDBACK free text | `scope=ui`, `search_query` | `web/components/BetaFeedback.tsx:67-70` |

Context captured: `record_id`, `stable_row_key` (reseed-proof), `paper_id`,
`field_name`, `model_value`, `search_query`, `ui_location`, anonymous
`session_id` (localStorage), `created_at`. Not captured: DOI, result count,
result rank, `figure_label` (column exists, never written), any person or
lab, and `app_version` is the hardcoded literal `beta-local`
(`api/app/routers/internal.py:170`).

## Gaps that matter for the UCSF trial

1. **No "was this useful" signal.** The instrument measures wrongness in
   detail and usefulness almost not at all. A correct-but-irrelevant result
   leaves no trace.
2. **Zero-result searches are not captured.** `SearchFeedback` renders only
   inside `results.length > 0` (`web/app/search/page.tsx:342-345`). On a
   3-paper corpus "my protein is not here" is the most common and most
   informative event, and we discard it.
3. **No export or aggregate path**, so analysis means hand-written SQL.
4. **Silent loss.** All hosted traffic arrives from the Vercel proxy, so the
   `20/minute` limit keyed on remote address (`api/app/limiter.py:6`,
   `api/app/config.py:53`) is one bucket shared by every UCSF user, and
   shared with search. A 429 or 503 still renders "✓ thanks — recorded"
   (`web/lib/feedback.ts:36-39`, `SearchFeedback.tsx:34`,
   `BetaFeedback.tsx:71`).
5. **No handle on the person.** `session_id` is a browser-local random
   string. Yashvi's named researchers cannot be joined to rows.
6. **The DEMO.md §7 questions have no capture path** other than notes.
7. Live/experimental tier is read-only for feedback by design
   (`DatabaseResultCard.tsx:414`, `EvidencePanel.tsx:544-549`). Not a UCSF
   blocker: the hosted beta is the reviewed corpus only.

Four of the five fixes below need **no schema change**: `feedback_type` is
free TEXT in Postgres (the vocabulary lives in `api/app/schemas.py:274-281`).

## Tickets

### F-0 · Supabase awake and feedback writes end to end — DONE 2026-09-09
Project active, RLS on, 1 row readable via `supabase db query --linked`.
Remaining: insert one row through the **hosted** UI after the next deploy
and read it back (part of F-8).

### F-1 · `scripts/export_feedback.py` — one command, CSV or JSON
- Why: the founder's literal question. Today there is no path from
  "researchers gave feedback" to "we looked at it".
- Acceptance: reads `DB_FEEDBACK_URL` from the environment (never
  hardcoded, never printed); `python scripts/export_feedback.py` writes CSV
  of every column ordered by `created_at` to stdout; `--json`; `--since
  YYYY-MM-DD`; green against `scripts/local_db.py`; one pytest asserting the
  header and one exported row. Output may contain unpublished data pasted by
  researchers: never commit an export.
- Estimate: 0.5 half-day. Depends on: nothing. Owner: Nik.

### F-2 · Capture zero-result searches
- Why: gap 2.
- Acceptance: `SearchFeedback` also renders on the empty-results branch with
  prompt "We found nothing for that — what were you hoping to find?";
  submits `scope=search`, `type=no_results`, the query and free text;
  `no_results` added to `SEARCH_FEEDBACK_TYPES`; tsc/lint clean; a nonsense
  query on local produces a row.
- Estimate: 0.5. Depends on: nothing. Owner: Srushti.

### F-3 · Result-level "This was useful" / "Not what I needed" (+ one-line why)
- Why: gap 1.
- Acceptance: two buttons in the evidence panel's record-level action row;
  `useful` and `not_useful_result` added to `RECORD_FEEDBACK_TYPES`; "Not
  what I needed" opens the existing correction form for a reason; rows carry
  `record_id`, `stable_row_key`, `paper_id`; hidden on live/read-only cards;
  `api/tests/test_record_detail_feedback.py` extended.
- Estimate: 1 (0.5 web, 0.5 api). Depends on: nothing. Owner: Srushti (web)
  + Nik (api).

### F-4 · Three-question end-of-session survey (DEMO.md §7 as rows)
- Why: gap 6. Turns Yashvi's spoken close into queryable data.
- Acceptance: Yashvi supplies final wording for three questions (fields that
  matter most / what is missing / what it would take to trust an unreviewed
  row); `BetaFeedback` gains an optional "Finished a session? Three
  questions" mode; each answered question writes one `scope=ui` row with
  `ui_location=survey_q1..q3`; skipping never blocks; F-1 export shows the
  answers as distinct rows.
- Estimate: 1. Depends on: Yashvi copy first. Owner: Yashvi (content) +
  Srushti (build).

### F-5 · Optional contact with explicit consent, and a real `app_version`
- Why: gap 5, plus demo-laptop clicks and UCSF clicks are indistinguishable.
- Acceptance: `migrations/006_feedback_contact.sql` adds nullable `contact
  TEXT` (idempotent, with `.down.sql`, mirrored by
  `scripts/sync_supabase_migrations.py`, green under
  `api/tests/test_supabase_migrations_sync.py`); no new policy or grant
  needed (confirm with `test_db_access_matrix.py`); UI collects it only
  behind an unchecked opt-in that states the purpose ("so we may follow up
  about this comment"); `contact` excluded from `FeedbackItem` and the
  rehydration query so it never renders in another browser; `app_version`
  read from settings and set per deployment. Free-text placeholders get one
  sentence asking people not to paste unpublished data.
- Estimate: 1. Depends on: F-4. Owner: Nik (migration + api), Srushti (the
  checkbox).

### F-6 · Separate feedback rate limit; stop faking success
- Why: gap 4.
- Acceptance: feedback gets its own, higher limit or a key that
  distinguishes users behind the proxy; `submitFeedback()` returning false
  shows "couldn't save that — try again" instead of a checkmark; verified by
  25 submissions in a minute from one client.
- Estimate: 0.5. Depends on: nothing. Owner: Nik (limit) + Srushti (UI).

### F-7 · Weekly feedback triage
- Why: an export nobody reads is a file. Corrections are labels for the
  evaluation set; Tanvi can tell a real biology correction from a
  misunderstanding.
- Acceptance: F-1 export run weekly during the UCSF trial; each correction
  classified valid / invalid / unclear; anything indicating an extraction
  bug becomes a bio-QA ticket; findings appended to HANDOFF; corrections are
  never auto-applied to `western_blot_records`.
- Estimate: 0.5 per pass. Depends on: F-1. Owner: Tanvi.

### F-8 · Beta release with F-2..F-6 (Vercel + Render) and hosted smoke
- Why: Vercel does not autodeploy this branch and Render `autoDeploy` is
  off; the hosted beta is frozen at `7d80b8b` (API `96678c8`). Nothing above
  reaches a researcher until Nik deploys.
- Acceptance: release branch decision recorded (see `tickets/README.md`
  decision D-0); `vercel deploy --prod` and a Render deploy by Nik; one
  hosted feedback row per new signal inserted and read back with the F-1
  export; test rows deleted; HANDOFF updated with commit SHAs.
- Estimate: 1. Depends on: F-2..F-6. Owner: Nik.

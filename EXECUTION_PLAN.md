# Hive — execution plan

Read this whole file before touching anything. It's written to be self-contained
for a fresh session with no prior context.

## Why this repo exists

The previous implementation was two repos:
- **`Ananya-Jha-code/QBI`** ("HiveBlot" frontend, Next.js) — had a real, working
  search flow, but it was fused with a dead leftover product ("VOC Triage":
  `/molecules`, `/receptors`, `/diseases`, `/oracle`, `lib/data.ts`, a 1.8MB mock
  JSON — none of it linked from nav), plus repo hygiene problems: `.next` build
  output committed (62MB `.git`), duplicate screenshots/videos, stray AI-prompt
  drafts, a hardcoded backend URL, and an always-on uncapped canvas animation.
- **`SuhasKM2001/blot_backend`** (FastAPI, 219 lines total) — its `/search`
  endpoint had GPT write **raw PostgreSQL from user text**, checked it with a
  **substring blocklist** (`if "drop" in sql.lower()`), and executed it via a
  Supabase RPC using what's almost certainly the service-role key. Unauthenticated,
  `CORS allow_origins=["*"]`, no rate limiting, no enforced `LIMIT`, no error
  handling on `/search`. This was the single most urgent finding of the whole
  audit — a live, internet-facing, unauthenticated endpoint executing
  LLM-generated SQL with no real sandboxing.

`nikhilesh-s/hive` is the clean rebuild. **Decisions locked in with the user:**
1. Monorepo: `web/` (frontend) + `api/` (backend), rebuilt together so the
   security fix isn't deferred.
2. Search stays natural-language-to-SQL (not switched to a filter-builder),
   but properly sandboxed: AST-level validation + a dedicated low-privilege
   DB role + a server-enforced `LIMIT`, replacing the substring blocklist.
3. The dead "VOC Triage" app is dropped entirely — only the real flow got rebuilt.
4. **This is a from-scratch deploy** — new Supabase project, new Render service,
   new Vercel project. Nothing is migrated from the old `.env`s; there is no
   existing production data to preserve.
5. **Preserve the frontend as much as possible.** Beyond dropping the dead
   VOC Triage pages and the specific fixes listed below (debounce, paused
   canvas animation, env-configurable backend URL, rebrand text), **do not
   redesign, restyle, or restructure the UI.** The look, copy, layout, and
   component structure of the real HiveBlot flow (`page.tsx`, `search/page.tsx`,
   `about`, `learn`, and all the carried-over components) should stay as close
   to the original as possible. If you think something in the UI should
   change beyond what's listed here, ask first rather than assuming the
   rebuild is a redesign opportunity.
6. **Two API surfaces, not one** — see below. This was added after the
   initial scaffold, so it's already reflected in the code in this repo, not
   something still to build.

## Architecture: internal APIs + one external, agent-facing API

The backend has two distinct surfaces sharing one search pipeline:

- **Internal** (`api/app/routers/internal.py`): `/health`, `/`, `/proteins`,
  `/search`. Called only by `web/`'s server-side `/api/search` route handler
  (Next.js BFF), authenticated with `INTERNAL_API_KEY`. This is a private
  contract between the frontend and its own backend — free to change shape
  as the frontend's needs change.
- **External** (`api/app/routers/external.py`): `POST /v1/search`. The one
  stable, documented endpoint meant for **agents/third-party integrations**
  to call directly, not through the frontend. Versioned (`/v1`) so its
  contract can stay stable independent of internal changes. Authenticated
  against a *set* of keys (`AGENT_API_KEYS`, comma-separated) rather than one
  shared secret, so an individual agent's access can be issued or revoked
  without affecting the frontend or any other agent. It has its own,
  separately-tunable rate limit (`AGENT_RATE_LIMIT`) and a rich OpenAPI
  `summary`/`description` (visible at `/docs`) written for an agent/LLM
  consumer, not a human reading source code.
- Both routers call **the same** `api/app/search_service.py:execute_search`,
  which runs the full `generate_sql → sql_guard.guard_and_limit_sql →
  run_readonly_query` pipeline. There is exactly one implementation of the
  security-critical path — the internal/external split is only about auth,
  rate limits, and API contract stability, never about having two different
  (and therefore two potentially-inconsistent) sandboxing implementations.

If you need to give an agent framework a tool spec, point it at
`GET /openapi.json` (or `/docs` for a human) — `/v1/search`'s description is
already written to double as that tool's description.

## What's already built in this repo (do not redo — verify, don't rewrite)

### `api/` — FastAPI backend
- `app/config.py` — `pydantic-settings` `Settings`, fails fast with a clear
  error if any required env var is missing. Holds `internal_api_key` and
  `agent_api_keys` (comma-separated, exposed as `.agent_api_keys_set`)
  separately — don't collapse these back into one key.
- `app/db.py` — `supabase` client (for the already-safe, parameterized
  `/proteins` and `/` queries) **and** a separate `asyncpg` pool
  (`get_readonly_pool`/`run_readonly_query`) used only to execute the
  validated, LLM-generated SQL from search.
- `app/sql_guard.py` — **the core security fix.** Parses generated SQL with
  `sqlglot`, rejects anything that isn't a single plain `SELECT` against
  `western_blot_records` (no unions, no writes/DDL, no disallowed functions),
  and rewrites in a server-enforced `LIMIT` regardless of what the model
  produced. This is defense layer 1.
- `db/schema.sql` — creates `western_blot_records` and a `hive_readonly`
  Postgres role that only has `SELECT` on that one table. `DB_READONLY_URL`
  (used by `db.py`) must point at this role, not the Supabase service key.
  This is defense layer 2 — even a bug in `sql_guard.py` can't escalate past
  what this role is physically allowed to do.
- `app/auth.py` — `require_internal_key` (checked against `INTERNAL_API_KEY`)
  and `require_agent_key` (checked against the `AGENT_API_KEYS` set, returns
  the matched key so callers can log which agent made the request).
- `app/search_service.py` — the one shared `execute_search()` pipeline, see
  architecture section above.
- `app/routers/internal.py` / `app/routers/external.py` — the two routers.
- `app/limiter.py` — the single shared `slowapi` `Limiter` instance both
  routers and `main.py` reference.
- `app/main.py` — just wires the app together now: CORS locked to
  `ALLOWED_ORIGINS` (not `*`, and only meaningful for the internal router —
  `/v1/search` is guarded by `require_agent_key`, not CORS), registers both
  routers, registers the rate-limit exception handler.
- `app/nlp.py` — the NL→SQL prompt (`generate_sql`), moved over as-is. The old
  repo's unused `parse_query`/Qwen code path was **deliberately dropped** —
  it was dead code contradicting the README (README claimed Qwen, live code
  path used GPT-4.1-mini). Don't resurrect it without a real decision to use it.
- `app/schemas.py` — `confidence` is typed `float | None` (0–1) to match the
  frontend's real `DatabaseResult` type. **Open decision, see step 3 below.**

### `web/` — Next.js frontend (preserved, not redesigned — see decision 5 above)
- Carried over as-is, with only the fixes listed: `app/page.tsx` (home +
  inline results), `app/search/page.tsx`, `app/about/page.tsx`,
  `app/learn/page.tsx`,
  `components/{SearchInput,ResultsTable,ResultsCard,DatabaseResultCard,Navigation,OrbitCanvas}.tsx`.
- Dropped entirely: `/molecules`, `/receptors`, `/diseases`, `/oracle`,
  `lib/data.ts`, the 1.8MB mock JSON dataset — none of it was linked from nav
  in the old repo; it was dead weight, not a feature to preserve.
- `app/api/search/route.ts` — calls the backend's *internal* `/search`
  endpoint. No longer hardcodes `blot-backend.onrender.com`; reads
  `API_BASE_URL` and attaches `Authorization: Bearer ${INTERNAL_API_KEY}`.
  This must never be pointed at an agent key or at `/v1/search`.
- `components/SearchInput.tsx` — now debounces `onSearch` (400ms, Enter key
  bypasses the debounce) since every search now costs a real OpenAI call —
  firing on every keystroke was fine when it was free (client-side JSON
  filtering); it isn't anymore.
- `components/OrbitCanvas.tsx` — now uses an `IntersectionObserver` to pause
  its `requestAnimationFrame` loop when off-screen, instead of running forever.
- Kept only the one background video actually referenced (`hive-background-v3.mp4`
  → renamed `hive-background.mp4`), dropped the 3 unused near-duplicates.
- `.gitignore` (both root-level configs) explicitly excludes `.next/`,
  `*.tsbuildinfo`, `node_modules/`, `.env*` from day one.
- Rebrand cleanup done: `package.json` name, and the "voc triage" label baked
  into `OrbitCanvas`'s canvas text, both fixed — this is copy/label
  correction, not a design change, and is in scope per decision 5.

**None of this has been run yet** (`npm install`/`npm run dev`,
`pip install`/`uvicorn`). That's step 1 below.

## Remaining steps — do these in order

### 1. Verify both apps actually run
- `api/`: create a venv, `pip install -r requirements.txt` (or `pip install -e .`),
  confirm `python -c "import app.main"` doesn't blow up on missing env vars in
  a sane way (it should raise a clear pydantic validation error, not a random
  crash) — you'll need dummy env vars for this, real ones come in step 3.
- `web/`: `npm install`, `npm run build` (not just `dev` — catches type errors
  the old repo probably had, `next.config.ts` should be checked for
  `ignoreBuildErrors`/`ignoreDuringBuilds` flags that would hide problems).
  If `npm run build` surfaces issues, fix them without changing the visual
  design (decision 5) — these should be type/config fixes, not rewrites.

### 2. Write and run tests for `sql_guard.py` — the highest-value test in the whole repo
No tests exist yet. Write `api/tests/test_sql_guard.py` covering at minimum:
- A normal generated query (`SELECT * FROM western_blot_records WHERE target ILIKE '%p53%'`)
  passes through and gets a `LIMIT` appended.
- `SELECT * FROM auth.users` → rejected (wrong table).
- `SELECT * FROM western_blot_records; DROP TABLE western_blot_records;` →
  rejected (multiple statements).
- A query with a huge or missing `LIMIT` → clamped to `min(requested, 500)`.
- `SELECT pg_sleep(10) FROM western_blot_records` → rejected (disallowed function).
- A `UNION`-based query trying to reach another table → rejected.
- Confirm these with **real invocations of `guard_and_limit_sql`**, not just
  reasoning about the code — `sqlglot`'s exact AST shapes are easy to get
  subtly wrong (e.g. whether `LIMIT` shows up as `stmt.args["limit"]` in every
  case). Run `pytest` and actually look at the output.
- Add one test for `auth.require_agent_key`: a key not in `AGENT_API_KEYS`
  is rejected, and removing a key from the set immediately invalidates it
  (no caching bug where an old key keeps working).

### 3. Provision the new Supabase project
- Create the project.
- Run `api/db/schema.sql` in the SQL editor. Read its inline comments — it
  creates `hive_readonly` without a password; set the password as a separate
  `ALTER ROLE` statement (commented example is in the file) so a real secret
  never sits in a checked-in file.
- Decide the `confidence` column's real type now, before any data is loaded —
  `schemas.py` currently assumes numeric (0–1). If the extraction pipeline
  naturally produces `"high"/"medium"/"low"`, either convert to a score before
  insert, or change the schema/column together — don't let frontend, backend,
  and DB drift on this like the old repo did.

### 4. Fill in both `.env` files
- `api/.env` from `api/.env.example`: `SUPABASE_URL`/`SUPABASE_KEY` (new
  project), `OPENAI_KEY`, `DB_READONLY_URL` (the `hive_readonly` connection
  string from step 3), `INTERNAL_API_KEY` and at least one entry in
  `AGENT_API_KEYS` (generate each with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"` — different
  values, don't reuse one key for both), `ALLOWED_ORIGINS` (your Vercel URL
  once you have it, plus `localhost:3000` for now).
- `web/.env` from `web/.env.example`: `API_BASE_URL` (local:
  `http://localhost:8000`), `INTERNAL_API_KEY` (must match the backend's
  `INTERNAL_API_KEY` — never one of the `AGENT_API_KEYS` values).

### 5. Local end-to-end test
- Start `api/` (`uvicorn app.main:app --reload`), start `web/` (`npm run dev`).
- Do a real search from the browser, confirm results render in `ResultsTable`,
  and confirm the UI looks like the original (decision 5) — this is a
  regression check, not just a functionality check.
- Separately, call `POST /v1/search` directly (e.g. via `curl` or `httpx`)
  with an `AGENT_API_KEYS` value, confirm it works standalone without the
  frontend involved at all — that's the point of it being an external API.
- Confirm `/molecules`, `/receptors`, `/diseases`, `/oracle` 404 rather than
  serving stale content (they shouldn't exist at all in this build).

### 6. Security verification (don't skip this — it's the whole point of the rebuild)
- Call `/search` with no `Authorization` header → expect 401. Same for
  `/v1/search`.
- Call `/search` (or `/v1/search`) with a query engineered to make GPT emit
  SQL touching another table (e.g. ask something like "show me all users and
  their emails") → confirm `sql_guard` rejects it (400), not that it
  silently returns empty.
- Confirm an `INTERNAL_API_KEY` does **not** work against `/v1/search`, and
  an `AGENT_API_KEYS` value does **not** work against `/search` — the two
  auth sets must not accidentally overlap in practice.
- Hammer `/search` past `SEARCH_RATE_LIMIT`, and `/v1/search` past
  `AGENT_RATE_LIMIT` independently → expect 429s from each without one
  affecting the other's budget.
- Confirm the DB connection used for search really is `hive_readonly` (not
  the Supabase service key) by checking `DB_READONLY_URL` in `.env` and
  trying (from `psql`, as that role) to `SELECT` from a different table or
  `INSERT` into `western_blot_records` — both should fail with a permission error.

### 7. Repo hygiene check before/after first push
- Confirm `.git` doesn't contain `.next/`, `node_modules/`, or any `.env` file
  (`git ls-files | grep -E '\.env$|\.next/|node_modules/'` should be empty).
- Confirm no stray debug/prompt files got copied over from the old repos.

### 8. Deploy
- `api/` → new Render (or equivalent) web service, root `api/`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, all env vars from step 4
  set in the platform's dashboard (never committed).
- `web/` → new Vercel project, root `web/`, `API_BASE_URL` set to the deployed
  API's URL, `INTERNAL_API_KEY` matching, `ALLOWED_ORIGINS` on the API updated
  to the real Vercel URL once you have it (not `*`).
- Smoke test the production URLs the same way as step 5, including a direct
  `/v1/search` call from outside the frontend.
- Whatever agent/integration is meant to call `/v1/search` in production
  should get its own dedicated entry in `AGENT_API_KEYS`, not share one
  generic key with everything else that might call it later.

### 9. Once verified, decide what happens to the old repos/services
`QBI` and `blot_backend` (and their Vercel/Render deployments) still exist and
are still live with the unauthenticated raw-SQL endpoint until you take them
down or repoint DNS/domains. Flag this to whoever owns those deployments —
rebuilding `hive` doesn't retire the old vulnerable one automatically.

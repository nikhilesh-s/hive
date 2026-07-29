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

## What's already built in this repo (do not redo — verify, don't rewrite)

### `api/` — FastAPI backend
- `app/config.py` — `pydantic-settings` `Settings`, fails fast with a clear
  error if any required env var is missing.
- `app/db.py` — `supabase` client (for the already-safe, parameterized
  `/proteins` and `/` queries) **and** a separate `asyncpg` pool
  (`get_readonly_pool`/`run_readonly_query`) used only to execute the
  validated, LLM-generated SQL from `/search`.
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
- `app/auth.py` — `require_api_key` dependency (`Authorization: Bearer <API_KEY>`),
  applied to `/search` and `/proteins`.
- `app/main.py` — wires it all together: CORS locked to `ALLOWED_ORIGINS`
  (not `*`), `slowapi` rate limiting on `/search` (`SEARCH_RATE_LIMIT`, default
  20/min), async handlers, try/except around every DB/OpenAI call returning
  clean JSON errors instead of raw tracebacks.
- `app/nlp.py` — the NL→SQL prompt (`generate_sql`), moved over as-is. The old
  repo's unused `parse_query`/Qwen code path was **deliberately dropped** —
  it was dead code contradicting the README (README claimed Qwen, live code
  path used GPT-4.1-mini). Don't resurrect it without a real decision to use it.
- `app/schemas.py` — `confidence` is typed `float | None` (0–1) to match the
  frontend's real `DatabaseResult` type. **Open decision, see below.**

### `web/` — Next.js frontend
- Carried over only the real flow: `app/page.tsx` (home + inline results),
  `app/search/page.tsx`, `app/about/page.tsx`, `app/learn/page.tsx`,
  `components/{SearchInput,ResultsTable,ResultsCard,DatabaseResultCard,Navigation,OrbitCanvas}.tsx`.
- Dropped entirely: `/molecules`, `/receptors`, `/diseases`, `/oracle`,
  `lib/data.ts`, the 1.8MB mock JSON dataset — none of it was linked from nav
  in the old repo; it was dead weight.
- `app/api/search/route.ts` — no longer hardcodes `blot-backend.onrender.com`;
  reads `API_BASE_URL` (server-only env var) and attaches
  `Authorization: Bearer ${API_KEY}` to the backend call.
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
  into `OrbitCanvas`'s canvas text, both fixed.

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

### 2. Write and run tests for `sql_guard.py` — this is the highest-value test in the whole repo
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
  string from step 3), `API_KEY` (generate with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`),
  `ALLOWED_ORIGINS` (your Vercel URL once you have it, plus `localhost:3000`
  for now).
- `web/.env` from `web/.env.example`: `API_BASE_URL` (local: `http://localhost:8000`),
  `API_KEY` (must match the backend's).

### 5. Local end-to-end test
- Start `api/` (`uvicorn app.main:app --reload`), start `web/` (`npm run dev`).
- Do a real search from the browser, confirm results render in `ResultsTable`.
- Confirm `/molecules`, `/receptors`, `/diseases`, `/oracle` 404 rather than
  serving stale content (they shouldn't exist at all in this build).

### 6. Security verification (don't skip this — it's the whole point of the rebuild)
- Call `/search` with no `Authorization` header → expect 401.
- Call `/search` with a query engineered to make GPT emit SQL touching another
  table (e.g. ask something like "show me all users and their emails") →
  confirm `sql_guard` rejects it (400), not that it silently returns empty.
- Hammer `/search` past `SEARCH_RATE_LIMIT` → expect 429s.
- Confirm the DB connection used for `/search` really is `hive_readonly` (not
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
  API's URL, `API_KEY` matching, `ALLOWED_ORIGINS` on the API updated to the
  real Vercel URL once you have it (not `*`).
- Smoke test the production URLs the same way as step 5.

### 9. Once verified, decide what happens to the old repos/services
`QBI` and `blot_backend` (and their Vercel/Render deployments) still exist and
are still live with the unauthenticated raw-SQL endpoint until you take them
down or repoint DNS/domains. Flag this to whoever owns those deployments —
rebuilding `hive` doesn't retire the old vulnerable one automatically.

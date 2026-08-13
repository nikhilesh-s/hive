# HiveBlot beta — deployment guide (no secrets in this file)

The beta is three pieces: **Postgres** (Supabase in prod, embedded pgserver
locally), **FastAPI** (`api/`), **Next.js** (`web/`). Everything below is
config + commands; all secret VALUES live in env vars / `.env` files only.

## 1. Database (Supabase project, once)
In the Supabase SQL editor (or psql), in order:
1. `api/db/schema.sql` — base table, pg_trgm index, `hive_readonly` role
2. `migrations/001_evidence_record.sql` — biological Evidence Record columns
3. `migrations/002_feedback.sql` — `hiveblot_feedback` + `hive_feedback` role
4. Set passwords (SQL editor):
   `ALTER ROLE hive_readonly WITH PASSWORD '<generated>';`
   `ALTER ROLE hive_feedback WITH PASSWORD '<generated>';`
5. Seed the demo records (dedicated script, idempotent per paper):
   `export SEED_DATABASE_URL='<owner connection string>'` then
   `.venv/bin/python scripts/seed_remote.py eval/demo/*/supabase_rows.json`
   (`--check` prints row counts only; refuses restricted roles; drops keys
   missing from an older remote schema and says so).

## 2. API (`api/`, FastAPI)
Any container/VM host (Fly.io, Railway, Render, EC2…):
- Run: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (deps:
  `pip install -r api/requirements.txt`, Python ≥3.13)
- Health check: `GET /health` (no auth)
- Env (names only): `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_KEY` (optional —
  empty ⇒ deterministic bio_query search), `DB_READONLY_URL` (hive_readonly),
  `DB_FEEDBACK_URL` (hive_feedback), `INTERNAL_API_KEY`, `AGENT_API_KEYS`,
  `ALLOWED_ORIGINS` (set to the web origin, e.g. `https://hiveblot.vercel.app`),
  `SEARCH_RATE_LIMIT`, `AGENT_RATE_LIMIT`.

## 3. Web (`web/`, Next.js)
Vercel (or any Node host): root `web/`, `npm run build`.
- Env: `API_BASE_URL` (the deployed API origin), `INTERNAL_API_KEY`
  (must equal the API's). Both are server-side only (used in route handlers);
  nothing secret ships to the browser.

## 4. Smoke test after deploy
1. `GET <api>/health` → `{"status":"ok"}`
2. Search `phospho STAT3 Tyr705` in the web UI → real STAT3 card
3. Expand → evidence panel loads (`GET /records/{id}` via the web proxy)
4. Click 👍 on a field → row appears in `hiveblot_feedback`

## Local development (no cloud at all)
```bash
.venv/bin/python scripts/local_db.py up
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json
cd api && .venv/bin/python -m uvicorn app.main:app --port 8000
cd web && npm run dev
```

## Known deployment gaps (deliberate, documented)
- Figure-crop serving works where the crop archive exists (local runs):
  `GET /records/{id}/crop` serves the record's own panel PNG, path-validated
  against `CROP_BASE_DIR` (default: the local pipeline run dir). Deployments
  without the crop archive gracefully degrade to text-only evidence.
- `/proteins` and `/` require real Supabase (PostgREST); `/search`,
  `/records/{id}`, `/feedback` run on plain Postgres.

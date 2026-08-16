# HiveBlot beta — deployment guide (no secrets in this file)

The beta is three pieces: **Postgres** (Supabase in prod, embedded pgserver
locally), **FastAPI** (`api/`), **Next.js** (`web/`). Everything below is
config + commands; all secret VALUES live in env vars / `.env` files only.

## 1. Database (fresh Supabase project — TOMORROW'S FLOW)
Preferred: the Supabase CLI against `supabase/migrations/` (timestamped copies
of the canonical SQL; a pytest drift guard keeps them byte-identical — edit the
canonical files and run `scripts/sync_supabase_migrations.py`, never edit the
copies).

```bash
# after creating the project in the Supabase dashboard:
supabase login
supabase link --project-ref <PROJECT_REF>     # from the project's URL/settings
supabase db push --dry-run                    # review: 4 migrations, additive
supabase db push                              # applies base schema + 001 + 002 + 003
```
Then set the two restricted-role passwords (SQL editor — generated values, do
not reuse anything):
```sql
ALTER ROLE hive_readonly WITH PASSWORD '<generated>';
ALTER ROLE hive_feedback WITH PASSWORD '<generated>';
```
Then seed the reviewed demo records (idempotent per paper):
```bash
export SEED_DATABASE_URL='<owner/postgres connection string>'   # NOT a restricted role
.venv/bin/python scripts/seed_remote.py eval/demo/*/supabase_rows.json
.venv/bin/python scripts/seed_remote.py --check                 # expect 475 rows
```
Fallback (no CLI): run the four canonical files in the SQL editor in order —
`api/db/schema.sql`, `migrations/001_evidence_record.sql`,
`migrations/002_feedback.sql`, `migrations/003_stable_row_key.sql` — then
passwords + seed as above. Do NOT run both
the CLI flow and the SQL-editor flow; everything is idempotent, but pick one.

**Security invariants (already encoded in the SQL, verify after push):**
`hive_readonly` = SELECT-only on evidence + feedback. `hive_feedback` =
INSERT+SELECT on `hiveblot_feedback` ONLY (+ its id sequence) — it holds **no
grant of any kind on `western_blot_records`** and cannot UPDATE or DELETE
anything. Neither restricted DSN ever reaches browser JavaScript: both live in
API-server env vars; the web app talks only to the API through the Next.js
server-side proxy with `INTERNAL_API_KEY`.

## 2. API (`api/`, FastAPI)
Any container/VM host (Fly.io, Railway, Render, EC2…):
- Run: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (deps:
  `pip install -r api/requirements.txt`, Python ≥3.13)
- Health check: `GET /health` (no auth)
- Env NAMES (exact, from `api/app/config.py` — never commit values):
  required: `SUPABASE_URL`, `SUPABASE_KEY` (may stay empty → only `/proteins`
  and `/` degrade), `OPENAI_KEY` (empty ⇒ deterministic bio_query search),
  `DB_READONLY_URL` (hive_readonly DSN), `DB_FEEDBACK_URL` (hive_feedback DSN),
  `INTERNAL_API_KEY`, `AGENT_API_KEYS`, `ALLOWED_ORIGINS` (the web origin);
  optional with defaults: `SEARCH_RATE_LIMIT`, `AGENT_RATE_LIMIT`,
  `TABLE_NAME`, `MAX_SEARCH_LIMIT`, `CROP_BASE_DIR` (crop archive dir; absent
  archive ⇒ text-only evidence), `OPENAI_MODEL`. Model-provider vars
  (`WBM_LLM_BACKEND`, `AWS_*`, `ANTHROPIC_API_KEY`) belong to the INGESTION
  engine later, not to this API.

## 3. Web (`web/`, Next.js)
Vercel (or any Node host): root `web/`, `npm run build`.
- Env: `API_BASE_URL` (the deployed API origin), `INTERNAL_API_KEY`
  (must equal the API's). Both are server-side only (used in route handlers);
  nothing secret ships to the browser.

## 4. Smoke test after deploy (tomorrow's checklist)
1. `GET <api>/health` → `{"status":"ok"}`
2. Web UI: type `phospho STAT3 Tyr705`, press Enter/SEARCH → 3 grouped
   experiment cards (18 lane records), STAT3 · phospho-Tyr705, Hep3B,
   CST #9145, expected 88.1 kDa
3. Search `co-IP PIK3CA` → co-IP cards with IP bait = PIK3CA
4. Expand a card → evidence panel loads (`GET /records/{id}` via web proxy)
5. Crop endpoint: `GET /records/{id}/crop` → PNG where the crop archive is
   deployed; clean 404 + text-only evidence panel where it is not
6. Click 👍 on a field → row appears in `hiveblot_feedback` (feedback role)
7. CORS: browser devtools show no blocked API calls (`ALLOWED_ORIGINS` = web
   origin; the browser only ever talks to the Next.js proxy)
8. No secrets client-side: view-source/devtools network — no DSNs, no
   `INTERNAL_API_KEY`, no Supabase service key in any browser-delivered asset

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

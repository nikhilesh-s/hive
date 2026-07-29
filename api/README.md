# Hive API

FastAPI backend for Hive. Serves Western Blot records extracted from
scientific papers, stored in Supabase, via keyword (`/proteins`) and
natural-language (`/search`) queries.

## How `/search` works

1. GPT (`OPENAI_MODEL`, default `gpt-4.1-mini`) turns the user's question into
   a PostgreSQL `SELECT` (`app/nlp.py`).
2. `app/sql_guard.py` parses that SQL into an AST (via `sqlglot`) and rejects
   anything that isn't a single `SELECT` against `western_blot_records`,
   rejects disallowed functions, and rewrites in a server-enforced `LIMIT`
   regardless of what the model produced.
3. The validated query runs through a **dedicated Postgres role that only has
   SELECT on `western_blot_records`** (`DB_READONLY_URL`, see `db/schema.sql`)
   - not the Supabase service-role key. A bug in step 2 still can't turn into
   a full-database read/write.

`/search` and `/proteins` require `Authorization: Bearer <API_KEY>` and are
rate-limited (`SEARCH_RATE_LIMIT`, default 20/minute) since each call costs
an OpenAI request.

## Setup

1. Create a new Supabase project.
2. Run `db/schema.sql` in the Supabase SQL editor (creates the table and the
   `hive_readonly` role - read the comments inline, set that role's password
   as a separate step before copying it into `.env`).
3. `cp .env.example .env` and fill in the values.
4. `pip install -r requirements.txt` (or `pip install -e .` / `uv sync`)
5. `uvicorn app.main:app --reload`

## Endpoints

| Method | Path        | Auth | Notes |
|--------|-------------|------|-------|
| GET    | `/health`   | none | liveness check for uptime pings |
| GET    | `/`         | none | Supabase connectivity check, returns 5 sample rows |
| GET    | `/proteins` | Bearer | keyword search on `target` |
| POST   | `/search`   | Bearer + rate-limited | natural-language search |

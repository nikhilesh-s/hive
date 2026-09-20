# HiveBlot beta: hosting status

Checked 2026-09-20 against branch `feature/bio-context-beta` @ `e0d2089` (working tree clean).

## Status: LIVE, both free plans, working end-to-end

Web, API, and DB are all up and talking to each other correctly. No blockers found.

## URLs

- Web: https://hiveblot-beta.vercel.app (Vercel, project `hiveblot-beta`, Hobby)
- API: https://hiveblot-api.onrender.com (Render, service `hiveblot-api` / `srv-da1rbvs9v7es738635ug`, Free)
- DB: Supabase `zafombwswztvnjikcsdm` (Free). Not curl-checked directly, only through the API

## Live checks (curl, `-m 90`)

| Check | Result |
|---|---|
| `GET /health` (API direct) | 200, `{"status":"ok"}`, 0.26s. Service was already warm, no cold start hit |
| `GET /` (API direct) | 200, route index JSON |
| `GET /docs` (API direct) | 200. FastAPI auto-docs are enabled and public (not disabled in `main.py`) |
| `GET /proteins` no auth (API direct) | 401 `{"detail":"Missing bearer token"}`. Internal auth enforced, as documented |
| `GET /` (web) | 200, title "HiveBlot — Western blot evidence search (beta)" (the page title as served) |
| `POST /api/search` (web proxy → API `/search`) | 200, real results for "phospho STAT3 Tyr705" (18 rows) |
| `GET /api/record/1189` (web proxy → API `/records/{id}`) | 200, full evidence record |
| `GET /api/record/1189/crop` (web proxy → API `/records/{id}/crop`) | 200, real PNG (1422x860) |
| `GET /health` with `Origin: https://hiveblot-beta.vercel.app` | `access-control-allow-origin` echoes the Vercel origin. CORS correctly scoped |

Record/crop endpoints 404 on id `1` and `5` (stale ids from prior smoke-test cleanup mentioned in HANDOFF.md) but work on a real id pulled from a live search (`1189`). Not a bug, just don't test with guessed ids.

## Env var names required (values not inspected/recorded)

API (Render, from `api/app/config.py` and `render.yaml`):
- `DB_READONLY_URL` (secret)
- `DB_FEEDBACK_URL` (secret)
- `SUPABASE_KEY` (secret, unused since migration 004 but still read)
- `INTERNAL_API_KEY` (secret, must match web's value)
- `SUPABASE_URL` (plain)
- `OPENAI_KEY` (plain, empty = deterministic search)
- `AGENT_API_KEYS` (plain, empty = `/v1/search` closed)
- `ALLOWED_ORIGINS` (plain, comma-separated origins)

Web (Vercel, from `web/.env.example`):
- `API_BASE_URL`
- `INTERNAL_API_KEY` (must equal API's value; never `NEXT_PUBLIC_`-prefixed)

## Consistency check

Everything lines up. No mismatches found between `render.yaml`, `api/app/config.py`, `web/.env.example`, and `DEPLOYMENT.md`:
- `ALLOWED_ORIGINS` in `render.yaml` (`https://hiveblot-beta.vercel.app,http://localhost:3000`) matches the live Vercel origin and was confirmed live via the CORS header check above.
- Branch is `feature/bio-context-beta` consistently in `render.yaml`, `DEPLOYMENT.md`, and the actual deployed commit history (`HANDOFF.md`).
- `healthCheckPath: /health` in `render.yaml` matches the real route in `api/app/routers/internal.py` and returns 200.
- `autoDeploy: false` in `render.yaml` matches `DEPLOYMENT.md`'s described manual-deploy workflow.
- Env var names match 1:1 between `render.yaml`'s `envVars` list and `Settings` fields in `api/app/config.py` (snake_case to SCREAMING_SNAKE via pydantic-settings' default env mapping).
- `web/.env.example`'s `API_BASE_URL`/`INTERNAL_API_KEY` match what `web/app/api/*/route.ts` actually read (`process.env.API_BASE_URL`, `process.env.INTERNAL_API_KEY`), and those proxies are confirmed to actually hit the Render origin (verified live, not just by reading code).

One thing worth flagging but not a bug: `api/Dockerfile` bakes crops into an absolute path that mirrors the original laptop authoring path (`/Users/niks/hive/western_blot_miner/data/pdf_runs/`), and `CROP_BASE_DIR` is set to match. This is called out and justified in `DEPLOYMENT.md` and `api/Dockerfile` comments (records store absolute `image_crop_ref` values, so the container reproduces the same absolute path). It works today (crop fetch confirmed live) but is brittle if the corpus is ever re-authored from a different path. `HANDOFF.md` already tracks "relative crop refs" as a known follow-up.

## Blockers

None. Stack is fully deployed and functioning.

## Manual steps still needed

None found. Per `DEPLOYMENT.md` and `HANDOFF.md`, the beta was already fully deployed (2026-09-02) and frozen. No first-time setup, no pending dashboard clicks, no missing secrets detected (the API would fail startup / return 500s on protected routes if secrets were missing, and it doesn't).

Plan confirmation: Render service is on `plan: free` in `render.yaml` (unchanged), Vercel project is Hobby per `DEPLOYMENT.md`. No plan changes made or needed.

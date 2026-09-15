# HiveBlot — demo-day architecture, experiments and plan (EXPERIMENTAL track)

**Status:** scaffolded on `experimental/demo-day` (2026-09-05); made to run
locally end-to-end on `experimental/ucsf-demo-2026-09-09` (2026-09-09: the
unified `/experimental/research` page, the `claude_cli` model backend, fixed
open-access PDF acquisition, CI, `scripts/demo_check.py`). The frozen UCSF
beta on `feature/bio-context-beta` is untouched.

Goal: at UCSF, a researcher names a paper they care about, HiveBlot reads it
in front of them and returns experiment-level blot evidence they can
interrogate, on top of the reviewed corpus that is already trustworthy. Three
papers stops being the story; *any open-access paper, read live, clearly
labelled unreviewed* becomes the story — without touching the honesty that
makes the beta credible.

---

## 1. What is built (this branch)

```
                 ┌────────────────────────── Browser / Next.js ──────────────────────────┐
                 │ /search (reviewed, frozen)   /experimental/live   /experimental/ask    │
                 │ /experimental/densitometry   (server-side proxies, INTERNAL_API_KEY)  │
                 └───────────────────────────────────┬───────────────────────────────────┘
                                                     │
        ┌────────────────────────────── FastAPI (Dockerfile.experimental) ───────────────────────────┐
        │ DISCOVER  POST /experimental/papers/search                                                 │
        │           Valency Bond MCP (semantic_search_papers …, bearer VALENCY_API_TOKEN)             │
        │           + PubMed Central OA search (NCBI E-utilities) as always-on fallback              │
        │                                                                                            │
        │ EXTRACT   POST /experimental/ingest {doi}  → background job                                │
        │           DOI → NCBI idconv → Europe PMC-listed OA PDF (else Unpaywall OA locations)         │
        │           → pdf_preprocess (PyMuPDF render, OpenCV panel candidates)                        │
        │           → run_records_stage (model claims → deterministic biology → Evidence Records)     │
        │           → rows tagged review_tier='live_unreviewed' + crops as bytes                      │
        │           GET /experimental/ingest/{job}  (stepper: fetching → preprocessing →              │
        │                                            extracting → loading → done|failed)             │
        │                                                                                            │
        │ SEARCH    POST /experimental/search  (same parser + sql_guard, pinned to the live table)    │
        │           GET  /experimental/records/{id}, /crop   (live tier detail + crop)                │
        │                                                                                            │
        │ ASK       POST /experimental/ask {question, doi?}                                           │
        │           deterministic retrieval over reviewed (+ live) → numbered evidence blocks         │
        │           → Claude answers ONLY from the blocks, cites [E#]; citations validated            │
        │                                                                                            │
        │ MEASURE   POST /experimental-densitometry {record_id | image, region, lane_bounds, labels}  │
        │           OpenCV: background opening → band row → lane boxes → relative intensity           │
        │           uncalibrated, never stored                                                        │
        └──────────────┬──────────────────────────────┬──────────────────────────────────────────────┘
                       │ hive_readonly (SELECT)        │ hive_ingest (INSERT/DELETE live tables only)
        ┌──────────────▼──────────────────────────────▼──────────────────────────────────────────────┐
        │ Supabase Postgres (migration 005, RLS on everything)                                        │
        │  western_blot_records  (reviewed, 475 rows — READ ONLY for every app role)                  │
        │  western_blot_records_live (+ review_tier, job_id)   ingest_jobs   ingest_crops (bytea)     │
        └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

Design rules that keep the beta honest while adding live ingestion:

- **Two tiers, never merged.** Live rows live in `western_blot_records_live`.
  The reviewed table has no write path from the API, before or after this
  branch. Cards from the live tier carry a `LIVE · UNREVIEWED` badge; their
  evidence panel is read-only (no feedback into the reviewed feedback table).
- **Same engine.** Live extraction is the exact pipeline that produced the
  reviewed corpus (`pipeline.run_records_stage`), so every status
  (SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING), provenance envelope and
  validation flag exists on live rows too. Nothing is a lighter "demo mode".
- **Legal full text only.** The PDF Europe PMC lists for the PMCID, else
  Unpaywall's open-access locations (only with a real `UNPAYWALL_EMAIL`).
  Discovery marks `oa_pdf` so the UI offers extraction only where a PDF
  exists; a paywalled DOI fails fast with a clear message; nothing is scraped.
- **Same security model.** Every experimental route needs the internal key;
  new tables are RLS'd with explicit per-role policies; `hive_ingest` cannot
  touch the reviewed table or feedback (`test_db_access_matrix.py` covers it).
- **Densitometry is a reading aid, not data.** Relative within one image,
  disclaimer on every response, `stored: false`, FUTURE intensity columns
  stay NULL. The `/learn` statement "HiveBlot does not measure intensity"
  remains true for Evidence Records. v0.2 (2026-09-14): researcher-drawn
  region + lane bounds, per-lane quality state, clipped-core / no-signal /
  unstable-reference refusals (`relative: null`), perturbation envelope,
  method + threshold metadata in every response, JSON/CSV export.

Files: `api/app/experimental/{ingest,router,ask,densitometry_router}.py`,
`api/app/valency.py`, `western_blot_miner/{fulltext,densitometry}.py`,
`migrations/005_experimental_live_tables.sql`, `api/Dockerfile.experimental`,
`web/app/experimental/{live,ask,densitometry}/page.tsx`,
`web/app/api/experimental/**`, `scripts/experiments/*.py`.

## 2. What it needs from Nik (blocking, in order)

| # | Item | Why | Where it goes |
|---|---|---|---|
| 1 | **Model backend.** LOCAL demo: `WBM_LLM_BACKEND=claude_cli` uses the already-authenticated Claude Code install (no key; proven 2026-09-09 for text and for the image pathway on a real crop). HOSTED: `ANTHROPIC_API_KEY` + `WBM_LLM_BACKEND=anthropic`. Optional `WBM_MODEL`. | live extraction and paper QA call a model; without one the job fails fast and /ask returns retrieval only | local `api/.env` / experimental API service env |
| 2 | **Valency token** `VALENCY_API_TOKEN` (Settings page in app.valency.io; Srushti) | semantic paper discovery; PMC fallback works without it | experimental API service env |
| 3 | **Migration 005** on the beta project (`supabase db push`, after `--dry-run` shows only `20260905000006_experimental_live_tables.sql`) + `ALTER ROLE hive_ingest WITH PASSWORD '<generated>'` | live tables + role | Supabase |
| 4 | `DB_INGEST_URL` (hive_ingest pooler DSN, session mode 5432) | the API's write path for the live tier | experimental API service env |
| 5 | **Second Render service** `hiveblot-api-experimental` from `api/Dockerfile.experimental`, branch `experimental/demo-day`, free plan, same env as `hiveblot-api` + items 1–4 | keeps the frozen beta API untouched | Render |
| 6 | **Vercel preview** of `experimental/demo-day` with `API_BASE_URL` = the experimental Render origin | separate URL for the demo; production alias stays on the frozen beta | Vercel |

Everything else runs today: `EXPERIMENTAL_ENABLED=true` is the default on
this branch, the local stack (`scripts/local_db.py up` applies 005; `status`
prints `DB_INGEST_URL`) runs all three pages, and the test suites are green.

## 3. Demo-day flow (live DOI ingestion)

**Pre-warm (the evening before, Suhas).** Ingest 3–5 papers UCSF is likely to
care about (ask the lab for DOIs in advance; otherwise pick open-access blot
papers on their targets) through `/experimental/live`. Live rows persist in
Postgres, crops in `ingest_crops`, so the demo can open them instantly even if
Render restarts. Run `scripts/experiments/live_ingest_eval.py` on the three
reviewed DOIs and keep the agreement table handy (section 5, L1).

**Live (Nik, ~4 min).**
1. Search page, reviewed corpus, one flagship query (trust story, 60 s).
2. `/experimental/live`: type a researcher's target ("STAT3 phosphorylation
   hepatocellular carcinoma") → Valency/PMC list → pick one → **Extract**.
   The stepper shows fetching → preprocessing → extracting → loading with the
   model backend named. Typical wall time: 60–180 s for a 10–12 page paper
   (5–10 panels × one model call each). Keep talking about what each stage is;
   if the room is impatient, switch to a pre-warmed paper.
3. Cards appear with `LIVE · UNREVIEWED`; open **Evidence & sources** on one:
   same provenance, same statuses, real crop. Say: *"same engine, no human
   review, that badge is the difference."*
4. `/experimental/ask`: ask one question about that paper; show the answer's
   citations pointing at the evidence blocks below it.
5. `/experimental/densitometry`: load one crop, box a strip, show relative
   intensities and the disclaimer. Say what it is not.

**Fallbacks.** Paywalled DOI → the job says so; have a PMC-indexed DOI ready.
Model outage → job fails at "extracting"; switch to pre-warmed rows. Valency
down → PMC search fills the list automatically (`sources_used` shows which).

## 4. Tests (all green on the branch)

```bash
cd api && ../.venv/bin/python -m pytest -q                       # 147 passed (+ RLS matrix below)
HIVE_DB_TEST_URL=$(.venv/bin/python scripts/local_db.py test-url) .venv/bin/python -m pytest api/tests/test_db_access_matrix.py -v   # 10, incl. live tier
.venv/bin/python western_blot_miner/tests/test_densitometry.py   # 61/61 synthetic-blot checks (v0.2: lanes, gates, stability)
cd web && npx tsc --noEmit && npm run lint                       # clean
```

Coverage: Valency JSON-RPC/SSE transport and argument adaptation; DOI
normalisation; Europe PMC → Unpaywall fallback order; the ingest job state
machine (fail-fast without a model, fail-clean without OA PDF, full run with a
stubbed pipeline storing filename-only crop refs and `review_tier`); search
guard pinned to the live table; every experimental route's auth; evidence
blocks carry statuses verbatim; citation validation; densitometry ordering,
ratios, inversion, saturation, stacked rows, text-row demotion, region boxes.

## 5. Experiments (how we measure before we claim anything)

| ID | Question | Script | Needs | Output |
|---|---|---|---|---|
| **L1** | On the 3 reviewed DOIs, how well does the live pipeline agree with the human-reviewed rows, lane by lane (target, modification, experiment type, sample, catalog #, band state)? | `scripts/experiments/live_ingest_eval.py` | model key + network | `research/experiments/L1_live_ingest_eval.{json,md}` |
| **D1** (retired 2026-09-14) | Does uncalibrated densitometry contradict the reviewed categorical band states? | `scripts/experiments/densitometry_vs_bands.py` | nothing | `research/experiments/D1_densitometry_vs_bands.{json,md}` — not a quality metric, see its header |
| **D2** | Where do the clip / stability gates sit relative to the ratio error on fixtures with known ratios? | `scripts/experiments/densitometry_clip_study.py` | nothing | `research/experiments/D2_clip_threshold_study.{json,md}` |
| **D5** | On the 21 reviewed crops, does v0.2 refuse where the pixels are clipped / signal-free / unstable? | `scripts/experiments/densitometry_real_crops.py` | nothing | `research/experiments/D5_real_crops_refusal.{json,md}` |
| **V1** | For 10 blot-heavy queries on UCSF's targets, does Valency return open-access, PMC-resolvable DOIs at better rank than PMC search alone? | manual via `/experimental/papers/search` with `source=valency` vs `pmc`, count PMC-resolvable DOIs in the top 5 | Valency token | table in this doc |
| **Q1** | For 10 questions with known answers in the reviewed corpus, does /ask cite the right record and never contradict a status? | manual via `/experimental/ask`; record cited refs vs expected record ids | model key | table in this doc |

**L1 is the only number to say out loud**, and only as "agreement with our
own reviewed read on papers we already reviewed". It is a self-consistency
check, not unseen-paper accuracy. The About page keeps saying that.

**D1 result (run 2026-09-05, no credentials needed):** 93 records, 21 crops,
424 lanes scored, **253 agree / 171 disagree (59.7%)**, 30 uncertain lanes
not scored (`research/experiments/D1_densitometry_vs_bands.md`). Read this
as: with automatic row/lane placement over a whole crop (printed row labels
included in lane 1, equal-width lanes, arbitrary 0.35/0.20 thresholds) the
measurement agrees with the human read only three times in five. That is
why the UI makes the researcher box one strip and give the printed lane
count, and why the numbers are never stored. D1 is a sanity check only.

## 6. Risks and go/no-go

| Risk | Mitigation | Gate |
|---|---|---|
| Model key not available | job fails fast with a clear message; pre-warmed rows still demo | **no key = no live demo**, show pre-warmed rows only |
| Valency corpus is arXiv-heavy, few biomedical DOIs | PMC fallback is automatic; V1 tells us which to lead with | run V1 the day before |
| Extraction quality on an unknown paper embarrasses us | labelled unreviewed; statuses abstain; pick pre-warmed papers whose L1-style spot check looked sane | Nik eyeballs each pre-warmed paper |
| 60–180 s wall time | stepper + narration; pre-warmed fallback | rehearse once with a stopwatch |
| Render free tier cold start on the experimental service | warm both services 10 min before | checklist |
| Densitometry read as quantification | disclaimer on page and response; say "reading aid" out loud | Tanvi listens for overclaims |

## 7. Not done / next

- Valency argument schema is read at runtime; the first real call with a
  token may need a mapping tweak (`api/app/valency.py::_arg_names`).
- Job state is in-process (single Render instance) with best-effort DB
  mirroring; a restart mid-job loses the stepper, not the data.
- No per-user quotas on ingestion beyond the rate limit (6/min).
- Live rows are never promoted to the reviewed tier automatically; promotion
  = human review + reseed, as today.

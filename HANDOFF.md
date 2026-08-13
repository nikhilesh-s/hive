# HiveBlot Agent Handoff

> Read this file first. It is the single source of truth for **current project
> state**. Any agent (Claude Code, another Claude session, Codex, a human) should
> be able to read this and immediately know what HiveBlot is, what's done, what's
> blocked, and the exact next task.

## Last Updated
- **2026-08-12 (session 2)** — Claude Code (Opus 4.8). **First real paper end-to-end.**
  Built the `.venv` (py3.12) + installed ingestion deps; live UniProt transport
  validated; ran a real phospho-STAT3 paper (PMC12856536) through the full records
  path via **agent-in-the-loop** Stage-2 extraction (no live model backend available).
  Field-by-field inspection found + fixed a **structural identity bug** (`P-ERK 1/2`→
  EPHB2 false-friend; p53/p38/PARP prefix mangling; ambiguous-family-as-SUPPORTED),
  with regression tests. Widened the API model additively; rebuilt the result card;
  wrote `research/RESEARCH_SYNTHESIS.md`. Demo run committed under `eval/demo/`.
- **2026-08-12 (session 1)** — Migrated Phase 2+3 into `/hive`; wired the Evidence
  Record engine into `pipeline.py` behind `WBM_EXTRACTION_MODE`; validated UniProt parsing.

## Product North Star
HiveBlot is a **biologically accurate Western blot evidence search / context
platform**. It turns Western blot figures, captions, methods, and paper context
into structured, searchable, **auditable** experimental evidence, so a researcher
can move between what a blot shows, the conditions that produced it, and
comparable evidence in the literature.

- **Biological validity is the #1 beta priority** — above feature count and UI polish.
- **HiveBlot and AGeneTic are separate projects.** AGeneTic must NOT shape this
  repository, its schema, or its scope.
- **Immediate user target: UCSF wet-lab researchers.**
- This is a **beta** whose explicit purpose is to collect detailed researcher
  feedback. Surface uncertainty; never present a guess as a settled fact.

## Canonical Repository
- **Repo:** `git@github.com:nikhilesh-s/hive.git` (this `/hive` working tree).
- **Branch:** `feature/bio-context-beta` (do NOT build features on `main`).
- **Latest implementation commit:** `2cb2d0c` (pipeline records-mode wiring). This HANDOFF
  update commits on top; see *Recent Commits* for the current tip.
- The old `Ananya-Jha-code/QBI` repo is **superseded**. Do not build there.

## Current Architecture
- **Frontend** — `web/` (Next.js App Router, TypeScript). Search UI → `web/app/api/search/route.ts` → API.
- **Backend API** — `api/` (FastAPI). Split routers: `internal` (frontend-only, `INTERNAL_API_KEY`)
  and `external` (agent-facing `/v1/search`, `AGENT_API_KEYS`). Security: `sql_guard.py`
  (AST validation of LLM-generated SQL) + a low-privilege `hive_readonly` Postgres role.
- **Supabase (Postgres)** — table `western_blot_records` (`api/db/schema.sql`), extended
  additively by `migrations/001_evidence_record.sql` with the biological Evidence Record columns.
- **Literature / PDF ingestion** — `western_blot_miner/` package. Free NCBI E-utilities +
  BioC (`pmc.py`) for literature; local PDF render via PyMuPDF (`pdf_preprocess.py`).
- **Deterministic CV filtering** — `pdf_preprocess.py` (OpenCV): renders pages, scores
  panel candidates (saturation / dark-fraction / horizontal morphology / intensity
  profiles), keeps only above-threshold crops before any model call. This is the cheap
  first stage of the cascade.
- **Biological Evidence Record engine** — `evidence_record.py` (schema), `biology.py`
  (deterministic biology), `reconcile.py` (evidence-hierarchy reconciliation),
  `record_builder.py` (assembly + validation/anomalies), `extract_records.py` (Stage 2→3→4).
- **LLM abstraction** — `llm_client.py`: **Bedrock-first** (`converse`), plus Anthropic /
  OpenAI-compatible / Mock backends. No RunPod dependency.
- **UniProt resolver** — `resolve.py`: live UniProt REST (reviewed, organism-scoped) +
  on-disk cache + local-map fallback. Never guesses an accession.

Cascade (low-compute by design): deterministic Stage 1 → cheap hosted model Stage 2 →
validation Stage 3 → expensive-model escalation Stage 4 only for ambiguous/conflicting.

## Completed Work
- **Phase 1 — Repository audit / canonical architecture.** Identified the real system
  and canonical components across the messy QBI branches.
- **Phase 2 — Biological schema + phospho classification fix.** `biology.py`; removed the
  `target.startswith("p")` heuristic; additive `migrations/001`. Tests: **test_biology 38**,
  **test_loader_enrichment 18**.
- **Phase 3 — Evidence Record + provenance + reconciliation + resolver + benchmark.**
  Field envelope, evidence hierarchy, conflict handling, UniProt resolver, Bedrock
  abstraction, antibody detection-vs-association, co-IP roles, MW reported-vs-expected,
  validation/anomaly flags. Tests: **test_reconcile 21**, **test_extract_records 10**;
  **eval benchmark 34/34** field-level across 4 seed cases.
- **Migration → /hive**: engine + migrations + eval brought into the canonical repo.
- **Pipeline wiring**: `pipeline.py` now supports `WBM_EXTRACTION_MODE=records`, routing the
  OpenCV panel candidates through the Evidence Record engine (`run_records_stage`); legacy
  path preserved. **113 assertions + 34/34 benchmark verified from `/hive`**
  (test_biology 53, test_reconcile 21, test_loader_enrichment 18, test_extract_records 10,
  test_pipeline_records 11) + **api pytest 81/81**.
- **UniProt resolver live-validated**: parsing checked against the live UniProt API via
  stdlib urllib — STAT3→P40763 (88.1 kDa), AKT1→P31749, TP53→P04637, EGFR→P00533,
  GAPDH→P04406, all exact. **`requests` transport now also live-validated** in the venv.
- **Session 2 — first real paper end-to-end** (`eval/demo/phospho_PMC12856536/`):
  Jang et al. 2026, DOI 10.3892/br.2026.2108, PMC12856536 (phospho-STAT3, Hep3B, IL-6).
  PDF → PyMuPDF → OpenCV (55→9 candidates) → **agent-in-the-loop** Stage-2 → build →
  reconcile → **live UniProt** → validation → **18 Evidence Records / 90 Supabase rows**;
  the 4 bar-chart candidates correctly produced 0 records. Verified correct: phospho vs
  total split, Tyr705/Ser727 residues, loading-control (β-actin), treatment parse
  (IL-6 10 ng/ml, 60 min), expected-MW 88.1 kDa, reported-MW null (never conflated).
  *Transport note:* no live model backend was available, so Stage-2 was performed by
  the agent (real observations in `responses_observed.json`); ALL downstream biology is
  the real production path. Reproducible via `eval/tools/manual_pipeline.py`.
- **Structural bug fixes (session 2, with tests):** `biology._core_symbol` rewritten —
  it stripped a lone `p`/`P` from any p-word (`p53`→`53`, `p38`→`38`, `PARP`→`ARP`),
  ignored total-protein `T-`, and dropped isoform suffixes (`P-ERK 1/2`→`ERK`→ UniProt
  **EPHB2**, a gene-synonym false-friend). Now: separators required for p-/t- stripping,
  glued lowercase-`p` only before uppercase, isoform preserved (`ERK 1/2`→`ERK1/2`).
  Resolver: curated **ambiguous families win over UniProt** (ERK→MAPK1/MAPK3, never one
  wrong accession). `record_builder`: an ambiguous-with-family resolution stays AMBIGUOUS
  (was falsely SUPPORTED) → flips `needs_review`. Tests: **test_biology now 53** (added 15).
- **API widened (additive):** `api/app/schemas.py::WesternBlotRecord` gained the
  migration-001 Evidence Record fields as Optional (Pydantic was silently dropping DB
  columns the frontend never received). The giant `provenance`/`validation` JSONB blobs
  are intentionally kept OUT of list responses. **api pytest 81/81.**
- **Frontend result card rebuilt** (`web/components/DatabaseResultCard.tsx`): biological
  headline (`STAT3 · phospho-Tyr705`) + review badge (Supported / Needs review /
  Conflicting) + antibody/treatment/band/MW (reported≠expected) + an evidence panel
  ("Why HiveBlot says this"). Additive + guarded (legacy rows still render); `tsc` clean.
- **Research tracks delivered** (`research/`): `biologist_western_workflow.md`,
  `biopharma_workflows.md`, `frontend_integration_plan.md`, `benchmark_candidates.md`
  (+ `eval/candidates.json`, 26 verified papers), `real_pipeline_report.md`, and the
  integration `RESEARCH_SYNTHESIS.md`.

## Current Biological Contract
Every important field is an **Evidence Field envelope**: `{value, confidence, status,
sources, candidates}` — **field-level** confidence, not just record-level. Statuses:
- **SUPPORTED** — evidence agrees; value is settled.
- **AMBIGUOUS** — under-supported or resolver returned multiple candidates; value is a
  best-guess flagged unsettled.
- **CONFLICTING** — credible sources disagree. **`value = null`** (never a falsely settled
  scalar); competing **candidates + their evidence are preserved** for review/repair.
- **MISSING** — not reported. Preserved in the record but not given prominent UI treatment;
  surfaces when relevant to a query, evidence review, or feedback.

Other invariants: **raw source wording is always preserved** alongside any normalized value;
**provenance** (which source: antibody / caption / methods / model_target / image / uniprot)
travels with each field; a disputed modification keeps its residue **unsettled** too.

## Known Biological Edge Cases (current gaps)
- **FIXED — ERK/family shorthand false-friend.** `P-ERK 1/2` used to resolve to EPHB2
  (P29323); now resolves to the ambiguous **MAPK1/MAPK3** family (status AMBIGUOUS,
  `needs_review=true`, no single accession). Curated ambiguous families now beat a
  UniProt synonym hit.
- **P-ERK 1/2 is NOT classified as phospho** (mod=`-`, experiment=`standard_western`)
  because there is no explicit site and `P-` alone isn't accepted as phospho evidence.
  Conservative-correct, but the phospho-specific antibody (rank-1) is a hint we don't yet
  use for site-less phospho labels — candidate improvement.
- **Non-human UniProt resolution ordering** — resolver defaults to `organism_id=9606`;
  mouse/rat targets can resolve wrong or expected-MW wrong until organism is threaded in.
- **Unusual phospho notation** far from the target mention (e.g. glued `STAT3(pY705)`, or
  "phosphorylated at Y705" across a clause) can be missed → falls back to antibody/model.
- **Antibody-to-panel association ambiguity** — "which antibody detected which row" in a
  dense reagents paragraph is *flagged* via `association_confidence`, not fully solved.
- **Dual modifications** (e.g. cleaved AND phospho on one target) → treated as a conflict,
  not yet represented as co-occurring.
- **Multi-dose lane extraction** — only the first dose/duration per row is captured deterministically.
- **IP-bait heuristic** (`_first_gene_after`) is best-effort; robust for "anti-EGFR", brittle in messy methods.

## Current Technical Blockers
- **RESOLVED — real paper end-to-end**: done (session 2, `eval/demo/phospho_PMC12856536/`).
- **RESOLVED — ingestion deps**: `.venv` (py3.12) at repo root has PyMuPDF, opencv-headless,
  numpy, requests, pydantic, anthropic. Recreate with
  `python3.12 -m venv .venv && .venv/bin/pip install -r western_blot_miner/requirements.txt`.
- **RESOLVED — `requests` / UniProt transport**: installed + live-validated in the venv.
- **RESOLVED — representative PDFs**: 3 real open-access PDFs in `research/papers/`
  (standard PMC9559174, phospho PMC12856536, co-IP PMC12706926); gitignored (fetch via
  the PMCIDs in `research/real_pipeline_report.md`).
- **OPEN — no live model backend**: `boto3`+Bedrock creds/region absent; no
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`; no `~/.aws`. The real run used **agent-in-the-loop**
  Stage-2 (honest, documented). For an automated run set `WBM_LLM_BACKEND` + matching creds.
  This is the main thing between us and a hands-off `pipeline.py … --mode records` run.
- **OPEN — Supabase not provisioned here**: no `SUPABASE_URL`/`KEY` in env, so migration 001
  is unapplied and no rows are loaded → the enriched frontend can't show live data yet.
  Apply `api/db/schema.sql` then `migrations/001_evidence_record.sql`, then load
  `eval/demo/phospho_PMC12856536/supabase_rows.json`. This is the last gap to the full
  success condition (search → real record in the UI).

## Immediate Next Task
Pick up in priority order (first two unblock the full success condition):
1. **Get the real records into the live frontend.** Provision/confirm the beta Supabase
   project, apply `api/db/schema.sql` + `migrations/001_evidence_record.sql`, load
   `eval/demo/phospho_PMC12856536/supabase_rows.json`, run `api` + `web`, and confirm a
   search for `phospho STAT3 Tyr705` returns the real card (the new
   `DatabaseResultCard` is ready; API model already passes the fields through).
2. **Thread organism into the UniProt query** (resolver defaults to human 9606). Needed
   before the mouse standard-Western demo (PMC9559174) resolves correctly. Then run the
   remaining two downloaded papers (standard PMC9559174, co-IP PMC12706926) the same way
   to reach 5–10 diverse demo records.
3. **When a live model backend exists**, re-run PMC12856536 hands-off
   (`WBM_LLM_BACKEND=… WBM_EXTRACTION_MODE=records python3 -m western_blot_miner.pipeline
   research/papers/phospho_PMC12856536.pdf --mode records`) and diff against the
   agent-in-the-loop records in `eval/demo/` to validate the automated backend.

Reproduce the agent-in-the-loop run:
```bash
PYTHONPATH=. .venv/bin/python eval/tools/manual_pipeline.py preprocess research/papers/phospho_PMC12856536.pdf
# inspect panel_candidates/*.png, write observed rows, then:
PYTHONPATH=. .venv/bin/python eval/tools/manual_pipeline.py run <out_dir> eval/demo/phospho_PMC12856536/responses_observed.json
```

## Next After That
- Live Bedrock + UniProt validation (real credentials + network).
- Phase 4: expand anomaly/validation rules + tests.
- Phase 5: advanced structured search (safe parameterized filters + NL→filter routing).
- Phase 6: Evidence Record UI (only after the biology is trusted).
- Phase 7: researcher feedback system.
- Phase 8: larger biological benchmark (10–20 wet-lab-annotated cases).

## Files That Matter Most
| Path | What it does |
|------|--------------|
| `western_blot_miner/biology.py` | Deterministic biology: modification/site detection, experiment type, loading control, protein core symbol. |
| `western_blot_miner/evidence_record.py` | Field envelope + EvidenceRecord + `to_supabase_rows()` projection. |
| `western_blot_miner/reconcile.py` | Evidence-hierarchy reconciliation; conflict handling. |
| `western_blot_miner/record_builder.py` | Builds an EvidenceRecord from model claims + biology; validation/anomalies. |
| `western_blot_miner/extract_records.py` | Stage 2→3(→4) panel extraction; `records_to_supabase_rows`. |
| `western_blot_miner/resolve.py` | UniProt resolver + cache + local fallback. |
| `western_blot_miner/llm_client.py` | Bedrock-first model abstraction + Mock. |
| `western_blot_miner/pdf_preprocess.py` | OpenCV candidate filtering (cheap stage). |
| `western_blot_miner/pipeline.py` | PDF ingestion orchestrator (**still old VLM path — to be wired**). |
| `western_blot_miner/supabase_loader.py` | Flatten/enrich rows + PostgREST upload. |
| `migrations/001_evidence_record.sql` | Additive Evidence Record columns (+ rollback). |
| `eval/score.py`, `eval/cases.json`, `eval/gold.json` | Biological benchmark (seed gold). |
| `api/app/` | FastAPI backend (routers, sql_guard, auth, search_service). |
| `api/db/schema.sql` | Base `western_blot_records` table + `hive_readonly` role. |
| `web/app/`, `web/components/` | Next.js frontend. |

## Tests / Commands
```bash
# Biological tests (need python3 + pydantic; run from repo root)
python3 western_blot_miner/tests/test_biology.py
python3 western_blot_miner/tests/test_reconcile.py
python3 western_blot_miner/tests/test_loader_enrichment.py
python3 western_blot_miner/tests/test_extract_records.py
python3 western_blot_miner/tests/test_pipeline_records.py   # ingestion wiring (mock model)

# Biological benchmark (offline; writes eval/out/)
python3 eval/score.py

# API tests
cd api && pytest

# Frontend
cd web && npm install && npm run dev

# Backend
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload

# Ingestion — legacy VLM path (default) or new Evidence Record path
python3 -m western_blot_miner.pipeline path/to/paper.pdf                 # legacy
WBM_EXTRACTION_MODE=records python3 -m western_blot_miner.pipeline paper.pdf --mode records
```

## Environment Variables / Services  (NAMES ONLY — never put values here)
- **API (`api/.env`):** `SUPABASE_URL`, `SUPABASE_KEY`, `DB_READONLY_URL`, `OPENAI_KEY`,
  `INTERNAL_API_KEY`, `AGENT_API_KEYS`, `ALLOWED_ORIGINS`, `AGENT_RATE_LIMIT`, `SEARCH_RATE_LIMIT`.
- **Web (`web/.env`):** `API_BASE_URL`, `INTERNAL_API_KEY`.
- **Ingestion engine (`western_blot_miner/.env`):** `ANTHROPIC_API_KEY`, `NCBI_API_KEY`,
  `NCBI_EMAIL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_TABLE`, `SUPABASE_IDEMPOTENT`,
  `WBM_MODEL`, `WBM_LLM_BACKEND`, `WBM_BEDROCK_MODEL`, `WBM_BEDROCK_ESCALATION_MODEL`,
  `AWS_REGION` (+ standard AWS credential vars for boto3), `WBM_LLM_BASE_URL`,
  `WBM_LLM_API_KEY`, `WBM_LLM_MODEL`, `WBM_OFFLINE`, `WBM_PROTEIN_CACHE`, `WBM_PDF_DPI`,
  `WBM_MIN_CANDIDATE_SCORE`, `WBM_MIN_LLM_SCORE`. (Legacy Qwen/VLM: `WBM_VLM_BASE_URL`,
  `WBM_VLM_API_KEY`, `WBM_VLM_MODEL`.)
- **Services:** Supabase (Postgres), NCBI E-utilities/BioC (free), UniProt REST (free),
  Amazon Bedrock (model inference). `.env` files are gitignored — keep it that way.

## Decisions That Must Not Be Reversed Casually
1. **Never use `target.startswith("p")` (or any name-prefix heuristic) to infer
   phosphorylation.** Require explicit evidence. p53/p38/PARP are not phospho.
2. **The model's row target is a claim, not ground truth.** Use the evidence hierarchy.
3. **Conflicting fields do not get a canonical scalar value** — `value=null`, candidates preserved.
4. **Expected MW ≠ observed/reported MW.** Keep them distinct and labeled.
5. **Image-derived MW requires an actual ladder/reference calibration.** Do not infer kDa from an image otherwise.
6. **Band presence is not densitometry.** `present/absent/uncertain` is categorical; the
   FUTURE intensity columns stay NULL until a real measurement pipeline writes them.
7. **Biological context and correctness before flashy UI.**
8. **No fake scientific fields.** Never fabricate a value the source doesn't contain.
9. **AGeneTic is a separate project** and must not shape this repo.
10. **Raw source wording is always preserved** alongside normalized values.

## Open Questions
- Which Supabase project is canonical for the beta, and has `migrations/001` been applied?
- Which Bedrock model + region are provisioned (model access approved)?
- Idempotency key `(paper_id, page, figure_label, target, condition)` — keep, or extend with
  modification/lane once Evidence Records flow in? (Affects dedupe on re-ingest.)
- Organism handling: thread cell-line→organism into the UniProt query before resolution?

## Recent Commits (rolling)
- `2cb2d0c` Wire Evidence Record engine into pipeline.py behind WBM_EXTRACTION_MODE flag
- `28f1372` Establish HANDOFF.md agent-handoff system + agent instructions
- `97cdcf2` Migrate HiveBlot Phase 3: Evidence Record engine + resolver + benchmark
- `6a3140b` Migrate HiveBlot Phase 2: biological schema + phospho fix
- `4d5df1e` Execute plan steps 1-7: tests, sql_guard fix, verification (pre-existing /hive)
- (this HANDOFF update commits on top of `2cb2d0c`)

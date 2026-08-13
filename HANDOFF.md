# HiveBlot Agent Handoff

> Read this file first. It is the single source of truth for **current project
> state**. Any agent (Claude Code, another Claude session, Codex, a human) should
> be able to read this and immediately know what HiveBlot is, what's done, what's
> blocked, and the exact next task.

## Last Updated
- **2026-08-13 (session 6)** — Claude Code. **M2 CLOSED: descriptive band
  multiplicity / smear representation.** Additive `BandObservation` fields
  `band_pattern` (single|doublet|multiple|smear|ladder|uncertain) + `band_count`
  (only when literally countable/stated) + `band_notes` (verbatim wording), each
  a full EvidenceField envelope. **Additive to `band_state`, never a replacement**
  (a smeared/doublet band is still `present`); null pattern = "source didn't
  say", NOT "single band". Two evidence channels only: (1) deterministic parsing
  of explicit wording (`biology.detect_band_pattern`: doublet, "two/three
  bands", smear(ed), ladder-like, polyubiquitin ladder/conjugates, high-MW
  species, multiple/additional/non-specific bands, single band; hedged wording →
  AMBIGUOUS; conflicting descriptions → uncertain), **clause-scoped to the
  target** so "LC3B resolved as a doublet, while ACTB…" never marks ACTB; and
  (2) explicit observer claims in Stage-2 output (contract updated with strict
  omit-when-in-doubt + no-identity-inference rules). **False-positive audit on
  the real 452-band set: with text-only evidence, zero patterns asserted**
  (correct — no paper states multiplicity wording); observer doublet claims
  were then added ONLY for the 4 targets visibly resolving as two bands in the
  inspected crops (LC3B, BEX2, P-ERK 1/2, T-ERK 1/2 → 30 lanes), each carrying
  image provenance + verbatim note. Phospho+total pairs, loading controls and
  multi-row panels remain pattern-free (multiplicity belongs to ONE band
  observation, never to row count). Exposed in `GET /records/{id}` + evidence-
  panel lane strip with an explicit "descriptive only — no isoform/cleavage
  interpretation" note. LIMITATIONS: no image-based smear/multiplicity detection
  (text/observer evidence only); no isoform/cleavage/dimer assignment ever; the
  no-creds automated model has not been tested against the new contract fields.
  Tests: **biology 124/124** (+30), api 106/106, benchmark 34/34, harness
  self-test 100% EXACT, tsc clean. Demo artifacts + DB regenerated (452 rows).
  Model creds re-checked: still absent. Optional QA sub-agent not spawned (the
  empirical zero-FP audit on all real bands stood in for it; flag for the
  independent pre-UCSF QA pass).
- **2026-08-13 (session 5, hackathon day)** — Claude Code. **RESULT GROUPING + MULTI-DOSE
  REPRESENTATION.** (1) Search results now group into one card per EXPERIMENT
  (paper + panel + target + experiment type + **cell line** + **modification label**)
  instead of one card per lane row: `phospho STAT3 Tyr705` reads "3 experiments
  (15 lane records)". The cell-line component is load-bearing — one real crop
  (PMC12706926 `page_004_cand_0025`) prints **H1792 | A549 side by side**, and the
  first key merged them. Verified against all 374 demo rows: 77 groups, **zero**
  groups containing >1 distinct target / canonical target / modification / residue /
  experiment type / UniProt / figure / cell line / catalog / organism.
  (2) **Multi-dose / time-course representation (QA finding M1 closed).** The old
  scalar took `values[0]`, which reported the **CL-E dose (60 µg/ml) as the IL-6
  dose** and **60 min as THE duration of a 0–60 min time course**. Now:
  enumerations sharing one unit expand (`extract_dose_series` /
  `extract_duration_series`: "10, 30 and 60 µg/ml" → 3 values; "(0, 5, 10, 20, 30,
  60 min)" → 6 timepoints); >1 distinct value ⇒ the panel scalar becomes
  **value=null, status=AMBIGUOUS with every value preserved as a candidate**
  (DB scalar NULL, never a wrong number); per-lane values are parsed from each
  lane's own printed condition into new `BandObservation.lane_dose/lane_duration`
  and served by `GET /records/{id}`. "for the indicated times/doses" is
  kind-specific, so a time course keeps its settled single stimulus concentration.
  Tests: **biology 94/94** (+17), api 106/106, benchmark 34/34, harness self-test
  100% EXACT, tsc clean. Demo artifacts + local DB regenerated (452 rows).
  **Model backend still blocked — no credentials present (re-verified).**
- **2026-08-13 (session 4)** — Claude Code (Opus 4.8). **SCIENTIST-REVIEW BETA COMPLETE.**
  Full provenance + researcher-feedback loop live end-to-end locally:
  `GET /records/{id}` serves curated field-level evidence envelopes (value /
  status / source snippets / competing candidates); the card's evidence panel is
  now a full-width accordion with the normalization chain (raw → canonical →
  UniProt), per-field audit rows + ✓/✗/not-useful/suggest-correction controls,
  equal-weight CONFLICTING candidate display ("Which is right?"), antibody
  roles, lane strip, `+ Missing information?`, result flagging, post-search
  "did HiveBlot understand?" prompt, and a general BETA FEEDBACK widget.
  **Migration 002** adds `hiveblot_feedback` + insert-only `hive_feedback` role:
  human corrections persist BESIDE the AI extraction (model_value snapshot),
  never over it. Verified in the real browser: feedback rows land in Postgres
  from UI clicks. Also: home-page search now routes to /search (legacy table
  retired); advanced-filters bar; `eval/model_comparison/compare_records.py`
  harness (self-test 100% EXACT on all 3 papers); boto3 installed → Bedrock
  path ready pending creds; `DEPLOYMENT.md`; `research/HACKATHON_DEMO_FLOW.md`;
  scientific QA self-audit (`research/demo_scientific_qa.md`: 0 critical open,
  2 major representational). Tests: engine 138 assertions green, benchmark
  34/34, **api 104/104**, web tsc clean. NOTE: two of three planned sub-agents
  (independent QA, eval design) were killed by session limits; QA was done as a
  self-audit and the eval harness written directly — re-run independent QA
  before UCSF.
- **2026-08-12 (session 3)** — Claude Code (Opus 4.8). **LIVE SEARCH LOOP WORKS.**
  `phospho STAT3 Tyr705`, `phospho AKT Ser473`, `co-IP PIK3CA`, `CST 9145`,
  `GAPDH mouse` all return real paper-derived Evidence Records in the running
  HiveBlot frontend. Stood up an **embedded local Postgres** (`scripts/local_db.py`,
  pgserver — no cloud creds needed) with schema + migration 001 + **452 rows from
  3 real papers**; added a **deterministic biological SQL generator**
  (`api/app/bio_query.py`) for the no-OPENAI_KEY path; fixed a latent sql_guard
  bug (AND/OR rejected with sqlglot≥30); made the Supabase client lazy; processed
  papers 2+3 (mouse standard PMC9559174, co-IP PMC12706926) agent-in-the-loop;
  threaded **organism into UniProt** (mouse accessions correct); fixed 4 more
  structural biology bugs found by real-paper inspection (one-letter phosphosites,
  page-level co-IP bleed, bare-mention fake total claims, page-blob reported-MW).
  Tests: biology 77/77, engine suites green, benchmark 34/34, api 95/95.
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

## Provenance & Feedback (session 4)
- **Record detail**: `GET /records/{id}` (internal auth) → curated `RecordDetail`:
  source identity, biological scalars, `fields{name → {value, confidence, status,
  sources[{type,text}], candidates[]}}` extracted from the provenance JSONB,
  antibodies (role + detection vs association confidence), per-lane bands,
  validation. Shaping: `api/app/record_detail.py`. Web proxy: `/api/record/[id]`.
- **Feedback**: `POST /feedback` (internal auth) → `hiveblot_feedback`
  (**migration 002**) via the **insert-only `hive_feedback` role**
  (`DB_FEEDBACK_URL`) — physically cannot touch `western_blot_records`.
  Scopes: `field` (correct/incorrect/not_useful/missing_context + suggested_value),
  `record` (9 flag types), `missing_field`, `search` (understood yes/partially/no),
  `ui`. `model_value` snapshots the AI claim at feedback time → every row is an
  auditable "AI claim → human correction" pair; corrections are NEVER auto-applied.
  Web proxy: `/api/feedback` (key-allowlisted); anonymous localStorage session id.
- **Frontend**: `EvidencePanel.tsx` (full-width accordion: normalization chain,
  per-field audit + feedback, conflict candidates "Which is right?", antibodies,
  lane strip, missing-info + flag-result forms, DOI link), `SearchFeedback.tsx`,
  `BetaFeedback.tsx`, `FiltersBar.tsx` (composes queries for the deterministic
  parser). Home-page search now routes to `/search?q=…` (legacy table retired).

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
- **FIXED (session 3) — one-letter phosphosites in row labels.** `p-AKT (S473)`,
  `p-RPS6KB1 (T389)`, `p-EIF4EBP1 (S65)` now yield residue+position (the phospho marker
  and site share one short label, satisfying the one-letter context guard). Bare `S473`
  without a marker still never claims phospho.
- **FIXED (session 3) — page-level co-IP bleed.** co_ip now requires panel-scoped
  evidence (IP-role antibody / co-IP caption / IP:,IgG,input lane labels); a methods-only
  mention becomes a non-settling `co_ip_context` flag. `ip_bait` extraction follows the
  same scoping.
- **FIXED (session 3) — bare mentions are not total claims.** "PI3K/AKT/mTOR signaling"
  no longer manufactures a `MODIFICATION_CONFLICT` against a phospho row; only explicit
  `total X` / `T-X` / `pan-X` wording asserts total, and mixed forms still abstain.
- **FIXED (session 3) — page-blob reported MW.** A kDa figure counts as reported only
  near a mention of the target's core symbol (caption-only fallback when the core is
  absent from a short caption). No more "BEX2 reported 70 kDa" from ladder text.
- **FIXED (session 3) — phospho-specific antibody vs uppercase P- label.** Uppercase
  `P-` is never a phospho *marker* (P-selectin, P-cadherin), but an explicit
  `phospho_specific=true` antibody claim now prevents settling the row as total:
  `P-ERK 1/2` + CST #4370 → modification CONFLICTING, value null, needs_review.
- **NEW (session 3) — organism threading.** `biology.organism_taxon_id` maps explicit
  human/mouse/rat wording → taxon id for the UniProt query (default human 9606, as
  before). Mouse validated live: Stat3→P42227, Gapdh→P16858, Actb→P60710, Tuba1b→P05213.
  Cell-line→organism inference is still NOT used for resolution (only explicit claims).
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
- **FIXED (session 5) — multi-dose / time-course collapse.** Enumerated series now
  expand; a panel with >1 distinct dose/duration keeps `value=null` + AMBIGUOUS +
  candidates instead of asserting one lane's value (which had cross-attributed the
  CL-E dose to IL-6). Per-lane values live on `BandObservation.lane_dose` /
  `lane_duration`, parsed only from that lane's own printed condition.
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
- **OPEN — no live model backend** (unchanged, re-verified session 3: no `~/.aws`, no
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`WBM_LLM_*`). All three real papers used
  **agent-in-the-loop** Stage-2 (honest, documented per demo README). For an automated
  run set `WBM_LLM_BACKEND` + matching creds, then diff against
  `eval/demo/*/responses_observed.json` + `evidence_records.json` as reference.
- **WORKED AROUND — cloud Supabase still not provisioned** (`SUPABASE_URL`/`KEY` empty
  in `api/.env`), but the live loop no longer needs it locally: `scripts/local_db.py`
  runs an embedded Postgres (pgserver, data in gitignored `.localdb/`), applies the
  SAME `api/db/schema.sql` + `migrations/001` (pg_trgm index skipped locally — not
  bundled), creates `hive_readonly`, and loads the demo rows. `api/.env`'s
  `DB_READONLY_URL` points at it. `/search` runs asyncpg-only, so against this DB the
  search path is the real production path; PostgREST-only endpoints (`/proteins`, `/`)
  still need real Supabase. **Cloud Supabase remains a user action for the hosted
  beta**: create the project, run schema+migration, load `eval/demo/*/supabase_rows.json`,
  fill `SUPABASE_URL`/`SUPABASE_KEY`/`DB_READONLY_URL`.
- **NOTE — /search SQL generation without OpenAI**: with `OPENAI_KEY` empty, /search
  uses the deterministic biological parser (`api/app/bio_query.py`) — protein,
  phospho-site (Tyr705/S473), vendor+catalog, co-IP, loading-control, needs-review,
  cell-line terms — through the same `sql_guard` + read-only role. With a key set, the
  legacy OpenAI NL→SQL path is unchanged (bio parser is the fallback on its failure only
  when no key; generation errors still 502).

## Immediate Next Task
~~Provenance detail endpoint + researcher feedback system + evidence UI~~ — **DONE (session 4)**.
~~Result grouping + multi-dose/time-course representation~~ — **DONE (session 5)**.

Next, in priority order:
1. **USER ACTION — model backend creds** (Bedrock preferred, or Anthropic). Everything
   is staged for a one-command evaluation. Bedrock:
   ```bash
   export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=… AWS_REGION=us-east-1
   export WBM_LLM_BACKEND=bedrock            # optional: WBM_BEDROCK_MODEL / WBM_BEDROCK_ESCALATION_MODEL
   WBM_EXTRACTION_MODE=records .venv/bin/python -m western_blot_miner.pipeline \
       research/papers/phospho_PMC12856536.pdf --mode records --no-cache
   .venv/bin/python eval/model_comparison/compare_records.py \
       western_blot_miner/data/pdf_runs/10.3892_br.2026.2108/evidence_records.json \
       eval/demo/phospho_PMC12856536/evidence_records.json
   ```
   Anthropic direct: `export ANTHROPIC_API_KEY=… WBM_LLM_BACKEND=anthropic` (same
   pipeline + compare commands). Protocol: `research/automated_extraction_eval_protocol.md`.
   Repeat for `standard_PMC9559174` (run dir `10.3892_ijmm.2022.5188`) and
   `coip_PMC12706926` (`10.1186_s12964-025-02385-8`). boto3 + anthropic are installed.
2. **USER ACTION — provision cloud Supabase** for the hosted beta: run
   `api/db/schema.sql` + `migrations/001` + **`migrations/002_feedback.sql`**, set
   `hive_readonly`/`hive_feedback` passwords, seed `eval/demo/*/supabase_rows.json`,
   fill `SUPABASE_URL`/`SUPABASE_KEY`/`DB_READONLY_URL`/`DB_FEEDBACK_URL`.
   Full steps: `DEPLOYMENT.md`.
3. Independent scientific QA re-run (session-4 QA was a self-audit; session-6 skipped
   the optional band-pattern review agent). Both former Major findings are now closed:
   **M1 (session 5)**, **M2 (session 6)**.
4. Figure-crop image serving (the evidence panel currently prints the crop filename
   and says image serving is not enabled locally).

Local dev bring-up (all one-time steps already done in this repo):
```bash
.venv/bin/python scripts/local_db.py up      # embedded Postgres + schema + migration
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json
cd api && .venv/bin/python -m uvicorn app.main:app --port 8000   # api/.venv
cd web && npm run dev                                            # port 3000
# search: phospho STAT3 Tyr705 · phospho AKT Ser473 · co-IP PIK3CA · CST 9145
```

Reproduce an agent-in-the-loop paper run:
```bash
PYTHONPATH=. .venv/bin/python eval/tools/manual_pipeline.py preprocess research/papers/<paper>.pdf
# inspect panel_candidates/*.png, write observed rows (see eval/tools/build_responses_*.py), then:
PYTHONPATH=. .venv/bin/python eval/tools/manual_pipeline.py run <out_dir> eval/demo/<paper>/responses_observed.json
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
| `api/app/bio_query.py` | Deterministic biological query→SQL (no-OPENAI_KEY path; same guard). |
| `scripts/local_db.py` | Embedded local Postgres (pgserver): up / load / status / stop. |
| `eval/tools/` | Agent-in-the-loop harness + per-paper observation builders. |
| `eval/demo/` | 3 real papers: Evidence Records + Supabase rows + observations + READMEs. |
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

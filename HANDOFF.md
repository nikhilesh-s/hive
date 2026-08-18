# HiveBlot Agent Handoff

> Read this file first. It is the single source of truth for **current project
> state**. Any agent (Claude Code, another Claude session, Codex, a human) should
> be able to read this and immediately know what HiveBlot is, what's done, what's
> blocked, and the exact next task.

## Last Updated
- **2026-08-17 (session 12)** — Claude Code (Opus 5). **CLOUD DATABASE LIVE ON
  THE CLEAN BETA PROJECT.** Deployment target is now Supabase
  **`zafombwswztvnjikcsdm`** (`https://zafombwswztvnjikcsdm.supabase.co`,
  us-east-1, PG 17.6). **The old QIB project `belalrbfrndxvdwvjxte` is NO
  LONGER A DEPLOYMENT TARGET** — never link/push/seed to it (empty migration
  history means a `db push` would ALTER Suhas's production tables).
  **Migrations:** repo re-linked; project verified fresh (0 tables, 0
  migrations, no hive roles); `db push --dry-run` showed exactly the canonical
  4-migration chain, no seeds, no `roles.sql`; pre-flight proved all 57 seed
  columns exist in the 73 migration columns; **push applied all 4, all recorded
  in remote history**. **Remote schema verified:** `western_blot_records` 73
  cols, `hiveblot_feedback` 16 cols, **`confidence` = `real`**, `stable_row_key`
  TEXT on both tables, `pg_trgm` 1.6, **17 indexes** (incl. the GIN trigram on
  `target`). **Security verified against `information_schema` + `pg_authid`:**
  `hive_readonly` = SELECT only; `hive_feedback` = INSERT+SELECT on
  `hiveblot_feedback` ONLY with **zero grants on `western_blot_records`** and
  USAGE on only the feedback sequence; neither role is superuser/createrole/
  createdb/bypassrls; both passwords set (SCRAM confirmed — note `pg_roles.
  rolpassword` always reads non-null and proves nothing). Roles are created **by
  the migrations**, not a `supabase/roles.sql`. Seeding needed INSERT, which
  neither restricted role has by design, so a **temporary `hive_seed` role was
  created, used, then revoked and DROPped** (verified: only the two designed
  roles remain). **Seed: 475 rows / 3 papers / 91 experiment groups**, zero
  dropped keys, 0 null `stable_row_key`, 0 null `provenance`, and **zero legacy
  QIB data** (0 `p53` rows, 0 legacy paper_ids). **Cloud verification (local API
  → cloud DB, all green):** `/health`; all 7 flagship searches — `phospho STAT3
  Tyr705` 3 groups/18 lanes, `co-IP PIK3CA` 4 co-IP groups + IP BAIT=PIK3CA,
  `CST 9145`, `GAPDH mouse` 5 groups with DEVELOPMENTAL SERIES on the E14.5/P0/
  P28 panels and correctly **untagged** ligation panels, `needs review`,
  `P-ERK` = MAPK1/MAPK3 **Conflicting** with both claims and no winner,
  `BRCA1 MCF7 olaparib` 0 results with scoped copy; record detail; **crops
  served (1153x909 PNG)**; feedback INSERT + rehydration (2 smoke rows render
  as RESEARCHER FEEDBACK beside the fields); lane-specific durations and
  "varies by lane: 0-60 min"; explicit-submit proven again (30 chars typed +
  2.5 s → **zero** fetches); **21 browser assets scanned: no DSN, no
  INTERNAL_API_KEY, no Supabase key, no `NEXT_PUBLIC_*`**.
  **Deployment prep:** `api/Dockerfile` (+ `Dockerfile.dockerignore`) and
  `scripts/stage_crops.py` (21 crops / 6.2 MB staged into `api/crops/`, so the
  container serves crops with zero code and zero corpus change);
  `DEPLOYMENT.md` rewritten for the new project incl. the **pooler-not-direct**
  rule (`db.<ref>` is IPv6-only; use Supavisor **session mode 5432**, not
  transaction 6543 which breaks asyncpg prepared statements).
  `research/TEAM_BETA_HANDOFF.md` written.
  **NOT DEPLOYED YET — one credential boundary:** Vercel CLI is authenticated
  (`nikhilesh-s`) so web can ship, but no container host is logged in
  (`railway login` needed; no Fly/Render CLI). Web alone is useless without the
  API, so nothing was published.
  **NEW KNOWN ISSUE (pre-existing, not caused by deployment): 12 duplicate
  `stable_row_key` values across 24 of 475 rows.** The co-IP crop
  `page_004_cand_0025.png` prints **H1792 and A549 side by side**; the search
  grouping key includes `cell_line` (so the UI correctly shows 2 cards) but
  `_record_id` does **not**, so P62/LC3B/ACTB collide across the two cell lines
  and feedback on one rehydrates onto its twin. Session 9's "113/113 unique"
  covered the phospho paper only. Fix = add cell line to `_record_id`; that
  rehashes every `stable_row_key` and needs a reviewed reseed, so it is
  deliberately NOT done here. Tests: biology **165/165**, reconcile 21/21,
  loader ok, extract 10/10, pipeline 11/11, benchmark **34/34 (100%)**, harness
  **100% EXACT** on all 3 papers, api **113/113** (incl. migration drift
  guard), web `tsc` clean + production build clean.
- **2026-08-17 (session 11)** — Claude Code (Opus 5). **BETA-TABLE INSPECTION +
  PLAN (READ-ONLY). Nothing altered, in QIB or anywhere.** Suhas created
  `western_blot_records_beta` and `blot_results_beta` inside the QIB production
  database. Full analysis: **`research/supabase_beta_table_plan.md`**.
  **Inspection:** both exist, both **0 rows**, and both are **exact structural
  copies of the legacy production tables** — identical column names, order,
  types, defaults and nullability (diffed field-by-field; only the copied
  functional index is auto-renamed `blot_results_beta_lower_idx`, the signature
  of `CREATE TABLE … (LIKE … INCLUDING ALL)`). So
  `western_blot_records_beta` is 12 columns with **`confidence text`** and a
  pkey-only index — it inherits *every* gap from the legacy audit. Still absent
  project-wide: `hiveblot_feedback` (any form), **`hive_readonly`**,
  **`hive_feedback`**, the trigram index, and any migration history.
  **Gap vs canonical: 61 missing columns** (60 from migration 001 +
  `stable_row_key`), 1 type change (`confidence text → real`, **required** —
  the seed inserts floats and asyncpg is strict), 10 missing indexes, plus a
  whole feedback table. `stable_row_key` itself would port cleanly (plain TEXT
  + b-tree, name-independent). Note numbering: CLI copy `…0004` **is**
  canonical `migrations/003`; there is no fifth migration.
  **RECOMMENDATION — do NOT use the beta tables; wait for Srushti's separate
  HiveBlot project.** The blocker is not effort: `/search` needs the
  `hive_readonly` role and `/feedback` needs `hive_feedback`, and Postgres
  **roles are cluster-level, not table-level**; the trigram index needs
  database-wide `CREATE EXTENSION pg_trgm`. All three land outside the two beta
  tables, against the "do not modify production roles/schema" constraint — so
  Option A **cannot be executed** without a fresh exception from Suhas. Also:
  `supabase db push` is unusable against QIB (empty remote history ⇒ it would
  apply the production-targeted migrations; the only fix writes production
  migration history, also forbidden), so the beta route means hand-pasting a
  ~700-line `_beta` SQL fork that sits **outside** the drift guard, plus code
  edits to `api/app/db.py` (feedback table is hardcoded) and
  `scripts/seed_remote.py` — all of it reverted later. `TABLE_NAME` is already
  env-configurable, so the records table alone would have been config-only.
  **This supersedes session 10's `hive-beta` branch recommendation:** Srushti's
  separate project is the same isolation with no plan upgrade, no per-hour
  branch compute, and HiveBlot ownership. Keep the persistent branch as the
  fallback only if her project stalls. Two items left unverified because they
  need a SQL console (neither changes the recommendation): whether the beta
  `id` default points at production's sequence, and RLS/policy state on the
  beta tables — exact read-only queries are in the plan doc §1.5. Production
  re-verified untouched: 616 + 2 rows. Docs only; api tests 113/113.
- **2026-08-17 (session 10)** — Claude Code (Opus 5). **LEGACY SUPABASE AUDIT
  (READ-ONLY). No production change.** The original hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`, org SuhasKM's-Org, us-west-2, PG 17.6) is now
  linked; CLI 2.113.0, already authenticated. Full findings:
  **`research/supabase_legacy_audit.md`**. Headlines: production `public` holds
  exactly two tables — **`western_blot_records` 616 rows** (5 papers, 64 of
  those rows an exact duplicate of another 64 under a second `paper_id`
  spelling) and **`blot_results` 2 rows** (fabricated demo: `p53 paper 1.pdf`,
  placeholder DOI `10.1234/example.2024`; referenced by no source file).
  **Migration history is EMPTY** — all four local migrations unapplied; prod was
  built by hand, so `db push` must never target it (`create table if not
  exists` would sail past and then ALTER prod). Production's 12 columns are
  exactly `api/db/schema.sql`'s list and order ⇒ **it IS a lineal ancestor of
  the current base table**, with one divergence: **`confidence` is `text`, not
  `real`** (the reviewed seed inserts floats ⇒ asyncpg would hard-fail). Also
  absent: all 60 migration-001 columns, `hiveblot_feedback`, `stable_row_key`,
  the GIN trigram index on `target`, and **both `hive_readonly` and
  `hive_feedback` roles** (verified against the full server role list).
  Legacy data is **not** worth migrating as evidence — it bakes in the banned
  p-prefix heuristic (62 `p53` + 4 `PARP` rows typed `phospho_signaling`), has
  no provenance/UniProt/residue/status, 4 of 6 `paper_id`s are filenames, and
  `confidence` is a constant `'0.9'`. Its one real value is a **5-paper
  shortlist for re-ingestion** through the current pipeline (zero paper overlap
  with the reviewed corpus). **Security finding (no action taken): both tables
  are fully readable with the project's anon key** — RLS is off or not
  restricting anon reads; write exposure deliberately untested (a probe would
  have mutated prod) — verify in the dashboard.
  **Recommendation (NOT implemented): a Supabase branch `hive-beta`, created
  PERSISTENT, not preview** — the beta must outlive any PR because collecting
  `hiveblot_feedback` from UCSF researchers IS the deliverable. Branching is
  available (`supabase branches list` → `[]`). Create **without `--with-data`**,
  re-link to the branch ref, `db push` the four migrations, verify
  `confidence real` (branch-only `ALTER` if the parent's `text` carries over),
  set the two role passwords, then `seed_remote.py` → 475 rows. Fallback if
  branching is plan-gated: a separate standalone project. No files outside
  `research/` + this HANDOFF changed; no tests affected.
- **2026-08-16 (session 9)** — Claude Fable 5. **FINAL INTERNAL-BETA FIX PASS.**
  All reproducible manual-beta findings fixed; no scientific regressions.
  **P0 feedback persistence/rehydration — diagnosed, fixed durably.** The
  manual P-ERK correction HAD persisted (row 6); the gap was (a) no retrieval
  path and (b) a worse latent hazard: reseeds regenerate serial ids, orphaning
  ALL feedback (verified: every stored row pointed at a dead id). Fix at the
  data layer: **migration 003** adds `stable_row_key` (= record-hash:lane_index,
  computed from reviewed observation data, reseed-proof) to both tables;
  `_record_id` strengthened with crop + treatment context so the Fig 3C/3D twin
  records no longer collide (20/20 distinct; 113/113 unique row keys).
  `GET /records/{id}/feedback` rehydrates by serial id OR stable key; the
  evidence panel shows prior feedback as a clearly-labeled RESEARCHER FEEDBACK
  annotation beside (never inside) the extraction. **Proven live: feedback
  submitted on id 4019 rehydrated on id 4494 after a full reseed.** Pre-003
  feedback rows (1–6) lack stable keys and stay orphaned-but-preserved.
  **P0 lane-series representation:** series-derived treatment candidates are
  now tagged `lane_series`; the UI renders "varies by lane: 0–60 min (see
  lanes below)" instead of a false "not reported" + pick-a-winner candidate
  list. **P0 design-tag false positives:** DOSE SERIES now requires explicit
  dose semantics (unit in lanes or context); developmental-stage lanes
  (E14.5/P0/P7/P28M) get their own DEVELOPMENTAL SERIES tag; ligation labels
  (L5d/DL14d) abstain. Verified on GAPDH mouse. **P0 multi-condition summary:**
  TREATMENT now reads e.g. "IL-6 (± CL-E, Bis II, U0126)" — co-conditions taken
  verbatim from the group's own lane labels. **P0 conflict explanation:** a
  generated "Why unresolved: …" sentence built only from the structured
  candidates (never picks a winner). **P1:** co-IP cards render "co-IP" + an
  IP BAIT field (from the panel's printed IP: lane); "DOI:" label; scoped
  zero-result copy ("…in the current HiveBlot beta dataset… does not mean no
  such evidence exists in the literature"). Supabase flow is now 4 migrations
  (docs + CLI copies + drift guard updated). Tests: engine suites green,
  benchmark 34/34, harness 100% EXACT, **api 113/113**, tsc clean. All seven
  flagship queries verified in-browser incl. zero-result and reseed-survival.
- **2026-08-13 (session 8, night sprint)** — Claude Fable 5. **MANUAL-TEST FIXES +
  SUPABASE READINESS.**
  (1) **Search is explicit-submit only** (manual issue 1): typing never fires a
  request; Enter or the new SEARCH button submits; submitted queries land in the
  URL via replaceState (shareable/refresh-safe); `?q=` auto-load unchanged and
  now also populates the input box. Browser-verified: 12 chars typed + 2 s wait
  → zero /api/search requests; button + real-KeyboardEvent Enter both submit.
  (2) **Experiment-card identity** (manual issue 2): each grouped card shows an
  identity line — a deterministic design tag derived ONLY from the group's own
  lane labels (≥3 pure timepoints → TIME COURSE; ≥3 shared-prefix distinct
  trailing numbers → DOSE SERIES) plus the reviewed record's verbatim
  `treatment_context` (truncated). Nothing invented; the Fig 3C/3D records
  carry their figure labels because the reviewed context text starts with them.
  The flagship query's three cards now read: TIME COURSE / "Fig 3D: …
  inhibitor matrix" / DOSE SERIES. Also removed the TREATMENT-field fallback to
  treatment_context (was duplicating the new identity line on co-IP cards).
  (3) **`IL-6 · 3D` RESOLVED — it was a fabricated duration** (manual issue 3):
  the paper never states a 3-day treatment; the case-insensitive duration regex
  parsed the FIGURE REFERENCE "Fig 3D" in the treatment context as "3 D(ays)"
  (same trap: "Fig. 3H" → 3 hours, "3D culture" → 3 days). Engine fix, two
  layers: single-letter units h/d must be lowercase (multi-letter units stay
  case-insensitive via scoped (?i:)), and `is_figure_reference_number()` guards
  every dose/duration/series match against a preceding fig/figure/panel
  reference (a rejected figure-list span is also consumed so its trailing
  number cannot leak back as a single). "Figure 2, 4 h exposure" keeps its real
  4 h. Phospho paper regenerated: Fig 3D records now duration=MISSING (the
  captured context states no duration). 10 new regressions.
  (4) **Lane readability** (manual issue 4): display-only formatter — trailing
  +/− state markers get colons and " / " becomes " · " ("IL-6: + · CL-E: −");
  conjunction "+" ("CL-E + Bis II") untouched; semantics unchanged.
  (5) **Supabase CLI readiness**: `supabase/config.toml` + timestamped
  `supabase/migrations/` copies of the canonical SQL, `scripts/
  sync_supabase_migrations.py`, and a pytest drift guard (byte-equality) so
  `supabase db push` and the SQL-editor flow can never diverge. Role grants
  audited: hive_feedback = INSERT+SELECT on hiveblot_feedback only, zero grants
  on western_blot_records. DEPLOYMENT.md rewritten: exact CLI sequence (login →
  link → db push --dry-run → push → role passwords → seed_remote.py, expect 475
  rows), exact env-var NAMES from api/app/config.py, 8-step smoke checklist.
  Browser-verified end-to-end: flagship query → 3 experiments (18 lanes) with
  distinct identities; co-IP PIK3CA → 4 grouped co-IP experiments, bait/IgG/
  Input intact; evidence panel + crop (1153 px PNG) + 33 feedback controls on
  grouped cards. Tests: **biology 165/165**, api **112/112**, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean. Model creds + cloud Supabase:
  re-checked, still absent (user actions below).
- **2026-08-13 (session 7)** — Claude Fable 5. **REVIEW SWEEP + CROP SERVING +
  RULE HARDENING.** Three parallel review agents ran; main agent implemented.
  (1) **Figure crops now render in the evidence panel**: `GET /records/{id}/crop`
  serves the record's own panel PNG (path from the DB column only, validated
  inside `CROP_BASE_DIR`, .png-only; 404→text fallback in deployments without
  the archive; 5 new API tests incl. traversal). Verified live end-to-end.
  (2) **Band-pattern rules hardened** — the independent probe-driven review
  (`research/band_pattern_scientific_review.md`) found 4 ship-blockers, all
  fixed with regressions: negation now abstains ("no smearing" no longer
  asserts smear); singular "higher-MW band" is not a ladder; caption-derived
  patterns on multi-lane panels are AMBIGUOUS, never per-lane SUPPORTED;
  absent+pattern contradictions raise BAND_PATTERN_STATE_MISMATCH (+ eval
  stamps corrected to present lanes only → 26 doublet lanes). Plus:
  "polyubiquitin smear"→ladder via containment pruning; count guard for
  "Fig. 3 bands"/"n = 3"/"1-2 bands"; parenthetical patterns no longer leak
  across "and".
  (3) **Demo dry-run** (`research/demo_readiness_review.md`): every scripted
  query verified live against the API; demo doc fixed (`needs review P-ERK`
  step, crop beat, 91-experiments close line, 20/min rate-limit warning).
  (4) **`scripts/seed_remote.py`** closes the DEPLOYMENT.md remote-seed TODO.
  (5) **Independent scientific QA delivered and acted on**
  (`research/independent_scientific_qa.md`: 3 Critical / 12 Major / 8 Minor /
  12 verified-correct). All three Criticals FIXED + regression-tested:
  **C1** — one CV crop (phospho paper cand_0034) held TWO experiments (Fig 3C
  + 3D); the collapsed observation asserted IL-6 on the Ser727 arm although
  the legend says Fig 3C ran WITHOUT IL-6. Reference data corrected to the
  printed 6-/7-lane matrices (unverifiable band states → `uncertain`); README
  correction note added. Phospho paper now 20 records / 113 rows; DB 475.
  **C2** — engine bug: an anti-ubiquitin antibody's own antigen name asserted
  `modification_type=ubiquitination` SUPPORTED (same failure class as the
  banned p-prefix rule). detect_modification now treats a mod-word that IS the
  whole target as protein identity; "ubiquitinated EGFR" still claims.
  **C3** — the session-4 self-audit contained false claims; correction banner
  added, independent QA is authoritative. Majors fixed: **M6** (µ-sign doses
  were dropped; series regex fabricated "1 nM" from "BafA1" — both fixed),
  **M7** (ACTB/TUBA1B now loading controls — 81 rows were misclassified),
  **M9** (doubtful BEX2 doublet removed; QA-confirmed Fig 1C LC3B doublet
  added; β-actin Greek-letter now resolves via beta-normalization), **M10**
  (README coverage note: Fig 5A/5B fell below the CV threshold — post-filter
  count ≠ paper content). Still open (documented, next-queue): M5 per-lane
  dose coverage (lane labels carry bare numbers, unit lives in the axis
  label), remaining Majors/Minors listed in the QA file.
  Creds RE-CHECKED: model backend + cloud Supabase both still absent — those
  two user actions remain the only blockers to automated extraction and
  hosted deployment. Tests: **biology 155/155**, api 111/111, benchmark 34/34,
  harness self-test 100% EXACT, tsc clean.
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
~~Manual-test fixes (search submit, card identity, IL-6·3D, lanes) + Supabase CLI prep~~ — **DONE (session 8)**.

~~Legacy Supabase production audit~~ — **DONE (session 10)**,
`research/supabase_legacy_audit.md`.
~~Beta-table inspection + plan~~ — **DONE (session 11)**,
`research/supabase_beta_table_plan.md`.

~~Wait for Srushti's clean Supabase project~~ — **DONE (session 12)**: linked,
migrated, seeded, verified on `zafombwswztvnjikcsdm`.

**NEXT — exact task: host the API, then the web app.**

1. **USER ACTION (the only blocker):** log in to one container host, then tell
   the agent. Recommended `railway login` (CLI already installed, free tier);
   Fly.io or Render are equally fine. Everything after this is prepared:
   ```bash
   python scripts/stage_crops.py                    # 21 crops, 6.2 MB
   docker build -f api/Dockerfile -t hiveblot-api . # context = repo root
   ```
   Then set the API env vars (names in `DEPLOYMENT.md` §2; values are already
   generated in the untracked `api/.env.cloud`) and deploy.
2. Deploy `web/` to Vercel (CLI already authenticated as `nikhilesh-s`), root
   `web/`, with `API_BASE_URL` = the deployed API origin and the SAME
   `INTERNAL_API_KEY`. **Never** prefix either with `NEXT_PUBLIC_`.
3. Set `ALLOWED_ORIGINS` on the API to the deployed web origin, redeploy the
   API, then run the 12-step hosted smoke checklist (`DEPLOYMENT.md` §4).
4. Fill the two URLs into `research/TEAM_BETA_HANDOFF.md` and send it to the
   team.
5. **Fix the duplicate `stable_row_key`** (session-12 finding): add cell line to
   `_record_id` so the H1792/A549 side-by-side crop stops collapsing P62, LC3B
   and ACTB across cell lines, then re-review and reseed. 24 of 475 rows.
6. Model creds when available → the staged automated-extraction evaluation
   below (harness already scores EXACT / ACCEPTABLE / PARTIAL / WRONG /
   MISSING / HALLUCINATED; protocol in
   `research/automated_extraction_eval_protocol.md`).

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
- ~~Which Supabase project is canonical for the beta, and has `migrations/001` been applied?~~
  **ANSWERED (session 10).** The legacy hackathon project `QIB`
  (`belalrbfrndxvdwvjxte`) is **NOT** canonical for the beta and must stay
  read-only: no migration has ever been applied to it and its owner has
  frozen the schema. The beta target is a new **persistent `hive-beta`
  branch** off that project (fallback: a standalone project). See
  `research/supabase_legacy_audit.md`.
- ~~Is `SuhasKM's-Org` on a plan that allows a persistent branch…?~~ **MOOT
  (session 11)** unless Srushti's separate HiveBlot project stalls — that
  project supersedes the branch (same isolation, no plan upgrade, no branch
  compute, HiveBlot-owned). Only revisit if it does not materialise.
- Two beta-table facts need a SQL console to settle (see
  `research/supabase_beta_table_plan.md` §1.5): does
  `western_blot_records_beta.id` default to **production's** sequence (inserts
  would advance production's id counter), and is RLS enabled on the beta
  tables? Neither blocks the recommendation — we are not using those tables.
- Which Bedrock model + region are provisioned (model access approved)?
- Should `image_crop_ref` become RELATIVE to `CROP_BASE_DIR`? The container
  currently reproduces the authoring absolute path to serve crops without
  touching the reviewed corpus (session 12). Relative refs are cleaner but
  rewrite every seeded row.
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

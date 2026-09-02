# HiveBlot — UCSF beta readiness report

**Date:** 2026-09-01 · **Branch:** `feature/bio-context-beta` · **Author:** primary
Claude engineering agent, consolidating the former Ananya / Suhas / Srushti /
Tanvi / Yashvi workstreams with Nik as founder.

**Verdict: READY FOR UCSF BETA WITH KNOWN LIMITATIONS** (section I).

Final commit SHA: see `HANDOFF.md` → Canonical Repository (this report was
committed together with the handoff; `git log -1` on the branch is
authoritative).

---

## A. Version control

| Item | Result |
|---|---|
| Canonical branch | `feature/bio-context-beta` (origin in sync; `main` predates the beta and was not touched) |
| Srushti integration | **Case A.** All 14 of Srushti Madhure's commits (`43c3b63` … `987c4aa`, 2026-08-25/26: `requirements-local.txt`, results IA redesign, row refinement, treatment/lanes column, compact metadata, evidence-panel hide, `allowedDevOrigins`, search-bar UX, spacing, IBM Plex typography, workspace alignment ×2, light/dark theme) are already ancestors of the branch. No separate local or remote branch, no dangling commits of hers (`git fsck` found only two pre-rebase copies of Nik's own commits), no cherry-picks needed, no merge performed. |
| Regression check | Only two commits landed after hers (`0653fbd`, docs) and none of her files changed; nothing regressed. |
| `requirements-local.txt` | Verified correct: `-r api/requirements.txt`, `-r western_blot_miner/requirements.txt`, `pgserver`. Production installs `api/requirements.txt` only (Dockerfile + `render.yaml`), so `pgserver` never reaches Render. |
| Additional work needed | None of her described work was missing. Her `View Evidence` removal is respected (see E: evidence access was re-added as a compact toggle because provenance had become unreachable, not as a reversal of her layout). Her `STATE3.png` stand-in preview was replaced by the record's own crop (a stand-in image on a provenance tool is a trust problem). |

Commits of this pass (logical, by phase):

1. `beaec0f` Harden Supabase table access with RLS and scoped roles
2. `393ffa6` Resolve UCSF beta P0 communication issues on About and Learn
3. `5c54352` Complete consolidated researcher and biology QA fixes
4. (this commit) Finalize UCSF beta handoff — docs, readiness report, consolidation notes

## B. Security

### Before → after (live project `zafombwswztvnjikcsdm`)

| Role | Before | After |
|---|---|---|
| `anon` (publishable key, PostgREST) | SELECT/INSERT/UPDATE/DELETE/TRUNCATE/… on **both** tables + sequence USAGE; **rows readable and mutable from any browser with the anon key** (verified: PostgREST returned rows) | **nothing** (verified: 401 `permission denied` on read, insert, update, delete) |
| `authenticated` | same as anon | nothing |
| `hive_readonly` | SELECT on `western_blot_records` **and** on `hiveblot_feedback` (via the base schema's `ALTER DEFAULT PRIVILEGES … GRANT SELECT ON TABLES` + 002's explicit grant) | SELECT on `western_blot_records` only, through policy `hive_readonly_select_records`; default privilege revoked |
| `hive_feedback` | INSERT+SELECT on feedback, sequence USAGE | unchanged privileges, now through policies `hive_feedback_insert_feedback` / `hive_feedback_select_feedback`; SELECT is a proven requirement (`INSERT … RETURNING feedback_id` and rehydration `GET /records/{id}/feedback` both run on this role) |
| `postgres`, `service_role` | owner / BYPASSRLS | unchanged (server-only) |
| RLS | disabled on both tables | **enabled on both**, no policies for client roles |
| Default privileges (`postgres` owner, `public`) | tables/sequences → anon, authenticated, service_role, hive_readonly | tables/sequences → service_role only |
| Security Advisor | 2 × ERROR `rls_disabled_in_public`, 1 × WARN `extension_in_public` (pg_trgm) | **0 errors**, 1 × WARN (pg_trgm, deferred — see below) |
| Row counts | 475 records / 1 feedback (+ smoke rows during testing) | 475 records / 475 distinct `stable_row_key` / 1 real feedback row (all smoke rows deleted) |

Migration: `migrations/004_secure_public_tables.sql` (+ `.down.sql`), CLI copy
`supabase/migrations/20260901000005_secure_hiveblot_public_tables.sql`,
applied with `supabase db push` (dry run showed exactly that one migration,
no seeds, no roles). The misleading statements in `api/db/schema.sql` and
`migrations/002_feedback.sql` were replaced with comments explaining the
repair (the CLI copies of applied migrations changed byte-wise; Supabase
records versions, not checksums, so history is unaffected).

Application changes: the API no longer opens a PostgREST client. `/` returns
a static index and `/proteins` runs a parameterized query on `hive_readonly`;
the `supabase` Python dependency is removed. `SUPABASE_KEY` is now optional.

Tests: `api/tests/test_db_access_matrix.py` (9 tests) applies the whole
migration chain to a scratch Postgres (`scripts/local_db.py test-url`) and
checks every allowed and denied operation per role, including the
future-table default-privilege leak and reversibility of the down migration.
`supabase test db` needs Docker, which this machine lacks; the matrix test is
the substitute and runs in plain pytest.

Backups (local, `chmod 600`, never committed): `~/hiveblot-backups/2026-09-01-pre-rls/`
holds a structured schema snapshot (columns, indexes, constraints, ACLs,
policies, roles, default ACLs) and the full pre-migration feedback rows.
`supabase db dump` also needs Docker and was not available.

**pg_trgm in `public` (WARN, deferred on purpose).** The GIN trigram index on
`target` uses `gin_trgm_ops`. `ALTER EXTENSION pg_trgm SET SCHEMA extensions`
would relocate the operator class; the existing index references it by OID and
should remain valid, and the search path only uses `ILIKE` (no `%` operator),
but this has not been proven on a copy of the database. Not worth the risk
the week before UCSF. Procedure when there is time: create the `extensions`
schema if absent, `ALTER EXTENSION pg_trgm SET SCHEMA extensions`, then rerun
the seven flagship searches and `EXPLAIN` one of them to confirm the index is
still used.

## C. Scientific QA (former Ananya workstream)

Method: all 93 reviewed records dumped and read field-by-field against the
three PDFs (text re-extracted with PyMuPDF), the figure legends, the methods
antibody lists, and the 21 panel crops in `api/crops/`. One complete
experiment audited per paper in depth, plus every AMBIGUOUS / CONFLICTING
field in the corpus.

### Corrected Fig 3C / Fig 3D (crop `page_005_cand_0034.png`)

Verified against the crop and the Figure 3 legend:

| | Panel C (Ser727) | Panel D (Tyr705) |
|---|---|---|
| Lanes in crop | 6: ctrl · CL-E · CL-E+Bis II · CL-E+U0126 · Bis II · U0126 | 7: ctrl · IL-6 · IL-6+CL-E · IL-6+CL-E+Bis II · IL-6+CL-E+U0126 · Bis II · U0126 |
| Lanes in records | identical, 6 | identical, 7 |
| IL-6 | none in panel, none in records ✓ (legend: "in the absence of IL-6") | present, records carry `IL-6` ✓ |
| Leakage between panels | none: separate `stable_row_key` hashes, separate treatment contexts, separate lane sets ✓ | ✓ |

Band states are conservative (several faint lanes marked `uncertain` rather
than present). Panel D lane 4 (IL-6 + CL-E + Bis II) shows a visible P-Tyr705
band in the crop but is recorded `uncertain`; this is an abstention, not a
false claim, and is logged as QA-1 below.

### One complete experiment per paper

| Paper | Experiment | Verdict |
|---|---|---|
| 10.3892/br.2026.2108 | Fig 2A time course, `P-STAT3 (Tyr705)` → STAT3 P40763, phospho Tyr705, phospho_western, Hep3B, IL-6 10 ng/ml, duration varies by lane 0–60 min, CST #9145 (methods: "p-STAT3 (Tyr705; 1:1,000; CST #9145)"), expected 88.1 kDa, reported none, β-actin loading control CST #4967 | **all fields correct** |
| 10.1186/s12964-025-02385-8 | Fig 4D co-IP, H1792, IP bait PIK3CA (lane "IP: PIK3CA"), readouts p85 / PIK3CA, inputs BEX2 / ACTB, lanes Input BEX2 −/+ and IP BEX2 −/+; PIK3CA CST #4249, p85 Proteintech 60225-1-Ig, ACTB Sigma A1978 | **correct**; p85 canonical identity deliberately MISSING (the paper never says PIK3R1/PIK3R2 — correct abstention); the methods list two anti-PIK3CA antibodies (CST 4249, SC-293172) and the record carries one (pre-existing open Major M12) |
| 10.3892/ijmm.2022.5188 | Fig 5C duct ligation, `GAPDH` → mouse Gapdh P16858, 35.8 kDa, loading_control, mouse SMG tissue, organism mouse, CST 5174s (methods: "cat. no. 5174s"), lanes L5d Ctrl / L5d / L7d Ctrl / L7d all present; ubiquitin lanes L5d / L7d `uncertain` (visibly faint) | **correct**; tissue stored in `cell_line` (pre-existing Minor M11) |

### Abstention review (every AMBIGUOUS / CONFLICTING in the corpus)

| Case | Rows | Judgment |
|---|---|---|
| `P-ERK 1/2` modification CONFLICTING (phospho-specific CST #4370 vs site-less `P-` label) | 10 | **Agree.** Uppercase `P-` alone is not a phospho marker; the antibody argues phospho. Neither settles it; value null + both claims is the honest output. |
| `P-ERK 1/2` / `T-ERK 1/2` protein AMBIGUOUS → MAPK1/MAPK3 family | 20 | **Agree.** The label names a family; picking one accession would be false precision. |
| Duration AMBIGUOUS on time courses ("varies by lane") | 40 | **Agree**, and it is not uncertainty: rendered as a range now without the `?` marker. |
| Dose AMBIGUOUS on multi-agent panels (Fig 3C/3D, CL-E dose series) | 22 | **Agree** that one scalar is wrong; the previous "varies by lane: 20–60" without a unit was misleading (µg/ml and µM mixed). Now rendered as "several agents at different doses in this panel". |
| `Ubiquitin`, `P62`, `LC3B`, `ATG12-ATG5`, `p85` protein identity MISSING | 66 | **Agree.** None resolves to a single reviewed accession from the paper's wording (ubiquitin is a family; p85 is PIK3R1 or PIK3R2; LC3B/P62 lack a gene symbol in the text). |

No SUPPORTED field was found to be unsupported. No false "Supported" exists in
the corpus.

### Findings (no corpus edits made)

| ID | Finding | Severity | Rows | Correction | Reseed? |
|---|---|---|---|---|---|
| QA-1 | Fig 3C/3D records carry no dose or duration although the legend states CL-E 60 µg/ml for 1 h (3C) and IL-6 10 ng/ml, 30 min after 1 h pretreatment (3D). Root cause: the reviewed treatment-context paraphrase omits the durations, and the panel-level dose is (correctly) unsettled because three agents share the panel. An abstention, not a false claim. | Minor | 6 | Extend the two reviewed context strings with the legend durations and regenerate | **Yes** (reviewed-data change) — deferred, founder decision |
| QA-2 | Panel D lane 4 (IL-6 + CL-E + Bis II) shows a visible P-Tyr705 band; record says `uncertain` | Minor | 1 | Re-review band state | Yes — deferred |
| QA-3 | Two anti-PIK3CA antibodies in the methods, one recorded (open M12) | Minor | 8 | Record both with association confidence | Yes — deferred |
| QA-4 | Mouse SMG tissue stored in `cell_line` (open M11) | Minor | 124 | Move to `tissue` | Yes — deferred |
| QA-5 | Input / loading-control rows inside co-IP crops inherit `experiment_type = co_ip` and the bait (open M8) | Minor | ~8 | Classify per row | Yes — deferred |

Regression tests added this pass: `api/tests/test_public_shaping.py` (7) and
`api/tests/test_db_access_matrix.py` (9). Corpus corrections above are NOT
applied; each would be a reviewed reseed and is Nik's call.

### Glossary (biology-checked; shipped on `/learn`)

IgG · IP bait · Input · phospho / site · loading control · doublet · kDa ·
expected vs reported MW · as printed — see `web/app/learn/page.tsx`.

## D. Search / data (former Suhas workstream)

### Flagship queries (hosted, before and after the migration; local new-code API identical)

| Query | Expected | Result |
|---|---|---|
| `phospho STAT3 Tyr705` | 3 / 18 | 3 / 18 ✓ |
| `co-IP PIK3CA` | 4 / 14 | 4 / 14 ✓ |
| `CST 9145` | 3 / 18 | 3 / 18 ✓ |
| `P-ERK` | 2 / 10 Conflicting | 2 / 10, both cards Conflicting with both claims and no winner ✓ |
| `GAPDH mouse` | 5 / 31 | 5 / 31 ✓ (see semantics below) |
| `needs review` | 4 / 20 | 4 / 20 ✓, every card lists why |
| `BRCA1 MCF7 olaparib` | 0 | 0 with scoped copy ✓ |

### `GAPDH mouse` — why it works and what it means

Generated SQL: two AND'd free-text groups, each OR'd across the ten
`TERM_COLUMNS` (`target`, `raw_target_name`, `canonical_target`,
`uniprot_id`, `cell_line`, `sample`, `treatment_name`, `treatment_context`,
`antibody_target`, `modification_label`). `mouse` is **not** a predicate on
the populated `organism` column; it matches because every mouse-paper row
stores `mouse submandibular gland (SMG) tissue` in `sample` and `cell_line`.

Corpus facts (live DB): `organism` = human 238, mouse 124, null 113. All 124
mouse rows contain "mouse" in a text column; 0 non-mouse rows contain the
word anywhere. So on this corpus the text match and a true organism predicate
return identical sets — the count is correct by coincidence of the data, not
by design.

False-positive cases a text match would produce (none present today): a human
sample whose context mentions "mouse anti-X antibody" or "mouse xenograft";
a treatment named after a mouse model. False negatives: a mouse cell line
named only by its code (`NIH/3T3`, `RAW 264.7`) with no "mouse" text; 113
rows with `organism` null that a strict predicate would drop although some are
human by cell line.

Recommendation (implemented: **no parser change**): keep honest over-returning.
A future structured organism filter should (a) fire only on an exact
organism token (`mouse`, `human`, `rat`, `murine`), (b) match
`organism = X OR <text match>` rather than replacing the text match, so rows
with null organism are never silently hidden, and (c) be shown in the
generated SQL. Founder decision.

### `image_crop_ref` — every consumer

| Consumer | Uses the value how | Status |
|---|---|---|
| `api/app/routers/internal.py` `/records/{id}/crop` | reads the DB column directly, validates inside `CROP_BASE_DIR` | unchanged; serving unaffected |
| `api/Dockerfile` | reproduces the authoring path so stored refs resolve | unchanged |
| `WesternBlotRecord` / `RecordDetail` (public responses) | **now serialize the filename only** (`page_004_cand_0025.png`) | fixed, tests pin it |
| `web/app/search/page.tsx` grouping fallback | only for legacy rows without `stable_row_key` (none in the corpus) | works with the filename |
| `web/components/EvidencePanel.tsx` | truthiness + basename for the fallback note | works |
| Seeded DB values | absolute authoring paths | **untouched** — no reseed needed |

Verified: zero occurrences of `/Users/` in any search or detail response from
the new API. The hosted Render API still runs the previous build until Nik
deploys (see H); until then list responses still carry the absolute path.

### Raw internal values

Root cause: `record_builder` writes engine markers into provenance
`sources[].text` (`"ambiguous_family"` for a family resolution, `str({})` for
an empty candidate, `""` for caption-derived cell lines) and `reconcile`
emits a modification candidate literally valued `"none"`; the detail shaper
passed them through into the slot the UI styles as a quotation. Fixed in
`api/app/record_detail.py` only: marker texts become `null` (the source
*type* is kept, so "via UniProt" still shows), null-valued candidates are
dropped, and the `none` modification candidate is relabeled
"no modification (total protein)" because it is a real claim (the row label
says total). Stored provenance is untouched. Verified on record 1252 (P-ERK)
and 999 (p85).

### `needs review` reasons

The engine already stores a plain-language `detail` per validation flag in
`anomaly_flags` (the list response already carried the flags, with their
internal evidence envelopes). Smallest researcher-facing shape, implemented:
`review_reasons: list[str]` on list rows and on record detail, derived server-
side from the flags, most severe first, de-duplicated; flags in list responses
are trimmed to `{code, severity, detail}`. Cards render the list under the
badge ("Why it needs review" / "Why conflicting"). The full `validation`
JSONB stays out of list responses. The frontend falls back to the flags'
`detail` when it talks to the previous API build.

### Cold starts

Measured: first `/health` after idle 21.2 s; warm requests ~0.15–0.3 s. Handled
with copy only: home page hint, `/about` hosting note, and a search-page note
that appears after 4 s of waiting. No keep-alive, no infra change.

## E. UX (former Srushti workstream)

Cold-researcher questions, before → after:

| Question | Before | After |
|---|---|---|
| What does HiveBlot search? | bare search box, typewriter headline | scope line under the headline: reviewed corpus, experiment-level Western blot evidence |
| How big is the corpus? | nowhere on the site (About said 2.8K papers) | home, search empty state, results header ("reviewed corpus · 3 papers"), About |
| What should I type? | placeholder only; search page example was a query with **zero** results (phospho-TBK1 in MEFs, not in the corpus) | flagship examples on home and search; empty state explains the query vocabulary |
| What is one card? | not explained | `/learn` "What one result represents"; results count reads "N experiments (M lane records)" |
| Why did this match? | not shown | not added (deferred; the generated SQL is in the API response and could be surfaced later) |
| Why Needs Review? | nothing on the card; validation flags unreachable | reasons listed on the card and in the evidence panel |
| What does Conflicting mean? | badge only | card lists why; panel shows both claims + "Why unresolved"; `/learn` teaches it |
| Where is provenance? | **unreachable** — `View Evidence` had been removed and the card showed a stand-in STAT3 image | `Evidence & sources` toggle on every card opens the existing panel: crop, sources, quotes, lanes, feedback, DOI; card preview is the record's own crop |
| What next? | dead end | DOI link on card and panel; Evidence toggle; feedback controls (see ranking) |

Presentation fixes: bare `RESULTS -` dash removed; `?` no longer shown on lane
series; empty "WHY HIVEBLOT SAYS THIS" now states that the label could not be
mapped to a single protein entry; mixed-unit doses no longer print a unit-less
range; cold-start note; flags section renamed "Why it needs review"; lane
durations render `30 min` not `30.0 min`.

Light/dark: both verified in the local browser (search page in light mode on a
375 px viewport; home, About, Learn, search in dark). Mobile: the filter
drawer, stacked cards and the review-reason list render; the drawer's click
path could not be re-driven by automation in this session (browser pane
hidden), but its markup, `aria-expanded` wiring and Escape handling are
unchanged from Srushti's session-27 implementation, which was verified then.

**Confidence display decision (recommendation, implemented as "hidden"):**
keep numeric confidence hidden. Per-field confidences are engine heuristics
(0.5 for every AMBIGUOUS family, 0.96 for every UniProt hit), not calibrated
probabilities; showing 0.96 vs 0.5 would invite a precision the numbers do not
have. The categorical status (Supported / Needs review / Conflicting / not
reported) plus the listed reasons is the honest signal. Revisit only after a
calibration study on unseen papers.

**Next-action ranking (exploration only, none built):**
1. **More from this paper** — cheapest and most useful (add `doi` to the parser's term columns so a DOI is searchable; one line).
2. **Cite / copy DOI** — already a link; a copy button is trivial.
3. **Export CSV of the current results** — useful for the antibody-before-buying question; small.
4. **Save / shortlist** — needs client state; defer.
5. **Related experiments** — needs a similarity notion; defer.

Remaining friction: cards on a 375 px viewport are long (four review reasons
on P-ERK); the evidence panel is dense; multi-row panels show the same crop on
each target card (the crop is the panel, which is honest but repetitive);
"why did this match" is not surfaced.

## F. Scientific communication (former Tanvi workstream)

`/about`: removed "2.8K+ PAPERS PROCESSED", "12.4K+ BLOTS INDEXED", "520+
PROTEINS TRACKED", "uses computer vision and language models to
automatically identify / extract / aggregate", "the database grows with every
new publication". Added the honest corpus numbers, the three DOIs, the
Evidence Record explanation, "what HiveBlot refuses to do", an explicit
demonstrated / not-demonstrated split, audience statement, and the hosting
note. `/learn`: removed "detect and quantify", "band intensity … is what you're
really measuring", "compare band intensity across lanes", Upregulated /
Downregulated; added the four statuses, categorical band presence, source
tags, expected vs reported MW, and the glossary. Site metadata no longer says
"search thousands of published western blot results"; nav tagline reads
"Western blot evidence · beta". Hosted HTML and JS were scanned after deploy:
no overclaim strings remain.

Claims still needing founder review: none blocking. Nik may want to tune the
tone of the "refuses to do" list and decide how prominently "3 papers" sits on
the home page (currently in the scope line under the headline).

## G. Tests (final run on the branch tip)

| Suite | Result |
|---|---|
| `western_blot_miner/tests/test_biology.py` | 165/165 |
| `test_reconcile.py` | 21/21 |
| `test_loader_enrichment.py` | 18/18 |
| `test_extract_records.py` | 10/10 |
| `test_pipeline_records.py` | 11/11 |
| `test_stable_row_key.py` | 34/34 |
| `eval/score.py` benchmark | 34/34 (seed set, self-consistency only) |
| `api` pytest (with `HIVE_DB_TEST_URL`) | **129 passed** (113 previous + 7 shaping + 9 access matrix) |
| `web` `tsc --noEmit` | clean |
| `web` `npm run lint` | **0 errors, 0 warnings** (was 5 errors / 7 warnings) |
| `web` `npm run build` | clean |
| `git diff --check` | clean |

## H. Known limitations

- **Only 3 reviewed papers.** Coverage gaps are expected; zero results are scoped honestly.
- **Automated unseen-paper extraction is not validated.** Stage 2 has only run agent-in-the-loop; no precision / recall / F1 exists. No copy anywhere claims otherwise.
- **No densitometry**, ever, by design.
- **Render free-tier cold start** ~20–30 s (measured 21 s) after ~15 min idle; documented on the site.
- **Render redeploy pending (Nik).** The Render CLI on this machine is unauthenticated, so the API build `5c54352` (review reasons, crop filename, raw-value shaping, no PostgREST) is **not yet live** on `hiveblot-api.onrender.com`. The deployed frontend works against the old build (it falls back to flag details and never displays the raw crop path). Until the redeploy, list responses from the hosted API still contain the absolute crop path. Deploy: `render deploys create srv-da1rbvs9v7es738635ug --commit <sha> --confirm -o json` after `render login`, or Manual Deploy in the dashboard.
- **pg_trgm in public** (advisor WARN) deferred with a documented procedure.
- **Corpus findings QA-1…QA-5** are abstentions / classification nits, not false claims; each needs a reviewed reseed and is deferred to Nik.
- `supabase test db` and `supabase db dump` need Docker; the pytest access matrix and the structured snapshot stand in.
- "Why did this match" is not surfaced; organism filtering is text-based (documented).

## I. Release verdict

**READY FOR UCSF BETA WITH KNOWN LIMITATIONS.**

Why ready: the P0 trust problems are gone (public overclaims removed; the
database is no longer publicly readable or writable; provenance is reachable
again from every card; needs-review cards explain themselves); all seven
flagship queries return the reviewed shapes through the hosted stack after the
migration; no false SUPPORTED exists in the corpus; every test suite is green.

Why "with known limitations": three papers, no unseen-paper accuracy claim,
free-tier cold start, and one deployment step (Render) that only Nik can
perform. None of these affect scientific correctness of what is shown.

## J. Presentation-day checklist

1. Supabase: dashboard shows `zafombwswztvnjikcsdm` ACTIVE_HEALTHY; Security Advisor shows 0 errors.
2. Warm the API 2–3 minutes before: `curl https://hiveblot-api.onrender.com/health` (first call may take ~20–30 s; the second should be < 1 s).
3. If not yet done, deploy the API build (see H) and re-run step 2.
4. Open https://hiveblot-beta.vercel.app; confirm the scope line reads "3 papers · 93 experiments · 475 evidence rows".
5. Search `phospho STAT3 Tyr705` → 3 experiments (18 lane records); the first card shows the panel crop.
6. Click **Evidence & sources** on that card → crop, field sources with quoted sentences, lanes, DOI link.
7. Search `P-ERK` → Conflicting, both claims shown, "Why conflicting" listed.
8. Search `BRCA1 MCF7 olaparib` → 0 with the scoped copy (this is the honesty demo).
9. Submit one feedback (✓ on a field) and reload: it rehydrates as RESEARCHER FEEDBACK.
10. Toggle Light/Dark once; open `/about` and `/learn`.
11. Present.

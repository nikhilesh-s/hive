# Track B — biological QA / scientific validity (Tanvi's questions, unparked)

Source: code audit 2026-09-09 against `TanviQuestions.md`. The PLOS Biology
paper in that file was not opened. Nothing implemented.

## Two framing facts

1. The biology layer (`western_blot_miner/biology.py`, `reconcile.py`) is
   careful and each guard records the bug it prevents. The weak parts are
   the plumbing around it: what text reaches the rules, what is thrown away
   before the rules run, and that none of it is measured.
2. **The 475 reviewed rows are not ground truth.** Stage-2 extraction was
   agent-in-the-loop (`eval/demo/phospho_PMC12856536/README.md`), reviewed
   by the implementer, and `research/independent_scientific_qa.md` found a
   Critical error (C1) in them that was fixed by hand. Agreement with them
   is a reproducibility number, never accuracy.

## Answers to Tanvi's items (state today)

| # | Item | State | Gap |
|---|---|---|---|
| 1 | Normalizing across blot images | Fixed 350 DPI render, hardcoded ink thresholds (`gray<245`, `gray<210`), fixed-pixel crop margins (`pdf_preprocess.py:15,65-98,248-265,314-377`). No illumination/contrast normalization on the extraction path. | Pixel margins are coupled to `WBM_PDF_DPI` undocumented. Recorded issue M10: CV stage dropped two complete 9-row panels on PMC12706926 p.9 (~18 records). |
| 2 | Non-AI "is this a blot" score before the model | Exists: `candidate_score` 0–1 (`pdf_preprocess.py:268-311`), gates at 0.35 (write crop) and 0.65 (send to model). Signals: desaturation, dark fraction, horizontal-run morphology (heaviest), row/col CV; colour penalty. | **No precision/recall number exists** (`HANDOFF.md:49`). It is a panel-candidate detector, not a blot classifier; the western-vs-not call is still the model's. |
| 3 | Read figure + caption + methods | Contract is right: typed `Source` ranks (`evidence_record.py:25-31`), caption/methods sent with the image (`extract_records.py:131-134`). | **In production the caption is empty.** `pipeline.py:258-273` sends `{"caption": "", "methods": text_context}`. So `caption_modification_for_core` always abstains, the MW caption fallback never fires, band-pattern scoping has nothing to scope, panel-scoped co-IP runs on lane text alone, and provenance labels caption text as `methods` (QA M2). Highest-leverage fix in this audit. |
| 4 | Statuses supported / not supported / ambiguous / contradicting | Vocabulary is `SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING` (`evidence_record.py:19-22`); CONFLICTING keeps `value=None` with candidates; `_v()` nulls both CONFLICTING and MISSING in the flat row; phospho search deliberately includes disputed rows (`bio_query.py:110-118`). | **"Not supported" (paper contradicts the value) is not expressible**; `MISSING` means silent, not contradicted. `AMBIGUOUS` is inconsistent: `EvidenceField.ambiguous` keeps the top candidate as the searchable value while two other producers null it (`record_builder.py:355,192-197`). Convention, not invariant. |
| 5 | Escalate on ambiguous/conflicting | Exists behind `WBM_ESCALATE=False` (`extract_records.py:139-152`, `pipeline.py:147-150`). | `get_client(escalation=True)` only changes model for Bedrock (`llm_client.py:320-332`); on `claude_cli` it is a second ~20 s call to the same Sonnet. And line `:152` **replaces every record in the panel**, including SUPPORTED ones. |
| 6 | Regex normalization | Extensive in `biology.py` (phospho sites, modification words, co-IP, catalog/vendor/dilution, kDa, dose/duration with figure-ref guards, band multiplicity, identifiers, 26 protein aliases, loading controls). | No cell-line normalizer ("Hep3B cells" vs "Hep3B"); no tissue routing (M11: 124 rows store a tissue in `cell_line`); no treatment vocabulary; **`extract_antibody` is never called on the records path** (`supabase_loader.py:326-345` vs `record_builder.py:52-58,392-426`), so catalog numbers the model omits are lost. All L1 catalog mismatches are `live=null / reviewed="4967"`. |
| 7 | Missing data vs failed normalization | **No distinction.** `_v()` and `mk()` map both to NULL. No LLM second-check on null exists (escalation never inspects MISSING). | Testable without a model: re-scan the paper's full text with the field's own regex near the target symbol; hit = not recovered, no hit = not stated. Only ever run an LLM check on the "not recovered" bucket, never on "not stated". |
| 8 | UniProt aliases | `UniProtResolver` (`resolve.py:82-146`): `gene:` + organism + reviewed, exact-gene wins, >1 hit → AMBIGUOUS with no accession, network failure → MISSING; curated ambiguity short-circuit stops `ERK`→EPHB2. 16/16 accessions verified live (`independent_scientific_qa.md:527`). | Only `gene:` is queried; UniProt synonym fields are never read, so a non-symbol alias resolves MISSING. `_core_symbol` truncates multi-word names. Organism from cell line is deliberately not used. Paper-stated antibody cross-reactivity caveats are dropped (Minor 6). |
| 9 | DB + SQL search | Deterministic parser `bio_query.py:97-159` behind `sql_guard.py` (sqlglot, single SELECT, pinned table, function allowlist, forced LIMIT) and a read-only role. | **Closed on `feature/saved-results`:** the stale `api/app/nlp.py` OpenAI NL-to-SQL path was deleted, so `OPENAI_KEY` no longer changes normal search behavior. |
| 10 | Paper retrieval for QA | `ask.py:107-169`: lexical terms AND'd, back-off drops the last term first, DOI fallback, reviewed before live, `MAX_EXPERIMENTS=12`. | No relevance ranking: on a 334-row paper the twelve blocks are effectively the first twelve by id. QA never reads the PDF; a panel the CV filter dropped is invisible to `/ask`. |

## The L1 number, and what to do instead

L1 (`scripts/experiments/live_ingest_eval.py`) matched **29 of 113** reviewed
lanes on one of three DOIs, scores six fields on matched lanes only, cannot
penalize anything missing, and the committed table is stale (`cell_line
0.0`, `catalog 0.655` from a pre-`norm()` run; rescore gives 1.0 / 0.828).
Keep the HANDOFF line "not an accuracy claim".

The right harness already exists and has never been run:
`eval/model_comparison/compare_records.py` (record-level alignment, EXACT /
ACCEPTABLE / PARTIAL / WRONG / MISSING / HALLUCINATED with hallucination
weighted −1, `--self-test`) plus `research/automated_extraction_eval_protocol.md`
(never pool three papers into one number). Run it; do not build another.

## What "better" means this week (numbers that cannot be over-read)

- **Panel recall measured** (it currently is not) against a hand-made panel
  inventory of the three papers. Goal ≥0.9 is defensible to state as a goal;
  claiming it needs the inventory to exist.
- **Per-field agreement per paper with n and a run-to-run variance band**
  from three identical repeats. A change is "better" only if it beats the
  spread between repeats. Any field with n < 20 prints its n.
- **Null causes**: move parser misses down, not nulls down. A pipeline that
  turns paper-silent nulls into values has gotten worse.
- Nothing generalizes past three papers, and the write-up says so first.

Not doable in a week, do not promise: unseen-paper accuracy (needs 20–30
independently adjudicated papers and a reviewer not on the team), a
validated blot classifier (needs a labelled panel corpus), a synonym-level
UniProt resolver, re-annotating 475 rows, the C1-class "one crop, two
experiments" invariant.

## Tickets (ordered by scientific-validity impact)

### B-1 · Restore caption / methods separation in live extraction
- Acceptance: `_panel_context` splits the existing `text_context` on its own
  `LIKELY_FIGURE_OR_CAPTION_CONTEXT:` / `PAPER_SAMPLE_OR_METHODS_SNIPPETS:`
  headers and routes them; a records-mode run on the phospho paper yields
  at least one field whose top source is `figure_caption`; new pipeline test
  asserts a non-empty caption for a candidate on a page with a legend; the
  13 pipeline checks still pass.
- Estimate: 1.5 half-days. Depends on: nothing. Owner: Nik.

### B-2 · Deterministic antibody backstop in the records path
- Acceptance: `_antibody_info` fills vendor / catalog / dilution / clone from
  target-scoped methods text only when the model returned empty, tagged
  `source.type="deterministic"`, never overwriting a model value; the
  phospho paper's β-actin rows recover CST #4967; Tanvi spot-checks recovered
  values against the PDF before merge.
- Estimate: 1. Depends on: nothing. Owner: Nik + Tanvi.

### B-3 · Null provenance: `not_stated` vs `not_recovered`
- Acceptance: `null_reason` on the field envelope, set by re-scanning the
  paper's full text with that field's regex near the core symbol (copy
  `_kda_near_core`, `record_builder.py:445-461`); a pytest over the three
  reviewed papers emits the two-way table per nullable field; zero model
  calls; the evidence panel shows the distinction.
- Estimate: 2 (+0.5 web). Depends on: B-2 (shared helper). Owner: Nik +
  Srushti (panel) + Tanvi (adjudicate a sample of `not_stated`).

### B-4 · Panel inventory and CV recall measurement
- Status 2026-09-15: scaffold landed. `scripts/experiments/panel_inventory_review.py`
  writes blank `eval/demo/*/panel_inventory.json` templates and
  `research/experiments/B4_panel_inventory_review.md` (per-page stored vs
  model-sent candidates, a review list of unsent candidates on
  western-mentioning pages). Recall / precision are blocked until Tanvi fills
  the inventories. Known limit: `candidates.json` only stores crops above the
  0.35 gate, so panels lost below it are visible only to the human inventory.
  B-1 and B-2 are landed on `experimental/ucsf-demo-2026-09-09` with tests.
- Acceptance: `eval/demo/*/panel_inventory.json` for all three papers (per
  page: Western panels, targets, lane counts); a script reporting recall and
  precision at current thresholds plus a sweep; below-threshold candidates
  on pages containing "western blot" / "immunoblot" emitted to a review
  list. **Do not change thresholds in this ticket.**
- Estimate: 2 (Tanvi 1, Nik 1). Depends on: nothing. Owner: Tanvi + Nik.

### B-5 · Run `compare_records.py` against `claude_cli`, three repeats per paper
- Acceptance: `record_key` includes cell line (QA Minor 8); three runs per
  paper with `--no-cache`; per-paper per-field tables with a variance band
  and record-level MISSING / HALLUCINATED rates; published under
  `research/experiments/` with any pooled figure labelled non-generalizable.
  Re-run after B-1 and B-2 land for the before/after.
- Estimate: 2. Depends on: nothing to start. Owner: Nik.

### B-6 · Correct the stale L1 report
- Acceptance: regenerate for all three DOIs or delete the table and point at
  B-5; matched-lane coverage printed next to every agreement figure.
- Estimate: 0.5. Depends on: nothing. Owner: Nik.

### B-7 · Make escalation escalate, and merge instead of replace
- Acceptance: `WBM_ESCALATION_MODEL` honoured per backend (`opus` for
  `claude_cli`); only CONFLICTING / AMBIGUOUS records are replaced, the
  first-pass claim preserved as a candidate with `escalated=true`; a test
  asserts a SUPPORTED sibling survives byte-identical.
- Estimate: 1.5. Depends on: B-5 for the before/after. Owner: Nik.

### B-8 · Sample normalization and tissue routing
- Acceptance: deterministic normalizer (strip "cells" / "cell line" /
  "tissue" suffixes, keep raw wording) and a rule routing non-cell-line
  samples to `tissue` with `cell_line` null; grouping keys use whichever is
  populated; **`record_id` must not move** (it hashes `identity_sample`,
  `record_builder.py:711-724,765-771`, and stored corrections key off it): a
  regression test proves the three papers' record_ids are byte-identical
  before and after. Tanvi rules on which strings are lines vs tissues.
- Estimate: 1.5. Depends on: nothing. Owner: Nik + Tanvi.

### B-9 · Delete the OpenAI NL→SQL path
- Status: closed on `feature/saved-results`.
- Acceptance: `nlp.py` and its branch in `search_service.py` were removed and
  the suite passes. Normal search now always uses deterministic `bio_query.py`
  plus `sql_guard.py`; this avoids a second model-generated SQL path based on
  an older schema prompt.
- Estimate: 0.5. Depends on: nothing. Owner: Nik or Srushti.

### B-10 · Recruit external adjudicators for week 2
- Acceptance: two or three UCSF wet-lab contacts agreed in principle to
  adjudicate one paper each; a one-page annotation brief (fields, the four
  statuses, what "cannot tell from the figure" means).
- Estimate: 1. Depends on: nothing. Owner: Yashvi + Tanvi.

### B-11 (stretch) · Promote `band_pattern`, `band_count`, `lane_dose`, `lane_duration` to columns
- Migration 006/007 so they are searchable (QA Minor 5). 1 half-day. Owner: Nik.

Deliberately not this week: changing CV thresholds before B-4 measures them;
any LLM second-check on nulls before B-3 splits the causes; touching
`identity_sample` / `record_id`; any copy claiming precision or recall on
unseen papers; reseeding the hosted 475 rows from a changed pipeline.

## Found 2026-09-27 on the first wave-1 pre-extraction (9 papers, live tier)

Evidence query: `canonical_target IS NULL` grouped by DOI over rows ingested 2026-09-27;
per-paper notes in `outreach/PREEXTRACT_CHECK.md` (branch `outreach/oct20`).

### B-12 · Target normalization misses common protein names
- What: extracted but unresolved (`canonical_target` NULL): Ras, GFP-KRAS, Bcl-xL, JNK,
  α-tubulin, vinculin, α-actinin, MyHC, IL-18, LC3-I / LC3-II / LC3B-II, "Ph-eIF2α",
  "non-phos-4EBP1", "α-CASP1", "α-CASP3 cl.", "CASP1p10", "Active β-catenin".
- Why: `UniProtResolver` only queries `gene:<core>` (`western_blot_miner/resolve.py`), so a
  protein name that is not the gene symbol never matches, and `biology.core_symbol` keeps
  antibody prefixes ("α-" = anti-), form suffixes (-I/-II, cl., p20/p10), tags (GFP-, -myc)
  and phospho prefixes ("Ph-", "non-phos-").
- Acceptance: strip anti-/tag/form/phospho decorations into their own fields before lookup
  (phospho goes to modification, cleavage to a form note); fall back to a
  `protein_name:` search and the alias map; ambiguous families (Ras, JNK, ERK) resolve to
  AMBIGUOUS with candidates, never to one guessed gene. Table-driven test over the names
  above. Viral proteins (Vpr, Nef, Vif, gp120, p55) may stay unresolved but must be labeled
  as non-human, not silently NULL.
- Owner: Srushti (code) + Tanvi (expected mappings). Estimate: 1.5.

### B-13 · Non-western blots are extracted as westerns
- What: the Lyons NAR paper (10.1093/nar/gkag499) has ~455 live rows whose "targets" are
  rRNA species (18S, 28S, 47S/45S, ITS2): Northern blots of rRNA processing, stored as
  western blot evidence.
- Acceptance: panel classification labels Northern / Southern / gel stain / dot blot and
  keeps them out of `western_blot_records_live`; a regression fixture from this paper's
  Northern panel. Tanvi confirms on the paper which panels are which.
- Owner: Nik (pipeline) + Tanvi. Estimate: 1.

### B-14 · An unresolved target does not set needs_review
- What: Serra-Moreno (10.1371/journal.ppat.1014020) has 1206 live rows with no canonical
  target and 0% `needs_review`; Taabazuing's paper is also 0%. `needs_review` is
  `record_status != SUPPORTED` (`record_builder.py`), and the record status does not
  consider the target's own resolution status.
- Acceptance: a MISSING or AMBIGUOUS target makes the record at least AMBIGUOUS
  (needs_review true) with an anomaly flag naming the unresolved target; test on one row
  from each paper above. This is the trust signal researchers see first.
- Owner: Srushti + Tanvi. Estimate: 0.5.

## Added 2026-10-11

### B-15 · Check 10 extracted panels by hand with ImageJ — Tanvi
Why: no person has checked HiveBlot's readouts against the actual crops since the UCSF push. This
is the evidence we need before telling any lab the extraction is good.
- Pick 10 panels from the hosted live tier. Spread them across at least 4 papers, and include 2
  from the papers flagged in B-12/B-13.
- For each panel, open the crop. Check target, antibody (vendor, catalog, dilution against the
  paper's methods) and band present/absent per lane, against HiveBlot's row.
- In ImageJ (Analyze > Gels), measure the bands of one lane pair per panel and compare the
  direction and rough ratio with what HiveBlot shows on the band-reading page. Note saturation or
  clipping.
- Record one row per panel in `eval/manual_check_2026-10.csv`: record_id, doi, field, HiveBlot
  value, Tanvi's value, match (yes/no/unclear), note. Agents turn each mismatch into a B ticket.
- Done when 10 rows are in, with a one-paragraph summary at the top of `team-log.md`.

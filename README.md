# HiveBlot

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23491677.svg)](https://doi.org/10.5281/zenodo.23491677) [![Benchmark dataset DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23524346.svg)](https://doi.org/10.5281/zenodo.23524346)


Structured, provenance-tracked extraction of Western blot evidence from
published figures.

HiveBlot reads a Western blot figure together with its caption and the paper's
methods, and turns it into lane-level **Evidence Records**. Every field in a
record (target, modification, antibody, cell line, treatment, band state, ...)
has its own status and the verbatim source wording it came from, so a
researcher can check a value against the paper. When the figure and the text
disagree, HiveBlot flags the conflict and leaves the value empty instead of
choosing one.

Live beta: <https://hiveblot-beta.vercel.app>

## How it works

1. **Panel candidates.** OpenCV finds and scores candidate blot panels on each
   rendered PDF page (`western_blot_miner/pdf_preprocess.py`).
2. **Vision-language model.** Each candidate panel is sent to a
   vision-language model with its caption and methods context, which proposes
   what the panel shows (backend is configurable).
3. **Deterministic biology and UniProt reconciliation.** Plain code, not the
   model, decides modification, phosphosite, experiment type, loading control
   and protein identity (UniProt lookup), and reconciles competing sources by an
   evidence hierarchy (`biology.py`, `resolve.py`, `reconcile.py`).
4. **Evidence Records.** One record per lane. Each field carries a status:
   `SUPPORTED`, `AMBIGUOUS`, `CONFLICTING` or `MISSING`, plus the verbatim
   source text and where it was found. A `CONFLICTING` field has `value = null`
   and keeps the competing candidates (`evidence_record.py`).

A FastAPI service (`api/`) searches the records, and a Next.js app (`web/`)
shows each result next to its figure crop and source wording.

## Biology rules

These are enforced in code and tests; the model's output is treated as a claim,
not ground truth.

- Phosphorylation is never inferred from a name prefix such as `p-ERK`; it
  needs evidence (a phospho-specific antibody, or explicit caption or methods
  wording).
- A conflict between sources is stored as `CONFLICTING` with `value = null`.
- Expected molecular weight (from UniProt) and observed molecular weight (from
  the paper) are separate fields and are never merged.
- Band presence is not densitometry. Records hold categorical band state only.
- Experiment type (for example co-IP) comes from methods and caption text, not
  from how the image looks.

## Repository layout

| Path | Contents |
|---|---|
| `western_blot_miner/` | Extraction engine: PDF preprocessing, model client, biology rules, reconciliation, Evidence Record schema, tests |
| `api/` | FastAPI search service (SQL-guarded, read-only DB role) and its tests |
| `web/` | Next.js frontend |
| `eval/` | Benchmark cases, scorer, and worked example runs (`eval/demo/`) |
| `migrations/`, `supabase/` | Postgres schema and migrations |
| `scripts/` | Local database, seeding, experiments, release archive script |
| `research/` | Protocols, scientific QA reviews, experiment write-ups |
| `AGENTS.md` | Contributor and agent rules (it mentions an internal project-state file that is not part of release archives) |

## Quick start (local, no cloud credentials)

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-local.txt
.venv/bin/python scripts/local_db.py up                       # embedded Postgres
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json

cp api/.env.example api/.env     # fill DB_READONLY_URL / DB_FEEDBACK_URL from
                                 # `local_db.py status`; generate your own
                                 # INTERNAL_API_KEY and AGENT_API_KEYS
cd api && ../.venv/bin/uvicorn app.main:app --reload

cp web/.env.example web/.env     # API_BASE_URL=http://localhost:8000 and the
                                 # same INTERNAL_API_KEY
cd web && npm install && npm run dev
```

Tests and the offline benchmark:

```bash
python3 western_blot_miner/tests/test_biology.py   # and the other tests in that folder
python3 eval/score.py
cd api && ../.venv/bin/python -m pytest
```

Extracting from your own PDF needs a model backend; see
`western_blot_miner/README.md` and `.env.example`.

## Status and limits

- **Beta.** Interfaces and schemas may change.
- **Small reviewed corpus.** The hosted beta holds records from 3 papers, not a
  literature-wide index. Model reading for those papers ran with a human in the
  loop, so it is not a clean test of unsupervised extraction.
- **No accuracy claim yet.** Accuracy on unseen papers is being measured in a
  pre-registered blind benchmark. No numbers are reported here until it is
  complete. The seed scorer in `eval/` uses four worked examples and is
  not a validation result.
- **Densitometry is experimental.** It is validated on synthetic images only,
  is kept out of Evidence Records, and should be read as a reading aid, not a
  quantification.
- **Figure crops are not included** in release archives (see below).

## How to cite

Cite the archived release via its DOI badge above (placeholder until Zenodo
mints it) and the metadata in [`CITATION.cff`](CITATION.cff). GitHub and Zenodo
read that file to build a citation.

## License and third-party material

Source code and documentation are released under the [MIT License](LICENSE).
Figure crops and quoted passages come from published papers and remain under
their publishers' terms; they are not covered by the MIT license. See
[`THIRD_PARTY_NOTICE.md`](THIRD_PARTY_NOTICE.md).

## Blind benchmark

A pre-registered blind test on three unseen open-access papers: 92% of the 553 values HiveBlot asserted matched a wet-lab annotator's labels (coverage 57%, 512 of 895). Protocol, annotations, scoring code and results: `eval/blind_2026_10/`, archived at https://doi.org/10.5281/zenodo.23524346.

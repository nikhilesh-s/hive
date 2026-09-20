# L1 — live ingestion vs reviewed corpus (self-consistency)

> **Stale (B-6, noted 2026-09-15).** One DOI only; generated before B-1
> (caption/methods split) and B-2 (antibody backstop) landed on
> `experimental/ucsf-demo-2026-09-09`, so the `antibody_catalog_number` and
> `modification_label` columns no longer describe the current pipeline. Read
> every agreement figure next to its coverage: 29 matched lanes out of 64
> reviewed / 35 live-only, i.e. the lane matcher paired fewer than half the
> reviewed lanes. Regenerate for all three DOIs with `scripts/experiments/
> live_ingest_eval.py` (needs a model backend) or replace with B-5 before
> quoting anything from this table. Not an accuracy claim.

Same DOIs, same pipeline the demo runs, compared lane-by-lane with the human-reviewed rows. Says nothing about unseen papers.

| DOI | PMCID | candidates | records | seconds | matched lanes | only live | only reviewed | canonical_target | modification_label | experiment_type | cell_line | antibody_catalog_number | band_state |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.3892/br.2026.2108 | PMC12856536 | 9 | 20 | 183.5 | 29 | 35 | 64 | 1.0 | 0.828 | 0.828 | 0.0 | 0.655 | 0.862 |

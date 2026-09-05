"""Experiment L1: live ingestion self-consistency against the reviewed corpus.

Runs the SAME code path the demo uses (DOI -> open-access PDF -> OpenCV
candidates -> model -> deterministic biology -> rows) on the three reviewed
DOIs, then compares the live rows with the reviewed rows lane by lane:

    key = (raw target label, lane condition)   [both normalised]
    fields = canonical_target, modification_label, experiment_type,
             cell_line/sample, antibody_catalog_number, band_state

and reports per-field agreement, rows found only on one side, and timing.
This is the number we can honestly show UCSF for "how well does the
automatic read agree with the human-reviewed read on papers we know" —
it says nothing about unseen papers, and the doc says so.

Needs a model backend (WBM_LLM_BACKEND=anthropic + ANTHROPIC_API_KEY) and
network. Writes research/experiments/L1_live_ingest_eval.{json,md}.

Run:  WBM_LLM_BACKEND=anthropic .venv/bin/python scripts/experiments/live_ingest_eval.py [DOI ...]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from western_blot_miner import fulltext, pdf_preprocess, pipeline  # noqa: E402

REVIEWED = {
    "10.3892/br.2026.2108": "phospho_PMC12856536",
    "10.3892/ijmm.2022.5188": "standard_PMC9559174",
    "10.1186/s12964-025-02385-8": "coip_PMC12706926",
}
FIELDS = ("canonical_target", "modification_label", "experiment_type", "cell_line", "antibody_catalog_number", "band_state")
OUT = REPO / "research" / "experiments"
PDF_DIR = REPO / "western_blot_miner" / "data" / "live_pdfs"


def norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def key(row: dict) -> tuple[str, str]:
    return norm(row.get("raw_target_name") or row.get("target")), norm(row.get("lane_condition") or row.get("condition"))


def compare(live: list[dict], reviewed: list[dict]) -> dict:
    lv = {key(r): r for r in live}
    rv = {key(r): r for r in reviewed}
    common = sorted(set(lv) & set(rv))
    per_field = {f: {"agree": 0, "total": 0} for f in FIELDS}
    mismatches = []
    for k in common:
        a, b = lv[k], rv[k]
        for f in FIELDS:
            per_field[f]["total"] += 1
            if norm(a.get(f)) == norm(b.get(f)):
                per_field[f]["agree"] += 1
            else:
                mismatches.append({"key": k, "field": f, "live": a.get(f), "reviewed": b.get(f)})
    return {
        "live_rows": len(live), "reviewed_rows": len(reviewed), "matched_lanes": len(common),
        "only_live": len(set(lv) - set(rv)), "only_reviewed": len(set(rv) - set(lv)),
        "per_field": {f: {**v, "agreement": round(v["agree"] / v["total"], 3) if v["total"] else None} for f, v in per_field.items()},
        "mismatches": mismatches[:200],
    }


def main(argv: list[str]) -> int:
    dois = argv or list(REVIEWED)
    if not os.environ.get("WBM_LLM_BACKEND"):
        print("Set WBM_LLM_BACKEND (and credentials) — this experiment needs a live model.")
        return 2
    results = {}
    for doi in dois:
        t0 = time.time()
        got = fulltext.fetch_pdf(doi, PDF_DIR)
        if not got.get("pdf_path"):
            results[doi] = {"error": "no open-access PDF"}
            continue
        summary = pdf_preprocess.preprocess_pdf(got["pdf_path"], paper_id=doi)
        rec = pipeline.run_records_stage(summary, use_cache=False)
        live_rows = json.loads(Path(rec["rows_path"]).read_text())
        entry = {"pmcid": got.get("pmcid"), "candidates": summary.get("llm_candidate_count"),
                 "records": rec.get("records"), "failures": rec.get("failures"), "seconds": round(time.time() - t0, 1),
                 "backend": os.environ.get("WBM_LLM_BACKEND"), "model": os.environ.get("WBM_MODEL")}
        if doi in REVIEWED:
            reviewed = json.loads((REPO / "eval" / "demo" / REVIEWED[doi] / "supabase_rows.json").read_text())
            entry["comparison"] = compare(live_rows, reviewed)
        results[doi] = entry
        print(doi, json.dumps({k: v for k, v in entry.items() if k != "comparison"}))
        if "comparison" in entry:
            print("  per-field agreement:", {f: v["agreement"] for f, v in entry["comparison"]["per_field"].items()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "L1_live_ingest_eval.json").write_text(json.dumps(results, indent=2, default=str))
    md = ["# L1 — live ingestion vs reviewed corpus (self-consistency)", "",
          "Same DOIs, same pipeline the demo runs, compared lane-by-lane with the human-reviewed rows. "
          "Says nothing about unseen papers.", "",
          "| DOI | PMCID | candidates | records | seconds | matched lanes | only live | only reviewed | " +
          " | ".join(FIELDS) + " |", "|---|---|---|---|---|---|---|---|" + "---|" * len(FIELDS)]
    for doi, e in results.items():
        c = e.get("comparison") or {}
        pf = c.get("per_field", {})
        md.append(f"| {doi} | {e.get('pmcid')} | {e.get('candidates')} | {e.get('records')} | {e.get('seconds')} | "
                  f"{c.get('matched_lanes')} | {c.get('only_live')} | {c.get('only_reviewed')} | " +
                  " | ".join(str(pf.get(f, {}).get('agreement')) for f in FIELDS) + " |")
    (OUT / "L1_live_ingest_eval.md").write_text("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

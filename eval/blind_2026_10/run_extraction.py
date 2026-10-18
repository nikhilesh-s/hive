#!/usr/bin/env python3
"""Run the frozen system on the frozen papers and seal the outputs (PREREGISTRATION.md §2, §5).

    # stage 1 only (OpenCV, no model):
    .venv/bin/python eval/blind_2026_10/run_extraction.py PRIVATE_DIR preprocess
    # model stage (needs a working backend; production model):
    WBM_LLM_BACKEND=claude_cli WBM_MODEL=claude-opus-5 \
        .venv/bin/python eval/blind_2026_10/run_extraction.py PRIVATE_DIR extract
    # hash every output file into SEALED_OUTPUTS.sha256 (commit it before annotations arrive):
    .venv/bin/python eval/blind_2026_10/run_extraction.py PRIVATE_DIR seal

Outputs and timings stay in PRIVATE_DIR/runs/<PMCID>/; nothing is uploaded anywhere.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
FROZEN_SHA = "f77d311"


def frozen_code_check() -> None:
    diff = subprocess.run(["git", "diff", "--stat", FROZEN_SHA, "--", "western_blot_miner", "api"],
                          cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if diff:
        raise SystemExit(f"system code differs from frozen {FROZEN_SHA}:\n{diff}")


def frozen_papers() -> list[dict]:
    papers = json.loads((HERE / "papers.json").read_text())["papers"]
    return [p for p in papers if p["status"] == "frozen"]


def stamp(path: Path, **kv) -> None:
    data = json.loads(path.read_text()) if path.exists() else {}
    data.update(kv)
    path.write_text(json.dumps(data, indent=2) + "\n")


def preprocess(private: Path) -> None:
    from western_blot_miner import pdf_preprocess

    for p in frozen_papers():
        run = private / "runs" / p["pmcid"]
        t0 = time.monotonic()
        summary = pdf_preprocess.preprocess_pdf(private / "pdfs" / f"{p['pmcid']}.pdf",
                                                paper_id=p["doi"], out_dir=run)
        secs = round(time.monotonic() - t0, 1)
        stamp(run / "timing.json", preprocess_seconds=secs, pages=summary.get("pages"),
              candidate_count=summary.get("candidate_count"),
              llm_candidate_count=summary.get("llm_candidate_count"))
        (run / "summary_path.txt").write_text(str(Path(summary["out_dir"]) / "summary.json"))
        print(p["pmcid"], f"{secs}s", summary.get("candidate_count"), "candidates,",
              summary.get("llm_candidate_count"), "to the model")


def extract(private: Path) -> None:
    from western_blot_miner import llm_client, pipeline

    if os.environ.get("WBM_UPLOAD") or os.environ.get("SUPABASE_URL") or os.environ.get("DB_INGEST_URL"):
        raise SystemExit("refusing: a database upload variable is set")
    if os.environ.get("WBM_ESCALATE"):
        raise SystemExit("refusing: escalation is off in production")
    os.environ["WBM_CONCURRENCY"] = "1"
    ok, why = llm_client.backend_status()
    if not ok:
        raise SystemExit(why)
    env = {"backend": why, "model": os.environ.get("WBM_MODEL", "(backend default)"),
           "python": platform.python_version()}
    if why == "claude_cli":
        env["claude_cli_version"] = subprocess.run(["claude", "--version"], capture_output=True,
                                                   text=True).stdout.strip()
    for p in frozen_papers():
        run = private / "runs" / p["pmcid"]
        summary = json.loads(Path((run / "summary_path.txt").read_text()).read_text())
        t0 = time.monotonic()
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rec = pipeline.run_records_stage(summary, use_cache=False)
        secs = round(time.monotonic() - t0, 1)
        stamp(run / "timing.json", extract_seconds=secs, extract_started=started,
              panels_queried=rec["queried"], panel_failures=rec["failures"],
              records=rec["records"], lane_rows=rec["rows"], uploaded=rec["uploaded"],
              environment=env, frozen_code=FROZEN_SHA)
        print(p["pmcid"], f"{secs}s", rec["records"], "records,", rec["failures"], "panel failures")


def seal(private: Path) -> None:
    lines = []
    for p in frozen_papers():
        run = private / "runs" / p["pmcid"]
        for f in sorted(x for x in run.rglob("*") if x.is_file()):
            lines.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(private)}")
    (HERE / "SEALED_OUTPUTS.sha256").write_text("\n".join(lines) + "\n")
    print(len(lines), "files hashed")


if __name__ == "__main__":
    private_dir, step = Path(sys.argv[1]), sys.argv[2]
    frozen_code_check()
    {"preprocess": preprocess, "extract": extract, "seal": seal}[step](private_dir)

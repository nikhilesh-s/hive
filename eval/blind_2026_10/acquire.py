#!/usr/bin/env python3
"""Freeze the paper list (PREREGISTRATION.md §4): take papers in draw order, get each PDF with
the system's own fetcher, stop at 4. Writes papers.json; PDFs stay in the private directory.

    .venv/bin/python eval/blind_2026_10/acquire.py PRIVATE_DIR [--manual PMCID=path ...]

--manual records a PDF a person downloaded in a browser after the fetcher failed.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from draw import draw_order, panel_sequence  # noqa: E402

N_PAPERS = 4
OUT = HERE / "papers.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("private_dir", type=Path)
    ap.add_argument("--manual", action="append", default=[], help="PMCID=path/to/downloaded.pdf")
    args = ap.parse_args()
    manual = dict(m.split("=", 1) for m in args.manual)

    import fitz  # PyMuPDF, already a pipeline dependency
    from western_blot_miner import fulltext

    candidates = {c["pmcid"]: c for c in json.loads((HERE.parent / "candidates.json").read_text())}
    prior = {p["pmcid"]: p for p in json.loads(OUT.read_text())["papers"]} if OUT.exists() else {}
    pdf_dir = args.private_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    papers, frozen = [], 0
    for rank, pmcid in enumerate(draw_order(), 1):
        if frozen == N_PAPERS:
            break
        c = candidates[pmcid]
        entry = prior.get(pmcid) or {"draw_rank": rank, "pmcid": pmcid, "doi": c["doi"],
                                     "citation": c["citation"], "license": c["license"]}
        if entry.get("status") == "frozen":
            papers.append(entry)
            frozen += 1
            continue
        dest = pdf_dir / f"{pmcid}.pdf"
        if pmcid in manual:
            shutil.copyfile(manual[pmcid], dest)
            entry.update(acquired_by="manual browser download (fetcher failed)")
        else:
            got = fulltext.fetch_pdf(c["doi"], pdf_dir / "fetch")
            entry["fetcher_tried"] = got.get("tried")
            if got.get("pdf_path"):
                shutil.move(got["pdf_path"], dest)
                entry.update(acquired_by=f"system fetcher ({got.get('source')})")
        if dest.exists():
            entry.update(status="frozen", pdf_sha256=sha256(dest), pages=fitz.open(dest).page_count,
                         panel_sampling_sequence=panel_sequence(pmcid),
                         frozen_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            frozen += 1
        else:
            entry.update(status="no_pdf_yet",
                         note="fetcher failed; a person may download it in a browser (--manual), "
                              "otherwise it is skipped for access reasons only")
        papers.append(entry)

    OUT.write_text(json.dumps({"seed_rule": "draw.py", "n_target": N_PAPERS, "papers": papers},
                              indent=2) + "\n")
    for p in papers:
        print(p["draw_rank"], p["pmcid"], p["status"], p.get("acquired_by", ""), p.get("pages", ""))
    return 0 if frozen == N_PAPERS else 2


if __name__ == "__main__":
    raise SystemExit(main())

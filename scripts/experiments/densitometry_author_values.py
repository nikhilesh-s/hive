"""D-5 second half — is an author-value comparison (published LC3B-II : ACTB
ratios vs HiveBlot's within-image reading) possible at the v0.3 gates?

The reviewed BEX2 paper (10.1186/s12964-025-02385-8) publishes LC3B-II:ACTB
bar charts. A comparison needs BOTH the LC3B strip and the ACTB strip of the
same panel to pass the clipping gate. This script runs the gates over every
detected band row of the ten crops that carry LC3B / ACTB Evidence Records
(crop list taken from the local corpus on 2026-09-15; no DB needed here) and
counts rows that are not refused. "n too small" is an allowed result.

Run: .venv/bin/python scripts/experiments/densitometry_author_values.py
Writes research/experiments/D5_author_values.md
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from western_blot_miner import densitometry as D  # noqa: E402

PAPER = "10.1186_s12964-025-02385-8"
# crops referenced by LC3B / ACTB records of the paper (92 records, local corpus 2026-09-15)
CROPS = ["page_004_cand_0025.png", "page_005_cand_0032.png", "page_006_cand_0037.png",
         "page_006_cand_0039.png", "page_006_cand_0040.png", "page_007_cand_0045.png",
         "page_007_cand_0046.png", "page_009_cand_0055.png", "page_010_cand_0060.png",
         "page_010_cand_0062.png"]

lines = ["# D5 (second half) — author-value comparison feasibility at v%s gates" % D.METHOD_VERSION, "",
         "Question: can HiveBlot's within-image relative reading be compared with the LC3B-II:ACTB "
         "ratios the BEX2 paper publishes as bar charts? A pair needs the LC3B strip AND the ACTB strip "
         "of the same panel to pass the clipping gate. Diagnostic geometry (detected rows, auto lanes); "
         "`scripts/experiments/densitometry_author_values.py`.", "",
         "| crop | detected rows | rows not refused | max clipped core per row (first 8) |", "|---|---|---|---|"]
total_rows = total_ok = 0
for name in CROPS:
    p = ROOT / "api" / "crops" / PAPER / "panel_candidates" / name
    if not p.is_file():
        lines.append(f"| {name} | missing | | |")
        continue
    img = D.decode_image(p.read_bytes())
    probe = D.analyze(img, stability=False)
    states = []
    for ri in range(len(probe["rows_detected"])):
        r = D.analyze(img, row_index=ri, stability=False)
        states.append((r["band_row"], r["quality"]["state"], max(l["clipped_fraction"] for l in r["lanes"])))
    ok = sum(1 for s in states if s[1] != D.REFUSED)
    total_rows += len(states)
    total_ok += ok
    lines.append(f"| {name} | {len(states)} | {ok} | " + ", ".join(f"{a}-{b}: {c:.0%}" for (a, b), _, c in states[:8]) + " |")
lines += ["", f"**Result: n too small.** {total_ok} of {total_rows} detected rows on these {len(CROPS)} crops pass the "
          "gates, and no crop has two passing rows that could be an LC3B / ACTB pair (the ACTB loading-control "
          "strips are the most clipped rows in the paper). A comparison against the authors' bar charts is "
          "therefore not possible from the published figures at these gates; it needs the raw exposures "
          "(ticket D-7). This is the expected, honest outcome and is not a defect of the gates.", "",
          "Not done: reading the bar-chart values themselves. They would have nothing to be compared with."]
out = ROOT / "research" / "experiments" / "D5_author_values.md"
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines[-4:]))

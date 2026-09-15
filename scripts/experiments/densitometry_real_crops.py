"""D5 step 3 — run the experimental densitometry gates over the 21 reviewed
crops in api/crops/ and report what the tool would REFUSE, WARN or accept.

There is no densitometry ground truth for these figures (the reviewed corpus
records categorical band presence only), so this is not an accuracy study.
It answers one question a UCSF researcher will ask on Wednesday: on real
published panels, does the tool print a number where it should not?

Geometry is DIAGNOSTIC here (detected band rows, auto lanes): a researcher
drawing the strip and lanes by hand is the product path. The clipped-core
fractions do not depend on lane placement much; the quality state does.

Run: .venv/bin/python scripts/experiments/densitometry_real_crops.py
Writes research/experiments/D5_real_crops_refusal.{json,md}
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from western_blot_miner import densitometry as D  # noqa: E402

CROPS = sorted((ROOT / "api" / "crops").glob("*/panel_candidates/*.png"))
OUT = ROOT / "research" / "experiments"

rows = []
for p in CROPS:
    img = D.decode_image(p.read_bytes())
    h, w = img.shape[:2]
    probe = D.analyze(img, stability=False)          # diagnostic: strongest non-text row, auto lanes
    n_rows = len(probe["rows_detected"])
    for ri in range(min(n_rows, 6)):
        r = D.analyze(img, row_index=ri)
        lanes = r["lanes"]
        rows.append({
            "paper": p.parts[-3], "crop": p.name, "size": [w, h], "row_index": ri,
            "band_row": r["band_row"], "n_lanes_auto": len(lanes),
            "max_clipped_fraction": max(l["clipped_fraction"] for l in lanes),
            "lanes_refused": sum(l["quality"] == D.REFUSED for l in lanes),
            "lanes_no_signal": sum(any("no signal" in x for x in l["reasons"]) for l in lanes),
            "state": r["quality"]["state"],
            "reasons": r["quality"]["reasons"],
            "ranking_stable": r["stability"]["ranking_stable"] if r["stability"] else None,
        })

states = Counter(x["state"] for x in rows)
crops_with_refusal = len({(x["paper"], x["crop"]) for x in rows if x["state"] == D.REFUSED})
crops_with_clip = len({(x["paper"], x["crop"]) for x in rows if x["max_clipped_fraction"] >= D.CLIP_FRACTION_REFUSE})
summary = {
    "method_version": D.METHOD_VERSION, "crops": len(CROPS), "band_rows_probed": len(rows),
    "state_counts": dict(states), "crops_with_at_least_one_refused_row": crops_with_refusal,
    "crops_with_a_row_clipped_past_refuse_gate": crops_with_clip,
    "rows_refused_for_ranking_instability": sum(1 for x in rows if x["ranking_stable"] is False),
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "D5_real_crops_refusal.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))

md = ["# D5 — refusal behaviour on the 21 reviewed crops (diagnostic geometry)", "",
      f"Method `{D.METHOD_NAME}` v{D.METHOD_VERSION}; `scripts/experiments/densitometry_real_crops.py`. "
      "No densitometry ground truth exists for these figures, so this reports only what the gates DO on real "
      "published panels: refuse, warn, or accept. Band rows and lanes are auto-detected here (diagnostic); a "
      "researcher's hand-drawn strip and lanes are the product path and will change the lane count, not the "
      "clipping.", "",
      f"- crops: {summary['crops']} · band rows probed (up to 6 per crop): {summary['band_rows_probed']}",
      f"- row states: {', '.join(f'{k} {v}' for k, v in sorted(states.items()))}",
      f"- crops with at least one refused row: {crops_with_refusal} / {len(CROPS)}",
      f"- crops with a row whose band core is clipped past the {D.CLIP_FRACTION_REFUSE:.0%} gate: {crops_with_clip} / {len(CROPS)}",
      f"- rows refused because the reference lane moves under perturbation: {summary['rows_refused_for_ranking_instability']}",
      "", "| paper | crop | row | y | lanes (auto) | max clipped core | refused lanes | no-signal lanes | ranking stable | state | reasons |",
      "|---|---|---|---|---|---|---|---|---|---|---|"]
for x in rows:
    md.append(f"| {x['paper']} | {x['crop']} | {x['row_index']} | {x['band_row'][0]}–{x['band_row'][1]} | {x['n_lanes_auto']} | "
              f"{x['max_clipped_fraction']:.0%} | {x['lanes_refused']} | {x['lanes_no_signal']} | {x['ranking_stable']} | "
              f"{x['state']} | {'; '.join(x['reasons'])} |")
md += ["", "## Reading this", "",
       "- A `quantification_refused` row is the tool working: the published panel cannot support a within-image "
       "relative number there (clipped reference, no signal, or an undefined reference under small geometry changes).",
       "- An `ok` row means the gates passed with auto geometry; it is still an uncalibrated, within-one-image pixel "
       "measurement with no protein-amount meaning.",
       "- Ticket D finding 3 said 14/21 reviewed crops have pure-black band cores; the clipped-core column is the "
       "same phenomenon measured per detected row with the v0.2 tolerance.",
       "- This replaces the retired D1 agreement number (`D1_densitometry_vs_bands.md`) as the real-crop check."]
(OUT / "D5_real_crops_refusal.md").write_text("\n".join(md) + "\n")
print("\n".join(md[:12]))

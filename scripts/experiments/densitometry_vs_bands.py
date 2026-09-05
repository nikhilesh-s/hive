"""Experiment D1: does uncalibrated densitometry agree with the reviewed
categorical band states?

For every reviewed record with a crop, run densitometry.analyze on the crop
with the record's printed lane count, pick the band row whose position best
matches the record's row order (records sharing a crop are stacked top to
bottom in the panel), and compare each lane's relative intensity with the
reviewed band_state:

    present   -> expect relative >= HI
    absent    -> expect relative <  LO
    uncertain -> no expectation (reported separately)

This is a SANITY experiment for the demo (is the tool obviously wrong?),
not a validation of densitometry. Writes research/experiments/D1_densitometry_vs_bands.{json,md}.

Run:  .venv/bin/python scripts/experiments/densitometry_vs_bands.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from western_blot_miner import densitometry  # noqa: E402

HI, LO = 0.35, 0.20
OUT = REPO / "research" / "experiments"


def load_records():
    recs = []
    for p in sorted((REPO / "eval" / "demo").glob("*/evidence_records.json")):
        recs += json.loads(p.read_text())
    return recs


def crop_path(ref: str) -> Path | None:
    name = Path(ref).name
    for p in (REPO / "api" / "crops").rglob(name):
        return p
    return None


def main() -> int:
    recs = load_records()
    by_crop: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        ref = r.get("figure", {}).get("image_crop_ref")
        if ref and r.get("bands"):
            by_crop[Path(ref).name].append(r)

    rows, agree, disagree, uncertain, skipped = [], 0, 0, 0, 0
    for name, group in by_crop.items():
        path = crop_path(name)
        if path is None:
            skipped += len(group)
            continue
        img = densitometry.decode_image(path.read_bytes())
        n_lanes = max(len(r["bands"]) for r in group)
        probe = densitometry.analyze(img, lanes=n_lanes)
        rows_detected = sorted(probe["rows_detected"])  # top to bottom
        for i, r in enumerate(group):
            if i >= len(rows_detected):
                skipped += 1
                continue
            res = densitometry.analyze(img, lanes=len(r["bands"]), band_row=tuple(rows_detected[i]))
            for lane, band in zip(res["lanes"], r["bands"]):
                state = (band.get("band_state") or {}).get("value")
                rel = lane["relative"]
                verdict = None
                if state == "present":
                    verdict = rel >= HI
                elif state == "absent":
                    verdict = rel < LO
                if verdict is None:
                    uncertain += 1
                elif verdict:
                    agree += 1
                else:
                    disagree += 1
                rows.append({"crop": name, "target": r["target"]["raw_target_name"], "row": i,
                             "lane": lane["index"], "condition": (band.get("lane_condition") or {}).get("value"),
                             "band_state": state, "relative": rel, "agree": verdict})
    total = agree + disagree
    summary = {"records": len(recs), "crops": len(by_crop), "lanes_scored": total, "agree": agree,
               "disagree": disagree, "uncertain_lanes": uncertain, "skipped": skipped,
               "agreement": round(agree / total, 3) if total else None, "thresholds": {"present_min": HI, "absent_max": LO}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "D1_densitometry_vs_bands.json").write_text(json.dumps({"summary": summary, "lanes": rows}, indent=2))
    md = ["# D1 — densitometry vs reviewed band states", "",
          f"Records {summary['records']} · crops {summary['crops']} · lanes scored {total} · "
          f"agree {agree} · disagree {disagree} · agreement **{summary['agreement']}** · uncertain lanes {uncertain} · skipped {skipped}",
          "", f"present ⇒ relative ≥ {HI}; absent ⇒ relative < {LO}; band row = i-th detected row for the i-th record on the crop.", "",
          "| crop | target | lane | condition | reviewed | relative | agree |", "|---|---|---|---|---|---|---|"]
    for x in rows:
        if x["agree"] is False:
            md.append(f"| {x['crop']} | {x['target']} | {x['lane']} | {x['condition']} | {x['band_state']} | {x['relative']:.2f} | ✗ |")
    md.append("")
    md.append("Only disagreements are listed; the JSON holds every lane. This is a sanity check on an "
              "uncalibrated measurement, not a validation.")
    (OUT / "D1_densitometry_vs_bands.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

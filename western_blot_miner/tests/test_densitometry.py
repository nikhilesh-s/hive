"""Synthetic-blot checks for the EXPERIMENTAL densitometry module.
Run: .venv/bin/python western_blot_miner/tests/test_densitometry.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner import densitometry  # noqa: E402

CHECKS = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))


def synthetic(strengths, light_bg=True, w=400, h=120, band_y=60, sigma=6.0, noise=0.0, seed=0):
    """Dark bands on a light background (or inverted); Gaussian band per lane
    with a known peak darkness, plus optional noise."""
    rng = np.random.default_rng(seed)
    n = len(strengths)
    img = np.full((h, w), 235.0 if light_bg else 20.0)
    ys = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    lane_w = w / n
    for i, s in enumerate(strengths):
        cx = (i + 0.5) * lane_w
        band = s * 200 * np.exp(-((ys - band_y) ** 2) / (2 * sigma ** 2)) * (np.abs(xs - cx) < lane_w * 0.32)
        img = img - band if light_bg else img + band
    if noise:
        img = img + rng.normal(0, noise, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


# 1. ordering + ratios recover the known strengths (dark-on-light)
img = synthetic([1.0, 0.5, 0.25, 0.0], noise=2.0)
res = densitometry.analyze(img, lanes=4)
rel = [l["relative"] for l in res["lanes"]]
check("four lanes", len(rel) == 4)
check("inverted for analysis (light background)", res["image"]["inverted_for_analysis"] is True)
check("strongest lane is lane 1", rel[0] == 1.0)
check("half-strength lane ~0.5", abs(rel[1] - 0.5) < 0.12)
check("quarter-strength lane ~0.25", abs(rel[2] - 0.25) < 0.12)
check("empty lane ~0", rel[3] < 0.08)
y0, y1 = res["band_row"]
check("band row brackets y=60", y0 <= 60 <= y1)

# 2. auto lane detection finds the printed lanes
res_auto = densitometry.analyze(synthetic([1.0, 0.7, 0.4], noise=1.0))
check("auto-detected 3 lanes", len(res_auto["lanes"]) == 3)
check("auto warning present", any("auto-detected" in w for w in res_auto["warnings"]))

# 3. light bands on a dark background are handled without inversion
res_dark = densitometry.analyze(synthetic([0.3, 1.0], light_bg=False), lanes=2)
check("no inversion on dark background", res_dark["image"]["inverted_for_analysis"] is False)
check("dark-bg strongest is lane 2", res_dark["lanes"][1]["relative"] == 1.0 and res_dark["lanes"][0]["relative"] < 0.6)

# 4. saturation is flagged
sat = synthetic([1.0, 1.0], noise=0.0)
sat[50:70, 20:140] = 0  # a fully clipped block in lane 1
res_sat = densitometry.analyze(sat, lanes=2)
check("saturation warning", any("saturated" in w for w in res_sat["warnings"]))
check("lane 1 saturated_fraction > 0", res_sat["lanes"][0]["saturated_fraction"] > 0)

# 5. two stacked band rows: row_index selects the second
two = synthetic([1.0, 0.2], band_y=30)
two2 = synthetic([0.2, 1.0], band_y=90)
stacked = np.minimum(two, two2)
r0 = densitometry.analyze(stacked, lanes=2, row_index=0)
r1 = densitometry.analyze(stacked, lanes=2, row_index=1)
check("two rows detected", len(r0["rows_detected"]) == 2)
check("rows give opposite strongest lanes",
      r0["lanes"][0]["relative"] != r1["lanes"][0]["relative"] and {r0["lanes"][0]["relative"], r1["lanes"][0]["relative"]} == {1.0, r0["lanes"][0]["relative"] if r0["lanes"][0]["relative"] != 1.0 else r1["lanes"][0]["relative"]})

# 6. printed labels: a solid-black text row is ranked after the blot strip,
#    and a region box confines the analysis (coordinates come back in full-image pixels)
labelled = synthetic([1.0, 0.5], band_y=40, h=120)
labelled[95:110, 60:340] = 0  # a black "lane label" text row under the blot
r_lab = densitometry.analyze(labelled, lanes=2)
check("text row not chosen as band row", r_lab["band_row"][0] <= 40 <= r_lab["band_row"][1])
r_reg = densitometry.analyze(labelled, lanes=2, region=(100, 20, 380, 70))
check("region respected", r_reg["image"]["region"] == [100, 20, 380, 70] and r_reg["lanes"][0]["x0"] == 100 and r_reg["lanes"][-1]["x1"] == 380)
check("region band row in full-image coords", r_reg["band_row"][0] >= 20 and r_reg["band_row"][1] <= 70)

# 7. disclaimer always present, no Evidence Record fields
check("disclaimer", "uncalibrated" in res["disclaimer"] and "not a measurement of protein amount" in res["disclaimer"])
check("encode/decode round trip", densitometry.decode_image(
    __import__("cv2").imencode(".png", img)[1].tobytes()).shape == img.shape)

failed = [n for n, ok in CHECKS if not ok]
print(f"densitometry: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
for n in failed:
    print("  FAIL:", n)
sys.exit(1 if failed else 0)

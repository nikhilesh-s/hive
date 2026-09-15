"""Synthetic-blot checks for the EXPERIMENTAL densitometry module (v0.2).
Run: .venv/bin/python western_blot_miner/tests/test_densitometry.py

Every check here is against a fixture with KNOWN structure; none of it is an
accuracy claim about real figures. Real-crop behaviour (clipping/refusal on
the reviewed corpus) is exercised in scripts/experiments/densitometry_real_crops.py.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner import densitometry as D  # noqa: E402

CHECKS = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))


def synthetic(strengths, light_bg=True, w=400, h=120, band_y=60, sigma=6.0, noise=0.0, seed=0, peak=200):
    """Dark bands on a light background (or inverted); Gaussian band per lane
    with a known peak darkness, plus optional noise. peak > 235 clips."""
    rng = np.random.default_rng(seed)
    n = len(strengths)
    img = np.full((h, w), 235.0 if light_bg else 20.0)
    ys = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    lane_w = w / n
    for i, s in enumerate(strengths):
        cx = (i + 0.5) * lane_w
        band = s * peak * np.exp(-((ys - band_y) ** 2) / (2 * sigma ** 2)) * (np.abs(xs - cx) < lane_w * 0.32)
        img = img - band if light_bg else img + band
    if noise:
        img = img + rng.normal(0, noise, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def equal_bounds(n, w=400, x0=0):
    edges = np.linspace(x0, x0 + w, n + 1).round().astype(int)
    return [[int(edges[i]), int(edges[i + 1])] for i in range(n)]


# 1. ordering + ratios recover the known strengths (dark-on-light), explicit lanes
img = synthetic([1.0, 0.5, 0.25, 0.0], noise=2.0)
res = D.analyze(img, lane_bounds=equal_bounds(4), lane_labels=["a", "b", "c", "d"])
rel = [l["relative"] for l in res["lanes"]]
check("four lanes", len(rel) == 4)
check("lane_mode explicit", res["lane_mode"] == "explicit")
check("labels carried", [l["label"] for l in res["lanes"]] == ["a", "b", "c", "d"])
check("inverted for analysis (light background)", res["image"]["inverted_for_analysis"] is True)
check("strongest lane is lane 1", rel[0] == 1.0)
check("half-strength lane ~0.5", abs(rel[1] - 0.5) < 0.12)
check("quarter-strength lane ~0.25", abs(rel[2] - 0.25) < 0.12)
check("empty lane ~0", rel[3] < 0.08)
check("empty lane flagged weak, not refused", res["lanes"][3]["quality"] == "ok" and any(r.startswith("weak:") for r in res["lanes"][3]["reasons"]))
check("overall ok", res["quality"]["state"] == "ok")
y0, y1 = res["band_row"]
check("band row brackets y=60", y0 <= 60 <= y1)
check("lane y bounds = band row", all(l["y0"] == y0 and l["y1"] == y1 for l in res["lanes"]))
pf = res["lanes"][0]["profile"]
check("profile covers the band row plus flanks in full-image y", pf["y0"] <= y0 and pf["y0"] + len(pf["values"]) >= y1
      and pf["flank"][0][1] <= y0 and pf["flank"][1][0] >= y1)
check("profile peaks inside the band row", y0 <= pf["y0"] + int(np.argmax(pf["values"])) < y1)
check("method metadata", res["method"]["name"] == D.METHOD_NAME and res["method"]["version"] == D.METHOD_VERSION
      and res["method"]["params"]["clip_fraction_refuse"] == D.CLIP_FRACTION_REFUSE)

# 2. stability envelope brackets the point value; clean fixture is stable
check("stability present", res["stability"] is not None and res["stability"]["runs"] > 5 and res["stability"]["ranking_stable"])
for l in res["lanes"]:
    e = l["stability"]
    check(f"envelope brackets lane {l['index']}", e and e["relative_min"] - 1e-9 <= l["relative"] <= e["relative_max"] + 1e-9)
check("clean fixture envelopes narrow", all((l["stability"]["relative_max"] - l["stability"]["relative_min"]) < 0.25 for l in res["lanes"]))
res_nostab = D.analyze(img, lane_bounds=equal_bounds(4), stability=False)
check("stability can be skipped", res_nostab["stability"] is None and all(l["stability"] is None for l in res_nostab["lanes"]))

# 3. diagnostic fallbacks: count -> equal width, none -> auto, both warn
res_eq = D.analyze(synthetic([1.0, 0.7, 0.4], noise=1.0), lanes=3)
check("equal_width mode", res_eq["lane_mode"] == "equal_width" and len(res_eq["lanes"]) == 3)
check("equal_width warns diagnostic", any("diagnostic" in w for w in res_eq["warnings"]))
res_auto = D.analyze(synthetic([1.0, 0.7, 0.4], noise=1.0))
check("auto-detected 3 lanes", res_auto["lane_mode"] == "auto" and len(res_auto["lanes"]) == 3)
check("auto warns diagnostic", any("auto-detected" in w for w in res_auto["warnings"]))

# 4. light bands on a dark background are handled without inversion
res_dark = D.analyze(synthetic([0.3, 1.0], light_bg=False), lane_bounds=equal_bounds(2))
check("no inversion on dark background", res_dark["image"]["inverted_for_analysis"] is False)
check("dark-bg strongest is lane 2", res_dark["lanes"][1]["relative"] == 1.0 and res_dark["lanes"][0]["relative"] < 0.6)

# 5. clipping gates
#    5a. reference lane clipped -> whole strip refused, relative None everywhere
clip = synthetic([1.0, 0.5], peak=400)  # lane 1 peak far past black -> flat clipped core
res_clip = D.analyze(clip, lane_bounds=equal_bounds(2))
check("clipped lane detected", res_clip["lanes"][0]["clipped_fraction"] >= D.CLIP_FRACTION_REFUSE)
check("reference clipped -> refused", res_clip["quality"]["state"] == "quantification_refused")
check("refused -> no relative values", all(l["relative"] is None for l in res_clip["lanes"]))
check("refusal reason names the lane", any("strongest lane (1)" in r for r in res_clip["quality"]["reasons"]))
#    5b. non-reference lane clipped -> that lane refused, others measured, overall warning
clip2 = synthetic([0.5, 1.0, 0.3], peak=200)
clip2[57:61, 45:85] = 0  # a thin solid-black streak in lane 1's band core only
res_clip2 = D.analyze(clip2, lane_bounds=equal_bounds(3))
check("non-reference clipped lane refused", res_clip2["lanes"][0]["quality"] == "quantification_refused" and res_clip2["lanes"][0]["relative"] is None)
check("other lanes still measured", res_clip2["lanes"][1]["relative"] == 1.0 and res_clip2["lanes"][2]["relative"] is not None)
check("overall warning, not ok", res_clip2["quality"]["state"] == "warning")
#    5c. clean fixture has ~no clipped pixels
check("clean fixture unclipped", all(l["clipped_fraction"] < D.CLIP_FRACTION_WARN for l in res["lanes"]))

# 6. no signal anywhere -> refused
blank = synthetic([0.0, 0.0, 0.0], noise=2.0)
res_blank = D.analyze(blank, lane_bounds=equal_bounds(3))
check("blank strip refused", res_blank["quality"]["state"] == "quantification_refused" and all(l["relative"] is None for l in res_blank["lanes"]))
check("blank reason", any("no lane has signal" in r for r in res_blank["quality"]["reasons"]))

# 7. geometry validation raises (never measures something else silently)
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False

check("reversed lane bounds rejected", raises(lambda: D.analyze(img, lane_bounds=[[100, 50]])))
check("overlapping lanes rejected", raises(lambda: D.analyze(img, lane_bounds=[[0, 120], [100, 200]])))
check("lane outside region rejected", raises(lambda: D.analyze(img, region=(50, 20, 350, 100), lane_bounds=[[40, 120]])))
check("too-narrow lane rejected", raises(lambda: D.analyze(img, lane_bounds=[[10, 12]])))
check("tiny region rejected", raises(lambda: D.analyze(img, region=(10, 10, 14, 14))))
check("label count mismatch rejected", raises(lambda: D.analyze(img, lane_bounds=equal_bounds(2), lane_labels=["x"])))
check("empty lane list rejected", raises(lambda: D.analyze(img, lane_bounds=[])))
check("band_row outside region rejected", raises(lambda: D.analyze(img, region=(0, 20, 400, 100), lane_bounds=equal_bounds(2), band_row=(10, 60))))
check("reversed band_row rejected", raises(lambda: D.analyze(img, lane_bounds=equal_bounds(2), band_row=(80, 40))))
r_br = D.analyze(img, region=(0, 20, 400, 100), lane_bounds=equal_bounds(2), band_row=(30, 90))
check("explicit band_row honoured in full-image coords", r_br["band_row"] == [30, 90] and r_br["lanes"][0]["y0"] == 30)
two_in_box = np.minimum(synthetic([1.0, 0.5], band_y=40), synthetic([0.5, 0.5], band_y=80))
r_two = D.analyze(two_in_box, region=(0, 25, 400, 95), lane_bounds=equal_bounds(2), band_row=(25, 95))
check("full-box band_row over two strips warns", any("spans 2 detected band rows" in w for w in r_two["warnings"]))
r_one = D.analyze(two_in_box, region=(0, 25, 400, 95), lane_bounds=equal_bounds(2))
check("detection inside the same box picks one strip", r_one["band_row"][1] - r_one["band_row"][0] < 30 and not any("spans" in w for w in r_one["warnings"]))
check("a box with two strips is at least a warning", r_one["quality"]["state"] != "ok"
      and any("contains 2 band rows" in r for r in r_one["quality"]["reasons"] + r_one["warnings"]))
r_single = D.analyze(two_in_box, region=(0, 25, 400, 60), lane_bounds=equal_bounds(2))
check("re-boxing one strip clears the multi-row warning", r_single["quality"]["state"] == "ok"
      and not any("band rows" in w for w in r_single["warnings"]))

# 8. two stacked band rows: row_index selects the second
two = synthetic([1.0, 0.2], band_y=30)
two2 = synthetic([0.2, 1.0], band_y=90)
stacked = np.minimum(two, two2)
r0 = D.analyze(stacked, lane_bounds=equal_bounds(2), row_index=0)
r1 = D.analyze(stacked, lane_bounds=equal_bounds(2), row_index=1)
check("two rows detected", len(r0["rows_detected"]) == 2)
check("rows give opposite strongest lanes", r0["lanes"][0]["relative"] == 1.0 and r0["lanes"][1]["relative"] < 0.5
      and r1["lanes"][1]["relative"] == 1.0 and r1["lanes"][0]["relative"] < 0.5)

# 9. region + explicit lanes: coordinates come back in full-image pixels and
#    the printed-label row under the blot is excluded by the box
labelled = synthetic([1.0, 0.5], band_y=40, h=120)
glyphs = (np.arange(60, 340) // 3) % 2 == 0          # 3 px strokes, 3 px gaps: printed text
labelled[95:110, 60:340][:, glyphs] = 0              # a "lane label" text row under the blot
solid_band = synthetic([1.0, 0.5], band_y=40, h=120)
solid_band[34:46, 30:170] = 0                         # a clipped, solid-black BAND (long runs) is not text
check("clipped solid band is not called text", D.row_text_like(solid_band, 34, 46, 120) is False
      and D.row_text_like(labelled, 95, 110, 120) is True)
r_lab = D.analyze(labelled, lanes=2)
check("text row not chosen as band row", r_lab["band_row"][0] <= 40 <= r_lab["band_row"][1])
check("text row flagged in rows_text_like", r_lab["rows_text_like"][0] is False and True in r_lab["rows_text_like"])
r_txt = D.analyze(labelled, lanes=2, band_row=(95, 110))
check("forcing the text row warns", any("printed text" in w for w in r_txt["warnings"]))
r_reg = D.analyze(labelled, region=(20, 20, 380, 70), lane_bounds=[[20, 180], [220, 380]])
check("region echoed", r_reg["image"]["region"] == [20, 20, 380, 70])
check("region size is the full image size", r_reg["image"]["width"] == 400 and r_reg["image"]["height"] == 120)
check("lane x in full-image coords", r_reg["lanes"][0]["x0"] == 20 and r_reg["lanes"][1]["x1"] == 380)
check("band row in full-image coords inside region", 20 <= r_reg["band_row"][0] and r_reg["band_row"][1] <= 70)
check("gap between lanes allowed", r_reg["lanes"][0]["x1"] == 180 and r_reg["lanes"][1]["x0"] == 220)
check("region + lanes measure the right lanes", r_reg["lanes"][0]["relative"] == 1.0 and abs(r_reg["lanes"][1]["relative"] - 0.5) < 0.12)
# same strip, box moved by a few px: stable conclusion, envelopes overlap
r_reg2 = D.analyze(labelled, region=(24, 24, 384, 74), lane_bounds=[[24, 184], [224, 384]])
check("moved box keeps ordering", r_reg2["lanes"][0]["relative"] == 1.0 and r_reg2["quality"]["state"] == "ok")
e1, e2 = r_reg["lanes"][1]["stability"], r_reg2["lanes"][1]["stability"]
check("moved box inside first envelope", e1["relative_min"] - 0.05 <= r_reg2["lanes"][1]["relative"] <= e1["relative_max"] + 0.05)

# 9b. polarity comes from the whole image: a tight box around dense dark bands
#     (region mean < 127) must still be read as dark-on-light
dense = synthetic([0.95, 0.95, 0.9, 0.95], peak=235, sigma=20.0, h=60, band_y=30)
r_dense = D.analyze(dense, region=(0, 10, 400, 50), lane_bounds=equal_bounds(4))
check("dense dark strip keeps light-background polarity", r_dense["image"]["inverted_for_analysis"] is True
      and D._to_gray(dense)[10:50].mean() < 127)
check("dense strip band row brackets the bands", r_dense["band_row"][0] <= 30 <= r_dense["band_row"][1])
check("a tightly boxed strip is not called printed text", not any("printed text" in w for w in r_reg["warnings"]))

# 10a. near-tie reference flip -> WARNING, values kept: two identical bands
#      (x 37-163 and 237-363), lane 1 drawn over the LEFT half of band 1 and
#      lane 2 over the RIGHT half of band 2, so a +dx shift favours lane 1
#      and a -dx shift favours lane 2. Both were ~1.0 at baseline: a tie.
tie = synthetic([1.0, 1.0], noise=0.0)
res_flip = D.analyze(tie, lane_bounds=[[37, 100], [300, 363]])
check("ranking flip detected", res_flip["stability"] is not None and res_flip["stability"]["ranking_stable"] is False)
check("near tie is a warning with values kept", res_flip["quality"]["state"] == "warning" and all(l["relative"] is not None for l in res_flip["lanes"]))
check("tie lanes named", res_flip["stability"]["reference_tie_lanes"] == [1, 2] and any("near tie" in r for r in res_flip["quality"]["reasons"]))
# 10b. severe reference flip -> REFUSED: lane 2 is half of lane 1 at the drawn
#      geometry, but a solid-black block sits just outside lane 2's right edge,
#      so a +dx shift makes lane 2 the strongest. Geometry chose the reference.
sev = np.full((120, 600), 235, dtype=np.uint8)
sev[54:66, 20:120] = 195          # lane 1: darkness 40 over 100 px
sev[54:66, 220:270] = 195         # lane 2: darkness 40 over 50 px (relative 0.5)
sev[54:66, 400:440] = 0           # black block right of lane 2's edge (x1 = 400)
res_sev = D.analyze(sev, lane_bounds=[[0, 200], [200, 400]])
check("severe flip detected", res_sev["stability"] is not None and res_sev["stability"]["ranking_stable"] is False)
check("severe flip refuses", res_sev["quality"]["state"] == "quantification_refused" and all(l["relative"] is None for l in res_sev["lanes"]))
check("severe flip reason", any("clearly weaker" in r for r in res_sev["quality"]["reasons"]))
# the same bands with lanes drawn over the whole of each band are stable
res_tie_ok = D.analyze(tie, lane_bounds=[[30, 170], [230, 370]])
check("full-band lanes on identical bands are stable", res_tie_ok["stability"]["ranking_stable"] and res_tie_ok["quality"]["state"] == "ok")

# 11. disclaimer always present; encode/decode round trip; 16-bit input tolerated
check("disclaimer", "uncalibrated" in res["disclaimer"] and "not a measurement of protein amount" in res["disclaimer"])
check("encode/decode round trip", D.decode_image(
    __import__("cv2").imencode(".png", img)[1].tobytes()).shape == img.shape)
res16 = D.analyze((img.astype(np.uint16) * 257), lane_bounds=equal_bounds(4))
check("16-bit input gives same ordering", [l["relative"] for l in res16["lanes"]][0] == 1.0)

# 12. reviewed real crops (present in the repo under api/crops): one strip
#     that yields a valid, ranking-stable within-image reading and one that
#     refuses for a clipped reference. Regions are hand-drawn full-image
#     pixel boxes around a single strip; these are gate checks, not accuracy.
CROPS = Path(__file__).resolve().parents[2] / "api" / "crops"
stat3 = CROPS / "10.3892_br.2026.2108" / "panel_candidates" / "page_005_cand_0034.png"
bex2 = CROPS / "10.1186_s12964-025-02385-8" / "panel_candidates" / "page_005_cand_0032.png"
if stat3.is_file() and bex2.is_file():
    img_s = D.decode_image(stat3.read_bytes())
    e = np.linspace(793, 1402, 7).round().astype(int)
    six = [[int(e[i]), int(e[i + 1])] for i in range(6)]
    r_p = D.analyze(img_s, region=(793, 120, 1402, 185), lane_bounds=six)      # P-STAT3 (Ser727), panel C
    check("real P-STAT3 strip: valid reading", r_p["quality"]["state"] == "ok" and r_p["stability"]["ranking_stable"]
          and r_p["image"]["inverted_for_analysis"] is True and 120 <= r_p["band_row"][0] < r_p["band_row"][1] <= 185)
    check("real P-STAT3 strip: no clipping, all lanes have signal", all(l["clipped_fraction"] < D.CLIP_FRACTION_WARN for l in r_p["lanes"])
          and all(l["relative"] is not None for l in r_p["lanes"]))
    r_t = D.analyze(img_s, region=(793, 227, 1402, 292), lane_bounds=six)      # T-Stat3, panel C: even loading
    check("real T-Stat3 strip: measured, all lanes within 0.7-1.0", r_t["quality"]["state"] in ("ok", "warning")
          and all(l["relative"] is not None and l["relative"] >= 0.7 for l in r_t["lanes"]))
    r_a = D.analyze(img_s, region=(793, 335, 1402, 400), lane_bounds=six)      # beta-actin, panel C: near-tie reference
    check("real beta-actin strip: near tie is a warning with values", r_a["quality"]["state"] == "warning"
          and len(r_a["stability"]["reference_tie_lanes"]) >= 2 and all(l["relative"] is not None for l in r_a["lanes"]))
    img_b = D.decode_image(bex2.read_bytes())
    r_c = D.analyze(img_b, region=(0, 530, img_b.shape[1], 582), lanes=6)       # clipped strip (diagnostic lanes)
    check("real clipped strip refuses", r_c["quality"]["state"] == "quantification_refused"
          and all(l["relative"] is None for l in r_c["lanes"]) and max(l["clipped_fraction"] for l in r_c["lanes"]) >= D.CLIP_FRACTION_REFUSE)
else:
    print("  (real-crop checks skipped: api/crops not present)")

# 13. loading-control pairing: a target strip with known ratios over a
#     uniform control strip in the same image -> normalized ratios recover
#     the target's pattern; a control lane with no signal refuses that lane;
#     a refused control strip refuses the pairing.
pair_img = np.minimum(synthetic([1.0, 0.5, 0.25, 0.0], band_y=35, h=160), synthetic([0.8, 0.8, 0.8, 0.8], band_y=110, h=160))
tgt = D.analyze(pair_img, region=(0, 10, 400, 60), lane_bounds=equal_bounds(4), lane_labels=["a", "b", "c", "d"])
ctl = D.analyze(pair_img, region=(0, 85, 400, 135), lane_bounds=equal_bounds(4))
pr = D.pair_ratio(tgt, ctl)
check("pair: valid", pr["quality"]["state"] == "ok" and pr["method"]["name"] == D.PAIR_METHOD_NAME)
check("pair: labels carried", [l["label"] for l in pr["lanes"]] == ["a", "b", "c", "d"])
nz = [l["normalized"] for l in pr["lanes"]]
check("pair: normalized ratios follow the target", nz[0] == 1.0 and abs(nz[1] - 0.5) < 0.12 and abs(nz[2] - 0.25) < 0.12 and nz[3] < 0.1)
check("pair: envelopes bracket the median", all(l["normalized_min"] - 1e-9 <= l["normalized"] <= l["normalized_max"] + 1e-9 for l in pr["lanes"]))
check("pair: same-membrane caveat always present", pr["warnings"][0] == D.PAIR_CAVEAT)
# uneven loading: control lane 2 is half -> normalized target/control for lane 2 doubles relative to the flat case
uneven = np.minimum(synthetic([1.0, 0.5, 0.25, 0.0], band_y=35, h=160), synthetic([0.8, 0.4, 0.8, 0.8], band_y=110, h=160))
pr_u = D.pair_ratio(D.analyze(uneven, region=(0, 10, 400, 60), lane_bounds=equal_bounds(4)),
                    D.analyze(uneven, region=(0, 85, 400, 135), lane_bounds=equal_bounds(4)))
check("pair: uneven loading corrected", abs(pr_u["lanes"][1]["normalized"] - 1.0) < 0.15 and abs(pr_u["lanes"][0]["normalized"] - 1.0) < 0.15
      and abs(pr_u["lanes"][2]["normalized"] - 0.25) < 0.12)
# control lane 4 empty -> that lane's ratio is refused, others stand
ctl_empty = D.analyze(np.minimum(synthetic([1.0, 0.5, 0.25, 0.3], band_y=35, h=160), synthetic([0.8, 0.8, 0.8, 0.0], band_y=110, h=160)),
                      region=(0, 85, 400, 135), lane_bounds=equal_bounds(4))
tgt2 = D.analyze(np.minimum(synthetic([1.0, 0.5, 0.25, 0.3], band_y=35, h=160), synthetic([0.8, 0.8, 0.8, 0.0], band_y=110, h=160)),
                 region=(0, 10, 400, 60), lane_bounds=equal_bounds(4))
pr_e = D.pair_ratio(tgt2, ctl_empty)
check("pair: empty control lane refused, others measured", pr_e["lanes"][3]["quality"] == "quantification_refused" and pr_e["lanes"][3]["normalized"] is None
      and pr_e["lanes"][0]["normalized"] == 1.0 and pr_e["quality"]["state"] == "warning")
# a weak (but not empty) control lane is warned, not refused
weak_c = np.minimum(synthetic([1.0, 0.5, 0.25, 0.1], band_y=35, h=160), synthetic([0.8, 0.8, 0.8, 0.08], band_y=110, h=160))
pr_w = D.pair_ratio(D.analyze(weak_c, region=(0, 10, 400, 60), lane_bounds=equal_bounds(4)),
                    D.analyze(weak_c, region=(0, 85, 400, 135), lane_bounds=equal_bounds(4)))
check("pair: weak control lane warned", pr_w["lanes"][3]["quality"] == "warning" and any("control lane is weak" in r for r in pr_w["lanes"][3]["reasons"])
      and pr_w["lanes"][3]["normalized"] is not None and pr_w["quality"]["state"] == "warning")
# clipped control strip -> pairing refused
ctl_clip = D.analyze(synthetic([1.0, 1.0, 1.0, 1.0], peak=400), lane_bounds=equal_bounds(4))
pr_c = D.pair_ratio(tgt, ctl_clip)
check("pair: refused control strip refuses the pairing", pr_c["quality"]["state"] == "quantification_refused" and all(l["normalized"] is None for l in pr_c["lanes"]))
check("pair: lane count mismatch raises", raises(lambda: D.pair_ratio(tgt, D.analyze(pair_img, region=(0, 85, 400, 135), lane_bounds=equal_bounds(2)))))

failed = [n for n, ok in CHECKS if not ok]
print(f"densitometry: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
for n in failed:
    print("  FAIL:", n)
sys.exit(1 if failed else 0)

"""EXPERIMENTAL densitometry on a published blot panel image.

Scope, stated plainly: this measures pixel intensity in a figure crop. A
figure crop is not raw data — exposure, contrast, JPEG/PNG re-encoding and
journal layout all shape it — so the numbers are relative within ONE panel
image and carry no units. They never enter an Evidence Record; the reviewed
corpus keeps categorical band presence only. This module exists so a
researcher can see what such a measurement would say, with its caveats, and
so the tool refuses instead of printing a number when the pixels cannot
support one.

Method (deterministic, OpenCV/NumPy), version in METHOD_VERSION:
  1. grayscale; if the image is light-background/dark-band (the common
     case) invert so signal = darkness
  2. background = morphological opening with a large kernel (rolling-ball
     style, radius from the whole image) over the selected region, then a
     per-lane flank baseline (median of the rows just above and below the
     band row in that lane) so membrane grey is not counted as signal when
     the box also contains white space; corrected = signal - both
  3. band row = the strongest contiguous horizontal band of corrected signal
     (or a caller-supplied row / the n-th detected row)
  4. lanes = researcher-supplied x bounds (the product path); equal-width
     slicing from a count, or valleys of the vertical profile, are
     DIAGNOSTIC fallbacks and are labelled as such in `lane_mode`
  5. per lane: raw, background, corrected integrated intensity, relative to
     the strongest lane, clipped fraction of the band core, quality state
  6. quality gates: clipped band core, no signal above background, invalid
     geometry -> `warning` or `quantification_refused` (relative = None)
  7. stability: the integration is re-run over a small deterministic set of
     geometry perturbations (band row edges, lane edges, region offset);
     each lane reports min/median/max relative; a changing reference lane
     refuses quantification because the relative scale is then undefined

Thresholds are first-generation defaults justified against the synthetic
fixtures in `scripts/experiments/densitometry_clip_study.py` (see
`research/experiments/D2_clip_threshold_study.md`); they are parameters of
the method, reported in every result, and are expected to be revised once a
real dilution-series benchmark exists (ticket D-7).
"""
from __future__ import annotations

import statistics
from typing import Any

import numpy as np

METHOD_NAME = "hiveblot.densitometry"
METHOD_VERSION = "0.3.0"

# Pixel values at or beyond this distance from the signal extreme count as
# clipped (8-bit; 0 = pure black on a light background). Journal PNG/JPEG
# re-encoding leaves clipped cores at 0-7, rarely exactly 0.
CLIP_THRESHOLD_DN = 8
# Fraction of the band core (pixels >= 50% of the lane's peak corrected
# signal) that may be clipped before the lane is warned / refused.
CLIP_FRACTION_WARN = 0.02
CLIP_FRACTION_REFUSE = 0.10
# Corrected signal of a lane must exceed this many robust-sigma of the
# flank residual (rows just above/below the band, same lane) to count as signal.
SNR_MIN = 3.0
# Flank = this fraction of the band-row height on each side (min 3 rows); its
# median is the per-lane membrane baseline, its MAD the noise scale.
FLANK_FRACTION = 0.5
FLANK_MIN_PX = 3
# Minimum lane width in pixels; narrower lanes are geometry errors.
MIN_LANE_WIDTH_PX = 3
MIN_REGION_PX = 8
# Perturbation scale for the stability study: fraction of the median lane
# width (x) and of the band-row height (y), floored at 2 px. Reviewed crops
# are 500-2600 px wide with 6-12 lanes, so this is 3-10 px, the order of a
# researcher's box-placement variation observed in ticket D finding 4.
PERTURB_FRACTION_X = 0.05
PERTURB_FRACTION_Y = 0.10
PERTURB_MIN_PX = 2
# A lane whose relative envelope (max - min across perturbations) exceeds
# this is flagged unstable.
STABILITY_WARN_WIDTH = 0.25

OK, WARNING, REFUSED = "ok", "warning", "quantification_refused"

DISCLAIMER = (
    "EXPERIMENTAL and uncalibrated. Intensities are integrated pixel darkness "
    "of a published figure crop after background subtraction, relative within "
    "this one image. They are not a measurement of protein amount: exposure, "
    "saturation, contrast adjustment and image re-encoding are unknown. Not "
    "loading-control normalized. Not stored in Evidence Records; never compare "
    "across images."
)


def _to_gray(img: np.ndarray) -> np.ndarray:
    import cv2

    if img.ndim == 3:
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if img.dtype == np.uint16:
        img = (img // 257).astype(np.uint8)   # 16-bit -> 8-bit, no stretch
    elif img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    return img


def decode_image(data: bytes) -> np.ndarray:
    import cv2

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("not a decodable image")
    return img


def _smooth(v: np.ndarray, k: int) -> np.ndarray:
    k = max(1, int(k))
    if k == 1:
        return v.astype(float)
    kernel = np.ones(k) / k
    return np.convolve(v.astype(float), kernel, mode="same")


def _segments_above(mask: np.ndarray) -> list[tuple[int, int]]:
    segs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            segs.append((start, i))
            start = None
    if start is not None:
        segs.append((start, len(mask)))
    return segs


def detect_band_rows(corrected: np.ndarray, gray: np.ndarray | None = None,
                     min_height: int = 4, total_h: int | None = None) -> list[tuple[int, int]]:
    """Horizontal bands of signal, strongest first. Rows that are mostly
    pure black/white pixels are printed text (lane labels, row labels), not
    bands; they are pushed to the end so auto mode lands on a blot strip."""
    prof = _smooth(corrected.sum(axis=1), max(3, corrected.shape[0] // 40))
    if prof.max() <= 0:
        return []
    thr = prof.mean() + 0.5 * prof.std()
    segs = [(a, b) for a, b in _segments_above(prof > thr) if b - a >= min_height]

    def score(seg):
        a, b = seg
        return (float(row_text_like(gray, a, b, total_h)), -prof[a:b].sum())

    return sorted(segs, key=score)


def row_text_like(gray: np.ndarray | None, a: int, b: int, total_h: int | None = None) -> bool:
    """Printed labels: solid-black glyphs and/or a tall block (stacked label
    lines); blot bands are grey-scaled and thin. `total_h` is the FULL image
    height: a strip boxed tightly by the researcher is not "tall" just
    because the box is short."""
    if gray is None:
        return False
    block = gray[a:b]
    # stacked label lines are >= ~40 px at the 350 DPI the crops are rendered at
    return bool((block < 16).mean() > 0.25 or (b - a) > max(40, 0.1 * (total_h or gray.shape[0])))


def detect_lanes(row: np.ndarray, expected: int | None = None, max_lanes: int = 16) -> list[tuple[int, int]]:
    """DIAGNOSTIC lane boundaries (x0, x1) inside one band row: equal-width
    slices from a count, or valleys of the smoothed vertical profile."""
    w = row.shape[1]
    if expected and expected > 0:
        edges = np.linspace(0, w, expected + 1).round().astype(int)
        return [(int(edges[i]), int(edges[i + 1])) for i in range(expected)]
    prof = _smooth(row.sum(axis=0), max(3, w // 60))
    if prof.max() <= 0:
        return [(0, w)]
    thr = max(0.12 * prof.max(), 0.5 * prof.mean())
    min_w = max(3, w // (max_lanes * 2))
    segs = [(a, b) for a, b in _segments_above(prof > thr) if b - a >= min_w]
    if not segs:
        return [(0, w)]
    # widen each band segment to the valley midpoints with its neighbours
    bounds = []
    for i, (a, b) in enumerate(segs):
        left = 0 if i == 0 else (segs[i - 1][1] + a) // 2
        right = w if i == len(segs) - 1 else (b + segs[i + 1][0]) // 2
        bounds.append((int(left), int(right)))
    return bounds


def validate_lane_bounds(lane_bounds, x_lo: int, x_hi: int) -> list[tuple[int, int]]:
    """Researcher lane bounds in full-image pixels. Reject impossible
    geometry loudly (ValueError) rather than measuring something else."""
    out: list[tuple[int, int]] = []
    prev_x1 = None
    for i, b in enumerate(lane_bounds, 1):
        if len(b) != 2:
            raise ValueError(f"lane {i}: bounds must be [x0, x1]")
        x0, x1 = int(b[0]), int(b[1])
        if x1 <= x0:
            raise ValueError(f"lane {i}: reversed or empty bounds [{x0}, {x1}]")
        if x1 - x0 < MIN_LANE_WIDTH_PX:
            raise ValueError(f"lane {i}: narrower than {MIN_LANE_WIDTH_PX} px")
        if x0 < x_lo or x1 > x_hi:
            raise ValueError(f"lane {i}: [{x0}, {x1}] outside the selected region [{x_lo}, {x_hi}]")
        if prev_x1 is not None and x0 < prev_x1:
            raise ValueError(f"lane {i}: overlaps lane {i - 1} (lanes must be ordered left to right)")
        prev_x1 = x1
        out.append((x0, x1))
    if not out:
        raise ValueError("no lanes supplied")
    return out


def _region_arrays(gray_full: np.ndarray, region):
    """Crop, polarity, background and corrected signal for one region."""
    import cv2

    H, W = gray_full.shape
    if region is not None:
        rx0, ry0, rx1, ry1 = region
        x0, x1 = max(0, min(rx0, rx1)), min(W, max(rx0, rx1))
        y0, y1 = max(0, min(ry0, ry1)), min(H, max(ry0, ry1))
        if x1 - x0 < MIN_REGION_PX or y1 - y0 < MIN_REGION_PX:
            raise ValueError(f"region too small (need at least {MIN_REGION_PX}x{MIN_REGION_PX} px inside the image)")
        gray = gray_full[y0:y1, x0:x1]
        ox, oy = x0, y0
    else:
        gray, ox, oy = gray_full, 0, 0
    h, w = gray.shape
    if h < MIN_REGION_PX or w < MIN_REGION_PX:
        raise ValueError("image too small")
    # Polarity from the WHOLE image, not the box: a tight box around dense
    # dark bands has a dark mean even though the figure is light-background,
    # and the flipped polarity would then measure the gaps between bands.
    inverted = bool(gray_full.mean() > 127)  # light background: darkness is signal
    signal = ((255 - gray) if inverted else gray).astype(np.float32)
    # Rolling-ball radius from the WHOLE image, not the box: a tight box
    # around one strip would otherwise shrink the kernel below the band
    # height, the opening would absorb the band into "background", and the
    # ratios would collapse toward 1 while still looking valid.
    k = max(5, (min(H, W) // 4) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    background = cv2.morphologyEx(signal, cv2.MORPH_OPEN, kernel)
    corrected = np.clip(signal - background, 0, None)
    return gray, signal, background, corrected, inverted, ox, oy, k


def _flank(corrected, x0, x1, y0, y1):
    """(baseline, sigma, n) from membrane rows near the band in this lane: a
    block of rows above and one below, each separated from the band row by a
    gap of the same height so band tails do not leak in. The lower of the two
    medians is the baseline (the other may hold a neighbouring strip). None
    when the box has no such rows -- the researcher must include a margin."""
    m = max(FLANK_MIN_PX, round(FLANK_FRACTION * (y1 - y0)))
    hh = corrected.shape[0]
    blocks = [corrected[max(0, y0 - 2 * m):max(0, y0 - m), x0:x1].ravel(),
              corrected[min(hh, y1 + m):min(hh, y1 + 2 * m), x0:x1].ravel()]
    cands = [b for b in blocks if b.size >= 10]
    if not cands:
        return None
    best = min(cands, key=lambda b: float(np.median(b)))
    base = float(np.median(best))
    mad = float(np.median(np.abs(best - base)))
    return base, max(1.4826 * mad, 0.5), int(sum(b.size for b in cands))


def _integrate(gray, signal, background, corrected, inverted, ox, oy, y0, y1, bounds, noise):
    """Per-lane sums over the band row. Bounds and the returned coordinates
    are in FULL-image pixels; y0/y1 are region-local. `noise` is the box-wide
    fallback (baseline, sigma) used only when a lane has no flank rows."""
    clip_val = 0 if inverted else 255
    out = []
    for i, (fx0, fx1) in enumerate(bounds, 1):
        x0, x1 = fx0 - ox, fx1 - ox
        box_sig = signal[y0:y1, x0:x1]
        box_bg = background[y0:y1, x0:x1]
        box_raw = gray[y0:y1, x0:x1]
        fl = _flank(corrected, x0, x1, y0, y1)
        flank_base, noise_sigma = (fl[0], fl[1]) if fl else (0.0, None)
        box_cor = np.clip(corrected[y0:y1, x0:x1] - flank_base, 0, None)
        peak = float(box_cor.max()) if box_cor.size else 0.0
        core = box_cor >= 0.5 * peak if peak > 0 else np.zeros_like(box_cor, dtype=bool)
        n_core = int(core.sum())
        if n_core:
            clipped = float((np.abs(box_raw[core].astype(int) - clip_val) <= CLIP_THRESHOLD_DN).mean())
        else:
            clipped = 0.0
        mean_cor = float(box_cor.mean()) if box_cor.size else 0.0
        snr = mean_cor / noise_sigma if noise_sigma else float("nan")
        out.append({
            "index": i, "x0": int(fx0), "x1": int(fx1), "y0": int(y0 + oy), "y1": int(y1 + oy),
            "raw": float(box_sig.sum()), "background": float(box_bg.sum() + flank_base * box_sig.size),
            "flank_baseline": round(flank_base, 3), "flank_rows": fl[2] if fl else 0,
            "corrected": float(box_cor.sum()), "clipped_fraction": round(clipped, 4),
            "core_pixels": n_core, "snr": round(float(snr), 2) if np.isfinite(snr) else None,
        })
    return out


def _relative(lanes) -> tuple[float, list[float | None]]:
    top = max((l["corrected"] for l in lanes), default=0.0)
    return top, [(l["corrected"] / top) if top > 0 else None for l in lanes]


def _noise_stats(corrected: np.ndarray, y0: int, y1: int) -> tuple[float, float]:
    """(median, robust sigma = 1.4826 * MAD) of the corrected residual OUTSIDE
    the band row; falls back to the whole region when the row is the whole
    region. The opening leaves a positive residual, so the median is the
    zero-signal baseline a lane is compared against."""
    rest = np.concatenate([corrected[:y0].ravel(), corrected[y1:].ravel()])
    if rest.size < 50:
        rest = corrected.ravel()
    med = float(np.median(rest))
    # lower-side MAD: other strips inside the box sit ABOVE the median and
    # would inflate a two-sided scale until every lane looked like noise
    low = rest[rest < med]
    mad = float(np.median(med - low)) if low.size >= 25 else float(np.median(np.abs(rest - med)))
    return med, max(1.4826 * mad, 0.5)


def analyze(img: np.ndarray, lanes: int | None = None, row_index: int = 0,
            band_row: tuple[int, int] | None = None,
            region: tuple[int, int, int, int] | None = None,
            lane_bounds: list | None = None,
            lane_labels: list[str] | None = None,
            stability: bool = True) -> dict[str, Any]:
    """`region` = (x0, y0, x1, y1) in image pixels: analyze only that box
    (the researcher draws it around one blot strip, excluding printed labels).
    `lane_bounds` = [[x0, x1], ...] in FULL-image pixels inside the region:
    the researcher's lanes. `lanes` (a count) is the diagnostic equal-width
    fallback. All coordinates in the result are FULL-image pixels."""
    gray_full = _to_gray(img)
    H, W = gray_full.shape
    reg = tuple(int(v) for v in region) if region is not None else None
    gray, signal, background, corrected, inverted, ox, oy, kernel_px = _region_arrays(gray_full, reg)
    h, w = gray.shape

    rows = detect_band_rows(corrected, gray, total_h=H)
    warnings: list[str] = []
    if band_row is not None:
        y0, y1 = int(band_row[0]) - oy, int(band_row[1]) - oy
        if y0 < 0 or y1 > h or y1 - y0 < 2:
            raise ValueError(f"band_row [{band_row[0]}, {band_row[1]}] is outside the selected region "
                             f"[{oy}, {oy + h}] or too thin")
        inside = [(a, b) for a, b in rows if a >= y0 and b <= y1 and not row_text_like(gray, a, b, H)]
        if len(inside) >= 2:
            warnings.append(f"the chosen band row spans {len(inside)} detected band rows; their signals are summed "
                            "per lane - draw the box around one strip or use row detection")
    elif rows:
        if row_index >= len(rows):
            warnings.append(f"row_index {row_index} out of range; {len(rows)} band row(s) detected, using the strongest")
            row_index = 0
        y0, y1 = rows[row_index]
    else:
        y0, y1 = 0, h
        warnings.append("no distinct band row detected; integrating the whole selected height")
    y0, y1 = max(0, y0), min(h, y1)
    if y1 - y0 < 2:
        raise ValueError("band row too thin")
    if row_text_like(gray, y0, y1, H):
        warnings.append("the selected band row looks like printed text (solid black glyphs or a tall block), "
                        "not a blot strip; draw the region around the membrane only")
    n_blot_rows = sum(1 for a, b in rows if not row_text_like(gray, a, b, H))
    multi_row_note = (f"the box contains {n_blot_rows} band rows; only the chosen row is integrated and its "
                      "baseline comes from the rows next to it - box one strip to check the geometry") if n_blot_rows >= 2 else None
    if multi_row_note:
        warnings.append(multi_row_note)

    if lane_bounds is not None:
        bounds = validate_lane_bounds(lane_bounds, ox, ox + w)
        lane_mode = "explicit"
    else:
        strip = corrected[y0:y1]
        bounds = [(a + ox, b + ox) for a, b in detect_lanes(strip, lanes)]
        lane_mode = "equal_width" if lanes else "auto"
        if lane_mode == "auto" and len(bounds) > 1:
            warnings.append("lane boundaries were auto-detected from the intensity profile (diagnostic); define lanes explicitly for a measurement")
        elif lane_mode == "equal_width":
            warnings.append("lanes are equal-width slices of the selected region (diagnostic); define lanes explicitly for a measurement")
    labels = list(lane_labels) if lane_labels else []
    if labels and len(labels) != len(bounds):
        raise ValueError(f"{len(labels)} lane labels for {len(bounds)} lanes")

    noise = _noise_stats(corrected, y0, y1)
    base = _integrate(gray, signal, background, corrected, inverted, ox, oy, y0, y1, bounds, noise)
    if any(l["flank_rows"] == 0 for l in base):
        warnings.append("no membrane rows above/below the band inside the box for some lanes: the flank baseline "
                        "and noise could not be estimated there (opening-only background); include a margin of "
                        "at least the band height above and below the strip")
    top, rel = _relative(base)
    top_idx = int(np.argmax([l["corrected"] for l in base])) if top > 0 else None

    # ---- per-lane quality --------------------------------------------------
    for l, r in zip(base, rel):
        reasons: list[str] = []
        state = OK
        if l["snr"] is not None and l["snr"] < SNR_MIN:
            reasons.append(f"weak: mean corrected signal is within {SNR_MIN:g} sigma of the off-band residual "
                           f"(SNR {l['snr']}); treat the value as at or near zero")
        if l["clipped_fraction"] >= CLIP_FRACTION_REFUSE:
            state = REFUSED
            reasons.append(f"band core clipped ({l['clipped_fraction']:.0%} of core pixels at the signal extreme; "
                           f"integrated intensity is a lower bound, not a measurement)")
        elif l["clipped_fraction"] >= CLIP_FRACTION_WARN:
            state = WARNING
            reasons.append(f"some clipped pixels in the band core ({l['clipped_fraction']:.1%})")
        l["quality"], l["reasons"] = state, reasons

    overall = OK
    overall_reasons: list[str] = []
    if top <= 0 or all(l["snr"] is not None and l["snr"] < SNR_MIN for l in base):
        overall = REFUSED
        overall_reasons.append("no lane has signal above background in the selected row"
                               + (f" ({multi_row_note})" if multi_row_note else ""))
    elif base[top_idx]["quality"] == REFUSED:
        overall = REFUSED
        overall_reasons.append(f"the strongest lane ({top_idx + 1}) is clipped, so nothing can be expressed relative to it")

    # ---- stability envelope -------------------------------------------------
    stab: dict[str, Any] | None = None
    if stability and overall != REFUSED and len(bounds) >= 1:
        dx = max(PERTURB_MIN_PX, round(PERTURB_FRACTION_X * statistics.median(b - a for a, b in bounds)))
        dy = max(PERTURB_MIN_PX, round(PERTURB_FRACTION_Y * (y1 - y0)))
        runs: list[list[float | None]] = [rel]
        top_ids = [top_idx]

        def run(g, s, bg, c, inv, oxx, oyy, yy0, yy1, bnds):
            yy0, yy1 = max(0, yy0), min(c.shape[0], yy1)
            if yy1 - yy0 < 2:
                return
            bnds = [(max(oxx, a), min(oxx + c.shape[1], b)) for a, b in bnds]
            if any(b - a < MIN_LANE_WIDTH_PX for a, b in bnds):
                return
            lanes_ = _integrate(g, s, bg, c, inv, oxx, oyy, yy0, yy1, bnds, noise)
            t, r = _relative(lanes_)
            runs.append(r)
            top_ids.append(int(np.argmax([l["corrected"] for l in lanes_])) if t > 0 else None)

        # band-row edges
        for a, b in ((y0 - dy, y1), (y0 + dy, y1), (y0, y1 - dy), (y0, y1 + dy)):
            run(gray, signal, background, corrected, inverted, ox, oy, a, b, bounds)
        # lane edges: shift, expand, contract
        for f in ((lambda a, b: (a - dx, b - dx)), (lambda a, b: (a + dx, b + dx)),
                  (lambda a, b: (a - dx, b + dx)), (lambda a, b: (a + dx, b - dx))):
            run(gray, signal, background, corrected, inverted, ox, oy, y0, y1, [f(a, b) for a, b in bounds])
        # region offset (re-estimates background); lanes/band row fixed in full-image pixels
        if reg is not None:
            rx0, ry0, rx1, ry1 = reg
            for sx, sy in ((-dx, 0), (dx, 0), (0, -dy), (0, dy)):
                try:
                    g2, s2, bg2, c2, inv2, ox2, oy2, _ = _region_arrays(gray_full, (rx0 + sx, ry0 + sy, rx1 + sx, ry1 + sy))
                except ValueError:
                    continue
                run(g2, s2, bg2, c2, inv2, ox2, oy2, y0 + oy - oy2, y1 + oy - oy2, bounds)

        n_lanes = len(bounds)
        env = []
        for i in range(n_lanes):
            vals = [r[i] for r in runs if r[i] is not None]
            env.append({"relative_min": round(min(vals), 4), "relative_median": round(statistics.median(vals), 4),
                        "relative_max": round(max(vals), 4)} if vals else None)
        ranking_stable = len(set(top_ids)) == 1
        # A reference change is a near tie when every alternative winner was
        # already within STABILITY_WARN_WIDTH of the top at baseline: the
        # relative values then stay valid to within their envelopes and only
        # the ordering of the tied lanes is unresolved (warning). A winner
        # that was clearly weaker at baseline means the geometry, not the
        # bands, chose the reference (refuse).
        other_tops = sorted({t for t in top_ids if t is not None and t != top_idx})
        severe_flip = any(rel[t] is None or rel[t] < 1 - STABILITY_WARN_WIDTH for t in other_tops)
        stab = {"perturbation_px": {"x": int(dx), "y": int(dy)}, "runs": len(runs), "ranking_stable": ranking_stable,
                "reference_tie_lanes": sorted([top_idx + 1] + [t + 1 for t in other_tops]) if other_tops and not severe_flip else []}
        for l, e in zip(base, env):
            l["stability"] = e
            if e and (e["relative_max"] - e["relative_min"]) > STABILITY_WARN_WIDTH:
                l["reasons"].append(f"unstable: relative ranges {e['relative_min']:.2f}-{e['relative_max']:.2f} "
                                    f"under +/-{dx}px lane / +/-{dy}px row perturbation")
                if l["quality"] == OK:
                    l["quality"] = WARNING
        if not ranking_stable and severe_flip:
            overall = REFUSED
            overall_reasons.append(f"the strongest lane changes under +/-{dx}px lane / +/-{dy}px row perturbation to a lane "
                                   "that was clearly weaker at the drawn geometry; the relative scale is not defined here")
        elif not ranking_stable:
            tie = ", ".join(str(i) for i in stab["reference_tie_lanes"])
            overall_reasons.append(f"lanes {tie} are a near tie for strongest (within {STABILITY_WARN_WIDTH:.0%}); their order "
                                   "is not resolved by this image, other lanes' relative values hold within their ranges")
            if overall == OK:
                overall = WARNING
    else:
        for l in base:
            l["stability"] = None

    # ---- assemble ------------------------------------------------------------
    for i, (l, r) in enumerate(zip(base, rel)):
        l["label"] = labels[i] if labels else None
        if overall == REFUSED or l["quality"] == REFUSED:
            l["relative"] = None
            if l["stability"] is not None and l["quality"] == REFUSED:
                l["stability"] = None
        else:
            l["relative"] = round(r, 4) if r is not None else None
        if overall != REFUSED and l["quality"] == WARNING:
            overall = WARNING if overall == OK else overall
    if multi_row_note and overall == OK:
        overall = WARNING
        overall_reasons.append(multi_row_note)
    if overall == WARNING and not overall_reasons:
        overall_reasons.append("one or more lanes carry a warning; read the per-lane reasons")
    if overall == OK and any(l["quality"] == REFUSED for l in base):
        overall = WARNING
        overall_reasons.append("a non-reference lane is clipped and reports no relative value")

    max_clip = max((l["clipped_fraction"] for l in base), default=0.0)
    if max_clip >= CLIP_FRACTION_WARN:
        warnings.append(f"clipped pixels in the band core of at least one lane ({max_clip:.1%})")
    if top <= 0:
        warnings.append("no signal above background in the selected row")

    return {
        "method": {
            "name": METHOD_NAME, "version": METHOD_VERSION,
            "steps": "grayscale -> polarity -> morphological-opening background -> band row -> "
                     "lane boxes -> per-lane flank baseline (median of the rows just above/below the band) "
                     "-> integrated corrected intensity (relative to the strongest lane) "
                     "-> clip/SNR gates -> geometry perturbation envelope",
            "params": {
                "background_kernel_px": int(kernel_px), "clip_threshold_dn": CLIP_THRESHOLD_DN,
                "clip_fraction_warn": CLIP_FRACTION_WARN, "clip_fraction_refuse": CLIP_FRACTION_REFUSE,
                "snr_min": SNR_MIN, "flank_fraction": FLANK_FRACTION, "flank_min_px": FLANK_MIN_PX,
                "box_noise_baseline": round(noise[0], 3), "box_noise_sigma": round(noise[1], 3),
                "min_lane_width_px": MIN_LANE_WIDTH_PX, "stability_warn_width": STABILITY_WARN_WIDTH,
                "perturb_fraction_x": PERTURB_FRACTION_X, "perturb_fraction_y": PERTURB_FRACTION_Y,
            },
        },
        "image": {"width": int(W), "height": int(H), "inverted_for_analysis": inverted,
                  "region": [ox, oy, ox + w, oy + h] if reg is not None else None},
        "band_row": [int(y0 + oy), int(y1 + oy)],
        "rows_detected": [[int(a + oy), int(b + oy)] for a, b in rows],
        "rows_text_like": [row_text_like(gray, a, b, H) for a, b in rows],
        "lane_mode": lane_mode,
        "lanes": base,
        "quality": {"state": overall, "reasons": overall_reasons},
        "stability": stab,
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }

"""EXPERIMENTAL densitometry on a published blot panel image.

Scope, stated plainly: this measures pixel intensity in a figure crop. A
figure crop is not raw data — exposure, contrast, JPEG/PNG re-encoding and
journal layout all shape it — so the numbers are relative within ONE panel
image and carry no units. They never enter an Evidence Record; the reviewed
corpus keeps categorical band presence only. This module exists so a
researcher can see what such a measurement would say, with its caveats.

Method (deterministic, OpenCV/NumPy):
  1. grayscale; if the image is light-background/dark-band (the common
     case) invert so signal = darkness
  2. background = morphological opening with a large kernel (rolling-ball
     style); corrected = signal - background
  3. band row = the strongest contiguous horizontal band of corrected signal
     (or a caller-supplied row / the n-th detected row)
  4. lanes = caller-supplied count (equal widths) or valleys of the smoothed
     vertical profile inside the band row
  5. per lane: raw, background, corrected integrated intensity, relative to
     the strongest lane, saturated-pixel fraction
"""
from __future__ import annotations

from typing import Any

import numpy as np

DISCLAIMER = (
    "EXPERIMENTAL and uncalibrated. Intensities are integrated pixel darkness "
    "of a published figure crop after background subtraction, relative within "
    "this one image. They are not a measurement of protein amount: exposure, "
    "saturation, contrast adjustment and image re-encoding are unknown. Not "
    "stored in Evidence Records; never compare across images."
)


def _to_gray(img: np.ndarray) -> np.ndarray:
    import cv2

    if img.ndim == 3:
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
                     min_height: int = 4) -> list[tuple[int, int]]:
    """Horizontal bands of signal, strongest first. Rows that are mostly
    pure black/white pixels are printed text (lane labels, row labels), not
    bands; they are pushed to the end so auto mode lands on a blot strip."""
    prof = _smooth(corrected.sum(axis=1), max(3, corrected.shape[0] // 40))
    if prof.max() <= 0:
        return []
    thr = prof.mean() + 0.5 * prof.std()
    segs = [(a, b) for a, b in _segments_above(prof > thr) if b - a >= min_height]

    total_h = corrected.shape[0]

    def score(seg):
        a, b = seg
        textlike = 0.0
        if gray is not None:
            block = gray[a:b]
            solid = (block < 16).mean()
            # printed labels: solid-black glyphs and/or a tall block (stacked
            # label lines); blot bands are grey-scaled and thin
            textlike = float(solid > 0.25 or (b - a) > 0.1 * total_h)
        return (textlike, -prof[a:b].sum())

    return sorted(segs, key=score)


def detect_lanes(row: np.ndarray, expected: int | None = None, max_lanes: int = 16) -> list[tuple[int, int]]:
    """Lane boundaries (x0, x1) inside one band row."""
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


def analyze(img: np.ndarray, lanes: int | None = None, row_index: int = 0,
            band_row: tuple[int, int] | None = None,
            region: tuple[int, int, int, int] | None = None) -> dict[str, Any]:
    """`region` = (x0, y0, x1, y1) in image pixels: analyze only that box
    (the researcher draws it around one blot strip, excluding printed labels).
    Lane x-coordinates in the result are reported in FULL-image pixels."""
    import cv2

    gray = _to_gray(img)
    ox = oy = 0
    if region is not None:
        x0, y0, x1, y1 = (int(v) for v in region)
        x0, y0 = max(0, min(x0, x1)), max(0, min(y0, y1))
        x1, y1 = min(gray.shape[1], max(region[0], region[2])), min(gray.shape[0], max(region[1], region[3]))
        if x1 - x0 < 8 or y1 - y0 < 8:
            raise ValueError("region too small")
        gray = gray[y0:y1, x0:x1]
        ox, oy = x0, y0
    h, w = gray.shape
    if h < 8 or w < 8:
        raise ValueError("image too small")
    inverted = bool(gray.mean() > 127)  # light background: darkness is signal
    signal = (255 - gray) if inverted else gray
    signal = signal.astype(np.float32)
    k = max(5, (min(h, w) // 4) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    background = cv2.morphologyEx(signal, cv2.MORPH_OPEN, kernel)
    corrected = np.clip(signal - background, 0, None)

    rows = detect_band_rows(corrected, gray)
    warnings: list[str] = []
    if band_row is not None:
        y0, y1 = int(band_row[0]), int(band_row[1])
    elif rows:
        if row_index >= len(rows):
            warnings.append(f"row_index {row_index} out of range; {len(rows)} band row(s) detected, using the strongest")
            row_index = 0
        y0, y1 = rows[row_index]
    else:
        y0, y1 = 0, h
        warnings.append("no distinct band row detected; integrating the whole image height")
    y0, y1 = max(0, y0), min(h, y1)
    strip = corrected[y0:y1]
    bounds = detect_lanes(strip, lanes)

    out_lanes = []
    sat_total = 0.0
    for i, (x0, x1) in enumerate(bounds, 1):
        box_sig = signal[y0:y1, x0:x1]
        box_bg = background[y0:y1, x0:x1]
        box_cor = corrected[y0:y1, x0:x1]
        box_raw = gray[y0:y1, x0:x1]
        # saturation = pixels clipped at the SIGNAL extreme (black on a light
        # background, white on a dark one); the background extreme is normal
        sat = float((box_raw == (0 if inverted else 255)).mean()) if box_raw.size else 0.0
        sat_total = max(sat_total, sat)
        out_lanes.append({
            "index": i, "x0": int(x0 + ox), "x1": int(x1 + ox),
            "raw": float(box_sig.sum()), "background": float(box_bg.sum()),
            "corrected": float(box_cor.sum()), "saturated_fraction": round(sat, 4),
        })
    top = max((l["corrected"] for l in out_lanes), default=0.0)
    for l in out_lanes:
        l["relative"] = round(l["corrected"] / top, 4) if top > 0 else 0.0
    if sat_total > 0.01:
        warnings.append(f"saturated pixels in at least one lane ({sat_total:.1%}); intensities there are clipped")
    if top <= 0:
        warnings.append("no signal above background in the selected row")
    if lanes is None and len(bounds) > 1:
        warnings.append("lane boundaries were auto-detected from the intensity profile; pass the printed lane count to fix them")
    return {
        "image": {"width": int(w + ox if region else w), "height": int(h + oy if region else h),
                  "inverted_for_analysis": inverted,
                  "region": [ox, oy, ox + w, oy + h] if region else None},
        "band_row": [int(y0 + oy), int(y1 + oy)],
        "rows_detected": [[int(a + oy), int(b + oy)] for a, b in rows],
        "lanes": out_lanes,
        "method": "grayscale -> morphological-opening background -> strongest band row -> "
                  "lane boxes -> integrated corrected intensity (relative to the strongest lane)",
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }

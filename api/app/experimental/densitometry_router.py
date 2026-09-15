"""POST /experimental-densitometry — EXPERIMENTAL, uncalibrated band
intensity on a panel image (a reviewed record's crop, a live record's crop,
or an uploaded image). Results are returned, never stored: the reviewed
corpus keeps categorical band presence only."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import require_internal_key
from ..config import settings
from ..db import fetch_live_crop, fetch_live_record, fetch_record_by_id
from ..limiter import limiter

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from western_blot_miner import densitometry  # noqa: E402

router = APIRouter(dependencies=[Depends(require_internal_key)], tags=["experimental"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024


class DensitometryRequest(BaseModel):
    record_id: int | None = None
    live: bool = False                       # record_id refers to the live tier
    image_base64: str | None = Field(default=None, max_length=12_000_000)
    # DIAGNOSTIC: equal-width slicing of the region into this many lanes.
    lanes: int | None = Field(default=None, ge=1, le=24)
    row_index: int = Field(default=0, ge=0, le=15)
    # Box around one blot strip, full-image pixels [x0, y0, x1, y1]; the UI
    # lets the researcher draw it so printed labels are excluded.
    region: list[int] | None = Field(default=None, min_length=4, max_length=4)
    # Researcher-defined lanes, full-image pixels [[x0, x1], ...] inside the
    # region, ordered left to right. The product path; `lanes` is the fallback.
    lane_bounds: list[list[int]] | None = Field(default=None, min_length=1, max_length=24)
    lane_labels: list[str] | None = Field(default=None, max_length=24)
    # Researcher-chosen band row [y0, y1] in full-image pixels (e.g. the full
    # height of a tightly drawn box); when absent the strongest row inside the
    # region is detected and `row_index` picks among detected rows.
    band_row: list[int] | None = Field(default=None, min_length=2, max_length=2)
    # Re-run the integration over small geometry perturbations and report an
    # envelope per lane (see densitometry.py).
    stability: bool = True


async def _record_png(record_id: int, live: bool) -> tuple[bytes, int | None, dict]:
    if live:
        row = await fetch_live_record(record_id)
        if row is None or not row.get("image_crop_ref"):
            raise HTTPException(404, "No crop for this live record")
        png = await fetch_live_crop(row.get("job_id"), str(row["image_crop_ref"]).rsplit("/", 1)[-1])
        if not png:
            raise HTTPException(404, "Crop not available")
        return png, None, row
    row = await fetch_record_by_id(record_id)
    if row is None or not row.get("image_crop_ref"):
        raise HTTPException(404, "No figure crop for this record")
    base = Path(settings.crop_base_dir).resolve()
    crop = Path(str(row["image_crop_ref"])).resolve()
    try:
        crop.relative_to(base)
    except ValueError:
        raise HTTPException(404, "Crop path not servable")
    if crop.suffix.lower() != ".png" or not crop.is_file():
        raise HTTPException(404, "Crop file not available")
    prov = row.get("provenance") or {}
    n_lanes = len(prov.get("bands") or []) or None
    return crop.read_bytes(), n_lanes, row


class PreviewRequest(BaseModel):
    image_base64: str = Field(max_length=40_000_000)


@router.post("/experimental-densitometry/preview")
@limiter.limit("60/minute")
async def experimental_densitometry_preview(request: Request, body: PreviewRequest):
    """Browsers cannot display TIFF (the usual imager export). Decode any
    OpenCV-readable upload and return an 8-bit PNG data URL for display; the
    measurement then runs on that PNG, which is exactly the 8-bit grayscale
    the analyzer would derive from the original (16-bit -> //257, no
    stretch). Nothing is stored."""
    import cv2

    try:
        raw = base64.b64decode(body.image_base64.split(",", 1)[-1], validate=False)
    except Exception:
        raise HTTPException(400, "image_base64 is not valid base64")
    if len(raw) > 3 * MAX_IMAGE_BYTES:
        raise HTTPException(413, "image too large")
    try:
        gray = densitometry._to_gray(densitometry.decode_image(raw))
    except ValueError as e:
        raise HTTPException(400, str(e))
    ok, buf = cv2.imencode(".png", gray)
    if not ok:
        raise HTTPException(400, "could not encode preview")
    png = buf.tobytes()
    if len(png) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "decoded image too large for the preview")
    return {"png_base64": "data:image/png;base64," + base64.b64encode(png).decode(),
            "width": int(gray.shape[1]), "height": int(gray.shape[0]),
            "source_sha256": hashlib.sha256(raw).hexdigest(), "stored": False}


@router.post("/experimental-densitometry")
@limiter.limit("60/minute")
async def experimental_densitometry(request: Request, body: DensitometryRequest):
    if body.record_id is None and not body.image_base64:
        raise HTTPException(400, "Provide record_id or image_base64")
    default_lanes = None
    source: dict = {}
    if body.record_id is not None:
        png, default_lanes, row = await _record_png(body.record_id, body.live)
        source = {"record_id": body.record_id, "tier": "live_unreviewed" if body.live else "reviewed",
                  "target": row.get("target"), "crop": str(row.get("image_crop_ref")).rsplit("/", 1)[-1],
                  "printed_lanes": default_lanes}
    else:
        try:
            png = base64.b64decode(body.image_base64.split(",", 1)[-1], validate=False)
        except Exception:
            raise HTTPException(400, "image_base64 is not valid base64")
        if len(png) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "image too large")
        source = {"upload": True}
    lanes = None if body.lane_bounds else (body.lanes or default_lanes)
    labels = [str(x)[:40] for x in body.lane_labels] if body.lane_labels else None
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: densitometry.analyze(densitometry.decode_image(png), lanes=lanes,
                                               row_index=body.row_index,
                                               region=tuple(body.region) if body.region else None,
                                               lane_bounds=body.lane_bounds, lane_labels=labels,
                                               band_row=tuple(body.band_row) if body.band_row else None,
                                               stability=body.stability))
    except ValueError as e:
        raise HTTPException(400, str(e))
    source["image_sha256"] = hashlib.sha256(png).hexdigest()
    result["source"] = source
    result["lanes_requested"] = lanes
    result["stored"] = False
    return result

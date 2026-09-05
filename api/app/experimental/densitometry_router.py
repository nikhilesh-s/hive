"""POST /experimental-densitometry — EXPERIMENTAL, uncalibrated band
intensity on a panel image (a reviewed record's crop, a live record's crop,
or an uploaded image). Results are returned, never stored: the reviewed
corpus keeps categorical band presence only."""
from __future__ import annotations

import asyncio
import base64
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
    lanes: int | None = Field(default=None, ge=1, le=24)
    row_index: int = Field(default=0, ge=0, le=15)
    # Box around one blot strip, full-image pixels [x0, y0, x1, y1]; the UI
    # lets the researcher draw it so printed labels are excluded.
    region: list[int] | None = Field(default=None, min_length=4, max_length=4)


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


@router.post("/experimental-densitometry")
@limiter.limit("20/minute")
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
    lanes = body.lanes or default_lanes
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: densitometry.analyze(densitometry.decode_image(png), lanes=lanes,
                                               row_index=body.row_index,
                                               region=tuple(body.region) if body.region else None))
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["source"] = source
    result["lanes_requested"] = lanes
    result["stored"] = False
    return result

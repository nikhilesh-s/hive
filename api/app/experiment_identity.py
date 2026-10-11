"""Canonical identity for one reviewed experiment card.

Stable row keys are preferred. Legacy rows use the same grouping fields as the
frontend's historical fallback, but receive a versioned SHA-256 key so the
database stores a compact, collision-resistant bookmark identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any


def _crop_name(value: Any) -> str | None:
    return PurePosixPath(str(value)).name if value else None


def identity_for_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    stable_key = row.get("stable_row_key")
    if stable_key:
        prefix = str(stable_key).split(":", 1)[0]
        identity = {
            "version": 1,
            "kind": "stable",
            "stable_key": prefix,
            "paper_id": row.get("paper_id"),
        }
        return f"reviewed:stable:{prefix}", identity

    crop = _crop_name(row.get("image_crop_ref"))
    crop_or_page = crop if crop else f"p{row.get('page')}"
    # Match web/lib/results.ts: nullish fallback for cell_line/sample and
    # empty string for optional identity fields.
    values = [
        row.get("paper_id"),
        crop_or_page,
        row.get("target"),
        row.get("experiment_type") or "",
        row.get("cell_line") if row.get("cell_line") is not None else row.get("sample"),
        row.get("modification_label") or "",
    ]
    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    identity = {"version": 1, "kind": "legacy", "values": values}
    return f"reviewed:legacy:{digest}", identity
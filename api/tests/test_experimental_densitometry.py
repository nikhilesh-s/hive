"""/experimental-densitometry: auth, input validation, upload path with a
synthetic blot, and the reviewed-record path (crop read from disk, printed
lane count used as default). Nothing is stored."""
from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.experimental import densitometry_router as dr
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}


def _png(strengths, w=300, h=90):
    import cv2

    img = np.full((h, w), 230.0)
    ys, xs = np.arange(h)[:, None], np.arange(w)[None, :]
    lane_w = w / len(strengths)
    for i, s in enumerate(strengths):
        cx = (i + 0.5) * lane_w
        img -= s * 200 * np.exp(-((ys - 45) ** 2) / 50.0) * (np.abs(xs - cx) < lane_w * 0.3)
    ok, buf = cv2.imencode(".png", np.clip(img, 0, 255).astype(np.uint8))
    assert ok
    return buf.tobytes()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_requires_internal_key(client):
    assert client.post("/experimental-densitometry", json={"record_id": 1}).status_code == 401


def test_requires_an_input(client):
    r = client.post("/experimental-densitometry", json={}, headers=AUTH)
    assert r.status_code == 400


def test_upload_path_returns_relative_intensities_and_disclaimer(client):
    b64 = base64.b64encode(_png([1.0, 0.5, 0.0])).decode()
    r = client.post("/experimental-densitometry", json={"image_base64": b64, "lanes": 3}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    rel = [l["relative"] for l in body["lanes"]]
    assert rel[0] == 1.0 and abs(rel[1] - 0.5) < 0.15 and rel[2] < 0.1
    assert body["stored"] is False and "uncalibrated" in body["disclaimer"]
    assert body["source"] == {"upload": True} and body["lanes_requested"] == 3


def test_bad_base64_and_bad_image(client):
    assert client.post("/experimental-densitometry", json={"image_base64": "zz"}, headers=AUTH).status_code == 400
    b64 = base64.b64encode(b"not an image at all").decode()
    assert client.post("/experimental-densitometry", json={"image_base64": b64}, headers=AUTH).status_code == 400


def test_record_path_uses_the_records_crop_and_printed_lane_count(client, monkeypatch, tmp_path):
    crop = tmp_path / "page_001_cand_0001.png"
    crop.write_bytes(_png([0.2, 1.0, 0.6, 0.6]))
    monkeypatch.setattr(settings, "crop_base_dir", str(tmp_path))

    async def fake_fetch(record_id):
        return {"id": record_id, "target": "STAT3", "image_crop_ref": str(crop),
                "provenance": {"bands": [{}, {}, {}, {}]}}
    monkeypatch.setattr(dr, "fetch_record_by_id", fake_fetch)
    r = client.post("/experimental-densitometry", json={"record_id": 42}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["record_id"] == 42 and body["source"]["printed_lanes"] == 4 and body["source"]["tier"] == "reviewed"
    assert len(body["lanes"]) == 4 and body["lanes"][1]["relative"] == 1.0
    assert body["source"]["crop"] == "page_001_cand_0001.png" and "/" not in body["source"]["crop"]


def test_record_path_refuses_crops_outside_base_dir(client, monkeypatch, tmp_path):
    outside = tmp_path / "elsewhere.png"
    outside.write_bytes(_png([1.0]))
    monkeypatch.setattr(settings, "crop_base_dir", str(tmp_path / "base"))

    async def fake_fetch(record_id):
        return {"id": record_id, "image_crop_ref": str(outside), "provenance": {}}
    monkeypatch.setattr(dr, "fetch_record_by_id", fake_fetch)
    assert client.post("/experimental-densitometry", json={"record_id": 1}, headers=AUTH).status_code == 404

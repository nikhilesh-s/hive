import datetime

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.limiter import limiter
from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}
SESSION = "browser-session-123"


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def row(record_id: int = 5, lane: int = 1, saved_at=None) -> dict:
    return {
        "id": record_id,
        "paper_id": "10.1000/example",
        "page": 3,
        "western_blot_type": "western_blot",
        "sample": "Hep3B",
        "organism": "human",
        "treatment_context": None,
        "figure_label": "Fig 2A",
        "target": "STAT3",
        "condition": f"{lane} h",
        "band_detected": True,
        "confidence": 0.9,
        "stable_row_key": f"experiment-hash:{lane}",
        "image_crop_ref": "panel.png",
        "saved_at": saved_at,
    }


def test_saved_status_requires_session_and_is_batched(client, monkeypatch):
    captured = {}

    async def fake_status(session_id, keys):
        captured.update(session=session_id, keys=keys)
        return {keys[0]}

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "saved_results_status", fake_status)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")
    response = client.post("/saved-results/status", headers=AUTH,
                           json={"session_id": SESSION, "stable_row_keys": ["k:1", "k:1", "k:2"]})
    assert response.status_code == 200
    assert response.json() == {"saved_keys": ["k:1"]}
    assert captured == {"session": SESSION, "keys": ["k:1", "k:2"]}
    assert client.post("/saved-results/status", headers=AUTH,
                       json={"session_id": "ssr", "stable_row_keys": ["k:1"]}).status_code == 400


def test_save_validates_and_saves_all_lane_records(client, monkeypatch):
    saved = []

    async def fake_save(session_id, records):
        saved.append((session_id, records))
        return [r["stable_row_key"] for r in records]

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "save_result_records", fake_save)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")
    payload = {
        "session_id": SESSION,
        "records": [
            {"record_id": 1189, "stable_row_key": "6057228515df6bd3:1"},
            {"record_id": 1190, "stable_row_key": "6057228515df6bd3:2"},
        ],
    }
    response = client.post("/saved-results", headers=AUTH, json=payload)
    assert response.status_code == 200
    assert response.json() == {"saved": True, "saved_keys": ["6057228515df6bd3:1", "6057228515df6bd3:2"]}
    assert saved == [(SESSION, payload["records"])]


def test_save_invalid_pair_returns_400(client, monkeypatch):
    async def fake_save(session_id, records):
        raise ValueError("One or more saved records do not exist")

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "save_result_records", fake_save)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")
    response = client.post("/saved-results", headers=AUTH, json={
        "session_id": SESSION,
        "records": [{"record_id": 1, "stable_row_key": "wrong:1"}],
    })
    assert response.status_code == 400


def test_remove_is_session_scoped(client, monkeypatch):
    removed = []

    async def fake_remove(session_id, keys):
        removed.append((session_id, keys))
        return len(keys)

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "remove_saved_result_records", fake_remove)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")
    response = client.request("DELETE", "/saved-results", headers=AUTH,
                              json={"session_id": SESSION, "stable_row_keys": ["k:1", "k:2"]})
    assert response.status_code == 200 and response.json()["saved"] is False
    assert removed == [(SESSION, ["k:1", "k:2"])]


def test_saved_list_returns_database_rows(client, monkeypatch):
    now = datetime.datetime(2026, 9, 27, tzinfo=datetime.timezone.utc)

    async def fake_list(session_id):
        assert session_id == SESSION
        return [row(1189, 1, now), row(1190, 2, now)]

    import app.routers.internal as internal
    monkeypatch.setattr(internal, "list_saved_result_records", fake_list)
    monkeypatch.setattr(settings, "db_feedback_url", "postgresql://stub")

    response = client.get("/saved-results", headers=AUTH, params={"session_id": SESSION})
    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [1189, 1190]
    assert items[0]["stable_row_key"] == "experiment-hash:1"
    assert items[0]["saved_at"].startswith("2026-09-27T")

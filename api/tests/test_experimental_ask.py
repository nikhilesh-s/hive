"""Grounded paper QA: evidence blocks carry statuses verbatim, retrieval is
table-pinned and DOI-filterable, the model is optional, and citations are
validated against the evidence actually shown."""
from __future__ import annotations

import asyncio

from app.config import settings
from app.experimental import ask
from fastapi.testclient import TestClient

from app.main import app

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}

ROWS = [
    {"id": 1, "paper_id": "10.3892/br.2026.2108", "doi": "10.3892/br.2026.2108", "target": "P-ERK 1/2",
     "canonical_target": "MAPK1/MAPK3", "protein_status": "AMBIGUOUS", "modification_status": "CONFLICTING",
     "modification_label": None, "experiment_type": None, "cell_line": "Hep3B", "organism": "human",
     "treatment_name": "IL-6", "dose": 10.0, "dose_unit": "ng/ml", "antibody_vendor": "Cell Signaling Technology",
     "antibody_catalog_number": "4370", "stable_row_key": "abc:1", "lane_condition": "0 min", "band_state": "uncertain",
     "needs_review": True, "page": 5,
     "anomaly_flags": [{"code": "MODIFICATION_CONFLICT", "severity": "high",
                        "detail": "Sources disagree on whether this is a modified or total protein."}]},
    {"id": 2, "paper_id": "10.3892/br.2026.2108", "doi": "10.3892/br.2026.2108", "target": "P-ERK 1/2",
     "canonical_target": "MAPK1/MAPK3", "modification_status": "CONFLICTING", "stable_row_key": "abc:2",
     "lane_condition": "5 min", "band_state": "present", "needs_review": True, "page": 5},
    {"id": 3, "paper_id": "10.1186/other", "doi": "10.1186/other", "target": "GAPDH", "canonical_target": "Gapdh",
     "protein_status": "SUPPORTED", "experiment_type": "loading_control", "organism": "mouse",
     "sample": "mouse SMG tissue", "stable_row_key": "def:1", "lane_condition": "L5d", "band_state": "present",
     "needs_review": False, "expected_molecular_weight_kda": 35.8, "page": 11},
]


def _run(c):
    return asyncio.run(c)


def test_evidence_blocks_group_lanes_and_carry_statuses():
    blocks = ask.evidence_blocks(ROWS)
    assert [b["headline"] for b in blocks] == ["MAPK1/MAPK3 · CONFLICTING (unresolved: phospho vs total)", "Gapdh"]
    erk = blocks[0]
    assert erk["lanes"] == 2 and "0 min=uncertain; 5 min=present" in erk["text"]
    assert "needs review: Sources disagree" in erk["text"] and "CST" not in erk["text"]
    assert "Cell Signaling Technology #4370" in erk["text"] and "IL-6 10.0 ng/ml" in erk["text"]
    assert "expected 35.8 kDa (UniProt)" in blocks[1]["text"] and "review=supported" in blocks[1]["text"]
    live = ask.evidence_blocks(ROWS[2:], "live_unreviewed")
    assert live[0]["text"].endswith("LIVE UNREVIEWED extraction")


def test_query_terms_keep_biology_drop_prose():
    q = "Is STAT3 phosphorylated at Tyr705 after IL-6 in Hep3B, and which antibody (CST) was used?"
    assert ask.query_terms(q) == ["phospho", "STAT3", "Tyr705", "IL-6", "Hep3B", "CST"]
    assert ask.query_terms("Does BEX2 co-immunoprecipitate with PIK3CA?") == ["BEX2", "PIK3CA"]
    assert ask.query_terms("loading controls in mouse submandibular gland") == ["loading control"]


def test_retrieve_backs_off_until_rows_appear(monkeypatch):
    seen = []

    async def fake_query(sql):
        seen.append(sql)
        return ROWS if "%after%" not in sql and "%Tyr705%" not in sql and "residue_position = 705" not in sql else []
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    blocks = _run(ask.retrieve("Is ERK phosphorylated at Tyr705 after IL-6?", None, include_live=False))
    assert blocks and len(seen) >= 2  # first AND-of-everything query was empty, back-off found rows


def test_retrieve_pins_tables_and_filters_doi(monkeypatch):
    seen = []

    async def fake_query(sql):
        seen.append(sql)
        return ROWS
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    blocks = _run(ask.retrieve("ERK", "10.1186/other", include_live=True))
    assert [b["doi"] for b in blocks] == ["10.1186/other", "10.1186/other"]  # reviewed + live copies
    assert any("FROM western_blot_records " in s for s in seen) and any("western_blot_records_live" in s for s in seen)
    blocks = _run(ask.retrieve("ERK", None, include_live=False))
    assert all(b["tier"] == "reviewed" for b in blocks) and len(blocks) == 2


def test_answer_without_model_returns_evidence_only(monkeypatch):
    async def fake_query(sql):
        return ROWS
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    out = _run(ask.answer("Is ERK phosphorylated after IL-6?", include_live=False))
    assert out["answer"] is None and "no model key" in out["note"]
    assert [b["ref"] for b in out["evidence"]] == ["E1", "E2"]


def test_answer_validates_citations(monkeypatch):
    async def fake_query(sql):
        return ROWS
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    prompts = {}

    def fake_llm(system, user):
        prompts["user"] = user
        return "The modification is unresolved: antibody says phospho, label says total [E1]. Also [E9].", "test-model"
    out = _run(ask.answer("Is ERK phosphorylated?", include_live=False, llm=fake_llm))
    assert out["cited"] == ["E1"] and out["model"] == "test-model" and out["note"] is None
    assert "target=MAPK1/MAPK3" in prompts["user"] and "QUESTION: Is ERK phosphorylated?" in prompts["user"]

    out = _run(ask.answer("Is ERK phosphorylated?", include_live=False, llm=lambda s, u: ("no cites", "m")))
    assert out["cited"] == [] and "without citing" in out["note"]

    def boom(s, u):
        raise RuntimeError("model declined to answer this question")
    out = _run(ask.answer("Is ERK phosphorylated?", include_live=False, llm=boom))
    assert out["answer"] is None and "declined" in out["note"]


def test_answer_with_no_evidence(monkeypatch):
    async def fake_query(sql):
        return []
    monkeypatch.setattr(ask, "run_readonly_query", fake_query)
    out = _run(ask.answer("BRCA1 in MCF7 with olaparib", include_live=False, llm=lambda s, u: ("x", "m")))
    assert out["evidence"] == [] and out["answer"] is None and "does not contain" in out["note"].lower() or "No matching" in out["note"]


def test_ask_route(monkeypatch):
    async def fake_answer(question, doi=None, include_live=True):
        return {"question": question, "doi": doi, "evidence": [], "answer": None, "cited": [], "model": None, "note": "n"}
    monkeypatch.setattr("app.experimental.router.ask_answer", fake_answer)
    with TestClient(app) as c:
        assert c.post("/experimental/ask", json={"question": "x?"}).status_code == 401
        r = c.post("/experimental/ask", json={"question": "Is STAT3 phosphorylated?", "doi": "10.3892/br.2026.2108"}, headers=AUTH)
        assert r.status_code == 200 and r.json()["doi"] == "10.3892/br.2026.2108"
        assert c.post("/experimental/ask", json={"question": "x"}, headers=AUTH).status_code == 422

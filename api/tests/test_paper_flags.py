import asyncio

from app import db, search_service
from app.schemas import WesternBlotRecord


def test_paper_flags_survive_public_response_shape():
    row = WesternBlotRecord(
        id=1,
        paper_id="paper",
        doi="10.1/example",
        paper_flags={
            "access_status": "open_access",
            "access_url": "https://example.org/paper.pdf",
            "relevance_status": "likely_relevant",
        },
    )
    assert row.paper_flags["access_status"] == "open_access"


def test_attach_paper_flags_matches_access_by_doi(monkeypatch):
    rows = [{"id": 1, "paper_id": "p", "doi": "10.1/example", "target": "STAT3"}]

    def fake_get(table, params):
        assert table == "ingest_jobs"
        return [{
            "doi": "10.1/example",
            "access_status": "open_access",
            "access_url": "https://example.org/open.pdf",
            "access_source": "unpaywall",
            "access_checked_at": "2026-10-02T00:00:00Z",
            "relevance_status": "likely_relevant",
            "relevance_score": 0.92,
            "relevance_reason": "mentions phospho STAT3 Tyr705",
            "relevance_checked_at": "2026-10-02T00:00:00Z",
            "discovery_query": "phospho STAT3 Tyr705",
            "updated_at": "2026-10-02T00:00:00Z",
            "created_at": "2026-10-01T00:00:00Z",
        }]

    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", fake_get)

    out = asyncio.run(db.attach_paper_flags(rows, "  Phospho   STAT3 Tyr705 "))
    assert out[0]["paper_flags"]["access_status"] == "open_access"
    assert out[0]["paper_flags"]["relevance_status"] == "likely_relevant"


def test_attach_paper_flags_omits_relevance_for_different_query(monkeypatch):
    rows = [{"id": 1, "paper_id": "p", "doi": "10.1/example", "target": "STAT3"}]

    def fake_get(table, params):
        return [{
            "doi": "10.1/example",
            "access_status": "no_open_copy_found",
            "access_url": None,
            "access_source": "unpaywall",
            "access_checked_at": "2026-10-02T00:00:00Z",
            "relevance_status": "low_relevance",
            "relevance_score": 0.1,
            "relevance_reason": "different campaign query",
            "relevance_checked_at": "2026-10-02T00:00:00Z",
            "discovery_query": "EGFR",
            "updated_at": "2026-10-02T00:00:00Z",
            "created_at": "2026-10-01T00:00:00Z",
        }]

    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", fake_get)

    out = asyncio.run(db.attach_paper_flags(rows, "phospho STAT3 Tyr705"))
    assert out[0]["paper_flags"]["access_status"] == "no_open_copy_found"
    assert "relevance_status" not in out[0]["paper_flags"]


def test_attach_paper_flags_leaves_unmatched_rows_unchanged(monkeypatch):
    rows = [{"id": 1, "paper_id": "p", "doi": "10.1/no-match", "target": "STAT3"}]
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", lambda table, params: [])
    out = asyncio.run(db.attach_paper_flags(rows, "STAT3"))
    assert "paper_flags" not in out[0]


def test_search_service_keeps_scientific_identity_and_adds_flags(monkeypatch):
    rows = [{
        "id": 1,
        "paper_id": "p",
        "doi": "10.1/example",
        "target": "STAT3",
        "stable_row_key": "exp:1",
        "needs_review": False,
    }]

    async def fake_query(sql):
        return rows

    async def fake_attach(results, query):
        results[0]["paper_flags"] = {"access_status": "open_access"}
        return results

    monkeypatch.setattr(search_service, "run_readonly_query", fake_query)
    monkeypatch.setattr(search_service, "attach_paper_flags", fake_attach)
    monkeypatch.setattr(search_service.settings, "supabase_url", "")
    monkeypatch.setattr(search_service.settings, "supabase_api_key", "")

    out = asyncio.run(search_service.execute_search("STAT3", 10))
    assert out.results[0].experiment_key
    assert out.results[0].needs_review is False
    assert out.results[0].paper_flags == {"access_status": "open_access"}

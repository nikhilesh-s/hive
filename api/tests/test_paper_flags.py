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
    assert out[0]["paper_flags"] == {"access_status": "unknown"}


def test_newer_relevance_only_run_preserves_access_and_uses_matching_query(monkeypatch):
    jobs = [
        {"doi": "10.1/example", "access_status": "open_access", "access_source": "openalex",
         "access_checked_at": "2026-10-01T00:00:00Z"},
        {"doi": "10.1/example", "relevance_status": "likely_relevant", "discovery_query": "STAT3",
         "relevance_checked_at": "2026-10-03T00:00:00Z"},
        {"doi": "10.1/example", "relevance_status": "low_relevance", "discovery_query": "other",
         "relevance_checked_at": "2026-10-04T00:00:00Z"},
    ]
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", lambda *args: jobs)
    flags = asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "STAT3"))[0]["paper_flags"]
    assert flags["access_status"] == "open_access"
    assert flags["relevance_status"] == "likely_relevant"


def test_latest_access_check_can_explicitly_be_unknown(monkeypatch):
    jobs = [
        {"doi": "10.1/example", "access_status": "open_access", "access_checked_at": "2026-10-01"},
        {"doi": "10.1/example", "access_status": "unknown", "access_checked_at": "2026-10-03"},
    ]
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", lambda *args: jobs)
    assert asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "STAT3"))[0]["paper_flags"]["access_status"] == "unknown"


def test_lookup_failure_or_absent_doi_does_not_imply_restricted_access(monkeypatch):
    def broken(*args):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", broken)
    rows = asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}, {"doi": None}], "STAT3"))
    assert all(row["paper_flags"] == {"access_status": "unknown"} for row in rows)


def test_unverified_job_cannot_set_access_or_relevance_label(monkeypatch):
    # Jobs stored before W-4 may carry caller-supplied access/relevance with checked_at NULL.
    jobs = [
        {"job_id": "a", "doi": "10.1/example", "access_status": "open_access",
         "access_url": "https://evil.example/x", "access_checked_at": None,
         "relevance_status": "likely_relevant", "discovery_query": "STAT3", "relevance_checked_at": None},
    ]
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", lambda *args: jobs)
    flags = asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "STAT3"))[0]["paper_flags"]
    assert flags == {"access_status": "unknown"}

    # A verified older check still wins over a newer unverified claim.
    jobs.append({"job_id": "b", "doi": "10.1/example", "access_status": "no_open_copy_found",
                 "access_checked_at": "2026-10-01T00:00:00Z"})
    flags = asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "STAT3"))[0]["paper_flags"]
    assert flags["access_status"] == "no_open_copy_found"
    assert "relevance_status" not in flags


def test_latest_check_compares_timestamps_not_strings_and_ties_break_by_job_id(monkeypatch):
    from datetime import datetime, timezone
    jobs = [
        {"job_id": "a", "doi": "10.1/example", "access_status": "open_access",
         "access_checked_at": "2026-10-03T00:00:00Z"},
        # Later instant, passed as a datetime object (asyncpg path) next to a string.
        {"job_id": "b", "doi": "10.1/example", "access_status": "no_open_copy_found",
         "access_checked_at": datetime(2026, 10, 3, 1, tzinfo=timezone.utc)},
    ]
    monkeypatch.setattr(db, "_use_supabase_rest", lambda: True)
    monkeypatch.setattr(db, "_supabase_get", lambda *args: jobs)
    assert asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "q"))[0]["paper_flags"]["access_status"] == "no_open_copy_found"

    jobs[1]["access_checked_at"] = "2026-10-03T00:00:00+00:00"  # same instant, different spelling
    assert asyncio.run(db.attach_paper_flags([{"doi": "10.1/example"}], "q"))[0]["paper_flags"]["access_status"] == "no_open_copy_found"


def test_pg_in_quotes_values_with_postgrest_metacharacters():
    assert db._pg_in(["10.1/a,b", "10.1/(x)", 7]) == 'in.("10.1/a,b","10.1/(x)","7")'
    assert db._pg_in(['a"b', "c\\d"]) == 'in.("a\\"b","c\\\\d")'


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


def test_live_search_also_exposes_stored_paper_access(monkeypatch):
    async def query(sql):
        return [{"id": 1, "paper_id": "p", "doi": "10.1/example", "target": "STAT3"}]
    async def attach(rows, query):
        rows[0]["paper_flags"] = {"access_status": "no_open_copy_found"}
        return rows
    monkeypatch.setattr(search_service, "run_readonly_query", query)
    monkeypatch.setattr(search_service, "attach_paper_flags", attach)
    monkeypatch.setattr(search_service.settings, "supabase_url", "")
    monkeypatch.setattr(search_service.settings, "supabase_api_key", "")
    out = asyncio.run(search_service.execute_search("STAT3", 10, search_service.settings.live_table_name))
    assert out.results[0].paper_flags["access_status"] == "no_open_copy_found"
    assert out.results[0].experiment_key is None

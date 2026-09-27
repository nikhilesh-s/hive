"""EXPERIMENTAL live ingestion: Valency client, DOI/full-text helpers, the
job state machine, the table-pinned search guard, and the routes. Every
external dependency (Valency, NCBI, Unpaywall, the extraction pipeline, the
database) is stubbed; nothing here touches the network or the corpus."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import valency
from app.config import settings
from app.experimental import ingest
from app.main import app
from app.sql_guard import SQLGuardError, guard_and_limit_sql
from app.bio_query import generate_bio_sql

from western_blot_miner import fulltext  # noqa: E402  (ingest put the repo root on sys.path)

AUTH = {"Authorization": f"Bearer {settings.internal_api_key}"}


# --- Valency ----------------------------------------------------------------

def _fake_valency(tool_props, papers):
    """A JSON-RPC transport that behaves like Valency Bond's MCP server."""
    calls = []

    def transport(payload):
        calls.append(payload)
        m = payload["method"]
        if m == "initialize":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"serverInfo": {"name": "valency"}}}
        if m == "tools/list":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": [
                {"name": "semantic_search_papers", "inputSchema": {"properties": tool_props}}]}}
        if m == "tools/call":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {
                "content": [{"type": "text", "text": json.dumps({"papers": papers})}]}}
        return {"jsonrpc": "2.0", "id": payload["id"], "error": {"code": -1, "message": "nope"}}

    return transport, calls


def test_valency_adapts_argument_names_and_normalizes():
    transport, calls = _fake_valency(
        {"q": {"type": "string"}, "top_k": {"type": "integer"}},
        [{"title": "STAT3 in HCC", "authors": "A Jang, B Kim", "doi": "10.3892/BR.2026.2108",
          "published": "2026-01-02", "journal": "Biomed Rep"}])
    c = valency.ValencyClient("tok", transport=transport)
    out = c.search_papers("phospho STAT3 hepatoma", limit=5)
    call = [p for p in calls if p["method"] == "tools/call"][0]
    assert call["params"] == {"name": "semantic_search_papers", "arguments": {"q": "phospho STAT3 hepatoma", "top_k": 5}}
    assert out[0]["doi"] == "10.3892/br.2026.2108" and out[0]["year"] == "2026"
    assert out[0]["authors"] == ["A Jang", "B Kim"] and out[0]["source"].startswith("valency:")


def test_valency_rpc_error_surfaces():
    def transport(payload):
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": 401, "message": "bad token"}}
    with pytest.raises(valency.ValencyError):
        valency.ValencyClient("tok", transport=transport).list_tools()


def test_valency_parses_sse_body():
    body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n'
    assert valency._parse_body(body, "text/event-stream")["result"] == {"tools": []}


def test_valency_requires_token_without_transport():
    with pytest.raises(valency.ValencyError):
        valency.ValencyClient("")


# --- full text helpers ------------------------------------------------------

def test_normalize_doi_forms():
    assert fulltext.normalize_doi("https://doi.org/10.3892/BR.2026.2108") == "10.3892/br.2026.2108"
    assert fulltext.normalize_doi("doi:10.1186/s12964-025-02385-8.") == "10.1186/s12964-025-02385-8"
    assert fulltext.normalize_doi("not a doi") == ""


def test_fetch_pdf_prefers_europepmc_listing_then_unpaywall(monkeypatch, tmp_path):
    class R:
        def __init__(self, status, content=b"", js=None, headers=None):
            self.status_code, self.content, self._js, self.headers = status, content, js, headers or {}
            self.text = content.decode("latin1") if content else ""
        def json(self):
            return self._js

    def epmc(pmcid, pdf):
        return R(200, js={"resultList": {"result": [{"pmcid": pmcid, "isOpenAccess": "Y", "title": "T",
                 "fullTextUrlList": {"fullTextUrl": ([{"documentStyle": "pdf", "url": pdf}] if pdf else [])}}]}})

    calls = []

    def fake_get(url, params=None, timeout=None, allow_redirects=True, headers=None):
        calls.append(url)
        if "idconv" in url:
            return R(200, js={"records": [{"requested-id": "10.1000/abc", "doi": "10.1000/ABC", "pmid": "1", "pmcid": "PMC9"}]})
        if url.endswith("PMC9?pdf=render"):
            return R(200, content=b"\n%PDF-1.4 fake")        # marker not at byte 0 is still a PDF
        raise AssertionError(url)

    monkeypatch.setattr(fulltext.requests, "get", fake_get)
    got = fulltext.fetch_pdf("10.1000/abc", tmp_path)
    assert got["source"] == "europepmc" and Path(got["pdf_path"]).name == "PMC9.pdf" and got["tried"] == ["europepmc_render"]

    # No Europe PMC PDF listed -> legacy endpoint 404 -> Unpaywall locations (needs a real contact email)
    monkeypatch.setenv("UNPAYWALL_EMAIL", "someone@ucsf.edu")

    def fake_get2(url, params=None, timeout=None, allow_redirects=True, headers=None):
        if "idconv" in url:
            return R(200, js={"records": [{"requested-id": "10.1000/xyz", "doi": "10.1000/xyz", "pmcid": "PMC10"}]})
        if url.endswith("PMC10?pdf=render"):
            return R(404, content=b'{"error":"no pdf"}')
        if "europepmc/webservices/rest/search" in url:
            return epmc("PMC10", "https://pub.example/listed.pdf")
        if url == "https://pub.example/listed.pdf":
            return R(200, content=b"<html>bot check</html>")        # publisher blocks scripts -> not a PDF
        if url.endswith("PMC10/fullTextPDF"):
            return R(404)
        if "openalex" in url:
            return R(200, js={"best_oa_location": None, "locations": []})
        if "unpaywall" in url:
            return R(200, js={"best_oa_location": {"url_for_pdf": "https://pub.example/p.pdf", "host_type": "publisher"},
                              "oa_locations": [{"url_for_pdf": "https://repo.example/p.pdf", "host_type": "repository"}]})
        if url == "https://pub.example/p.pdf":
            return R(200, content=b"<html>bot check</html>")        # publisher blocks scripts -> not a PDF
        if url == "https://repo.example/p.pdf":
            return R(200, content=b"%PDF-1.7 x")
        raise AssertionError(url)

    monkeypatch.setattr(fulltext.requests, "get", fake_get2)
    got = fulltext.fetch_pdf("10.1000/xyz", tmp_path)
    assert got["source"] == "unpaywall:repository" and got["pdf_path"].endswith("10.1000_xyz.pdf")
    assert got["tried"] == ["europepmc_render", "europepmc_listed_pdf", "europepmc_legacy", "openalex", "unpaywall"]

    # Placeholder contact email => Unpaywall is skipped, never called with a fake address
    monkeypatch.setenv("UNPAYWALL_EMAIL", "western-blot-miner@example.com")
    monkeypatch.setattr(fulltext.requests, "get",
                        lambda url, **k: R(200, js={"records": [{"requested-id": "10.1000/none", "doi": "10.1000/none"}]}) if "idconv" in url
                        else R(404))
    got = fulltext.fetch_pdf("10.1000/none", tmp_path)
    assert got["pdf_path"] is None and "unpaywall_skipped_no_contact_email" in got["tried"]


def test_fetch_pdf_falls_back_to_openalex_when_pmc_blocks_scripts(monkeypatch, tmp_path):
    """Europe PMC answers 403 to scripted PDF requests (observed 2026-09-20);
    the publisher's own OA PDF, found through OpenAlex, still works and needs
    no contact email."""
    class R:
        def __init__(self, status, content=b"", js=None):
            self.status_code, self.content, self._js, self.headers = status, content, js, {}
        def json(self):
            return self._js

    monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)

    def fake_get(url, params=None, timeout=None, allow_redirects=True, headers=None):
        if "idconv" in url:
            return R(200, js={"records": [{"requested-id": "10.1000/oa", "doi": "10.1000/oa", "pmcid": "PMC11"}]})
        if url.endswith("PMC11?pdf=render") or url.endswith("PMC11/fullTextPDF"):
            return R(403, content=b"<!DOCTYPE html>blocked")
        if "europepmc/webservices/rest/search" in url:
            return R(200, js={"resultList": {"result": []}})
        if "openalex" in url:
            return R(200, js={"best_oa_location": {"pdf_url": "https://pub.example/blocked.pdf"},
                              "locations": [{"pdf_url": "https://pub.example/blocked.pdf"},
                                            {"pdf_url": "https://pub.example/real.pdf"}]})
        if url == "https://pub.example/blocked.pdf":
            return R(200, content=b"<html>bot check</html>")
        if url == "https://pub.example/real.pdf":
            return R(200, content=b"%PDF-1.7 real")
        raise AssertionError(url)

    monkeypatch.setattr(fulltext.requests, "get", fake_get)
    got = fulltext.fetch_pdf("10.1000/oa", tmp_path)
    assert got["source"] == "openalex" and got["pdf_path"].endswith("10.1000_oa.pdf")
    assert got["tried"] == ["europepmc_render", "europepmc_legacy", "openalex"]


def test_download_retries_rate_limits_then_gives_up(monkeypatch, tmp_path):
    seen = []

    class R:
        def __init__(self, status, content):
            self.status_code, self.content, self.headers = status, content, {}

    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(fulltext.requests, "get", lambda url, **k: (seen.append(url), R(200, b"Rate limit exceeded"))[1])
    assert fulltext._download("https://x/pdf", tmp_path / "x.pdf") is None and len(seen) == fulltext.RETRIES


def test_annotate_oa_pdf_marks_extractable_papers(monkeypatch):
    monkeypatch.setattr(fulltext, "resolve_ids_batch", lambda dois, timeout=60: {"10.1000/a": {"pmcid": "PMC1"}})
    monkeypatch.setattr(fulltext, "europepmc_fulltext", lambda ids, timeout=60: {"PMC1": {"is_oa": True, "pdf_url": None}})
    papers = fulltext.annotate_oa_pdf([{"doi": "10.1000/a"}, {"doi": "10.1000/b"}, {"doi": None}])
    assert papers[0]["pmcid"] == "PMC1" and papers[0]["oa_pdf"] is True
    assert papers[1]["oa_pdf"] is False and papers[2]["oa_pdf"] is False


# --- route boundaries -------------------------------------------------------

def test_oversized_record_id_is_a_validation_error_not_a_500():
    big = "99999999999999999999"
    with TestClient(app) as c:
        for path in (f"/experimental/records/{big}", f"/experimental/records/{big}/crop",
                     f"/records/{big}", f"/records/{big}/crop", f"/records/{big}/feedback", "/experimental/records/0"):
            assert c.get(path, headers=AUTH).status_code == 422, path
        for path in ("/experimental-densitometry", "/experimental-densitometry/pair"):
            assert c.post(path, json={"record_id": int(big)}, headers=AUTH).status_code == 422, path


def test_delete_job_needs_the_ingest_db_and_a_finished_job(monkeypatch):
    deleted = []

    async def fake_delete(job_id):
        deleted.append(job_id)
        return 3
    monkeypatch.setattr("app.experimental.router.delete_live_job", fake_delete)
    job = ingest.start_job("10.3892/br.2026.2108")
    with TestClient(app) as c:
        monkeypatch.setattr(settings, "db_ingest_url", None)
        assert c.delete(f"/experimental/ingest/{job.job_id}", headers=AUTH).status_code == 503
        monkeypatch.setattr(settings, "db_ingest_url", "postgresql://hive_ingest:x@localhost/x")
        job.status = "extracting"   # a running job would re-insert its rows after the delete
        assert c.delete(f"/experimental/ingest/{job.job_id}", headers=AUTH).status_code == 409
        assert deleted == []
        job.status = "done"
        r = c.delete(f"/experimental/ingest/{job.job_id}", headers=AUTH)
        assert r.status_code == 200 and r.json()["rows_deleted"] == 3 and deleted == [job.job_id]


def test_job_status_survives_an_api_restart(monkeypatch):
    async def stored(limit=20):
        return [{"job_id": "abc123def", "doi": "10.1/x", "status": "done", "created_at": "2026-09-15T10:00:00"}]
    monkeypatch.setattr("app.experimental.router.list_ingest_jobs", stored)
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://hive_ingest:x@localhost/x")
    with TestClient(app) as c:
        r = c.get("/experimental/ingest/abc123def", headers=AUTH)
        assert r.status_code == 200 and r.json()["status"] == "done"
        assert c.get("/experimental/ingest/nope12345", headers=AUTH).status_code == 404


# --- search guard pinned to the live table ----------------------------------

def test_live_search_is_pinned_to_the_live_table():
    sql = generate_bio_sql("GAPDH mouse", "western_blot_records_live")
    assert "FROM western_blot_records_live" in sql
    guarded = guard_and_limit_sql(sql, 50, "western_blot_records_live")
    assert "western_blot_records_live" in guarded and "LIMIT 50" in guarded
    with pytest.raises(SQLGuardError):  # a live query may not read the reviewed table
        guard_and_limit_sql("SELECT * FROM western_blot_records", 10, "western_blot_records_live")
    with pytest.raises(SQLGuardError):  # and the default guard still refuses the live table
        guard_and_limit_sql(sql, 10)


# --- job state machine ------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def test_job_fails_fast_without_a_model_backend(monkeypatch):
    monkeypatch.delenv("WBM_LLM_BACKEND", raising=False)
    job = ingest.start_job("10.3892/br.2026.2108")
    _run(ingest.run_job(job.job_id))
    assert job.status == "failed" and "model" in job.error.lower()


def test_job_fails_cleanly_when_no_open_access_pdf(monkeypatch):
    monkeypatch.setenv("WBM_LLM_BACKEND", "mock")
    monkeypatch.setattr(ingest.fulltext, "fetch_pdf", lambda doi, out: {"pdf_path": None, "pmcid": None})
    job = ingest.start_job("10.1000/closed")
    _run(ingest.run_job(job.job_id))
    assert job.status == "failed" and "open-access" in job.error


def test_job_runs_the_pipeline_and_loads_live_rows(monkeypatch, tmp_path):
    monkeypatch.setenv("WBM_LLM_BACKEND", "mock")
    run_dir = tmp_path / "run"
    (run_dir / "panel_candidates").mkdir(parents=True)
    crop = run_dir / "panel_candidates" / "page_003_cand_0001.png"
    crop.write_bytes(b"\x89PNG fake")
    rows_path = run_dir / "supabase_rows.json"
    rows_path.write_text(json.dumps([
        {"paper_id": "10.1000/abc", "target": "STAT3", "image_crop_ref": str(crop), "provenance": {"x": 1}},
        {"paper_id": "10.1000/abc", "target": "ACTB", "image_crop_ref": str(crop)},
    ]))
    monkeypatch.setattr(ingest.fulltext, "fetch_pdf",
                        lambda doi, out: {"pdf_path": str(tmp_path / "p.pdf"), "pmcid": "PMC1"})
    monkeypatch.setattr(ingest.pdf_preprocess, "preprocess_pdf",
                        lambda pdf, paper_id=None: {"paper_id": paper_id, "out_dir": str(run_dir),
                                                    "llm_candidate_count": 1})
    monkeypatch.setattr(ingest.pipeline, "run_records_stage",
                        lambda summary, use_cache: {"records": 1, "rows_path": str(rows_path)})
    captured = {}

    async def fake_replace(doi, job_id, rows, crops, jsonb_cols):
        captured.update(doi=doi, job_id=job_id, rows=rows, crops=crops)
        return len(rows)

    monkeypatch.setattr(ingest.db, "replace_live_rows", fake_replace)
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://hive_ingest:x@localhost/x")
    job = ingest.start_job("https://doi.org/10.1000/ABC")
    _run(ingest.run_job(job.job_id))
    assert job.status == "done", job.error
    assert job.doi == "10.1000/abc" and job.pmcid == "PMC1" and job.candidates == 1 and job.rows == 2
    assert captured["doi"] == "10.1000/abc" and set(captured["crops"]) == {"page_003_cand_0001.png"}
    for r in captured["rows"]:
        assert r["image_crop_ref"] == "page_003_cand_0001.png"   # filename only, never a path
        assert r["review_tier"] == "live_unreviewed" and r["job_id"] == job.job_id and r["doi"] == "10.1000/abc"


def test_job_reuse_loads_previous_run_without_model(monkeypatch, tmp_path):
    monkeypatch.delenv("WBM_LLM_BACKEND", raising=False)
    monkeypatch.setattr(ingest, "run_dir_for", lambda doi: tmp_path)
    (tmp_path / "supabase_rows.json").write_text(json.dumps([
        {"paper_id": "10.1000/abc", "target": "LC3B", "stable_row_key": "h1:1", "image_crop_ref": "x.png"},
        {"paper_id": "10.1000/abc", "target": "LC3B", "stable_row_key": "h1:2", "image_crop_ref": "x.png"}]))
    captured = {}

    async def fake_replace(doi, job_id, rows, crops, jsonb_cols):
        captured.update(rows=rows)
        return len(rows)
    monkeypatch.setattr(ingest.db, "replace_live_rows", fake_replace)
    monkeypatch.setattr(settings, "db_ingest_url", "postgresql://hive_ingest:x@localhost/x")
    job = ingest.start_job("10.1000/abc", reuse=True)
    _run(ingest.run_job(job.job_id))
    assert job.status == "done" and job.backend == "reuse" and job.rows == 2 and job.records == 1
    assert all(r["review_tier"] == "live_unreviewed" for r in captured["rows"])


# --- routes -----------------------------------------------------------------

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_experimental_routes_require_internal_key(client):
    assert client.get("/experimental/status").status_code == 401
    assert client.post("/experimental/ingest", json={"doi": "10.1000/x"}).status_code == 401


def test_ingest_returns_503_without_model_backend(client, monkeypatch):
    monkeypatch.delenv("WBM_LLM_BACKEND", raising=False)
    r = client.post("/experimental/ingest", json={"doi": "10.3892/br.2026.2108"}, headers=AUTH)
    assert r.status_code == 503 and "model" in r.json()["detail"].lower()


def test_ingest_rejects_non_doi(client, monkeypatch):
    monkeypatch.setenv("WBM_LLM_BACKEND", "mock")
    r = client.post("/experimental/ingest", json={"doi": "not-a-doi"}, headers=AUTH)
    assert r.status_code == 400


def test_papers_search_falls_back_to_pmc(client, monkeypatch):
    monkeypatch.setattr(settings, "valency_api_token", "")
    monkeypatch.setattr(ingest.fulltext, "pmc_search",
                        lambda q, limit: [{"title": "T", "doi": "10.1000/t", "source": "pmc"}])
    r = client.post("/experimental/papers/search", json={"query": "STAT3 western"}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["sources_used"] == ["pmc"] and body["results"][0]["doi"] == "10.1000/t"


def test_papers_search_reports_valency_failure_but_still_answers(client, monkeypatch):
    monkeypatch.setattr(settings, "valency_api_token", "tok")

    class Boom(valency.ValencyClient):
        def __init__(self, *a, **k):
            pass
        def search_papers(self, q, limit):
            raise valency.ValencyError("token rejected")

    monkeypatch.setattr("app.experimental.router.ValencyClient", Boom)
    monkeypatch.setattr(ingest.fulltext, "pmc_search", lambda q, limit: [])
    r = client.post("/experimental/papers/search", json={"query": "STAT3"}, headers=AUTH)
    assert r.status_code == 200 and "token rejected" in r.json()["errors"]["valency"]


def test_fetch_pdf_reads_the_publisher_page_only_for_open_access(monkeypatch, tmp_path):
    """OpenAlex often marks a paper OA without a direct PDF link (PLOS, Nature,
    microPublication); the publisher's citation_pdf_url tag names it. A
    paywalled paper never reaches the publisher page."""
    class R:
        def __init__(self, status, content=b"", js=None, text=""):
            self.status_code, self.content, self._js, self.text, self.headers = status, content, js, text, {}
        def json(self):
            return self._js

    monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
    is_oa = {"v": True}

    def fake_get(url, params=None, timeout=None, allow_redirects=True, headers=None):
        if "idconv" in url:
            return R(200, js={"records": [{"requested-id": "10.1000/pl", "doi": "10.1000/pl"}]})
        if "openalex" in url:
            return R(200, js={"open_access": {"is_oa": is_oa["v"]}, "best_oa_location": {"pdf_url": None},
                              "locations": [{"pdf_url": None}]})
        if url == "https://doi.org/10.1000/pl":
            return R(200, text='<meta name="citation_pdf_url" content="https://pub.example/pl.pdf">')
        if url == "https://pub.example/pl.pdf":
            return R(200, content=b"%PDF-1.7 pub")
        raise AssertionError(url)

    monkeypatch.setattr(fulltext.requests, "get", fake_get)
    got = fulltext.fetch_pdf("10.1000/pl", tmp_path / "a")
    assert got["source"] == "publisher_landing" and got["tried"] == ["openalex", "publisher_landing"]

    is_oa["v"] = False
    got = fulltext.fetch_pdf("10.1000/pl", tmp_path / "b")
    assert got["pdf_path"] is None and "publisher_landing" not in got["tried"]

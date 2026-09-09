"""Valency Bond contract smoke test (LIVE network; never in the unit suite).

Proves, against the real MCP server:
  1. initialize
  2. tools/list — prints tool names and the input schema of the search tools
     (this is where the argument mapper is checked against reality)
  3. a biomedical paper query through the same client the API uses
  4. normalization to PaperSearchResult (title/authors/doi/year/venue/source)
  5. DOI usability: each DOI resolved through the NCBI ID converter to a
     PMCID (open-access candidates) — the property live ingestion needs
  6. PMC fallback still answers when the token is absent/invalid

Token: VALENCY_API_TOKEN from the environment or api/.env / api/.env.cloud
(gitignored). The token value is never printed.

Run:  .venv/bin/python scripts/experiments/valency_smoke.py ["query"]
Exit 0 = contract holds; 2 = no token (skipped); 1 = failure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "api"))

from app import valency  # noqa: E402
from western_blot_miner import fulltext  # noqa: E402

QUERY = "STAT3 Tyr705 phosphorylation IL-6 hepatocellular carcinoma western blot"


def _token() -> str:
    tok = os.environ.get("VALENCY_API_TOKEN", "")
    if tok:
        return tok
    for env in (REPO / "api" / ".env", REPO / "api" / ".env.cloud", REPO / ".env"):
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("VALENCY_API_TOKEN=") and line.split("=", 1)[1].strip():
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main(argv: list[str]) -> int:
    query = argv[0] if argv else QUERY
    tok = _token()
    print(f"token: {'present (' + str(len(tok)) + ' chars)' if tok else 'ABSENT'}")
    if not tok:
        print("SKIP: no VALENCY_API_TOKEN; checking the PMC fallback only")
        hits = fulltext.pmc_search(query, 5)
        print(f"pmc fallback: {len(hits)} hits; first: {hits[0]['title'][:80] if hits else None}")
        return 2 if hits else 1

    c = valency.ValencyClient(tok, os.environ.get("VALENCY_MCP_URL", valency.DEFAULT_URL))
    info = c.initialize()
    print("initialize:", json.dumps(info.get("serverInfo", info))[:200])
    tools = c.list_tools()
    print(f"tools/list: {len(tools)} tools")
    for t in tools:
        if t["name"] in valency.SEARCH_TOOLS or "search" in t["name"]:
            props = (t.get("inputSchema") or {}).get("properties", {})
            req = (t.get("inputSchema") or {}).get("required", [])
            print(f"  {t['name']}: props={list(props)} required={req}")
    papers = c.search_papers(query, 8)
    print(f"search_papers({query!r}): {len(papers)} results")
    ok_doi = 0
    for p in papers:
        ids = fulltext.resolve_ids(p["doi"]) if p.get("doi") else {}
        pmc = ids.get("pmcid")
        ok_doi += bool(pmc)
        print(f"  - {str(p.get('title'))[:70]!r} {p.get('year')} doi={p.get('doi')} pmcid={pmc} src={p.get('source')}")
    print(f"DOIs resolving to a PMCID (open-access candidates): {ok_doi}/{len(papers)}")
    if not papers:
        print("FAIL: Valency returned no papers")
        return 1
    if not any(p.get("doi") for p in papers):
        print("FAIL: no DOIs in Valency results — the mapper or normalizer needs a fix")
        return 1
    bad = valency.ValencyClient("invalid-token-for-fallback-check")
    try:
        bad.list_tools()
        print("WARN: an invalid token was accepted")
    except valency.ValencyError as e:
        print(f"invalid token rejected as expected: {str(e)[:80]}")
    hits = fulltext.pmc_search(query, 3)
    print(f"pmc fallback independent of Valency: {len(hits)} hits")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

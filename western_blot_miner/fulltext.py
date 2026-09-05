"""Open-access full text by DOI / PMCID, plus a PMC discovery search.

Ported from AGeneTic's ``src/search/pdf_download.py`` (same legal-source
policy): a paper is only downloaded from an open-access location —
Europe PMC's PDF for a PMCID, else Unpaywall's best OA location for the DOI.
Papers with no open-access full text return ``None``; they are never scraped.

    ids  = resolve_ids("10.3892/br.2026.2108")        # {pmcid, pmid, doi}
    path = fetch_pdf("10.3892/br.2026.2108", out_dir)  # cached by DOI

Discovery fallback (no Valency token needed): ``pmc_search(query)`` returns
PubMed Central hits with title / year / DOI / PMCID via NCBI E-utilities.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests

from . import config

logger = logging.getLogger(__name__)

ID_CONVERTER = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
EUROPEPMC_PDF = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextPDF"
UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"
DEFAULT_TIMEOUT = 60
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    """'https://doi.org/10.1/ABC' / 'doi:10.1/abc' -> '10.1/abc' (DOIs are case-insensitive)."""
    m = _DOI_RE.search((value or "").strip())
    return m.group(0).rstrip(".,;)") .lower() if m else ""


def _email() -> str:
    return os.environ.get("UNPAYWALL_EMAIL") or config.NCBI_EMAIL


def _is_pdf(content: bytes) -> bool:
    return content[:5].startswith(b"%PDF")


def _download(url: str, dest: Path, timeout: int = DEFAULT_TIMEOUT, params: dict | None = None) -> Optional[str]:
    """GET ``url``; save to ``dest`` only if the body is a real PDF."""
    if dest.exists() and dest.stat().st_size > 0:
        return str(dest.resolve())
    try:
        resp = requests.get(url, params=params, timeout=timeout, allow_redirects=True,
                            headers={"User-Agent": f"{config.NCBI_TOOL} (mailto:{_email()})"})
    except requests.RequestException as error:
        logger.debug("download failed %s: %s", url, error)
        return None
    if resp.status_code != 200 or not resp.content or not _is_pdf(resp.content):
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return str(dest.resolve())


def resolve_ids(identifier: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """DOI / PMID / PMCID -> {doi, pmid, pmcid} via the NCBI ID converter (empty on failure)."""
    params = {"ids": identifier, "format": "json", "tool": config.NCBI_TOOL, "email": _email()}
    try:
        resp = requests.get(ID_CONVERTER, params=params, timeout=timeout)
        records = resp.json().get("records", []) if resp.status_code == 200 else []
    except (requests.RequestException, ValueError) as error:
        logger.debug("idconv failed for %s: %s", identifier, error)
        return {}
    if not records or records[0].get("status") == "error":
        return {}
    rec = records[0]
    return {"doi": (rec.get("doi") or "").lower() or None, "pmid": rec.get("pmid"), "pmcid": rec.get("pmcid")}


def fetch_pdf(doi: str, out_dir: str | Path, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """DOI -> open-access PDF on disk. Returns {pdf_path|None, pmcid, pmid, doi, source}."""
    doi = normalize_doi(doi)
    out_dir = Path(out_dir)
    ids = resolve_ids(doi, timeout) if doi else {}
    pmcid = ids.get("pmcid")
    result = {"doi": doi, "pmid": ids.get("pmid"), "pmcid": pmcid, "pdf_path": None, "source": None}
    if pmcid:
        path = _download(EUROPEPMC_PDF.format(pmcid=pmcid), out_dir / f"{pmcid}.pdf", timeout)
        if path:
            result.update(pdf_path=path, source="europepmc")
            return result
    if doi:
        try:
            resp = requests.get(UNPAYWALL.format(doi=doi), params={"email": _email()}, timeout=timeout)
            data = resp.json() if resp.status_code == 200 else {}
        except (requests.RequestException, ValueError) as error:
            logger.debug("unpaywall failed for %s: %s", doi, error)
            data = {}
        pdf_url = (data.get("best_oa_location") or {}).get("url_for_pdf")
        if pdf_url:
            path = _download(pdf_url, out_dir / f"{doi.replace('/', '_')}.pdf", timeout)
            if path:
                result.update(pdf_path=path, source="unpaywall")
    return result


def pmc_search(query: str, limit: int = 10, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """PubMed Central open-access discovery: normalized {title, authors, year, doi, pmcid, venue, source}."""
    base = {"tool": config.NCBI_TOOL, "email": _email()}
    if config.NCBI_API_KEY:
        base["api_key"] = config.NCBI_API_KEY
    try:
        r = requests.get(f"{config.EUTILS}/esearch.fcgi", timeout=timeout, params={
            **base, "db": "pmc", "retmode": "json", "retmax": limit, "sort": "relevance",
            "term": f"({query}) AND open access[filter]"})
        ids = r.json().get("esearchresult", {}).get("idlist", []) if r.status_code == 200 else []
        if not ids:
            return []
        s = requests.get(f"{config.EUTILS}/esummary.fcgi", timeout=timeout, params={
            **base, "db": "pmc", "retmode": "json", "id": ",".join(ids)})
        summ = s.json().get("result", {}) if s.status_code == 200 else {}
    except (requests.RequestException, ValueError) as error:
        logger.debug("pmc search failed: %s", error)
        return []
    out = []
    for pid in ids:
        d = summ.get(pid) or {}
        art = {a.get("idtype"): a.get("value") for a in d.get("articleids", []) if isinstance(a, dict)}
        out.append({
            "title": d.get("title"), "authors": [a.get("name") for a in d.get("authors", []) if isinstance(a, dict)][:6],
            "year": (d.get("pubdate") or "")[:4] or None, "doi": (art.get("doi") or "").lower() or None,
            "pmcid": art.get("pmcid") or f"PMC{pid}", "venue": d.get("fulljournalname") or d.get("source"),
            "abstract": None, "source": "pmc",
        })
    return out

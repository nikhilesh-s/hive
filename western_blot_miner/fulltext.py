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
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_RENDER = "https://europepmc.org/articles/{pmcid}?pdf=render"  # Europe PMC's own PDF render
EUROPEPMC_PDF = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextPDF"  # legacy; often 404 now
UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"
OPENALEX = "https://api.openalex.org/works/https://doi.org/{doi}"  # keyless OA resolver
DEFAULT_TIMEOUT = 60
RETRIES = 3
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    """'https://doi.org/10.1/ABC' / 'doi:10.1/abc' -> '10.1/abc' (DOIs are case-insensitive)."""
    m = _DOI_RE.search((value or "").strip())
    return m.group(0).rstrip(".,;)") .lower() if m else ""


def _email() -> str:
    """Contact address for polite API use. Unpaywall rejects placeholder
    domains, so Unpaywall is skipped unless UNPAYWALL_EMAIL / NCBI_EMAIL is real."""
    return os.environ.get("UNPAYWALL_EMAIL") or os.environ.get("NCBI_EMAIL") or config.NCBI_EMAIL


def _has_real_email() -> bool:
    e = _email()
    return "@" in e and not e.endswith("example.com")


def _headers() -> dict:
    return {"User-Agent": f"Mozilla/5.0 (compatible; {config.NCBI_TOOL}/0.1; mailto:{_email()})"}


def _is_pdf(content: bytes) -> bool:
    return b"%PDF" in content[:1024]


def _download(url: str, dest: Path, timeout: int = DEFAULT_TIMEOUT, params: dict | None = None) -> Optional[str]:
    """GET ``url`` (with retry/backoff on rate limits and 5xx); save to
    ``dest`` only if the body is a real PDF."""
    import time

    if dest.exists() and dest.stat().st_size > 0:
        return str(dest.resolve())
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=timeout, allow_redirects=True, headers=_headers())
        except requests.RequestException as error:
            logger.debug("download failed %s: %s", url, error)
            return None
        body = resp.content or b""
        if resp.status_code == 200 and _is_pdf(body):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            return str(dest.resolve())
        transient = resp.status_code in (429, 500, 502, 503, 504, 520) or b"Rate limit" in body[:200]
        if not transient:
            return None  # e.g. a publisher's HTML bot check: not a PDF, not retryable
        retry_after = resp.headers.get("Retry-After")
        wait = float(retry_after) if retry_after and retry_after.isdigit() else (5, 15, 30)[min(attempt, 2)]
        time.sleep(wait)
    return None


def europepmc_fulltext(pmcids: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict[str, dict]:
    """Europe PMC REST: {pmcid: {is_oa, pdf_url}} for up to 25 PMCIDs in one
    call. The listed pdf URL is the legal open-access full text HiveBlot may
    download; papers without one are not extractable."""
    ids = [p for p in pmcids if p]
    if not ids:
        return {}
    query = " OR ".join(f"PMCID:{p}" for p in ids[:25])
    try:
        resp = requests.get(EUROPEPMC_SEARCH, timeout=timeout, headers=_headers(),
                            params={"query": query, "format": "json", "resultType": "core", "pageSize": 25})
        results = resp.json().get("resultList", {}).get("result", []) if resp.status_code == 200 else []
    except (requests.RequestException, ValueError) as error:
        logger.debug("europepmc search failed: %s", error)
        return {}
    out = {}
    for r in results:
        pdf = next((u.get("url") for u in (r.get("fullTextUrlList") or {}).get("fullTextUrl", [])
                    if u.get("documentStyle") == "pdf" and u.get("url")), None)
        out[r.get("pmcid")] = {"is_oa": r.get("isOpenAccess") == "Y", "pdf_url": pdf, "title": r.get("title")}
    return out


def resolve_ids_batch(identifiers: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict[str, dict]:
    """Up to 200 DOIs / PMIDs / PMCIDs -> {identifier(lower): {doi, pmid, pmcid}}."""
    ids = [i for i in identifiers if i][:200]
    if not ids:
        return {}
    params = {"ids": ",".join(ids), "format": "json", "tool": config.NCBI_TOOL, "email": _email()}
    try:
        resp = requests.get(ID_CONVERTER, params=params, timeout=timeout)
        records = resp.json().get("records", []) if resp.status_code == 200 else []
    except (requests.RequestException, ValueError) as error:
        logger.debug("idconv failed: %s", error)
        return {}
    out = {}
    for rec in records:
        if rec.get("status") == "error":
            continue
        entry = {"doi": (rec.get("doi") or "").lower() or None, "pmid": rec.get("pmid"), "pmcid": rec.get("pmcid")}
        for key in (rec.get("requested-id"), rec.get("doi"), rec.get("pmcid"), str(rec.get("pmid") or "")):
            if key:
                out[str(key).lower()] = entry
    return out


def resolve_ids(identifier: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """DOI / PMID / PMCID -> {doi, pmid, pmcid} via the NCBI ID converter (empty on failure)."""
    return resolve_ids_batch([identifier], timeout).get(identifier.lower(), {})


def openalex_record(doi: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """OpenAlex's open-access view of a DOI ({} on any failure). Keyless."""
    try:
        resp = requests.get(OPENALEX.format(doi=doi), timeout=timeout, headers=_headers(),
                            params={"select": "best_oa_location,locations,open_access"})
        return (resp.json() or {}) if resp.status_code == 200 else {}
    except (requests.RequestException, ValueError) as error:
        logger.debug("openalex failed for %s: %s", doi, error)
        return {}


def openalex_pdf_urls(doi: str, timeout: int = DEFAULT_TIMEOUT, data: dict | None = None) -> list[str]:
    """OpenAlex: every open-access location that lists a direct PDF URL for
    this DOI, best location first. No key or contact email required."""
    data = openalex_record(doi, timeout) if data is None else data
    urls: list[str] = []
    for loc in [data.get("best_oa_location") or {}] + list(data.get("locations") or []):
        url = (loc or {}).get("pdf_url")
        if url and url not in urls:
            urls.append(url)
    return urls


_CITATION_PDF = re.compile(
    r"<meta[^>]+name=[\"']citation_pdf_url[\"'][^>]+content=[\"']([^\"']+)"
    r"|<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+name=[\"']citation_pdf_url", re.I)


def landing_pdf_url(doi: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """The publisher's own PDF link from its article page (the
    citation_pdf_url tag scholarly indexers read). Pages behind a bot check
    simply have no tag and return None."""
    try:
        resp = requests.get(f"https://doi.org/{doi}", timeout=timeout, headers=_headers(), allow_redirects=True)
    except requests.RequestException as error:
        logger.debug("landing page failed for %s: %s", doi, error)
        return None
    m = _CITATION_PDF.search(resp.text or "") if resp.status_code == 200 else None
    return (m.group(1) or m.group(2)) if m else None


def fetch_pdf(doi: str, out_dir: str | Path, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """DOI -> open-access PDF on disk. Returns {pdf_path|None, pmcid, pmid, doi, source}."""
    doi = normalize_doi(doi)
    out_dir = Path(out_dir)
    ids = resolve_ids(doi, timeout) if doi else {}
    pmcid = ids.get("pmcid")
    result = {"doi": doi, "pmid": ids.get("pmid"), "pmcid": pmcid, "pdf_path": None, "source": None, "tried": []}
    if pmcid:
        # 1. Europe PMC's own render of the open-access article (works for
        #    most PMC OA papers; rate-limited, hence the backoff)
        result["tried"].append("europepmc_render")
        path = _download(EUROPEPMC_RENDER.format(pmcid=pmcid), out_dir / f"{pmcid}.pdf", timeout)
        if path:
            result.update(pdf_path=path, source="europepmc")
            return result
        # 2. the PDF URL Europe PMC lists (often the publisher; some publishers
        #    answer scripts with an HTML bot check, which is rejected as non-PDF)
        info = europepmc_fulltext([pmcid], timeout).get(pmcid) or {}
        if info.get("pdf_url"):
            result["tried"].append("europepmc_listed_pdf")
            path = _download(info["pdf_url"], out_dir / f"{pmcid}.pdf", timeout)
            if path:
                result.update(pdf_path=path, source="europepmc_listed")
                return result
        # 3. legacy REST PDF endpoint (kept; frequently 404)
        result["tried"].append("europepmc_legacy")
        path = _download(EUROPEPMC_PDF.format(pmcid=pmcid), out_dir / f"{pmcid}.pdf", timeout)
        if path:
            result.update(pdf_path=path, source="europepmc")
            return result
    if doi:
        # 4. OpenAlex (Europe PMC and PMC block scripted PDF downloads since
        #    2026-08; publishers' own OA PDFs still answer a plain client)
        result["tried"].append("openalex")
        record = openalex_record(doi, timeout)
        for pdf_url in openalex_pdf_urls(doi, timeout, record):
            path = _download(pdf_url, out_dir / f"{doi.replace('/', '_')}.pdf", timeout)
            if path:
                result.update(pdf_path=path, source="openalex")
                return result
        # 4b. open access per OpenAlex but no direct PDF link listed (common
        #     for PLOS, Nature, microPublication): the publisher's own page
        #     names its PDF. Only for OA papers; paywalled ones are never tried.
        if (record.get("open_access") or {}).get("is_oa"):
            result["tried"].append("publisher_landing")
            pdf_url = landing_pdf_url(doi, timeout)
            path = pdf_url and _download(pdf_url, out_dir / f"{doi.replace('/', '_')}.pdf", timeout)
            if path:
                result.update(pdf_path=path, source="publisher_landing")
                return result
    if doi and _has_real_email():
        # 5. Unpaywall: every open-access location that offers a PDF
        result["tried"].append("unpaywall")
        try:
            resp = requests.get(UNPAYWALL.format(doi=doi), params={"email": _email()}, timeout=timeout)
            data = resp.json() if resp.status_code == 200 else {}
        except (requests.RequestException, ValueError) as error:
            logger.debug("unpaywall failed for %s: %s", doi, error)
            data = {}
        locations = [data.get("best_oa_location") or {}] + list(data.get("oa_locations") or [])
        seen = set()
        for loc in locations:
            pdf_url = (loc or {}).get("url_for_pdf")
            if not pdf_url or pdf_url in seen:
                continue
            seen.add(pdf_url)
            path = _download(pdf_url, out_dir / f"{doi.replace('/', '_')}.pdf", timeout)
            if path:
                result.update(pdf_path=path, source=f"unpaywall:{loc.get('host_type', 'oa')}")
                return result
    elif doi:
        result["tried"].append("unpaywall_skipped_no_contact_email")
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
    return annotate_oa_pdf(out, timeout)


def annotate_oa_pdf(papers: list[dict], timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """Add `pmcid` (via DOI when missing) and `oa_pdf` (Europe PMC lists a
    downloadable PDF) so the UI only offers extraction where it can succeed."""
    need = [p["doi"] for p in papers if p.get("doi") and not p.get("pmcid")]
    if need:
        ids = resolve_ids_batch(need, timeout)
        for p in papers:
            if p.get("doi") and not p.get("pmcid"):
                p["pmcid"] = (ids.get(p["doi"].lower()) or {}).get("pmcid")
    info = europepmc_fulltext([p["pmcid"] for p in papers if p.get("pmcid")], timeout)
    for p in papers:
        i = info.get(p.get("pmcid") or "") or {}
        # Europe PMC marks the article open access => its own render is
        # normally downloadable (publisher links may still bot-check scripts).
        p["is_oa"] = bool(i.get("is_oa"))
        p["oa_pdf"] = bool(i.get("is_oa") or i.get("pdf_url"))
    return papers

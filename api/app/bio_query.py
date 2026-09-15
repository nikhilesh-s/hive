"""Deterministic biological query -> SQL generator.

Used by /search when OPENAI_KEY is not configured (and as a way to serve the
structured biological queries UCSF researchers actually type without any LLM):

    phospho STAT3 Tyr705      -> modification + residue/position + target term
    co-IP EGFR                -> experiment_type co_ip + target term
    CST 9145                  -> antibody vendor + catalog number
    A549 STAT3                -> two AND'd terms, each OR'd across bio columns
    phospho AKT Ser473        -> modification + residue Ser/473 + target term

Design constraints:
  * Output is a SINGLE `SELECT * FROM western_blot_records ...` string that
    still goes through sql_guard.guard_and_limit_sql and executes under the
    scoped read-only role — this generator gets no special trust.
  * Deterministic and transparent: the generated SQL is returned to the client
    in the response (same as the LLM path), so a researcher can see exactly
    what was searched. No model, no guessing.
  * Unrecognized tokens degrade to broad ILIKE term matching — never an error.
"""
from __future__ import annotations

import re

from .config import settings

# Columns a free-text term is matched against (OR within a term, AND between
# terms). Covers protein identity, sample, treatment and antibody target.
TERM_COLUMNS = (
    "target",
    "raw_target_name",
    "canonical_target",
    "uniprot_id",
    "cell_line",
    "sample",
    "treatment_name",
    "treatment_context",
    "antibody_target",
    "modification_label",
    "antibody_catalog_number",  # "sc-398486", "ab108629", "5174s" typed without a vendor
    "doi",  # a pasted DOI finds a paper's rows ("more from this paper")
)

RESIDUE_NAMES = {"y": "Tyr", "s": "Ser", "t": "Thr",
                 "tyr": "Tyr", "ser": "Ser", "thr": "Thr"}

# Vendor vocabulary -> the string matched against antibody_vendor.
VENDORS = {
    "cst": "cell signaling",
    "cell signaling": "cell signaling",
    "cell signaling technology": "cell signaling",
    "santa cruz": "santa cruz",
    "abcam": "abcam",
    "sigma": "sigma",
    "sigma-aldrich": "sigma",
    "millipore": "millipore",
    "thermo": "thermo",
    "invitrogen": "invitrogen",
    "proteintech": "proteintech",
    "bd biosciences": "bd biosciences",
}

STOPWORDS = {
    "western", "blot", "blots", "westerns", "in", "of", "for", "with", "the",
    "a", "an", "and", "show", "me", "find", "papers", "paper", "evidence",
    "cells", "cell", "detect", "detected", "detection", "antibody",
    "antibodies", "data", "records", "record", "results", "human",
    # measurement / perturbation words: as AND terms they matched nothing ("STAT3 expression" -> 0 rows)
    "expression", "expressed", "level", "levels", "protein", "proteins", "knockdown", "knockout",
}

_SITE_RE = re.compile(r"\b(tyr|ser|thr|y|s|t)\s?-?(\d{2,4})\b", re.IGNORECASE)
# Cell lines spelled like a one-letter site stay search terms (T24 bladder, Y79 retinoblastoma).
_SITE_LIKE_CELL_LINES = {"t24", "y79"}
# A catalog number is trusted only directly after a vendor: "CST 9145", "abcam ab108629",
# "Santa Cruz sc-398486", "Sigma A1978", "CST #5174s" -- not "HEK 293 CST" or "CST 1:1000".
_VENDOR_CATALOG_RE = re.compile(r"\s*#?\s*([A-Za-z]{0,3}-?\d{3,7}[A-Za-z]?)\b")
# Only the explicit WORD "phospho" adds a modification filter. A "p-" prefix
# ("P-ERK", "p-AKT") stays a plain term: the printed row label matches it
# directly, and adding a phospho filter would EXCLUDE rows whose modification
# is honestly CONFLICTING (value null) — hiding exactly the records that most
# need review.
_PHOSPHO_RE = re.compile(r"\bphospho\w*", re.IGNORECASE)
_COIP_RE = re.compile(r"\bco-?ip\b|\bimmunoprecipitat\w*", re.IGNORECASE)
_LOADING_RE = re.compile(r"\bloading[\s-]?controls?\b", re.IGNORECASE)
_NEEDS_REVIEW_RE = re.compile(r"\bneeds?[\s-]?review\b", re.IGNORECASE)
_CATALOG_RE = re.compile(r"#\s?(\d{3,7})\b")
_DILUTION_RE = re.compile(r"\d+:[\d,]+")


def _esc(term: str) -> str:
    """Sanitize a term for embedding in an ILIKE literal. Defense-in-depth:
    the output still passes through sql_guard AST validation + the read-only
    role, but we never build a literal from raw user text anyway."""
    # Letters of any script survive (IκBα, α-tubulin): stripping κ/α turned "IκBα" into "ib",
    # which matched every kinase-inhibitor drug name. '_' and '%' are ILIKE wildcards: removed.
    term = re.sub(r"[^\w/+.\- ]|_", "", term)
    return term.replace("'", "''").strip()


def _term_clause(term: str) -> str:
    t = _esc(term)
    if len(t) <= 4 and t[-1:].isalpha() and "+" not in t:
        # Short gene symbols (MYC, MET, KIT, ERK) must not match inside a word:
        # '%myc%' returned 86 Rapamycin/Bafilomycin rows for 4 MYC rows. The
        # symbol may not be followed by a letter (c-Myc, ERK1/2 still match;
        # MYCN, IL-6R, metformin do not). SIMILAR TO keeps this inside the
        # guard's allowlist, no regex functions. ponytail: right boundary only,
        # so PERK still matches ERK; longer words (actin/actinin) stay substring.
        pat = f"%{t.lower()}([^a-z]%)?"
        ors = " OR ".join(f"{c} ILIKE '%{t}%'" if c == "doi" else f"lower({c}) SIMILAR TO '{pat}'"
                          for c in TERM_COLUMNS)
    else:
        ors = " OR ".join(f"{c} ILIKE '%{t}%'" for c in TERM_COLUMNS)
    return f"({ors})"


# The URL / "doi:" prefix is consumed with the DOI; left behind it became an AND term matching nothing.
_DOI_IN_QUERY_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|\bdoi:\s*)?\b(10\.\d{4,9}/\S+)", re.IGNORECASE)


def _doi_clause(q: str) -> tuple[str | None, str]:
    """A pasted DOI is an exact paper filter. It is taken out of the question
    first, so its characters never become a phospho site ('s0092-8674(00)'
    read as Ser92) or a substring that also matches a longer DOI ('...2227'
    inside '...2227-4'), and '_' / '()' in it survive."""
    m = _DOI_IN_QUERY_RE.search(q)
    if not m:
        return None, q
    doi = m.group(1).rstrip(".,;?!")
    if doi.count(")") > doi.count("("):
        doi = doi.rstrip(")")
    doi = re.sub(r"[\\'\x00-\x1f]", "", doi).lower()
    return f"lower(doi) = '{doi}'", q[: m.start()] + " " + q[m.end():]


def generate_bio_sql(question: str, table_name: str | None = None) -> str:
    q = " " + question.strip() + " "
    clauses: list[str] = []
    doi, q = _doi_clause(q)
    if doi:
        clauses.append(doi)

    # Phospho-site notation (Tyr705 / Y705 / Ser 473) -> residue + position.
    sites = [m for m in _SITE_RE.finditer(q) if m.group(0).lower() not in _SITE_LIKE_CELL_LINES]
    if sites:
        residue = RESIDUE_NAMES[sites[0].group(1).lower()]
        position = int(sites[0].group(2))
        clauses.append(f"(residue ILIKE '{residue}' AND residue_position = {position})")
        for m in reversed(sites):
            q = q[: m.start()] + " " + q[m.end():]

    # Modification / experiment-type keywords.
    if _PHOSPHO_RE.search(q):
        # Unsettled modifications (CONFLICTING/AMBIGUOUS) stay INCLUDED: a
        # phospho search must surface a disputed phospho-vs-total row for
        # review, not silently hide it (its scalar modification_type is null
        # by design). Settled rows rank first via ORDER BY needs_review.
        clauses.append("(modification_type ILIKE '%phospho%' OR "
                       "modification_status ILIKE 'CONFLICTING' OR "
                       "modification_status ILIKE 'AMBIGUOUS')")
        q = re.sub(r"\bphospho\w*", " ", q, flags=re.IGNORECASE)
    if _COIP_RE.search(q):
        clauses.append("experiment_type ILIKE 'co_ip'")
        q = _COIP_RE.sub(" ", q)
    if _LOADING_RE.search(q):
        clauses.append("experiment_type ILIKE 'loading_control'")
        q = _LOADING_RE.sub(" ", q)
    if _NEEDS_REVIEW_RE.search(q):
        clauses.append("needs_review = true")
        q = _NEEDS_REVIEW_RE.sub(" ", q)

    # Antibody vendor + catalog number.
    after_vendor = None
    for alias in sorted(VENDORS, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(alias)}\b", q, re.IGNORECASE)
        if m:
            clauses.append(f"antibody_vendor ILIKE '%{_esc(VENDORS[alias])}%'")
            after_vendor = _VENDOR_CATALOG_RE.match(q, m.end())
            q = q[: m.start()] + " " + q[m.end():]
            break
    cat = _CATALOG_RE.search(q)
    if cat:
        clauses.append(f"antibody_catalog_number ILIKE '%{_esc(cat.group(1))}%'")
        q = q.replace(cat.group(0), " ")
    elif after_vendor:
        clauses.append(f"antibody_catalog_number ILIKE '%{_esc(after_vendor.group(1))}%'")
        q = q.replace(after_vendor.group(1), " ", 1)

    # Remaining free-text terms: AND between terms, OR across bio columns.
    for token in re.split(r"[\s,;]+", q):
        token = token.strip(" .?!()[]{}\"'")
        if len(token) < 2 or token.lower() in STOPWORDS or _DILUTION_RE.fullmatch(token):
            continue
        if not _esc(token):
            continue
        clauses.append(_term_clause(token))

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    # Settled evidence first (needs_review=false), stable order within.
    return (
        f"SELECT * FROM {table_name or settings.table_name}{where} "
        f"ORDER BY needs_review ASC, id ASC"
    )

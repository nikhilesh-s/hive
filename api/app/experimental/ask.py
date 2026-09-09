"""Grounded paper QA (EXPERIMENTAL) — the AGeneTic "paper-qa" idea on top of
HiveBlot's structured evidence.

AGeneTic hands PDFs to paper-qa, which ranks passages and answers with
citations. HiveBlot already holds something better than passages: reviewed
Evidence Records with statuses and provenance. So retrieval here is the
deterministic biological parser over the reviewed table (and, optionally,
the live unreviewed tier), the evidence is rendered as numbered blocks,
and the model may answer ONLY from those blocks, citing [E#]. Statuses are
carried into the answer: a CONFLICTING field stays unresolved, a live row
stays "unreviewed". Without a model key the endpoint still returns the
ranked evidence, so the retrieval half is testable and useful on its own.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Callable

import sys
from pathlib import Path as _Path

from ..bio_query import generate_bio_sql
from ..config import settings
from ..db import run_readonly_query
from ..schemas import WesternBlotRecord, review_reasons_from_flags
from ..sql_guard import guard_and_limit_sql

logger = logging.getLogger("hive.experimental.ask")

_REPO = _Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:  # western_blot_miner (provider plumbing) lives at the repo root
    sys.path.insert(0, str(_REPO))

MAX_EXPERIMENTS = 12
_CITE_RE = re.compile(r"\[E(\d+)\]")

SYSTEM = """You are HiveBlot's evidence assistant for Western blot experiments.
Answer the researcher's question using ONLY the numbered evidence records below.
Rules:
- Cite the record after every factual claim, like [E2]. A claim without a citation is not allowed.
- If a record's field is CONFLICTING or AMBIGUOUS, say it is unresolved and show the competing claims; never pick a winner.
- If a record is marked LIVE UNREVIEWED, say so when you use it.
- Band information is categorical (present / absent / uncertain). Never infer intensity, fold change, or up/down regulation.
- If the records do not answer the question, say that the current HiveBlot evidence does not contain it. Do not use outside knowledge.
- Be concise: at most ~180 words, plain prose, no headings."""


def _lane_text(rows: list[dict]) -> str:
    parts = []
    for r in rows:
        cond = r.get("lane_condition") or r.get("condition") or "lane"
        state = r.get("band_state") or ("present" if r.get("band_detected") else "absent" if r.get("band_detected") is False else "uncertain")
        parts.append(f"{cond}={state}")
    return "; ".join(parts)


def evidence_blocks(rows: list[dict], tier: str = "reviewed") -> list[dict]:
    """Group lane rows into experiments and render one compact block each."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = (r.get("stable_row_key") or f"{r.get('paper_id')}|{r.get('id')}").split(":")[0]
        groups.setdefault(key, []).append(r)
    blocks = []
    for key, lanes in groups.items():
        f = lanes[0]
        rec = WesternBlotRecord.model_validate(f)  # applies the public shaping (reasons, crop filename)
        mod = f.get("modification_label")
        mod_status = f.get("modification_status")
        if mod_status == "CONFLICTING":
            mod = "CONFLICTING (unresolved: phospho vs total)"
        elif mod_status == "AMBIGUOUS":
            mod = f"{mod or 'modification'} (AMBIGUOUS)"
        treat = " ".join(str(x) for x in (f.get("treatment_name"), f.get("dose"), f.get("dose_unit"),
                                          f.get("duration"), f.get("duration_unit")) if x not in (None, ""))
        ab = " ".join(str(x) for x in (f.get("antibody_vendor"), f"#{f['antibody_catalog_number']}" if f.get("antibody_catalog_number") else None) if x)
        mw = []
        if f.get("expected_molecular_weight_kda") is not None:
            mw.append(f"expected {f['expected_molecular_weight_kda']} kDa (UniProt)")
        if f.get("reported_molecular_weight_kda") is not None:
            mw.append(f"reported {f['reported_molecular_weight_kda']} kDa (paper)")
        blocks.append({
            "key": key, "tier": tier, "record_id": f.get("id"), "doi": f.get("doi") or f.get("paper_id"),
            "title": f.get("title"), "lanes": len(lanes),
            "headline": f"{f.get('canonical_target') or f.get('target')}{' · ' + mod if mod else ''}",
            "text": (
                f"target={f.get('canonical_target') or f.get('target')} (as printed: {f.get('target')}; "
                f"protein status {f.get('protein_status') or 'n/a'}; UniProt {f.get('uniprot_id') or 'none'}); "
                f"modification={mod or 'none stated'}; experiment={f.get('experiment_type') or f.get('western_blot_type') or 'n/a'}; "
                f"sample={f.get('cell_line') or f.get('sample') or 'n/a'}; organism={f.get('organism') or 'n/a'}; "
                f"treatment={treat or 'not reported'}; antibody={ab or 'not reported'}; "
                f"MW={', '.join(mw) or 'not reported'}; lanes[{len(lanes)}]: {_lane_text(lanes)}; "
                f"review={'needs review: ' + '; '.join(rec.review_reasons) if rec.review_reasons else 'supported'}; "
                f"source: {f.get('figure_label') or 'figure'} p.{f.get('page')} DOI {f.get('doi') or f.get('paper_id')}"
                + ("; LIVE UNREVIEWED extraction" if tier != "reviewed" else "")
            ),
        })
    return blocks


_KEYWORDS = ("phospho", "co-ip", "coip", "immunoprecipitation", "loading control", "needs review")
_TERM_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Za-z0-9][A-Za-z0-9/+.-]*$")


def query_terms(question: str) -> list[str]:
    """Biological tokens from a natural-language question, in order: anything
    with a digit, an uppercase run or a hyphen (STAT3, Tyr705, IL-6, Hep3B,
    P-ERK, CST) plus the parser's keyword filters. Prose words are dropped
    because the parser ANDs every term against the evidence columns."""
    ql = question.lower()
    terms = [k for k in _KEYWORDS if k in ql]
    for tok in re.split(r"[\s,;?!()\[\]\"']+", question):
        t = tok.strip(".:")
        if len(t) < 2 or not _TERM_RE.match(t):
            continue
        if t.lower() in {"is", "in", "of", "the", "and", "or", "a", "an", "was", "were", "does", "do", "did", "which", "what"}:
            continue
        if not (any(c.isdigit() for c in t) or sum(c.isupper() for c in t) >= 2 or "-" in t or t.lower() in ql.split()):
            continue
        if t not in terms:
            terms.append(t)
    return terms


async def _rows_for(q: str, table: str) -> list[dict]:
    sql = guard_and_limit_sql(generate_bio_sql(q, table), 300, table)
    return await run_readonly_query(sql)


async def retrieve(question: str, doi: str | None, include_live: bool) -> list[dict]:
    """Deterministic retrieval: biological terms from the question, parser +
    guard over the reviewed table (and live tier). If the AND of all terms
    finds nothing, back off by dropping the last term until something does,
    so a wordy question still reaches the right experiment."""
    blocks: list[dict] = []
    terms = query_terms(question) or [question]
    tables = [(settings.table_name, "reviewed")]
    if include_live:
        tables.append((settings.live_table_name, "live_unreviewed"))
    for table, tier in tables:
        rows: list[dict] = []
        for n in range(len(terms), 0, -1):
            q = " ".join(terms[:n]) + (f" {doi}" if doi else "")
            try:
                rows = await _rows_for(q, table)
            except Exception as e:  # live table may not exist yet
                logger.warning("retrieval on %s failed: %s", table, e)
                rows = []
                break
            if rows:
                break
        if doi and not rows:
            # Paper-scoped question whose terms match nothing in this paper
            # (e.g. it asks about phosphorylation and the paper has none):
            # fall back to the paper's own rows so the answer can say so
            # from evidence instead of returning nothing.
            try:
                rows = await _rows_for(doi, table)
            except Exception as e:
                logger.warning("doi fallback on %s failed: %s", table, e)
                rows = []
        if doi:
            rows = [r for r in rows if (r.get("doi") or "").lower() == doi.lower()]
        blocks += evidence_blocks(rows, tier)
    # settled evidence first, then live; cap so the prompt stays small
    blocks.sort(key=lambda b: (b["tier"] != "reviewed", "needs review" in b["text"]))
    return blocks[:MAX_EXPERIMENTS]


def _default_llm(system: str, user: str) -> tuple[str, str]:
    """The configured provider (WBM_LLM_BACKEND: claude_cli | anthropic |
    bedrock | openai), same plumbing as extraction. Returns (text, model)."""
    from western_blot_miner import llm_client

    return llm_client.get_client().complete_text(system, user, max_tokens=1200)


def llm_ready() -> bool:
    from western_blot_miner import llm_client

    return llm_client.backend_status()[0]


async def answer(question: str, doi: str | None = None, include_live: bool = True,
                 llm: Callable[[str, str], tuple[str, str]] | None = None) -> dict:
    blocks = await retrieve(question, doi, include_live)
    for i, b in enumerate(blocks, 1):
        b["ref"] = f"E{i}"
    out = {"question": question, "doi": doi, "evidence": blocks, "answer": None, "cited": [], "model": None, "note": None}
    if not blocks:
        out["note"] = "No matching evidence in the current HiveBlot tiers for this question."
        return out
    if llm is None and not llm_ready():
        out["note"] = "Retrieval only: no model backend configured (WBM_LLM_BACKEND=claude_cli for a local Claude Code login, or anthropic + ANTHROPIC_API_KEY)."
        return out
    user = "EVIDENCE RECORDS:\n" + "\n".join(f"[{b['ref']}] {b['text']}" for b in blocks) + \
           f"\n\nQUESTION: {question}\n\nAnswer from the records only, citing [E#]."
    fn = llm or _default_llm
    loop = asyncio.get_running_loop()
    try:
        text, model = await loop.run_in_executor(None, fn, SYSTEM, user)
    except Exception as e:
        out["note"] = f"Model call failed: {type(e).__name__}: {e}"[:300]
        return out
    cited = sorted({f"E{n}" for n in _CITE_RE.findall(text)}, key=lambda s: int(s[1:]))
    out.update(answer=text, cited=[c for c in cited if any(b["ref"] == c for b in blocks)], model=model)
    if not out["cited"]:
        out["note"] = "The model answered without citing any record; treat the answer as unsupported."
    return out

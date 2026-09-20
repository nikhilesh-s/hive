"""Rebuild the three reviewed papers' Evidence Records from their stored model
claims with the CURRENT code and check invariants that unit fixtures cannot:

* every rebuilt record_id already exists in the stored reviewed records and is
  unique (ids key stored corrections; they must never move);
* building twice in one process gives identical records (determinism);
* every Source typed figure_caption quotes the panel's caption, and every Source
  typed methods quotes the panel's methods (whitespace, soft hyphen and dash
  variants folded) -- provenance must come from the claimed text.

No model calls, no network. The per-paper run inputs under
western_blot_miner/data/pdf_runs/ are not tracked in git, so this test skips
where they are absent (CI) and runs on a machine that has the runs.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PAPERS = {
    "10.3892_br.2026.2108": "phospho_PMC12856536",
    "10.3892_ijmm.2022.5188": "standard_PMC9559174",
    "10.1186_s12964-025-02385-8": "coip_PMC12706926",
}
RUNS = REPO / "western_blot_miner" / "data" / "pdf_runs"
NEEDED = ("summary.json", "candidate_contexts.jsonl", "llm_candidates.json")

pytestmark = pytest.mark.skipif(
    not all((RUNS / d / f).is_file() for d in PAPERS for f in NEEDED),
    reason="stored pdf_runs inputs are not tracked in git; run locally where they exist",
)

_DASH = re.compile("[‐-―−]")


def _fold(t: str) -> str:
    return re.sub(r"\s+", " ", _DASH.sub("-", (t or "").replace("­", ""))).strip()


def _sources(node):
    if isinstance(node, dict):
        if {"type", "rank", "text"} <= set(node):
            yield node
            return
        for v in node.values():
            yield from _sources(v)
    elif isinstance(node, list):
        for v in node:
            yield from _sources(v)


def _rebuild(tmp_path):
    from western_blot_miner import pipeline
    from western_blot_miner.evidence_record import ExtractionMeta
    from western_blot_miner.extract_records import extract_records_from_claims
    from western_blot_miner.resolve import CachingResolver, LocalMapResolver

    cache_src = REPO / "western_blot_miner" / "data" / "protein_cache.json"
    cache = tmp_path / "protein_cache.json"
    if cache_src.is_file():
        shutil.copy(cache_src, cache)
    resolver = CachingResolver(LocalMapResolver(), fallback=LocalMapResolver(), cache_path=cache)
    meta = ExtractionMeta(stage="deterministic+llm", backend="replay", model="replay", escalated=False)
    out = {}
    for doi, demo in PAPERS.items():
        run = RUNS / doi
        summary = json.loads((run / "summary.json").read_text())
        ctx = {Path(k).name: v for k, v in pipeline._read_contexts(run / "candidate_contexts.jsonl").items()}
        cands = {Path(c["candidate_path"]).name: c for c in json.loads((run / "llm_candidates.json").read_text())}
        panels = []
        for resp in json.loads((REPO / "eval" / "demo" / demo / "responses_observed.json").read_text()):
            base = Path(resp["candidate_path"]).name
            pc = pipeline._panel_context(summary, cands[base], ctx.get(base, ""))
            recs = extract_records_from_claims(pc, {"rows": resp.get("rows", [])}, resolver, meta)
            panels.append((pc["texts"]["caption"], pc["texts"]["methods"], [r.model_dump(mode="json") for r in recs]))
        out[doi] = panels
    return out


def _strip_times(d):
    return {k: v for k, v in d.items() if k not in ("extracted_at", "created_at")}


def test_record_ids_are_stable_unique_and_rebuild_is_deterministic(tmp_path):
    first = _rebuild(tmp_path)
    second = _rebuild(tmp_path)
    for doi, demo in PAPERS.items():
        stored = {r["record_id"] for r in json.loads((REPO / "eval" / "demo" / demo / "evidence_records.json").read_text())}
        ids = [r["record_id"] for _, _, recs in first[doi] for r in recs]
        assert len(ids) == len(set(ids)), f"{doi}: duplicate record_id"
        assert set(ids) <= stored, f"{doi}: record_id moved: {sorted(set(ids) - stored)[:3]}"
        a = [_strip_times(r) for _, _, recs in first[doi] for r in recs]
        b = [_strip_times(r) for _, _, recs in second[doi] for r in recs]
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), f"{doi}: rebuild not deterministic"


def test_caption_and_methods_sources_quote_their_claimed_text(tmp_path):
    bad = []
    for doi, panels in _rebuild(tmp_path).items():
        for caption, methods, recs in panels:
            fc, fm = _fold(caption), _fold(methods)
            for rec in recs:
                for src in _sources(rec):
                    text = _fold(src.get("text", ""))
                    if not text:
                        continue
                    if src["type"] == "figure_caption" and text not in fc:
                        bad.append((doi, rec.get("raw_target"), "figure_caption", src["text"][:80]))
                    if src["type"] == "methods" and text not in fm:
                        bad.append((doi, rec.get("raw_target"), "methods", src["text"][:80]))
    assert not bad, f"{len(bad)} sources do not quote their claimed text, e.g. {bad[:3]}"

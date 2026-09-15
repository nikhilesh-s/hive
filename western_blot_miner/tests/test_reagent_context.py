"""B-2 on the live path: reagent sentences reach the methods text and the
deterministic backstop recovers from verbatim methods, not from paraphrase."""
from western_blot_miner.pdf_preprocess import build_text_context_for_candidate
from western_blot_miner.pipeline import _split_text_context
from western_blot_miner.record_builder import build_evidence_record

REAGENT = ("Western blotting. Membranes were incubated overnight with primary antibodies against "
           "p\u2011STAT3 (Tyr705; 1:1,000; CST #9145), t\u2011STAT3 (1:1,000; CST #4904) and "
           "\u03b2\u2011actin (1:2,000; CST #4967). After washing, membranes were probed with a secondary antibody.")


def test_long_page_and_figure_text_no_longer_truncate_the_methods_section():
    pages = [{"page": 1, "text": "Cells were cultured in DMEM. " * 600},
             {"page": 2, "text": "Figure 1. STAT3 signalling in cells. " * 500},
             {"page": 3, "text": REAGENT}]
    paper = " ".join(p["text"] for p in pages)
    ctx = build_text_context_for_candidate({"paper_id": "x", "page": 1, "bbox_page": [0, 0, 1, 1]}, pages, paper)
    assert "PAPER_SAMPLE_OR_METHODS_SNIPPETS:" in ctx
    assert "#4967" in ctx and len(ctx) <= 14000
    caption, methods = _split_text_context(ctx)
    assert "#4967" in methods[:8000]                 # inside what the extraction prompt sends
    assert "#4967" not in caption


def _actin(extra=None, target="\u03b2-actin", text="\u03b2-actin (loading control label on blot panel C)"):
    ab = {"target": target, "role": "detection", "source": {"type": "methods", "rank": 3, "text": text}, **(extra or {})}
    return build_evidence_record({"raw_target": target, "texts": {"caption": "", "methods": REAGENT},
                                  "model_claims": {"antibodies": [ab], "bands": []}}).antibodies[0]


def test_backstop_recovers_from_verbatim_methods_when_model_text_is_paraphrase():
    ab = _actin()
    assert ab.catalog_number.value == "4967" and ab.dilution.value == "1:2000"
    src = ab.catalog_number.sources[0]
    assert src.type == "deterministic" and src.text and src.text in REAGENT
    assert "\u03b2\u2011actin" in src.text


def test_backstop_over_methods_never_overwrites_and_keeps_disagreement_as_candidate():
    ab = _actin({"catalog": "9145"})
    assert ab.catalog_number.value == "9145"
    assert [c.value for c in ab.catalog_number.candidates] == ["4967"]


def test_backstop_over_methods_abstains_for_phospho_and_total_of_one_protein():
    for target in ("P-STAT3 (Tyr705)", "total STAT3"):
        ab = _actin(target=target, text=f"{target} antibody (model summary)")
        assert ab.catalog_number.value is None and ab.dilution.value is None, target

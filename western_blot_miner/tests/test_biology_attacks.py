"""Regression tests for adversarial biology-normalization defects (D4-D6, P2)."""
import pytest

from western_blot_miner import biology
from western_blot_miner.supabase_loader import extract_antibody


@pytest.mark.parametrize("text", [
    "anti-STAT3 (Santa Cruz) was used at the indicated 1000-fold dilution",
    "blots were run in duplicate 500 times",
    "the band located 500 bp away",
])
def test_catalog_needs_word_boundary(text):
    assert extract_antibody(text)["catalog_number"] is None


@pytest.mark.parametrize("text,cat", [
    ("anti-STAT3 (CST, cat. no. 9139)", "9139"),
    ("anti-STAT3 (CST #9145)", "9145"),
    ("Catalog number 12640", "12640"),
])
def test_catalog_real_numbers_still_found(text, cat):
    assert extract_antibody(text)["catalog_number"] == cat


@pytest.mark.parametrize("name", [
    "pVHL", "pRB", "p-glycoprotein", "P-gp", "Pgp", "p-cadherin", "P-selectin",
    "p62", "p53", "p38", "p21", "p27Kip1", "p70S6K", "p85",
])
def test_non_phospho_p_names(name):
    assert biology.antibody_modification(name)["modification_type"] is None


@pytest.mark.parametrize("name", [
    "p-STAT3", "pSTAT3", "phospho-ERK1/2", "p-AKT (S473)", "pS6", "p-p38",
])
def test_real_phospho_names(name):
    assert biology.antibody_modification(name)["modification_type"] == "phosphorylation"


@pytest.mark.parametrize("name,core", [
    ("P-cadherin", "P-cadherin"), ("P-selectin", "P-selectin"),
    ("P-gp", "P-gp"), ("t-PA", "t-PA"), ("P-glycoprotein", "P-glycoprotein"),
    ("E-cadherin", "E-cadherin"),
    ("P-STAT3", "STAT3"), ("p-STAT3", "STAT3"), ("phospho-STAT3", "STAT3"),
    ("t-STAT3", "STAT3"), ("pSTAT3", "STAT3"),
])
def test_core_symbol_keeps_name_prefix(name, core):
    assert biology.core_symbol(name) == core


def test_two_sites_for_same_target_assign_no_site():
    m = biology.detect_modification("p-STAT3", caption="p-STAT3 Ser727 and p-STAT3 Tyr705 blots")
    assert m["modification_type"] == "phosphorylation"
    assert m["residue"] is None and m["residue_position"] is None


def test_caption_claim_two_sites_assigns_no_site():
    m = biology.caption_modification_for_core("STAT3", "p-STAT3 Ser727 and p-STAT3 Tyr705 blots")
    assert m == {"modification_type": "phosphorylation", "residue": None, "residue_position": None}
    one = biology.caption_modification_for_core("STAT3", "p-STAT3 Tyr705 blots")
    assert (one["residue"], one["residue_position"]) == ("Tyr", 705)


def test_single_site_caption_still_resolves():
    m = biology.detect_modification("p-STAT3", caption="p-STAT3 Tyr705 blot; p-AKT Ser473 blot")
    assert (m["residue"], m["residue_position"]) == ("Tyr", 705)



def test_caption_p_names_are_not_glued_phospho_prefixes():
    from western_blot_miner.biology import caption_modification_for_core, core_symbol
    assert caption_modification_for_core(core_symbol("pVHL"), "pVHL expression in 786-O cells.") is None
    assert caption_modification_for_core(core_symbol("pRB"), "pRB levels were unchanged.") is None
    # a real glued phospho prefix in a caption still counts
    got = caption_modification_for_core(core_symbol("pSTAT3"), "pSTAT3 (Tyr705) increased after IL-6.")
    assert got is not None and got["modification_type"] == "phosphorylation"


def test_pvhl_record_has_no_phospho_conflict():
    from western_blot_miner.record_builder import build_evidence_record
    rec = build_evidence_record({
        "raw_target": "pVHL", "texts": {"caption": "pVHL expression in 786-O cells.", "methods": "anti-VHL (CST #68547)"},
        "model_claims": {"antibodies": [{"target": "pVHL", "role": "detection",
                                         "source": {"type": "methods", "rank": 3, "text": "anti-VHL (CST #68547)"}}],
                         "bands": []},
    })
    mt = rec.modification.modification_type
    assert mt.value is None and "phosphorylation" not in [c.value for c in (mt.candidates or [])]

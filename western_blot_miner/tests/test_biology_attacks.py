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

"""B-12: conservative target-name normalization.

One table row per rule (ids match biology.normalize_target and
tickets/b12-expected-mappings.md), plus guards that names which must NOT change
still do not. Offline: no network, no model.
"""
import sys
import types

import pytest

from western_blot_miner import biology
from western_blot_miner import resolve
from western_blot_miner.record_builder import build_evidence_record
from western_blot_miner.resolve import CachingResolver, LocalMapResolver, ProteinResolution

norm = biology.normalize_target

# --------------------------------------------------------------------------- #
# normalize_target: raw -> (lookup, kind, family label, rule id)
# --------------------------------------------------------------------------- #

LOOKUPS = [
    # name_alias
    ("Vinculin", "VCL", "name_alias"),
    ("Bcl-xL", "BCL2L1", "name_alias"),
    ("IL-18", "IL18", "name_alias"),
    ("β-catenin", "CTNNB1", "name_alias"),
    ("Total-eIF2α", "EIF2S1", "name_alias"),
    ("Ph-eIF2α", "EIF2S1", "name_alias"),
    ("4E-BP1", "EIF4EBP1", "name_alias"),
    ("Mcl-1(long exposure)", "MCL1", "name_alias"),
    ("Bcl-2", "BCL2", "name_alias"),
    ("Beclin 1", "BECN1", "name_alias"),
    ("SHP-1", "PTPN6", "name_alias"),
    ("SHP2", "PTPN11", "name_alias"),
    ("Survivin", "BIRC5", "name_alias"),
    ("c-Myc", "MYC", "name_alias"),
    ("Cyclin D1", "CCND1", "name_alias"),
    ("caspase-3", "CASP3", "name_alias"),
    ("Caspase 7", "CASP7", "name_alias"),
    # form_qualifier
    ("Cleaved caspase-3", "CASP3", "form_qualifier"),
    ("Active β-catenin", "CTNNB1", "form_qualifier"),
    # cleaved_abbreviation + anti_alpha_prefix
    ("α-CASP3 cl. (CASP3 p19 / CASP3 p17)", "CASP3", "cleaved_abbreviation"),
    ("α-CASP3 cl. (CASP3 p19 / CASP3 p17)", "CASP3", "anti_alpha_prefix"),
    ("α-CASP1", "CASP1", "anti_alpha_prefix"),
    ("α-CASP7 cl.", "CASP7", "anti_alpha_prefix"),
    ("α-GSDMD (GSDMD / GSDMD p30)", "GSDMD", "anti_alpha_prefix"),
    ("α-GSDME", "GSDME", "anti_alpha_prefix"),
    ("α-IL-18", "IL18", "anti_alpha_prefix"),
    # cleavage_fragment_suffix
    ("CASP1p10", "CASP1", "cleavage_fragment_suffix"),
    ("CASP3 p17", "CASP3", "cleavage_fragment_suffix"),
    # non_phospho_prefix
    ("Non-Phos-4EBP1", "EIF4EBP1", "non_phospho_prefix"),
    ("non-phospho-4E-BP1", "EIF4EBP1", "non_phospho_prefix"),
    # epitope_tag (prefix and suffix)
    ("GFP-KRAS", "KRAS", "epitope_tag"),
    ("FLAG-STAT3", "STAT3", "epitope_tag"),
    ("GFP-STAT3", "STAT3", "epitope_tag"),
    ("STAT3-HA", "STAT3", "epitope_tag"),
    # lc3_isoform_stated
    ("LC3B", "MAP1LC3B", "lc3_isoform_stated"),
    ("LC3B-II", "MAP1LC3B", "lc3_isoform_stated"),
    ("LC3B I / II", "MAP1LC3B", "lc3_isoform_stated"),
    ("LC3A", "MAP1LC3A", "lc3_isoform_stated"),
]


@pytest.mark.parametrize("raw,lookup,rule", LOOKUPS)
def test_lookup_rules(raw, lookup, rule):
    n = norm(raw)
    assert n["lookup"] == lookup, n
    assert rule in n["rules"], n
    assert n["kind"] is None


FAMILIES = [
    ("Ras", "HRAS/KRAS/NRAS", ["HRAS", "KRAS", "NRAS"]),
    ("pan-Ras", "HRAS/KRAS/NRAS", ["HRAS", "KRAS", "NRAS"]),
    ("Jnk", "MAPK8/MAPK9/MAPK10", ["MAPK8", "MAPK9", "MAPK10"]),
    ("p-JNK", "MAPK8/MAPK9/MAPK10", ["MAPK8", "MAPK9", "MAPK10"]),
    ("SAPK/JNK", "MAPK8/MAPK9/MAPK10", ["MAPK8", "MAPK9", "MAPK10"]),
    ("α-actinin", "ACTN1/ACTN2/ACTN3/ACTN4", ["ACTN1", "ACTN2", "ACTN3", "ACTN4"]),
    ("α-tubulin", None, []),
    ("β-tubulin", None, []),
    ("MyHC", None, []),
    ("myosin heavy chain", None, []),
    # lc3_isoform_unstated: every spelling of the I/II forms without a B
    ("LC3", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC3-I", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC3-II", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC3-I/LC3-II", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC3 I/LC3 II", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC3-II/LC3-I", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("LC-3", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
    ("GFP-LC3", "MAP1LC3A/MAP1LC3B/MAP1LC3C", ["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"]),
]


@pytest.mark.parametrize("raw,label,genes", FAMILIES)
def test_ambiguous_families(raw, label, genes):
    n = norm(raw)
    assert n["kind"] == "family", n
    assert n["family_label"] == label
    assert n["candidates"] == genes
    assert n["lookup"] is None          # never collapsed to one guessed gene


@pytest.mark.parametrize("raw", ["Vpr", "Vif", "Nef", "Vpu", "gp120", "gp41", "Vpr-myc", "Flag-Vif", "Nef-HA"])
def test_viral_proteins_are_labeled_not_resolved(raw):
    n = norm(raw)
    assert n["kind"] == "viral" and n["lookup"] is None
    assert "viral_protein" in n["rules"]
    assert any("non-human" in note for note in n["notes"])


@pytest.mark.parametrize("raw", ["FLAG", "HA", "GFP", "mCherry", "V5", "myc-tag"])
def test_bare_tags_are_not_proteins(raw):
    n = norm(raw)
    assert n["kind"] == "tag" and n["lookup"] is None
    assert "bare_tag" in n["rules"]


def test_tag_noted_when_protein_remains():
    n = norm("GFP-KRAS")
    assert any("GFP tag" in note for note in n["notes"])
    assert any("lipidated" in note for note in norm("LC3B-II")["notes"])
    assert any("NON-phospho" in note for note in norm("Non-Phos-4EBP1")["notes"])


# --------------------------------------------------------------------------- #
# Names that MUST NOT change (no rule fires, lookup falls back to core_symbol)
# --------------------------------------------------------------------------- #

UNCHANGED = [
    "STAT3", "pSTAT3", "p-AKT", "p53", "p38", "p21", "PARP", "ERK 1/2", "GAPDH",
    "P-cadherin", "t-PA", "pVHL", "beta-actin",
    "α-SMA", "α-catenin", "α-synuclein",     # alpha is part of the name
    "Myc",                                  # bare Myc is the MYC protein, not the tag
    "Tat", "Rev",                           # TAT is a human gene; context needed
    "p55", "p24",                           # host proteins share the name
    "p62", "Sqstm1/p62",                    # shared name, deliberately left alone
    "MAP1LC3B",                             # already a gene symbol
    "Ubiquitin", "Input", "IgG",
    "pTyr-STAT3",                           # phospho-residue prefixes need modification support
    "CASP1/4 p20/p19",                      # two genes in one label
]


@pytest.mark.parametrize("raw", UNCHANGED)
def test_unrelated_names_untouched(raw):
    n = norm(raw)
    assert n["lookup"] is None and n["kind"] is None and n["rules"] == [], n


def test_alpha_prefix_is_not_stripped_from_names():
    assert norm("α-tubulin")["lookup"] is None            # family, not "tubulin"
    assert norm("α-SMA")["rules"] == []


# --------------------------------------------------------------------------- #
# core_symbol / modification detection
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,core", [
    ("β actin", "beta-actin"),             # Greek + space no longer cut to "beta"
    ("α actinin", "alpha-actinin"),
    ("Total-eIF2α", "eIF2alpha"),
    ("Total-4EBP1", "4EBP1"),
    ("Ph-eIF2α", "eIF2alpha"),
    ("Non-Phos-4EBP1", "4EBP1"),
    ("non-phospho-4EBP1", "4EBP1"),
    ("Total protein", "Total"),            # loading control, not a "total-" marker
    ("p53", "p53"), ("PARP", "PARP"), ("P-cadherin", "P-cadherin"), ("t-PA", "t-PA"),
    ("pSTAT3", "STAT3"), ("p-AKT", "AKT"), ("ERK 1/2", "ERK1/2"),
])
def test_core_symbol(raw, core):
    assert biology.core_symbol(raw) == core


def test_ph_prefix_is_phospho_nonphos_is_not():
    assert biology.detect_modification("Ph-eIF2α")["modification_type"] == "phosphorylation"
    # "non-phospho" contains the word "phospho": it must NOT read as phosphorylation
    for raw in ("Non-Phos-4EBP1", "non-phospho-4EBP1", "Non-phospho 4E-BP1"):
        assert biology.detect_modification(raw)["modification_type"] is None, raw
    # PH-20 / lowercase "ph-" are not the abbreviation
    assert biology.detect_modification("PH-20")["modification_type"] is None


def test_cleavage_recorded_only_from_explicit_words():
    mod = biology.detect_modification("α-CASP3 cl. (CASP3 p19 / CASP3 p17)")
    assert mod["modification_type"] == "cleavage" and mod["normalized_label"] == "cleaved"
    assert biology.detect_modification("Cleaved caspase-3")["modification_type"] == "cleavage"
    # a size suffix, "CL" (cell lysate) and a clone "cl." are NOT cleavage claims
    for raw in ("CASP1p10", "CASP1 (p12/10)", "IL-18 CL", "STAT3 (cl. 4G10)", "anti-pTyr (cl. 4G10)"):
        assert biology.detect_modification(raw)["modification_type"] is None, raw


# --------------------------------------------------------------------------- #
# Resolvers (offline)
# --------------------------------------------------------------------------- #

OFFLINE_ACCESSIONS = [
    ("Vinculin", "VCL", "P18206"), ("Bcl-xL", "BCL2L1", "Q07817"), ("GFP-KRAS", "KRAS", "P01116"),
    ("LC3B-II", "MAP1LC3B", "Q9GZQ8"), ("IL-18", "IL18", "Q14116"),
    ("α-CASP1", "CASP1", "P29466"), ("α-CASP3 cl.", "CASP3", "P42574"), ("CASP1p10", "CASP1", "P29466"),
    ("α-CASP7", "CASP7", "P55210"), ("α-GSDMD", "GSDMD", "P57764"), ("α-GSDME", "GSDME", "O60443"),
    ("Active β-catenin", "CTNNB1", "P35222"), ("Ph-eIF2α", "EIF2S1", "P05198"),
    ("Total-eIF2α", "EIF2S1", "P05198"), ("Non-Phos-4EBP1", "EIF4EBP1", "Q13541"),
    ("Mcl-1", "MCL1", "Q07820"), ("Bcl-2", "BCL2", "P10415"), ("Beclin 1", "BECN1", "Q14457"),
    ("SHP-1", "PTPN6", "P29350"), ("SHP2", "PTPN11", "Q06124"), ("Survivin", "BIRC5", "O15392"),
    ("c-Myc", "MYC", "P01106"), ("Cyclin D1", "CCND1", "P24385"), ("Cleaved caspase-3", "CASP3", "P42574"),
    ("β actin", "ACTB", "P60709"),
]


@pytest.mark.parametrize("raw,symbol,acc", OFFLINE_ACCESSIONS)
def test_local_resolver_supported(raw, symbol, acc):
    r = LocalMapResolver().resolve(raw)
    assert (r.status, r.canonical, r.uniprot_id) == ("SUPPORTED", symbol, acc), r


@pytest.mark.parametrize("raw", ["Ras", "Jnk", "LC3-I", "LC3-II", "LC3-I/LC3-II", "MyHC", "α-tubulin", "α-actinin"])
def test_local_resolver_families_stay_ambiguous(raw):
    r = LocalMapResolver().resolve(raw)
    assert r.status == "AMBIGUOUS" and r.uniprot_id is None, r
    assert r.source == "normalization_rule"
    # a family label is only the joined candidate genes, never a single chosen one
    assert r.canonical is None or set(r.canonical.split("/")) == {c["gene"] for c in r.candidates}


@pytest.mark.parametrize("raw", ["Vpr", "Nef", "Vif", "gp120", "FLAG", "Flag-Vif", "Vpr-myc"])
def test_local_resolver_viral_and_tags_missing_with_kind(raw):
    r = LocalMapResolver().resolve(raw)
    assert r.status == "MISSING" and r.canonical is None and r.uniprot_id is None
    assert r.kind in ("viral", "tag") and r.notes


def test_legacy_normalize_protein_matches():
    assert biology.normalize_protein("Vinculin")["uniprot_id"] == "P18206"
    assert biology.normalize_protein("Ras")["status"] == "AMBIGUOUS"
    assert biology.normalize_protein("JNK")["canonical"] == "MAPK8/MAPK9/MAPK10"
    assert biology.normalize_protein("Vpr")["status"] == "MISSING"
    assert biology.normalize_protein("GFP-KRAS")["canonical"] == "KRAS"
    assert biology.normalize_protein("Xyzzy1")["status"] == "MISSING"
    assert biology.normalize_protein("ERK")["status"] == "AMBIGUOUS"      # unchanged


class _SpyPrimary(resolve.ProteinResolver):
    def __init__(self):
        self.calls = []

    def resolve(self, raw_name, organism_id=9606):
        self.calls.append((raw_name, organism_id))
        return ProteinResolution(raw=raw_name, canonical="KRAS", uniprot_id="P01116",
                                 organism="human", status="SUPPORTED", source="uniprot")


def test_caching_resolver_rules_skip_the_network_and_notes_are_not_cached(tmp_path):
    spy = _SpyPrimary()
    r = CachingResolver(spy, cache_path=tmp_path / "cache.json")
    for raw in ("Vpr", "Ras", "LC3-II", "FLAG"):          # settled by rules: primary never asked
        r.resolve(raw)
    assert spy.calls == []
    tagged = r.resolve("GFP-KRAS")
    plain = r.resolve("KRAS")                               # same symbol -> same cache entry
    assert any("GFP tag" in n for n in tagged.notes)
    assert plain.notes == []                                # the tag note did not leak
    assert len(spy.calls) == 1


def test_uniprot_query_uses_the_lookup_symbol_and_organism(monkeypatch):
    seen = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"primaryAccession": "P18206", "genes": [{"geneName": {"value": "VCL"}}],
                                 "sequence": {"molWeight": 116722}}]}

    def fake_get(url, params=None, timeout=None):
        seen["query"] = params["query"]
        return _Resp()

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=fake_get))
    r = resolve.UniProtResolver().resolve("Vinculin", organism_id=10090)
    assert "gene:VCL" in seen["query"] and "organism_id:10090" in seen["query"]
    assert r.status == "SUPPORTED" and r.canonical == "VCL"


# --------------------------------------------------------------------------- #
# Evidence record end to end
# --------------------------------------------------------------------------- #

def _record(raw_target, caption="", antibody_target=None):
    return build_evidence_record({
        "paper": {"doi": "10.x/t"}, "figure": {"page": 1}, "raw_target": raw_target,
        "texts": {"caption": caption, "methods": ""},
        "model_claims": {
            "sample": "HEK293T",
            "antibodies": [{"target": antibody_target or raw_target, "role": "detection",
                            "phospho_specific": False,
                            "source": {"type": "methods", "rank": 3, "text": "anti-" + raw_target}}],
            "bands": [{"lane_index": 1, "lane_condition": "ctrl", "band_state": "present",
                       "confidence": "high"}],
        },
    })


def test_record_tagged_protein_resolves_with_tag_note():
    rec = _record("GFP-KRAS")
    t = rec.target
    assert (t.canonical_target.status, t.canonical_target.value) == ("SUPPORTED", "KRAS")
    assert t.uniprot_id.value == "P01116"
    assert t.raw_target_name == "GFP-KRAS"                  # raw wording preserved
    assert any("GFP tag" in s.text for s in t.canonical_target.sources)


@pytest.mark.parametrize("raw", ["Ras", "JNK", "LC3-II", "MyHC", "α-tubulin"])
def test_record_family_is_ambiguous_and_needs_review(raw):
    rec = _record(raw)
    t = rec.target
    assert t.canonical_target.status == "AMBIGUOUS"
    assert t.uniprot_id.value is None                       # no accession chosen
    assert rec.validation.needs_review is True
    assert "PROTEIN_AMBIGUOUS" in {f.code for f in rec.validation.anomaly_flags}


def test_record_family_keeps_candidates_as_gene_symbols():
    t = _record("JNK").target
    assert t.canonical_target.value == "MAPK8/MAPK9/MAPK10"
    assert [c.value for c in t.canonical_target.candidates] == ["MAPK8", "MAPK9", "MAPK10"]
    rows = _record("JNK").to_supabase_rows()
    assert rows[0]["protein_status"] == "AMBIGUOUS" and rows[0]["uniprot_id"] is None


def test_record_viral_target_is_labeled_non_human():
    rec = _record("Vpr-myc")
    t = rec.target
    assert t.canonical_target.status == "NOT_RECOVERED" and t.canonical_target.value is None
    assert t.target_kind == "viral"
    assert any("non-human" in s.text for s in t.canonical_target.sources)
    flags = {f.code: f for f in rec.validation.anomaly_flags}
    assert flags["NON_HUMAN_TARGET"].severity == "low"      # informational: no status change
    assert rec.to_supabase_rows()[0]["canonical_target"] is None


def test_record_bare_tag_is_labeled_not_a_protein():
    rec = _record("FLAG")
    assert rec.target.target_kind == "tag"
    assert "EPITOPE_TAG_TARGET" in {f.code for f in rec.validation.anomaly_flags}


def test_record_cleaved_caspase_label():
    rec = _record("α-CASP3 cl. (CASP3 p19 / CASP3 p17)")
    assert rec.target.canonical_target.value == "CASP3"
    assert rec.modification.modification_type.value == "cleavage"


def test_record_fragment_suffix_resolves_without_claiming_cleavage():
    rec = _record("CASP1p10")
    assert rec.target.canonical_target.value == "CASP1"
    assert rec.modification.modification_type.value is None


def test_record_phospho_ph_prefix_and_nonphos():
    ph = _record("Ph-eIF2α")
    assert ph.target.canonical_target.value == "EIF2S1"
    assert ph.modification.modification_type.value == "phosphorylation"
    nonphos = _record("Non-Phos-4EBP1")
    assert nonphos.target.canonical_target.value == "EIF4EBP1"
    assert nonphos.modification.modification_type.value != "phosphorylation"


def test_record_unchanged_for_ordinary_target():
    rec = _record("p-STAT3")
    assert rec.target.canonical_target.value == "STAT3" and rec.target.uniprot_id.value == "P40763"
    assert rec.target.target_kind is None
    assert not {"NON_HUMAN_TARGET", "EPITOPE_TAG_TARGET"} & {f.code for f in rec.validation.anomaly_flags}

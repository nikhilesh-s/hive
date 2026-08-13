"""Runnable with either pytest or `python3 test_biology.py`.

These assert the biological rules that MUST hold -- especially the phospho
heuristic fix. If any of these fail, we are making a scientific error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from western_blot_miner import biology as bio  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def check(name: str, condition: bool) -> None:
    CHECKS.append((name, bool(condition)))


# --- The phospho-heuristic bug fix: p<number> proteins are NOT phospho ------
def test_p_number_proteins_are_not_phospho():
    for name in ("p53", "p38", "p21", "p27", "PARP", "p130", "p65"):
        mod = bio.detect_modification(name, caption=f"Immunoblot for {name}", methods="")
        check(f"{name} not phospho", mod["modification_type"] is None)


# --- Explicit phospho WITH site -> supported, site captured -----------------
def test_phospho_with_site():
    mod = bio.detect_modification(
        "phospho-STAT3",
        caption="Immunoblot for phospho-STAT3 (Tyr705)",
        methods="anti-phospho-STAT3 Tyr705, CST #9145",
    )
    check("phospho-STAT3 Tyr705 -> phosphorylation", mod["modification_type"] == "phosphorylation")
    check("phospho-STAT3 Tyr705 -> residue Tyr", mod["residue"] == "Tyr")
    check("phospho-STAT3 Tyr705 -> position 705", mod["residue_position"] == 705)
    check("phospho-STAT3 Tyr705 -> label", mod["normalized_label"] == "phospho-Tyr705")
    check("phospho-STAT3 Tyr705 -> SUPPORTED", mod["status"] == "SUPPORTED")
    check("phospho-STAT3 Tyr705 -> phospho-specific ab", mod["phospho_specific_antibody"] is True)


def test_phospho_akt_ser473():
    mod = bio.detect_modification("p-AKT", caption="p-AKT Ser473 after insulin", methods="")
    check("p-AKT Ser473 -> phospho", mod["modification_type"] == "phosphorylation")
    check("p-AKT Ser473 -> Ser", mod["residue"] == "Ser")
    check("p-AKT Ser473 -> 473", mod["residue_position"] == 473)


def test_pY_one_letter_site():
    # target names the phospho form; caption supplies the site (pY705 -> Tyr705)
    mod = bio.detect_modification("p-STAT3", caption="pY705 signal increased", methods="")
    check("pY705 -> phospho", mod["modification_type"] == "phosphorylation")
    check("pY705 -> Tyr705", mod["residue"] == "Tyr" and mod["residue_position"] == 705)


def test_total_target_not_contaminated_by_sibling_phospho():
    # Shared caption lists BOTH phospho-STAT3 and total STAT3; the total-STAT3
    # row must stay total. This is the core STAT3 != phospho-STAT3 requirement.
    caption = "Immunoblot for phospho-STAT3 (Tyr705) and total STAT3 in HEK293T"
    mod = bio.detect_modification("STAT3", caption=caption, methods="")
    check("total STAT3 stays total", mod["modification_type"] is None)


# --- Phospho WITHOUT a site must NOT invent Tyr705 --------------------------
def test_phospho_without_site_stays_siteless():
    mod = bio.detect_modification("phospho-STAT3", caption="phospho-STAT3 immunoblot", methods="")
    check("phospho no-site -> phospho", mod["modification_type"] == "phosphorylation")
    check("phospho no-site -> residue None", mod["residue"] is None)
    check("phospho no-site -> label 'phospho'", mod["normalized_label"] == "phospho")


# --- Non-phospho modifications only on explicit words -----------------------
def test_cleavage():
    # VLM names the row as shown on the blot ("cleaved PARP")
    mod = bio.detect_modification("cleaved PARP", caption="cleaved PARP", methods="")
    check("cleaved PARP -> cleavage", mod["modification_type"] == "cleavage")


# --- Experiment-type classification -----------------------------------------
def test_co_ip_from_methods_only():
    mod = bio.detect_modification("STAT3", caption="STAT3 blot", methods="")
    exp = bio.classify_experiment(
        "STAT3",
        caption="STAT3 detected after co-immunoprecipitation with EGFR",
        methods="Lysates were immunoprecipitated with anti-EGFR.",
        modification=mod,
    )
    check("co-IP detected", exp["experiment_type"] == "co_ip")
    check("co-IP has evidence", len(exp["evidence"]) >= 1)


def test_co_ip_plus_phospho_non_exclusive():
    mod = bio.detect_modification("phospho-STAT3", caption="phospho-STAT3 (Tyr705)", methods="")
    exp = bio.classify_experiment(
        "phospho-STAT3",
        caption="phospho-STAT3 after co-IP with EGFR",
        methods="immunoprecipitated with EGFR antibody",
        modification=mod,
    )
    check("co_ip primary", exp["experiment_type"] == "co_ip")
    check("phospho_western coexists", "phospho_western" in exp["experiment_flags"])


def test_loading_control():
    exp = bio.classify_experiment("GAPDH", caption="GAPDH loading control", methods="")
    check("GAPDH -> loading_control", exp["experiment_type"] == "loading_control")


def test_standard_western_default():
    mod = bio.detect_modification("STAT3", caption="STAT3 immunoblot", methods="")
    exp = bio.classify_experiment("STAT3", caption="STAT3 immunoblot", methods="", modification=mod)
    check("STAT3 total -> standard_western", exp["experiment_type"] == "standard_western")


def test_never_co_ip_without_text_evidence():
    mod = bio.detect_modification("STAT3", caption="", methods="")
    exp = bio.classify_experiment("STAT3", caption="STAT3 blot", methods="Standard SDS-PAGE.", modification=mod)
    check("no co-IP without evidence", "co_ip" not in exp["experiment_flags"])


# --- Protein normalization ---------------------------------------------------
def test_normalize_protein():
    n = bio.normalize_protein("pSTAT3")
    check("pSTAT3 -> STAT3", n["canonical"] == "STAT3")
    check("pSTAT3 -> UniProt P40763", n["uniprot_id"] == "P40763")
    check("pSTAT3 -> SUPPORTED", n["status"] == "SUPPORTED")

    amb = bio.normalize_protein("ERK")
    check("ERK -> ambiguous (no single UniProt)", amb["status"] == "AMBIGUOUS")

    unknown = bio.normalize_protein("Xyzzy1")
    check("unknown protein -> MISSING, not guessed", unknown["canonical"] is None and unknown["status"] == "MISSING")


def test_deterministic_extractors_exist():
    # site parser handles the canonical notations
    check("Tyr705 parse", bio.parse_phospho_site("Tyr705")["position"] == 705)
    check("Ser 473 parse", bio.parse_phospho_site("Ser 473")["residue"] == "Ser")
    check("pS473 parse", bio.parse_phospho_site("pS473")["residue"] == "Ser")


def test_core_symbol_prefix_and_isoform():
    """core_symbol must strip real modification/total prefixes WITHOUT eating a
    letter that is part of the protein name, and must preserve isoform suffixes.
    Regressions here caused P-ERK 1/2 -> "ERK" -> EPHB2 (a false UniProt friend),
    and p53/p38/PARP -> 53/38/ARP (unresolvable). Surfaced by the first real
    paper (Jang et al., 10.3892/br.2026.2108).
    """
    cs = bio.core_symbol
    # phospho / total prefixes are stripped
    check("p-STAT3 -> STAT3", cs("P-STAT3 (Tyr705)") == "STAT3")
    check("t-STAT3 -> STAT3", cs("T-STAT3") == "STAT3")
    check("pSTAT3 glued -> STAT3", cs("pSTAT3") == "STAT3")
    check("phospho-STAT3 -> STAT3", cs("phospho-STAT3 (Tyr705)") == "STAT3")
    # p<number> and P-initial proteins keep their leading letter
    check("p53 kept", cs("p53") == "p53")
    check("p38 kept", cs("p38") == "p38")
    check("PARP kept", cs("PARP") == "PARP")
    # isoform designation preserved (not collapsed to family false-friend)
    check("P-ERK 1/2 -> ERK1/2", cs("P-ERK 1/2") == "ERK1/2")
    check("T-ERK 1/2 -> ERK1/2", cs("T-ERK 1/2") == "ERK1/2")


def test_one_letter_site_in_phospho_marked_label():
    """'p-AKT (S473)' style labels (extremely common) must yield the site: the
    phospho marker and one-letter site travel in the same short label, which
    satisfies the phospho-context guard. Surfaced by the second real paper
    (PMC12706926) where residue came back empty."""
    for label, res_, pos in [("p-AKT (S473)", "Ser", 473),
                             ("p-RPS6KB1 (T389)", "Thr", 389),
                             ("p-EIF4EBP1 (S65)", "Ser", 65)]:
        m = bio.detect_modification(label)
        check(f"{label} is phospho", m["modification_type"] == "phosphorylation")
        check(f"{label} residue {res_}{pos}",
              m["residue"] == res_ and m["residue_position"] == pos)
    # bare one-letter forms WITHOUT a phospho marker still never claim a site
    m = bio.detect_modification("AKT S473")
    check("no phospho marker -> no phospho from bare S473",
          m["modification_type"] is None)


def test_phospho_specific_antibody_flag_prevents_false_total():
    """Uppercase 'P-' is never a phospho MARKER (P-selectin, P-cadherin are
    protein names) — but an explicit phospho_specific antibody claim is real
    evidence. 'P-ERK 1/2' + phospho-specific CST #4370 must NOT settle as
    total; it stays unsettled (CONFLICTING, value null, needs_review)."""
    from western_blot_miner.record_builder import build_evidence_record
    case = {
        "paper": {"doi": "10.x/t"}, "figure": {"page": 1},
        "raw_target": "P-ERK 1/2", "texts": {"caption": "", "methods": ""},
        "model_claims": {
            "sample": "Hep3B",
            "antibodies": [{"target": "P-ERK 1/2", "vendor": "CST", "catalog": "4370",
                            "role": "detection", "phospho_specific": True,
                            "source": {"type": "methods", "rank": 3,
                                       "text": "p-ERK (1:1,000; CST #4370)"}}],
            "bands": [{"lane_index": 1, "lane_condition": "x",
                       "band_state": "present", "confidence": "high"}],
        },
    }
    rec = build_evidence_record(case)
    mt = rec.modification.modification_type
    check("P-ERK + phospho-ab does not settle as total",
          not (mt.status == "SUPPORTED" and mt.value is None))
    check("P-ERK + phospho-ab unsettled -> value null + review",
          mt.value is None and rec.validation.needs_review)
    # A genuinely total antibody (phospho_specific False) still settles total.
    case2 = dict(case, raw_target="T-ERK 1/2")
    case2["model_claims"] = dict(case["model_claims"])
    case2["model_claims"]["antibodies"] = [{
        "target": "T-ERK 1/2", "vendor": "CST", "catalog": "4695",
        "role": "detection", "phospho_specific": False,
        "source": {"type": "methods", "rank": 3, "text": "t-ERK (CST #4695)"}}]
    rec2 = build_evidence_record(case2)
    mt2 = rec2.modification.modification_type
    check("T-ERK + total-ab settles total",
          mt2.status == "SUPPORTED" and mt2.value is None)


def test_bare_mention_is_not_a_total_claim():
    """A pathway sentence ('PI3K/AKT/mTOR signaling') must not be read as an
    explicit 'AKT is unmodified' claim — that manufactured fake MODIFICATION_
    CONFLICTs against real phospho rows (PMC12706926, page 10). Explicit
    'total X' wording still asserts total; mixed forms still abstain."""
    cm = bio.caption_modification_for_core
    check("bare pathway mention -> abstain",
          cm("AKT", "BEX2 impairs PI3K/AKT/mTOR signaling in NSCLC.") is None)
    check("explicit total -> none-claim",
          cm("STAT3", "Total STAT3 levels remained constant.")["modification_type"] is None)
    check("T- prefix -> none-claim",
          cm("STAT3", "T-STAT3 was blotted.")["modification_type"] is None)
    check("phospho-only mention -> phospho claim",
          cm("STAT3", "pSTAT3 blot.")["modification_type"] == "phosphorylation")
    check("mixed phospho + bare forms -> abstain",
          cm("STAT3", "pSTAT3 and STAT3 were blotted.") is None)


def test_co_ip_requires_panel_scoped_evidence():
    """A methods paragraph about immunoprecipitation must not reclassify every
    panel on the page as co_ip; panel-scoped evidence (IP-role antibody, co-IP
    caption, or IP:/IgG lane labels) is required. Surfaced by PMC12706926 where
    autophagy/mTOR expression panels all came back co_ip."""
    from western_blot_miner.record_builder import build_evidence_record
    methods_blob = ("Cells were lysed... For co-immunoprecipitation, lysates were "
                    "immunoprecipitated with anti-PIK3CA... antibodies: anti-LC3B (2775)...")
    base = {
        "paper": {"doi": "10.x/test"},
        "figure": {"page": 1},
        "texts": {"caption": "", "methods": methods_blob},
    }
    # Expression panel: NO panel-scoped IP evidence -> NOT co_ip.
    case = dict(base, raw_target="LC3B", model_claims={
        "sample": "H1299",
        "antibodies": [{"target": "LC3B", "vendor": "CST", "catalog": "2775",
                        "role": "detection", "phospho_specific": False,
                        "source": {"type": "methods", "rank": 3, "text": "anti-LC3B (2775)"}}],
        "bands": [{"lane_index": 1, "lane_condition": "DMSO", "band_state": "present",
                   "confidence": "high"}],
    })
    rec = build_evidence_record(case)
    check("methods-only co-IP mention does not settle co_ip",
          rec.experiment.experiment_type.value != "co_ip")
    check("methods mention preserved as co_ip_context flag",
          "co_ip_context" in (rec.experiment.experiment_flags.value or []))
    # Same page, but the panel's lanes say IP:/IgG -> IS co_ip.
    case2 = dict(base, raw_target="BEX2", model_claims={
        "sample": "H1299",
        "antibodies": [{"target": "BEX2", "vendor": "Santa Cruz", "catalog": "SC-398486",
                        "role": "detection", "phospho_specific": False,
                        "source": {"type": "methods", "rank": 3, "text": "anti-BEX2"}}],
        "bands": [{"lane_index": 1, "lane_condition": "Input", "band_state": "present", "confidence": "high"},
                  {"lane_index": 2, "lane_condition": "IgG", "band_state": "absent", "confidence": "high"},
                  {"lane_index": 3, "lane_condition": "IP:PIK3CA", "band_state": "present", "confidence": "high"}],
    })
    rec2 = build_evidence_record(case2)
    check("IP:/IgG lane labels settle co_ip", rec2.experiment.experiment_type.value == "co_ip")


def test_organism_taxon_mapping():
    """Explicit organism wording scopes the UniProt query; anything else keeps
    the previous human default. The map must never invent an organism."""
    check("human -> 9606", bio.organism_taxon_id("human") == 9606)
    check("Mouse -> 10090", bio.organism_taxon_id("Mouse") == 10090)
    check("Mus musculus -> 10090", bio.organism_taxon_id("Mus musculus") == 10090)
    check("rat -> 10116", bio.organism_taxon_id("rat") == 10116)
    check("None -> default 9606", bio.organism_taxon_id(None) == 9606)
    check("unknown wording -> default 9606", bio.organism_taxon_id("zebrafish-ish") == 9606)


def test_erk_family_not_a_false_friend_offline():
    """The curated map must mark ERK-family shorthand ambiguous (ERK1/ERK2), so
    it is never collapsed to a single accession -- offline resolver check."""
    from western_blot_miner import resolve
    r = resolve.LocalMapResolver()
    for label in ("P-ERK 1/2", "T-ERK 1/2", "ERK", "p44/42 MAPK"):
        res = r.resolve(label)
        check(f"{label} ambiguous ERK1/2", res.status == "AMBIGUOUS"
              and res.canonical == "MAPK1/MAPK3" and res.uniprot_id is None)
    # p53 / PARP must resolve to the right protein via the curated map
    check("p53 -> TP53 offline", r.resolve("p53").uniprot_id == "P04637")
    check("PARP -> PARP1 offline", r.resolve("PARP").uniprot_id == "P09874")


def run() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    passed = sum(1 for _, ok in CHECKS if ok)
    failed = [name for name, ok in CHECKS if not ok]
    print(f"\n{passed}/{len(CHECKS)} biological checks passed")
    if failed:
        print("FAILED:")
        for name in failed:
            print(f"  - {name}")
        return 1
    print("All biological rules hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

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

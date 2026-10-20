"""B-13: Northern / Southern / gel-stain / zymography / EMSA panels are not westerns.

Rule under test (biology.classify_non_western): the PANEL must say so (row target,
lane labels, sibling rows) AND the caption/methods must name the technique.
Run: python3 -m pytest western_blot_miner/tests/test_non_western.py
"""
import json
import tempfile
from pathlib import Path

from western_blot_miner import biology
from western_blot_miner.evidence_record import ExtractionMeta
from western_blot_miner.extract_records import extract_records_from_claims, records_to_supabase_rows
from western_blot_miner.llm_client import MockLLMClient
from western_blot_miner.pipeline import run_records_stage
from western_blot_miner.resolve import LocalMapResolver
from western_blot_miner.supabase_loader import enrich_biological_fields

META = ExtractionMeta(stage="deterministic+llm", backend="mock", model="fixture")
NORTHERN = ("Figure 2. Northern blot of total RNA from HeLa cells after arsenite, probed for "
            "pre-rRNA processing intermediates.")


def _row(target, lanes=("Ctrl", "AsO2"), antibodies=()):
    return {"raw_target": target, "sample": "HeLa", "antibodies": list(antibodies),
            "bands": [{"lane_index": i, "lane_condition": c, "band_state": "present", "confidence": "high"}
                      for i, c in enumerate(lanes, 1)]}


def _ab(target):
    return {"target": target, "role": "detection", "phospho_specific": False,
            "source": {"type": "methods", "rank": 3, "text": f"anti-{target}"}}


def _records(rows, caption="", methods="", doi="10.1000/b13"):
    ctx = {"paper": {"doi": doi}, "figure": {"figure_label": "Figure 2", "panel_label": "A", "page": 4},
           "texts": {"caption": caption, "methods": methods}}
    return extract_records_from_claims(ctx, {"rows": rows}, LocalMapResolver(), META)


def _by_target(records):
    return {r.target.raw_target_name: r for r in records}


def test_rrna_northern_rows_are_flagged_and_the_western_row_in_the_same_paper_is_not():
    recs = _by_target(_records(
        [_row("47S/46S/45S"), _row("28S"), _row("18S-E"), _row("30S (34S*)"),
         _row("β-Actin", antibodies=[_ab("β-Actin")])],
        caption=NORTHERN, methods="Proteins were separated by SDS-PAGE and probed with anti-β-Actin."))
    for t in ("47S/46S/45S", "28S", "18S-E", "30S (34S*)"):
        r = recs[t]
        assert r.experiment.experiment_type.value == "non_western", t
        assert "northern_blot" in r.experiment.experiment_flags.value
        assert r.validation.needs_review is True and r.validation.record_status == "AMBIGUOUS"
        flag = next(a for a in r.validation.anomaly_flags if a.code == "NON_WESTERN_PANEL")
        assert flag.severity == "high" and any("Northern blot" in s.text for s in flag.evidence)
    actin = recs["β-Actin"]
    assert actin.experiment.experiment_type.value == "loading_control"
    assert not [a for a in actin.validation.anomaly_flags if a.code == "NON_WESTERN_PANEL"]


def test_non_western_rows_stay_out_of_the_western_rows_unless_asked():
    records = _records([_row("28S"), _row("18S"), _row("β-Actin", antibodies=[_ab("β-Actin")])],
                       caption=NORTHERN)
    rows = records_to_supabase_rows(records)
    assert [r["raw_target_name"] for r in rows] == ["β-Actin", "β-Actin"]
    everything = records_to_supabase_rows(records, include_non_western=True)
    assert len(everything) == 6
    r28 = next(r for r in everything if r["raw_target_name"] == "28S")
    assert r28["experiment_type"] == "non_western" and r28["needs_review"] is True
    assert r28["anomaly_flags"][0]["code"] == "NON_WESTERN_PANEL"


def test_flagging_never_moves_the_record_identity():
    flagged = _records([_row("28S")], caption=NORTHERN)[0]
    plain = _records([_row("28S")], caption="Figure 2. 28S levels.")[0]
    assert flagged.experiment.experiment_type.value == "non_western"
    assert plain.experiment.experiment_type.value != "non_western"
    assert flagged.record_id == plain.record_id


def test_a_western_that_only_mentions_rna_extraction_is_not_flagged():
    recs = _records(
        [_row("STAT3", antibodies=[_ab("STAT3")]), _row("GAPDH", antibodies=[_ab("GAPDH")])],
        caption="Figure 3. Western blot of STAT3 in HEK293T after IL-6.",
        methods="Total RNA was extracted with TRIzol for qPCR. Lysates were immunoblotted for STAT3.")
    for r in recs:
        assert r.experiment.experiment_type.value != "non_western"
        assert not [a for a in r.validation.anomaly_flags if a.code == "NON_WESTERN_PANEL"]
    assert len(records_to_supabase_rows(recs)) == 4


def test_northern_wording_alone_never_flags_a_protein_row():
    # the caption channel is page-level text: a Northern paragraph on the page says nothing about this row
    recs = _records([_row("Total-eIF2α", antibodies=[_ab("eIF2α")]), _row("TIA1", antibodies=[_ab("TIA1")])],
                    caption=NORTHERN)
    assert all(r.experiment.experiment_type.value != "non_western" for r in recs)


def test_a_nucleic_acid_name_alone_never_flags_without_technique_wording():
    assert biology.classify_non_western("18S", "Western blot of lysates.", "Total RNA was extracted.") is None
    assert biology.classify_non_western("26S", "Western blot for the proteasome.", "") is None
    # a protein that merely contains the S-value text is not a species
    assert biology.classify_non_western("26S proteasome", NORTHERN, "") is None
    assert biology.classify_non_western("U1-70K", NORTHERN, "") is None
    assert biology.classify_non_western("U2OS", NORTHERN, "") is None


def test_other_rna_species_and_prime_spacers():
    for t in ("U6", "U6 snRNA", "tRNA-Met", "5S rRNA", "5.8S", "5' ETS", "5′ETS", "ITS1", "SNORD14", "miR-21"):
        hit = biology.classify_non_western(t, NORTHERN, "")
        assert hit and hit["kind"] == "northern_blot", t


def test_southern_blot():
    cap = "Southern blot of EcoRI-digested genomic DNA from targeted clones."
    hit = biology.classify_non_western("genomic DNA", cap, "")
    assert hit and hit["kind"] == "southern_blot"
    assert biology.classify_non_western("genomic DNA", "Western blot of lysates.", "") is None


def test_zymography_needs_panel_labels_and_wording():
    rec = _records([_row("MMP-9", lanes=("gelatin zymography ctrl", "TNF"))],
                   caption="Gelatin zymography of conditioned media.")[0]
    assert rec.experiment.experiment_type.value == "non_western"
    assert "zymography" in rec.experiment.experiment_flags.value
    # same wording on the page, but this panel's labels do not say zymography
    other = _records([_row("MMP-9", antibodies=[_ab("MMP-9")])],
                     caption="MMP-9 western blot. Gelatin zymography is shown in Fig. 5.")[0]
    assert other.experiment.experiment_type.value != "non_western"


def test_emsa_needs_panel_labels_and_wording():
    methods = "Binding reactions were analysed by EMSA on a 5% native gel."
    rec = _records([_row("NF-κB", lanes=("free probe", "+ nuclear extract", "supershift"))],
                   caption="Figure 4.", methods=methods)[0]
    assert rec.experiment.experiment_type.value == "non_western"
    assert "emsa" in rec.experiment.experiment_flags.value
    other = _records([_row("NF-κB", antibodies=[_ab("NF-κB")])], caption="Figure 4.", methods=methods)[0]
    assert other.experiment.experiment_type.value != "non_western"


def test_gel_stain_is_non_western_only_when_it_is_the_whole_panel():
    cap = "Coomassie-stained SDS-PAGE gel of purified fractions."
    alone = _records([_row("Coomassie")], caption=cap)[0]
    assert alone.experiment.experiment_type.value == "non_western"
    assert "gel_stain" in alone.experiment.experiment_flags.value
    # Ponceau S as a loading control under a western stays a loading control
    pair = _by_target(_records([_row("STAT3", antibodies=[_ab("STAT3")]), _row("Ponceau S")],
                               caption="Western blot of STAT3; Ponceau S stain of the membrane."))
    assert pair["Ponceau S"].experiment.experiment_type.value == "loading_control"
    assert pair["STAT3"].experiment.experiment_type.value != "non_western"
    # unknown siblings (no panel_targets) never flags a stain
    assert biology.classify_non_western("Ponceau S", "Ponceau S stained membrane.", "") is None


def test_legacy_enrichment_agrees():
    row = enrich_biological_fields("28S", caption=NORTHERN)
    assert row["experiment_type"] == "non_western" and row["needs_review"] is True
    assert "northern_blot" in row["experiment_flags"]
    western = enrich_biological_fields("STAT3", caption="Western blot of STAT3.", methods="Total RNA was extracted.")
    assert western["experiment_type"] != "non_western"


def test_pipeline_withholds_non_western_rows_but_keeps_the_records():
    output = {"rows": [_row("28S"), _row("18S"), _row("β-Actin", antibodies=[_ab("β-Actin")])]}
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        crop = run_dir / "page_004_cand_0001.png"  # absent on purpose -> no image
        (run_dir / "llm_candidates.json").write_text(json.dumps(
            [{"paper_id": "10.1000/b13", "page": 4, "candidate_path": str(crop), "cv_score": 0.8}]))
        (run_dir / "candidate_contexts.jsonl").write_text(json.dumps(
            {"candidate_path": str(crop), "page": 4, "text_context": NORTHERN}) + "\n")
        summary = {"out_dir": str(run_dir), "paper_id": "10.1000/b13", "extracted_doi": "10.1000/b13"}
        result = run_records_stage(summary, use_cache=False, client=MockLLMClient(output),
                                   resolver=LocalMapResolver())
        assert result["records"] == 3 and result["non_western_withheld"] == 2
        assert result["rows"] == 2
        rows = json.loads((run_dir / "supabase_rows.json").read_text())
        assert {r["raw_target_name"] for r in rows} == {"β-Actin"}
        recs = json.loads((run_dir / "evidence_records.json").read_text())
        flagged = [r for r in recs if r["experiment"]["experiment_type"]["value"] == "non_western"]
        assert {r["target"]["raw_target_name"] for r in flagged} == {"28S", "18S"}

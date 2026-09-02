"""Researcher-facing shaping of list and detail responses (UCSF beta pass).

Stored provenance is the reviewed corpus and is never modified; these tests
pin what the API SHOWS of it:
- review_reasons: plain-language reasons derived only from stored flags
- image_crop_ref: filename only (the stored authoring path leaked a username)
- internal envelope markers ("ambiguous_family", "{}", "") never render as
  quoted source text; null candidates are dropped; the modification
  candidate "none" is relabeled as the claim it is (total protein)
- detail anomaly messages come from the engine's `detail` key
"""

from app.record_detail import build_record_detail
from app.schemas import RecordDetail, WesternBlotRecord, review_reasons_from_flags

FLAGS = [
    {"code": "PROTEIN_AMBIGUOUS", "severity": "med",
     "detail": "Protein name maps to more than one reviewed UniProt entry.",
     "evidence": [{"rank": 4, "text": "internal"}]},
    {"code": "MODIFICATION_CONFLICT", "severity": "high",
     "detail": "Sources disagree on whether this is a modified or total protein.",
     "evidence": []},
    {"code": "PROTEIN_AMBIGUOUS", "severity": "med",
     "detail": "Protein name maps to more than one reviewed UniProt entry."},
]

ABS_REF = "/Users/someone/hive/western_blot_miner/data/pdf_runs/10.x/panel_candidates/page_004_cand_0025.png"


def test_review_reasons_ordered_by_severity_and_deduplicated():
    reasons = review_reasons_from_flags(FLAGS)
    assert reasons == [
        "Sources disagree on whether this is a modified or total protein.",
        "Protein name maps to more than one reviewed UniProt entry.",
    ]


def test_review_reasons_fall_back_to_code_when_no_detail():
    assert review_reasons_from_flags([{"code": "MW_DISCREPANCY"}]) == ["Mw discrepancy"]
    assert review_reasons_from_flags([]) == []


def test_list_row_derives_reasons_and_trims_flag_evidence():
    row = WesternBlotRecord(id=1, paper_id="p", anomaly_flags=FLAGS, needs_review=True,
                            image_crop_ref=ABS_REF)
    assert row.review_reasons[0].startswith("Sources disagree")
    assert all(set(f) == {"code", "severity", "detail"} for f in row.anomaly_flags)
    assert "internal" not in str(row.anomaly_flags)


def test_list_and_detail_expose_crop_filename_only():
    row = WesternBlotRecord(id=1, paper_id="p", image_crop_ref=ABS_REF)
    assert row.image_crop_ref == "page_004_cand_0025.png"
    assert WesternBlotRecord(id=1, paper_id="p", image_crop_ref=None).image_crop_ref is None
    d = RecordDetail(id=1, image_crop_ref=ABS_REF)
    assert d.image_crop_ref == "page_004_cand_0025.png"
    assert "/Users" not in d.model_dump_json()


def _env(value, status, sources=(), candidates=()):
    return {"value": value, "confidence": 0.5, "status": status,
            "sources": list(sources), "candidates": list(candidates)}


def test_detail_hides_internal_markers_and_relabels_total_claim():
    row = {
        "id": 7, "raw_target_name": "P-ERK 1/2", "image_crop_ref": ABS_REF,
        "anomaly_flags": FLAGS[:2],
        "validation": {"record_status": "CONFLICTING"},
        "provenance": {
            "target": {
                "canonical_target": _env("MAPK1/MAPK3", "AMBIGUOUS",
                                         sources=[{"type": "uniprot_reference", "text": "ambiguous_family"}],
                                         candidates=[{"value": None, "source_type": "uniprot_reference"}]),
                "uniprot_id": _env(None, "AMBIGUOUS",
                                   sources=[{"type": "uniprot_reference", "text": "{}"}],
                                   candidates=[{"value": None, "source_type": "uniprot_reference"}]),
            },
            "modification": {
                "modification_type": _env(None, "CONFLICTING", candidates=[
                    {"value": "phosphorylation", "source_type": "antibody", "confidence": 0.9},
                    {"value": "none", "source_type": "model_target", "confidence": 0.6},
                ]),
            },
            "sample": {"cell_line": _env("Hep3B", "SUPPORTED",
                                         sources=[{"type": "figure_caption", "text": ""}])},
        },
    }
    d = build_record_detail(row)
    canon = d.fields["canonical_target"]
    assert canon.value == "MAPK1/MAPK3" and canon.status == "AMBIGUOUS"
    assert canon.sources == [{"type": "uniprot_reference", "text": None}]   # type kept, marker gone
    assert canon.candidates == []                                          # null candidate dropped
    assert d.fields["uniprot_id"].sources == [{"type": "uniprot_reference", "text": None}]
    mod = d.fields["modification_type"]
    assert [c["value"] for c in mod.candidates] == ["phosphorylation", "no modification (total protein)"]
    assert d.fields["cell_line"].sources[0]["text"] is None
    blob = d.model_dump_json()
    assert "ambiguous_family" not in blob and '"{}"' not in blob and "/Users" not in blob
    # detail flags carry the engine's plain-language `detail` as message
    assert d.anomaly_flags[0]["message"].startswith("Protein name maps")
    assert d.review_reasons[0].startswith("Sources disagree")


def test_detail_keeps_real_source_wording():
    row = {"id": 1, "provenance": {"sample": {"cell_line": _env(
        "Hep3B", "SUPPORTED", sources=[{"type": "figure_caption", "text": "Hep3B cells were treated"}])}}}
    d = build_record_detail(row)
    assert d.fields["cell_line"].sources == [{"type": "figure_caption", "text": "Hep3B cells were treated"}]


def test_lane_measures_drop_float_noise():
    row = {"id": 1, "provenance": {"bands": [
        {"lane_index": 1, "lane_condition": _env("30 min", "SUPPORTED"),
         "band_state": _env("present", "SUPPORTED"),
         "lane_duration": _env(30.0, "SUPPORTED"), "lane_duration_unit": _env("min", "SUPPORTED"),
         "lane_dose": _env(0.5, "SUPPORTED"), "lane_dose_unit": _env("µM", "SUPPORTED")},
    ]}}
    b = build_record_detail(row).bands[0]
    assert b.lane_duration == "30 min" and b.lane_dose == "0.5 µM"

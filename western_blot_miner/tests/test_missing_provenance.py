"""Missing-data provenance contract: source silence != extraction failure."""
from api.app.record_detail import build_record_detail
from western_blot_miner.evidence_record import (
    MISSING,
    NOT_RECOVERED,
    NOT_STATED,
    EvidenceField,
    _v,
)


def test_explicit_missing_constructors_and_projection():
    stated = EvidenceField.not_stated()
    recovered = EvidenceField.not_recovered()
    legacy = EvidenceField.missing()

    assert stated.status == NOT_STATED and stated.value is None
    assert recovered.status == NOT_RECOVERED and recovered.value is None
    assert legacy.status == MISSING and legacy.value is None
    assert _v(stated) is None
    assert _v(recovered) is None
    assert _v(legacy) is None


def test_record_detail_preserves_new_statuses_and_antibody_statuses():
    row = {
        "id": 1,
        "provenance": {
            "modification": {
                "modification_type": {
                    "value": None,
                    "confidence": 0.0,
                    "status": "NOT_STATED",
                    "sources": [],
                    "candidates": [],
                },
                "reported_dummy": {},
            },
            "experiment": {},
            "sample": {},
            "treatment": {},
            "molecular_weight": {
                "reported_kda": {
                    "value": None,
                    "confidence": 0.0,
                    "status": "NOT_RECOVERED",
                    "sources": [],
                    "candidates": [],
                },
            },
            "antibodies": [{
                "role": "detection",
                "antibody_target": {
                    "value": "STAT3", "status": "SUPPORTED",
                    "confidence": 0.9, "sources": [], "candidates": [],
                },
                "vendor": {
                    "value": None, "status": "NOT_STATED",
                    "confidence": 0.0, "sources": [], "candidates": [],
                },
                "catalog_number": {
                    "value": None, "status": "NOT_RECOVERED",
                    "confidence": 0.0, "sources": [], "candidates": [],
                },
                "clone": {
                    "value": None, "status": "MISSING",
                    "confidence": 0.0, "sources": [], "candidates": [],
                },
                "dilution": {
                    "value": None, "status": "NOT_STATED",
                    "confidence": 0.0, "sources": [], "candidates": [],
                },
            }],
            "bands": [],
        },
        "validation": {},
        "anomaly_flags": [],
    }

    detail = build_record_detail(row)
    assert detail.fields["modification_type"].status == "NOT_STATED"
    assert detail.fields["reported_molecular_weight_kda"].status == "NOT_RECOVERED"
    assert detail.antibodies[0].vendor_status == "NOT_STATED"
    assert detail.antibodies[0].catalog_number_status == "NOT_RECOVERED"
    assert detail.antibodies[0].clone_status == "MISSING"
    assert detail.antibodies[0].dilution_status == "NOT_STATED"

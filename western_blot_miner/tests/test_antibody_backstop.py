"""B-2: deterministic antibody backstop in record_builder._antibody_info."""
from western_blot_miner.evidence_record import MISSING, SUPPORTED, RANK_METHODS
from western_blot_miner.record_builder import build_evidence_record

TEXT = "anti-β-actin (Cell Signaling, #4967, 1:1000)"


def _record(ab_extra: dict, text: str = TEXT):
    ab = {"target": "β-actin", "role": "detection", "phospho_specific": False,
          "source": {"type": "methods", "rank": 3, "text": text}, **ab_extra}
    return build_evidence_record({
        "raw_target": "β-actin", "texts": {"caption": "", "methods": text},
        "model_claims": {"antibodies": [ab], "bands": []},
    })


def test_empty_model_fields_recovered_deterministically():
    ab = _record({}).antibodies[0]
    assert ab.vendor.value == "Cell Signaling Technology"
    assert ab.catalog_number.value == "4967"
    assert ab.dilution.value == "1:1000"
    for f in (ab.vendor, ab.catalog_number, ab.dilution):
        assert f.status == SUPPORTED
        assert [s.type for s in f.sources] == ["deterministic"]
        assert f.sources[0].text == TEXT
        assert f.sources[0].rank > RANK_METHODS  # never outranks model/methods


def test_model_catalog_not_overwritten_when_text_disagrees():
    ab = _record({"catalog": "9145"}).antibodies[0]
    assert ab.catalog_number.value == "9145"
    assert ab.catalog_number.status == SUPPORTED
    assert [s.type for s in ab.catalog_number.sources] == ["methods"]
    # disagreement is recorded, not settled
    assert [c.value for c in ab.catalog_number.candidates] == ["4967"]
    assert ab.catalog_number.candidates[0].source_type == "deterministic"
    # agreeing text (modulo '#') adds no candidate
    ab2 = _record({"catalog": "#4967"}).antibodies[0]
    assert ab2.catalog_number.value == "#4967" and ab2.catalog_number.candidates == []


def test_no_text_leaves_fields_missing():
    ab = _record({}, text="").antibodies[0]
    for f in (ab.vendor, ab.catalog_number, ab.dilution, ab.clone):
        assert f.status == MISSING and f.value is None


def test_deterministic_confidence_never_above_model_default():
    det = _record({}).antibodies[0]
    model = _record({"vendor": "Cell Signaling", "catalog": "4967", "dilution": "1:1000"}).antibodies[0]
    for name in ("vendor", "catalog_number", "dilution"):
        assert getattr(det, name).confidence <= getattr(model, name).confidence
        assert getattr(det, name).confidence <= 0.9


MULTI = ("Membranes were probed with anti-p-STAT3 (Tyr705) (Cell Signaling, #9145, 1:1000) "
         "and anti-\u03b2-actin (Santa Cruz, sc-47778, 1:5000).")


def test_multi_antibody_sentence_is_scoped_to_this_target():
    ab = _record({}, text=MULTI).antibodies[0]
    assert ab.catalog_number.value == "sc-47778"
    assert ab.vendor.value == "Santa Cruz Biotechnology"
    assert ab.dilution.value == "1:5000"


def test_multi_antibody_sentence_without_this_target_abstains():
    text = "anti-p-STAT3 (Cell Signaling, #9145, 1:1000) and anti-GAPDH (Abcam, ab8245, 1:2000)."
    ab = _record({}, text=text).antibodies[0]      # record target is beta-actin: not in the sentence
    for f in (ab.vendor, ab.catalog_number, ab.dilution):
        assert f.status == MISSING

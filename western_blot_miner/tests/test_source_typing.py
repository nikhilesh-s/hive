"""A Source's type must match where its text actually comes from."""
from western_blot_miner.evidence_record import MISSING, RANK_METHODS, RANK_MODEL_TARGET
from western_blot_miner.record_builder import build_evidence_record


def _rec(caption="", methods="", **mc):
    return build_evidence_record({"raw_target": "STAT3", "texts": {"caption": caption, "methods": methods},
                                  "model_claims": {"antibodies": [], "bands": [], **mc}})


def _ab_rec(text, methods, caption=""):
    ab = {"target": "STAT3", "role": "detection", "source": {"type": "methods", "rank": 3, "text": text}}
    return _rec(caption, methods, antibodies=[ab]).antibodies[0]


METHODS = "Primary antibodies: anti-STAT3 (Cell Signaling, #9139, 1:1000) were used."


def test_antibody_source_verbatim_in_methods_is_methods():
    ab = _ab_rec("anti-STAT3 (Cell Signaling, #9139, 1:1000)", METHODS)
    assert [(s.type, s.rank) for s in ab.antibody_target.sources] == [("methods", RANK_METHODS)]


def test_antibody_paraphrase_is_model_claim():
    ab = _ab_rec("STAT3 (CST #9139; 1:1,000)", METHODS)
    assert [(s.type, s.rank) for s in ab.antibody_target.sources] == [("model_target", RANK_MODEL_TARGET)]


def test_antibody_nonbreaking_hyphen_still_verbatim():
    ab = _ab_rec("anti‑STAT3 (Cell Signaling, #9139, 1:1000)", METHODS)
    assert ab.antibody_target.sources[0].type == "methods"


def test_antibody_verbatim_in_caption_is_caption():
    ab = _ab_rec("anti-STAT3 (#9139)", "", caption="Blots probed with anti-STAT3 (#9139).")
    assert ab.antibody_target.sources[0].type == "figure_caption"


def test_backstop_does_not_fill_from_paraphrase():
    ab = _ab_rec("anti-STAT3 (Cell Signaling, #9139, 1:1000)", "Antibodies are listed in Table S1.")
    for f in (ab.vendor, ab.catalog_number, ab.dilution):
        assert f.status == MISSING
    # same text verbatim in methods -> backstop fills
    assert _ab_rec("anti-STAT3 (Cell Signaling, #9139, 1:1000)", METHODS).catalog_number.value == "9139"


def test_treatment_wording_not_in_caption_is_not_caption():
    t = _rec("Figure 2. STAT3 in HeLa cells.", "",
             treatment_name="IL-6", treatment_context="treated with IL-6 at 10 ng/ml for 30 min").treatment
    assert all(s.type != "figure_caption" for s in t.treatment_context.sources + t.treatment_name.sources)
    assert t.treatment_context.sources[0].type == "model_target"
    verbatim = _rec("HeLa cells were treated with IL-6 at 10 ng/ml for 30 min.", "",
                    treatment_context="treated with IL-6 at 10 ng/ml for 30 min").treatment
    assert verbatim.treatment_context.sources[0].type == "figure_caption"


def test_sample_value_absent_from_caption_has_no_caption_source():
    s = _rec("In the sham operation group, STAT3 was evaluated.", "",
             sample="mouse submandibular gland tissue", organism="mouse").sample
    for f in (s.sample, s.cell_line, s.organism):
        for src in f.sources:
            assert src.type != "figure_caption" or str(f.value).lower() in src.text.lower()
    assert s.sample.sources[0].type == "model_target"
    # value present -> caption snippet that names it; organism not borrowed from sample snippet
    s2 = _rec("STAT3 in NSCLC cell line H1299.", "", cell_line="H1299", organism="human").sample
    assert s2.cell_line.sources[0].type == "figure_caption" and "H1299" in s2.cell_line.sources[0].text
    assert s2.organism.sources[0].type == "model_target"



def test_treatment_dose_from_model_wording_is_not_deterministic():
    from western_blot_miner.record_builder import build_evidence_record
    base = {"raw_target": "STAT3", "model_claims": {"antibodies": [], "bands": [],
            "treatment_name": "IL-6", "treatment_context": "Hep3B cells treated with IL-6 (10 ng/ml) for 30 min"}}
    para = build_evidence_record({**base, "texts": {"caption": "Figure 1. STAT3 after cytokine.", "methods": ""}})
    assert para.treatment.dose.value is not None
    assert [x.type for x in para.treatment.dose.sources] == ["model_target"]
    verb = build_evidence_record({**base, "texts": {"caption": "Hep3B cells treated with IL-6 (10 ng/ml) for 30 min", "methods": ""}})
    assert [x.type for x in verb.treatment.dose.sources] == ["deterministic"]
    assert verb.treatment.dose.value == para.treatment.dose.value



def _coip_record(caption, lane_condition):
    from western_blot_miner.record_builder import build_evidence_record
    return build_evidence_record({
        "raw_target": "p85", "texts": {"caption": caption, "methods": ""},
        "model_claims": {"antibodies": [], "bands": [{"lane_index": 1, "lane_condition": lane_condition, "band_state": "present"}]},
    })


def test_coip_bait_from_lane_labels_is_image_evidence():
    rec = _coip_record("Figure 4. Interaction analysis in H1299 cells.", "Co-IP anti-PIK3CA")
    bait = rec.experiment.ip_bait_protein
    assert bait.value == "PIK3CA"
    assert [x.type for x in bait.sources] == ["image"]


def test_coip_bait_from_caption_is_caption_evidence_with_caption_text():
    caption = "Figure 4. Co-IP with anti-PIK3CA pulled down p85 in H1299 cells."
    rec = _coip_record(caption, "IgG")
    bait = rec.experiment.ip_bait_protein
    assert bait.value is not None
    assert [x.type for x in bait.sources] == ["figure_caption"]
    assert bait.sources[0].text in caption

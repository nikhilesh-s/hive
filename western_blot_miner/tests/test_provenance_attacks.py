"""Provenance attacks: antibody attribution scope, MW source typing, text-context split."""
from western_blot_miner.evidence_record import MISSING
from western_blot_miner.pipeline import _split_text_context
from western_blot_miner.record_builder import build_evidence_record

H1, H2 = "LIKELY_FIGURE_OR_CAPTION_CONTEXT:", "PAPER_SAMPLE_OR_METHODS_SNIPPETS:"


def _ab(target, text):
    ab = {"target": target, "role": "detection", "source": {"type": "methods", "rank": 3, "text": text}}
    return build_evidence_record({
        "raw_target": target, "texts": {"caption": "", "methods": text},
        "model_claims": {"antibodies": [ab], "bands": []},
    }).antibodies[0]


# D1: target not named -> abstain, even for a single-antibody text.
def test_single_fragment_without_target_abstains():
    ab = _ab("STAT3", "anti-GAPDH (Abcam ab8245, 1:5000)")
    for f in (ab.vendor, ab.catalog_number, ab.dilution):
        assert f.status == MISSING
    assert _ab("STAT3", "GAPDH (Abcam, ab8245, 1:5000) was the loading control").dilution.status == MISSING


# D2: neighbour values listed without "anti-" are not stolen.
def test_unprefixed_neighbour_dilution_not_attached():
    ab = _ab("ACTB", "GAPDH (1:5000) and ACTB (Abcam ab8227) antibodies were used")
    assert ab.dilution.status == MISSING
    assert ab.catalog_number.value == "ab8227"


def test_antibodies_against_list_catalog_not_attached():
    ab = _ab("ACTB", "Antibodies against GAPDH (Abcam ab8245, 1:5000) and ACTB (Sigma A5441) were used")
    assert ab.catalog_number.value != "ab8245"
    assert ab.dilution.status == MISSING


def test_semicolon_inside_parentheses_does_not_split_scope():
    ab = _ab("GAPDH", "primary antibodies: STAT3 (#9139; 1:500), GAPDH (#2118; 1:5000)")
    assert ab.dilution.value == "1:5000"
    assert ab.catalog_number.value == "2118"


def test_multiple_distinct_values_in_scope_abstain():
    ab = _ab("STAT3", "anti-STAT3 (CST #9139 and #12640, 1:1000)")
    assert ab.catalog_number.status == MISSING
    assert ab.dilution.value == "1:1000"


# D3: alphanumeric boundaries on the target.
def test_target_is_not_matched_as_substring():
    assert _ab("ERK", "anti-ERK5 (CST #3372) and anti-GAPDH (CST #2118)").catalog_number.status == MISSING
    assert _ab("actin", "anti-GAPDH (CST #2118) and anti-alpha-actinin (sc-17829)").catalog_number.status == MISSING


# D7: reported MW source typed by channel, text verbatim; expected MW untouched.
def _mw(caption, methods):
    return build_evidence_record({"raw_target": "STAT3", "texts": {"caption": caption, "methods": methods},
                                  "model_claims": {"antibodies": [], "bands": []}}).molecular_weight


def test_methods_derived_mw_is_typed_methods_with_verbatim_text():
    methods = "STAT3 (88 kDa) was detected"
    mw = _mw("Figure 1. STAT3 in HeLa.", methods)
    assert mw.reported_kda.value == 88.0
    [src] = mw.reported_kda.sources
    assert src.type == "methods" and src.text and src.text in methods
    assert all(s.type == "uniprot_reference" for s in mw.expected_kda.sources)


def test_caption_derived_mw_is_typed_caption_with_verbatim_text():
    caption = "STAT3 (~88 kDa)"
    [src] = _mw(caption, "").reported_kda.sources
    assert src.type == "figure_caption" and src.text and src.text in caption


# P4: header parsing.
def test_split_strips_headers_and_concatenates_caption_sections():
    cap, meth = _split_text_context(f"PRE\n{H1}\nCap one.\n{H1}\nCap two.\n{H2}\nMethods here.\n")
    assert "Cap one." in cap and "Cap two." in cap
    assert H1 not in cap and H2 not in meth and H1 not in meth
    assert "Methods here." in meth and "PRE" in meth and "Methods" not in cap


def test_split_ignores_header_quoted_mid_line_and_methods_first_order():
    cap, meth = _split_text_context(f'PRE says "{H1}" here\n{H1}\nCap.\n{H2}\nMeth.')
    assert cap == "Cap." and meth.startswith('PRE says "') and "Meth." in meth
    cap, meth = _split_text_context(f"{H2}\nMeth.\n{H1}\nCap.\n")
    assert cap == "Cap." and meth == "Meth."


# P5: IP/IgG/input lane markers come from the image lane labels, not the caption.
def test_ip_lane_marker_is_image_evidence():
    r = build_evidence_record({
        "raw_target": "STAT3", "texts": {"caption": "Figure 1. STAT3 blot.", "methods": ""},
        "model_claims": {"antibodies": [], "bands": [{"lane_index": 1, "lane_condition": "IgG", "band_state": "present"}]},
    })
    assert "co_ip" in (r.experiment.experiment_flags.value or [])
    ip_sources = [s for f in (r.experiment.experiment_type, r.experiment.experiment_flags)
                  for s in f.sources if "IgG" in s.text]
    assert ip_sources and all(s.type == "image" for s in ip_sources)

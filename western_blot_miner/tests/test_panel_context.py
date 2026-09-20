"""B-1: _panel_context routes the pdf_preprocess blob into caption vs methods."""
from western_blot_miner.pipeline import _panel_context

CAPTION = "Figure 3. Western blot of p-STAT3 (Tyr705) in HEK293T after IL-6."
METHODS = "Cells were lysed in RIPA; anti-STAT3 (CST #4904, 1:1000)."
BLOB = (
    "\nPAPER_ID: 10.1000/x\nCROP_PAGE: 5\n\nNEARBY_PAGE_TEXT:\nlanes 1-4\n\n"
    f"LIKELY_FIGURE_OR_CAPTION_CONTEXT:\n{CAPTION}\n\n"
    f"PAPER_SAMPLE_OR_METHODS_SNIPPETS:\n{METHODS}\n"
)


def test_split_routes_caption_and_methods():
    texts = _panel_context({}, {}, BLOB)["texts"]
    assert texts["caption"] == CAPTION
    assert METHODS in texts["methods"]
    assert CAPTION not in texts["methods"]
    assert METHODS not in texts["caption"]
    assert "LIKELY_FIGURE_OR_CAPTION_CONTEXT" not in texts["caption"]
    assert "NEARBY_PAGE_TEXT" in texts["methods"]  # preamble is not dropped


def test_no_headers_keeps_everything_under_methods():
    blob = "just some page text with anti-STAT3 (CST #4904)"
    texts = _panel_context({}, {}, blob)["texts"]
    assert texts["caption"] == ""
    assert texts["methods"] == blob

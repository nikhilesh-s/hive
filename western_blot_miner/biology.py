"""Deterministic biological interpretation for Western blot evidence.

This module is intentionally dependency-free (standard library only) so it can
run and be unit-tested anywhere -- no anthropic, no opencv, no network. It holds
the *rules* that must not be delegated to an LLM because getting them wrong is a
scientific error, not a style choice:

  * modification detection (esp. phosphorylation) with EVIDENCE, not a
    ``target.startswith("p")`` heuristic;
  * phospho-site (residue + position) parsing;
  * experiment-type classification from METHODS/CAPTION text (never from the
    image alone -- co-IP is a claim about the assay, not the picture);
  * loading-control recognition;
  * conservative protein-name normalization with an explicit "ambiguous" state.

Every function returns both the value *and* where it came from, so the product
can always answer "why did HiveBlot say this?".
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

# --------------------------------------------------------------------------- #
# Reference vocabularies
# --------------------------------------------------------------------------- #

# Housekeeping / loading-control proteins. Matched case-insensitively against a
# normalized target token, so "beta-actin" and "b-actin" both hit "actin".
LOADING_CONTROLS: tuple[str, ...] = (
    "actin",
    "actb",        # gene symbol — "β-actin" matched but "ACTB" did not (QA M7)
    "b-actin",
    "beta-actin",
    "gapdh",
    "tubulin",
    "tuba1b",      # alpha-tubulin 1B gene symbol
    "alpha-tubulin",
    "vinculin",
    "hsp90",
    "hsp70",
    "lamin b",
    "lamin b1",
    "lamin a/c",
    "histone h3",
    "cyclophilin",
    "ponceau",
    "total protein",
)

# Antibody vendors we can recognize deterministically. Kept small and explicit;
# extend as researchers confirm more. Value = normalized vendor label.
VENDORS: dict[str, str] = {
    "cell signaling": "Cell Signaling Technology",
    "cst": "Cell Signaling Technology",
    "abcam": "Abcam",
    "santa cruz": "Santa Cruz Biotechnology",
    "sigma": "Sigma-Aldrich",
    "sigma-aldrich": "Sigma-Aldrich",
    "millipore": "Millipore (Merck)",
    "merck": "Millipore (Merck)",
    "thermo": "Thermo Fisher Scientific",
    "thermofisher": "Thermo Fisher Scientific",
    "thermo fisher": "Thermo Fisher Scientific",
    "invitrogen": "Thermo Fisher Scientific",
    "bd biosciences": "BD Biosciences",
    "r&d systems": "R&D Systems",
    "proteintech": "Proteintech",
    "bethyl": "Bethyl Laboratories",
    "genetex": "GeneTex",
    "novus": "Novus Biologicals",
    "biolegend": "BioLegend",
}

# Residue three-letter <-> one-letter for phospho-site normalization.
_RESIDUE_ONE_TO_THREE = {"y": "Tyr", "s": "Ser", "t": "Thr"}
_RESIDUE_THREE = {"tyr": "Tyr", "ser": "Ser", "thr": "Thr"}

# Minimal, curated protein alias -> (canonical symbol, UniProt) map. This is a
# deterministic offline stand-in; a live UniProt resolver can augment it in a
# later stage. Only high-confidence, unambiguous mappings live here.
PROTEIN_ALIASES: dict[str, tuple[str, Optional[str]]] = {
    "stat3": ("STAT3", "P40763"),
    "p-stat3": ("STAT3", "P40763"),
    "pstat3": ("STAT3", "P40763"),
    "phospho-stat3": ("STAT3", "P40763"),
    "akt": ("AKT1", "P31749"),
    "akt1": ("AKT1", "P31749"),
    "pkb": ("AKT1", "P31749"),
    "p-akt": ("AKT1", "P31749"),
    "p53": ("TP53", "P04637"),
    "tp53": ("TP53", "P04637"),
    "trp53": ("TP53", "P04637"),
    "erk": ("MAPK1/MAPK3", None),    # ERK is ambiguous (ERK1/ERK2) -> no single UniProt
    "erk1/2": ("MAPK1/MAPK3", None),
    "p44/42": ("MAPK1/MAPK3", None), # CST's name for total ERK1/2 (p44/42 MAPK)
    "mapk1/2": ("MAPK1/MAPK3", None),
    "p38": ("MAPK14", "Q16539"),
    "gapdh": ("GAPDH", "P04406"),
    "actin": ("ACTB", "P60709"),
    "beta-actin": ("ACTB", "P60709"),
    "b-actin": ("ACTB", "P60709"),
    "egfr": ("EGFR", "P00533"),
    "parp": ("PARP1", "P09874"),
    "parp1": ("PARP1", "P09874"),
    # B-12: the gene symbols that the name rules in normalize_target() map TO,
    # keyed by lowercase symbol. Accessions are UniProtKB reviewed HUMAN entries
    # checked against rest.uniprot.org on 2026-10-19 (the offline fallback is
    # human-only like every entry above; the live resolver is organism-scoped).
    "vcl": ("VCL", "P18206"),
    "bcl2l1": ("BCL2L1", "Q07817"),
    "kras": ("KRAS", "P01116"),
    "map1lc3a": ("MAP1LC3A", "Q9H492"),
    "map1lc3b": ("MAP1LC3B", "Q9GZQ8"),
    "map1lc3c": ("MAP1LC3C", "Q9BXW4"),
    "il18": ("IL18", "Q14116"),
    "casp1": ("CASP1", "P29466"),
    "casp3": ("CASP3", "P42574"),
    "casp7": ("CASP7", "P55210"),
    "gsdmd": ("GSDMD", "P57764"),
    "gsdme": ("GSDME", "O60443"),
    "ctnnb1": ("CTNNB1", "P35222"),
    "eif2s1": ("EIF2S1", "P05198"),
    "eif4ebp1": ("EIF4EBP1", "Q13541"),
    "mcl1": ("MCL1", "Q07820"),
    "bcl2": ("BCL2", "P10415"),
    "becn1": ("BECN1", "Q14457"),
    "ptpn6": ("PTPN6", "P29350"),
    "ptpn11": ("PTPN11", "Q06124"),
    "birc5": ("BIRC5", "O15392"),
    "myc": ("MYC", "P01106"),
    "ccnd1": ("CCND1", "P24385"),
}

# Organism wording -> NCBI taxonomy id, for scoping the UniProt query. Only
# explicit, unambiguous wordings map; anything else falls back to human (9606),
# which was the previous unconditional behavior. Never used to *invent* an
# organism claim — the claimed organism string is preserved separately.
ORGANISM_TAXON: dict[str, int] = {
    "human": 9606, "homo sapiens": 9606,
    "mouse": 10090, "mus musculus": 10090, "murine": 10090, "mice": 10090,
    "rat": 10116, "rattus norvegicus": 10116, "rats": 10116,
}
DEFAULT_TAXON = 9606


def organism_taxon_id(organism: Optional[str]) -> int:
    """Taxon id for an explicitly claimed organism string (default: human)."""
    if not organism:
        return DEFAULT_TAXON
    return ORGANISM_TAXON.get(_norm(organism).lower(), DEFAULT_TAXON)


# Proteins whose name legitimately starts with "p" + digits and must NEVER be
# auto-classified as phospho. (Documented guard; the regex handles the general
# case, this is belt-and-suspenders for the well-known ones.)
P_NUMBER_PROTEINS = {
    "p53", "p63", "p73", "p38", "p21", "p27", "p16", "p65", "p50",
    "p130", "p107", "p120", "p62", "p45", "p90", "p70", "p110",
}

# Proteins whose leading "P-"/"t-" is part of the NAME, not a phospho/total
# prefix: P-cadherin (CDH3), P-selectin (SELP), P-glycoprotein / P-gp (ABCB1),
# t-PA (PLAT). Matched case-insensitively on the first token.
NAME_PREFIX_PROTEINS = {"p-cadherin", "p-selectin", "p-glycoprotein", "p-gp", "t-pa"}
# p-names that are never phosphorylation by name: pVHL (von Hippel-Lindau),
# pRB (retinoblastoma), Pgp (ABCB1), plus the hyphenated names above.
NON_PHOSPHO_P_NAMES = NAME_PREFIX_PROTEINS | {"pvhl", "prb", "pgp"}

# --------------------------------------------------------------------------- #
# Regexes
# --------------------------------------------------------------------------- #

# Strong site notation with an explicit residue name: "Ser473", "Tyr 705".
_SITE_THREE = re.compile(r"\b(Tyr|Thr|Ser)[\s\-]?(\d{1,4})\b", re.IGNORECASE)
# "p" + one-letter residue + position: "pY705", "pS473", "pT180".
_SITE_P_ONE = re.compile(r"\bp[\s\-]?([YST])[\s\-]?(\d{1,4})\b")
# One-letter residue + position, e.g. "Y705" -- only trusted inside phospho
# context (guarded in code) because "S1"/"T2" collide with figure labels.
_SITE_ONE = re.compile(r"\b([YST])(\d{2,4})\b")
# "phospho" word in any spelling: phospho, phospho-, phosphorylated, phosphorylation.
_PHOSPHO_WORD = re.compile(r"phospho", re.IGNORECASE)
# Hyphenated phospho prefix on a symbol: "p-STAT3", "p-AKT".
_PHOSPHO_HYPHEN = re.compile(r"\bp-\s?[A-Za-z]")
# Glued phospho prefix on an UPPERCASE symbol: "pSTAT3", "pAKT" (not p53).
_PHOSPHO_GLUED = re.compile(r"\bp([A-Z]{2,}[A-Za-z0-9/]*)")
# Phospho-specific antibody phrasing.
_PHOSPHO_AB = re.compile(r"phospho[-\s]?specific|anti[-\s]?phospho|phospho[-\s]?\w+\s+antibod", re.IGNORECASE)

# Other modifications -- only asserted on explicit words.
_MOD_WORDS = {
    # "cl." is the explicit abbreviation of "cleaved" ("α-CASP3 cl."). Anchored to the
    # END of the label / a following parenthetical so an antibody clone written
    # "(cl. 4G10)" is never read as cleavage. Bare "CL" (cell lysate) is NOT matched.
    "cleavage": re.compile(r"\bcleav(ed|age)\b|\bcl\.(?=\s*(?:\(|$))", re.IGNORECASE),
    "ubiquitination": re.compile(r"\bubiquitin|poly[-\s]?ub\b|\bK\d{1,3}[-\s]?linked", re.IGNORECASE),
    "acetylation": re.compile(r"\bacetyl|\bac-K\d", re.IGNORECASE),
    "methylation": re.compile(r"\bmethylat|\btri[-\s]?methyl|\bme3\b", re.IGNORECASE),
    "sumoylation": re.compile(r"\bsumoylat|\bSUMO\b", re.IGNORECASE),
}

# Experiment-type evidence (must come from TEXT, never the image).
_CO_IP = re.compile(
    r"co[-\s]?immunoprecipitat|co[-\s]?ip\b|\bpull[-\s]?down|pulled\s+down|immunoprecipitat",
    re.IGNORECASE,
)
# Panel-scoped IP markers as printed ON the figure itself: "IP: PIK3CA" column
# headers and IgG-control lanes. Used to scope co-IP classification to the
# panel, so a methods paragraph about a co-IP elsewhere in the paper does not
# reclassify every unrelated panel on the page.
_IP_LANE = re.compile(r"\bIP\s*[:.]|\bIgG\b|\binput\b", re.IGNORECASE)
_PURIFIED = re.compile(
    r"\brecombinant\b|purified\s+protein|in\s+vitro\s+(?:binding|kinase|translat)|GST[-\s]?tag|His[-\s]?tag",
    re.IGNORECASE,
)
_INPUT_BLOT = re.compile(r"\binput\b", re.IGNORECASE)

# Catalog number: "#9145", "cat. no. 9145", "ab32157", "sc-482".
_CATALOG = re.compile(
    # full digit run plus an optional 1-2 letter suffix ("5174s", "20200728"), never a truncated prefix
    r"(?:\bcat(?:alog)?\.?\s*(?:no\.?|#|number)?\s*|#)\s*([A-Za-z]{0,3}[-\s]?\d{3,}[A-Za-z]{0,2})(?![\w-])",
    re.IGNORECASE,
)
_CATALOG_VENDORCODE = re.compile(r"\b(ab\d{3,7}|sc[-\s]?\d{3,7})\b", re.IGNORECASE)
# Antibody dilution: "1:1000".
# "1:1,000" and "1:100,000" keep their thousands groups (callers strip the commas);
# "1:500, 1:1000" still yields two separate values.
_DILUTION = re.compile(r"\b1\s?:\s?(\d{1,3}(?:,\d{3})+|\d{2,6})(?!\d|,\d{3}\b)")
# Molecular weight: "86 kDa", "~120 kDa".
_KDA = re.compile(r"(~?\s?\d{1,4}(?:\.\d+)?)\s?kDa", re.IGNORECASE)
# Dose: "20 ng/mL", "10 uM", "0.2 umol/L".
_DOSE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?(ng/ml|[uµμ]g/ml|mg/ml|nmol/l|[uµμ]mol/l|mmol/l|nm|[uµμ]m|mm|mg/kg|ng/kg|%)\b",
    re.IGNORECASE,
)
# Duration: "30 min", "24 h", "48 hours". NOT case-insensitive for the
# single-letter units: "Fig 3D" / "Fig. 3H" are FIGURE PANEL references and
# "3D culture" is a dimensionality, yet a global IGNORECASE read them as
# 3 days / 3 hours — a fabricated duration rendered as "IL-6 · 3D" in the UI
# (manual-test issue 3). Durations in papers are written lowercase ("3 d",
# "24 h", "30 min"); multi-letter units stay case-insensitive via (?i:...).
_DURATION = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?((?i:hrs?|hours?|mins?|minutes?|days?)|[hd])\b")

# A number immediately preceded by a figure/panel reference is a FIGURE
# NUMBER, never a dose or duration ("Fig 3D", "Figure 2, 4 h exposure" keeps
# the 4 h — only the number the reference points at is guarded).
_FIG_REF_BEFORE = re.compile(
    r"(?i)\b(?:fig(?:ure)?s?\.?|panels?|supp(?:lementary)?\.?(?:\s+fig(?:ure)?s?\.?)?)\s*$")


def is_figure_reference_number(text: str, num_start: int) -> bool:
    """True when the number starting at ``num_start`` follows a figure/panel
    reference and must not be read as a dose/duration value."""
    return bool(_FIG_REF_BEFORE.search(text[max(0, num_start - 20):num_start]))
# Enumerated series that share ONE trailing unit: "10, 30 and 60 ug/ml",
# "0, 5, 10, 20, 30, 60 min". The plain _DOSE/_DURATION regexes only match the
# final value (the earlier numbers carry no adjacent unit), which silently
# collapses a dose-response or time course to a single scalar.
# Leading (?<![\w.]) guard: without it the series regex started matching INSIDE
# an identifier — "BafA1, 20 nM" captured "1, 20 nM" and fabricated a 1 nM dose
# candidate from the trailing digit of the drug's NAME (independent QA, M6).
_DOSE_SERIES = re.compile(
    r"(?<![\w.])((?:\d+(?:\.\d+)?\s*(?:,|;|/|\bor\b|\band\b)\s*)+\d+(?:\.\d+)?)\s*"
    r"(ng/ml|[uµμ]g/ml|mg/ml|nmol/l|[uµμ]mol/l|mmol/l|nm|[uµμ]m|mm|mg/kg|ng/kg|%)\b",
    re.IGNORECASE,
)
_DURATION_SERIES = re.compile(
    r"(?<![\w.])((?:\d+(?:\.\d+)?\s*(?:,|;|/|(?i:\bor\b)|(?i:\band\b))\s*)+\d+(?:\.\d+)?)\s*"
    r"((?i:hrs?|hours?|mins?|minutes?|days?)|[hd])\b",
)
# Explicit "this figure varies it per lane" phrasing. Presence means a single
# scalar is NOT attributable to the panel even if only one value is parseable.
# Kind-specific: "for the indicated times" must not make the (single, settled)
# stimulus CONCENTRATION ambiguous, and vice versa.
_INDICATED_TIME = re.compile(
    r"\bindicated\s+(times?|time\s*points?|durations?|intervals?)\b", re.IGNORECASE)
_INDICATED_DOSE = re.compile(
    r"\bindicated\s+(doses?|concentrations?|amounts?)\b", re.IGNORECASE)

# --------------------------------------------------------------------------- #
# Band multiplicity / pattern (DESCRIPTIVE ONLY)
# --------------------------------------------------------------------------- #
# What the source SAYS the blot shows. This is not densitometry, not image
# segmentation, and never an inference from protein identity: "LC3B" does not
# imply a doublet, and "ubiquitin" does not imply a ladder -- only explicit
# wording (or an explicit observer claim) counts. Isoform / cleavage-product /
# dimer interpretation is deliberately NOT derived here; those are biochemical
# claims the wording alone does not license.
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

_BAND_DOUBLET = re.compile(r"\bdoublets?\b", re.IGNORECASE)
_BAND_SMEAR = re.compile(r"\bsmears?\b|\bsmear(?:ed|ing)\b|\bdiffuse\s+(?:band|signal)\b", re.IGNORECASE)
# high-MW alternation is PLURAL-ONLY: "a higher molecular weight band" is the
# standard phrasing for a SINGLE upshifted band (phospho/SUMO/mono-Ub/glyco
# forms) and must never become a "ladder" claim (review finding B2).
_BAND_LADDER = re.compile(
    r"\bladder[-\s]?like\b|\b(?:poly[-\s]?ubiquitin|polyubiquitin)\s+(?:ladder|smear|species|conjugates?)\b"
    r"|\bhigh(?:er)?[-\s]molecular[-\s]?weight\s+(?:species|forms|bands|conjugates)\b",
    re.IGNORECASE,
)
# "two bands", "three distinct bands", "2 bands"
_BAND_COUNT = re.compile(
    r"\b(two|three|four|five|six|\d{1,2})\s+(?:distinct\s+|discrete\s+|separate\s+|major\s+)?bands?\b",
    re.IGNORECASE,
)
# Immediately-preceding context that makes a "<number> bands" match NOT a
# multiplicity statement: figure/panel/lane references ("Fig. 3 bands" ranges
# like "1-2 bands", "n = 3 bands").
_COUNT_CONTEXT_GUARD = re.compile(
    r"(?:fig\.?|figure|panel|lane|lanes)\s*$|n\s*=\s*$|[\d][\s]*[–\-]\s*$", re.IGNORECASE)
# Negation directly governing a pattern mention: "no smearing", "without
# additional bands", "did not detect a doublet". Negated multiplicity is the
# STANDARD antibody-specificity boilerplate; asserting the pattern from it
# would invert the paper's claim (review finding B1). We ABSTAIN — a negated
# mention is not read as evidence of "single" either.
_NEGATION_GUARD = re.compile(
    r"\b(?:no|not|without|neither|nor|lack(?:s|ed|ing)?|absence\s+of|free\s+of|"
    r"did\s+not|does\s+not|do\s+not)\b[^.;]{0,40}$", re.IGNORECASE)
_BAND_MULTIPLE = re.compile(
    r"\bmultiple\s+bands?\b|\bseveral\s+bands?\b|\badditional\s+bands?\b|\bextra\s+bands?\b"
    r"|\bunexpected\s+bands?\b|\bnon[-\s]?specific\s+bands?\b",
    re.IGNORECASE,
)
_BAND_SINGLE = re.compile(r"\b(?:a\s+)?single\s+band\b|\bone\s+band\b", re.IGNORECASE)
# Hedged wording keeps multiplicity UNCERTAIN rather than asserting a pattern.
_BAND_HEDGE = re.compile(
    r"\b(?:may|might|could|possibly|possible|appears?\s+to|seem(?:s|ed)?\s+to|"
    r"unclear|ambiguous|difficult\s+to)\b", re.IGNORECASE)

# Recognized pattern vocabulary (order = precedence when several co-occur).
BAND_PATTERNS = ("smear", "ladder", "doublet", "multiple", "single", "uncertain")


def detect_band_pattern(*texts: str) -> Optional[dict]:
    """Descriptive band pattern from EXPLICIT source wording, or None.

    Returns ``{"pattern", "count", "raw", "hedged"}`` where ``count`` is filled
    only when the text literally states one ("two bands" -> 2). Returns None
    when the text says nothing about multiplicity -- callers must then leave the
    field MISSING rather than assume "single".
    """
    for text in texts:
        if not text:
            continue
        hedged = bool(_BAND_HEDGE.search(text))
        # (kind, raw, count, span) — spans let us (a) drop matches whose
        # wording is negated, and (b) prune a match fully contained inside a
        # more specific one ("polyubiquitin smear" matches both the smear and
        # the ladder regex on overlapping text; that is ONE ladder statement,
        # not two conflicting descriptions).
        found: list[tuple[str, str, Optional[int], tuple[int, int]]] = []

        def _negated(start: int) -> bool:
            return bool(_NEGATION_GUARD.search(text[max(0, start - 45): start]))

        for m in _BAND_SMEAR.finditer(text):
            if not _negated(m.start()):
                found.append(("smear", m.group(0), None, m.span()))
        for m in _BAND_LADDER.finditer(text):
            if not _negated(m.start()):
                found.append(("ladder", m.group(0), None, m.span()))
        for m in _BAND_DOUBLET.finditer(text):
            if not _negated(m.start()):
                found.append(("doublet", m.group(0), 2, m.span()))
        for m in _BAND_COUNT.finditer(text):
            if _negated(m.start()) or _COUNT_CONTEXT_GUARD.search(text[max(0, m.start() - 12): m.start()]):
                continue
            raw_n = m.group(1).lower()
            n = _NUMBER_WORDS.get(raw_n) or (int(raw_n) if raw_n.isdigit() else None)
            if n is not None and n >= 2:
                found.append(("doublet" if n == 2 else "multiple", m.group(0), n, m.span()))
        for m in _BAND_MULTIPLE.finditer(text):
            if not _negated(m.start()):
                found.append(("multiple", m.group(0), None, m.span()))
        for m in _BAND_SINGLE.finditer(text):
            if not _negated(m.start()):
                found.append(("single", m.group(0), 1, m.span()))
        if not found:
            continue
        # Containment pruning: keep only matches not inside a longer match.
        pruned = [f for f in found if not any(
            g is not f and g[3][0] <= f[3][0] and f[3][1] <= g[3][1]
            and (g[3][1] - g[3][0]) > (f[3][1] - f[3][0]) for g in found)]
        # Several distinct patterns in one statement -> do not pick a winner.
        kinds = {k for k, _, _, _ in pruned}
        if len(kinds) > 1:
            raw = "; ".join(r for _, r, _, _ in pruned)
            return {"pattern": "uncertain", "count": None, "raw": raw, "hedged": True}
        kind, raw, count, _span = pruned[0]
        return {"pattern": "uncertain" if hedged else kind,
                "count": None if hedged else count, "raw": raw, "hedged": hedged}
    return None


# Identifiers.
_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_PMID = re.compile(r"\bPMID:?\s*(\d{6,9})\b", re.IGNORECASE)
_PMCID = re.compile(r"\bPMC(\d{5,9})\b", re.IGNORECASE)
_UNIPROT = re.compile(r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _norm(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _token(target: Optional[str]) -> str:
    """Lowercased, de-prefixed target token for vocabulary matching."""
    t = _norm(target).lower()
    t = re.sub(r"^(phospho[-\s]?|p[-\s])", "", t)  # strip a leading phospho marker
    return t.strip()


def _ev(source: str, text: str) -> dict:
    """A single provenance entry."""
    return {"type": source, "text": _norm(text)[:300]}


def _first_snippet(pattern: re.Pattern, *texts_with_src: tuple[str, str]) -> Optional[dict]:
    """Return an evidence dict for the first text in which ``pattern`` matches."""
    for src, text in texts_with_src:
        if not text:
            continue
        m = pattern.search(text)
        if m:
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            return _ev(src, text[start:end])
    return None


# --------------------------------------------------------------------------- #
# Phospho-site parsing
# --------------------------------------------------------------------------- #

def parse_phospho_site(*texts: str) -> Optional[dict]:
    """Return {'residue': 'Tyr', 'position': 705, 'raw': 'Tyr705'} or None.

    Only strong, position-bearing notations are accepted:
      * three-letter residue + number  (Tyr705, Ser 473)
      * p + one-letter residue + number (pY705, pS473)
    Bare one-letter forms (Y705) are handled by the caller only once phospho
    context is already established, to avoid colliding with figure labels.
    """
    for text in texts:
        if not text:
            continue
        m = _SITE_THREE.search(text)
        if m:
            residue = _RESIDUE_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
        m = _SITE_P_ONE.search(text)
        if m:
            residue = _RESIDUE_ONE_TO_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
    return None


def _one_letter_site_in_context(*texts: str) -> Optional[dict]:
    for text in texts:
        if not text:
            continue
        m = _SITE_ONE.search(text)
        if m:
            residue = _RESIDUE_ONE_TO_THREE[m.group(1).lower()]
            return {"residue": residue, "position": int(m.group(2)), "raw": _norm(m.group(0))}
    return None


# --------------------------------------------------------------------------- #
# Modification detection  (the phospho-heuristic replacement)
# --------------------------------------------------------------------------- #

def _greek(s: str) -> str:
    """Greek letters -> spelled-out forms so "β-actin" reaches the alias map /
    UniProt as "beta-actin" (raw wording is preserved elsewhere). A Greek word
    followed by a SPACE is glued with a hyphen ("β actin" -> "beta-actin"):
    the first-token split would otherwise cut the label down to "beta"."""
    s = s.replace("β", "beta").replace("α", "alpha")
    return re.sub(r"(?i)\b(alpha|beta)\s+(?=[A-Za-z])", r"\1-", s)


# Leading modification/expression markers that are NOT part of the protein name
# (stripped for IDENTITY only; the modification layer decides what they mean):
#   non-phos[pho]-  antibody to the NON-phosphorylated form (4E-BP1)
#   phospho-/p-/t-  phospho / total (separator REQUIRED, so p53, p38, PARP keep their p)
#   total-          total-protein marker ("Total-eIF2α"); "Total protein" is a loading control
#   Ph-             case-sensitive abbreviation of phospho ("Ph-eIF2α")
_MOD_PREFIX = re.compile(
    r"^(?:non[-\s]?phos(?:pho)?[-\s]?|phospho[-\s]?|total[-\s](?!protein\b)|(?-i:Ph)-(?=[A-Za-z])|[pt][-\s])",
    re.IGNORECASE)


def _strip_mod_prefix(s: str) -> str:
    """Drop a leading phospho/total/non-phospho marker, never a letter that is
    part of the protein's own name (P-cadherin, t-PA, p53, PARP)."""
    if re.split(r"[\s(]+", s.strip())[0].lower() in NAME_PREFIX_PROTEINS:  # P-cadherin, t-PA keep their prefix
        return s
    s = _MOD_PREFIX.sub("", s, count=1)
    # glued lowercase-p phospho prefix on an uppercase symbol: pSTAT3, pERK.
    return re.sub(r"^p([A-Z]{2,})", r"\1", s)


def _core_symbol(target: str) -> str:
    """Gene symbol with a leading phospho/total marker and any site stripped.

    Strips ONLY genuine modification/expression prefixes, and never a "p"/"P"
    that is part of the protein's own name:
      * "phospho-" / "phospho " (any case).
      * "p-" / "p " and total-protein "t-" / "t " -- a separator is REQUIRED, so
        p53, p38, PARP keep their leading letter (the old ``p[-\\s]?`` stripped a
        lone "p"/"P", mangling p53->53, p38->38, PARP->ARP, and left "t-" alone).
      * a glued *lowercase* "p" before an UPPERCASE run (pSTAT3, pERK) -- but not
        uppercase "P" (PARP) and not "p"+digits (p53).
    A trailing isoform designation is preserved and glued ("ERK 1/2" -> "ERK1/2")
    so a family label does not collapse to a bare-symbol false-friend (UniProt
    ``gene:ERK`` resolves to EPHB2, whose gene synonym is literally "ERK").
    """
    s = _greek(_norm(target))
    s = _strip_mod_prefix(s)
    tokens = re.split(r"[\s(]+", s.strip())
    core = tokens[0] if tokens else ""
    # Glue a trailing pure-isoform token (digits / slashes): "ERK 1/2" -> "ERK1/2".
    if len(tokens) > 1 and re.fullmatch(r"[0-9/]+", tokens[1] or ""):
        core = core + tokens[1]
    return core.strip(" -()")


def _target_has_phospho_marker(target: str) -> bool:
    """True only when the TARGET NAME itself denotes phosphorylation.

    This is what prevents STAT3 (total) from being contaminated by a sibling
    'phospho-STAT3' band described in the same caption -- modification identity
    comes from the per-row target label, not the shared caption.
    """
    low = target.lower()
    # "non-phospho-4EBP1" / "Non-Phos-4EBP1" is an antibody to the NON-phosphorylated
    # form: the word "phospho" inside it must not read as a phospho marker.
    if re.match(r"non[-\s]?phos", low.strip()):
        return False
    # Guard on the UN-stripped first token: bare p38/p53 are never phospho by
    # name, but an explicit marker on them ("p-p38", "phospho-p38") still is.
    first = re.split(r"[\s(]+", low.strip())[0]
    if first in P_NUMBER_PROTEINS or re.fullmatch(r"p\d{1,3}[a-z/0-9]*", first):
        return False  # p53, p38, p21, p27Kip1, p70S6K ... never phospho by name alone
    if first in NON_PHOSPHO_P_NAMES:
        return False  # pVHL, pRB, P-glycoprotein ... protein names, not phospho
    if "phospho" in low:
        return True
    if re.search(r"\bp-\s?[A-Za-z]", target):  # p-STAT3, p-AKT
        return True
    if re.match(r"Ph-[A-Za-z]", target.strip()):  # Ph-eIF2α: explicit, case-sensitive abbreviation
        return True
    if re.match(r"^p([A-Z]{2,}[A-Za-z0-9/]*)$", target):  # pSTAT3, pAKT, pERK (not pRb, not p53)
        return True
    return False


def _scoped_site(core: str, *texts: str) -> Optional[dict]:
    """Find a phospho-site near the target's core symbol; fall back to whole text.

    Scoping avoids grabbing a sibling target's site (e.g. picking Ser473 for a
    STAT3 row from '...phospho-AKT Ser473...'). Whole-text fallback only fires
    when the core symbol is not present, i.e. the text is plausibly about this
    single target.
    """
    core_low = (core or "").lower()
    found_core = False
    for text in texts:
        if not text or not core_low:
            continue
        low = text.lower()
        idx = low.find(core_low)
        sites = {}
        while idx != -1:
            found_core = True
            window = text[max(0, idx - 10): idx + len(core) + 45]
            site = parse_phospho_site(window)
            if site:
                sites.setdefault((site["residue"], site["position"]), site)
            idx = low.find(core_low, idx + 1)
        if len(sites) > 1:
            return None  # "p-STAT3 Ser727 and p-STAT3 Tyr705": no single site
        if sites:
            return next(iter(sites.values()))
    if found_core:
        return None  # core present but no site next to it -> don't guess
    # core absent from all texts: text is likely about this one target -> allow
    return parse_phospho_site(*texts) or _one_letter_site_in_context(*texts)


def detect_modification(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    antibody_text: str = "",
) -> dict:
    """Evidence-based modification detection, authoritative from the target name.

    Returns a dict:
        {
          "modification_type": "phosphorylation" | "cleavage" | ... | None,
          "residue": "Tyr" | None,
          "residue_position": 705 | None,
          "normalized_label": "phospho-Tyr705" | "phospho" | "cleaved" | None,
          "status": "SUPPORTED" | "AMBIGUOUS" | "MISSING",
          "phospho_specific_antibody": bool,
          "evidence": [ {type, text}, ... ],
        }

    Rules (deliberately conservative):
      * Modification identity comes from the per-row TARGET NAME. A shared
        caption listing several targets never upgrades a bare target.
      * ``p`` + digits (p53, p38, PARP) is NEVER phosphorylation.
      * A site is attached only when a residue notation is actually present near
        this target; 'phospho-STAT3' with no site stays site=None (never Tyr705).
    """
    target = _norm(raw_target)
    core = _core_symbol(target)

    # --- (A) explicit non-phospho modification encoded in the TARGET NAME -----
    for mod_type, pat in _MOD_WORDS.items():
        m = pat.search(target)
        if m:
            # The mod word being essentially the ENTIRE target means the row's
            # analyte IS that protein: an anti-ubiquitin blot detects the
            # protein ubiquitin; it does not establish that some other target
            # is ubiquitinated. Asserting a modification from the antibody's
            # own antigen name is the same failure class as the banned
            # startswith("p") phospho rule (independent QA finding C2).
            # "ubiquitinated EGFR" keeps the claim: a real target remains.
            rest = target[:m.start()] + target[m.end():]
            rest = re.sub(r"(?i)\b(?:ated|ation|ylation)\b|[-()\s]+", " ", rest)
            if not re.search(r"[A-Za-z]{2}", rest):
                continue
            label = m.group(0).lower() if mod_type == "cleavage" else mod_type
            if label == "cl.":
                label = "cleaved"
            return {
                "modification_type": mod_type,
                "residue": None,
                "residue_position": None,
                "normalized_label": label,
                "status": "SUPPORTED",
                "phospho_specific_antibody": False,
                "evidence": [_ev("target", target)],
            }

    # --- (B) phospho decided by the TARGET NAME (no sibling contamination) ----
    site = parse_phospho_site(target)
    target_phospho = bool(site) or _target_has_phospho_marker(target)
    if not target_phospho:
        return {
            "modification_type": None,
            "residue": None,
            "residue_position": None,
            "normalized_label": None,
            "status": "MISSING",  # no modification on this target -> total protein
            "phospho_specific_antibody": False,
            "evidence": [],
        }

    # Target is phospho: enrich the site (scoped) and phospho-antibody flag.
    if site is None:
        # One-letter site inside the SAME phospho-marked label — "p-AKT (S473)",
        # "p-RPS6KB1 (T389)" — is trustworthy: the phospho marker and the site
        # travel together in one short row label, which satisfies the phospho-
        # context guard that one-letter forms require. (Guarded from cell-line
        # tokens like T47D because \b never splits digit->letter.)
        site = _one_letter_site_in_context(target)
    if site is None:
        site = _scoped_site(core, caption, methods, antibody_text)
    phospho_ab_ev = _first_snippet(
        _PHOSPHO_AB, ("methods", methods), ("antibody", antibody_text), ("figure_caption", caption)
    )

    evidence = [_ev("target", target)]
    if site:
        site_ev = _first_snippet(_SITE_THREE, ("figure_caption", caption), ("methods", methods)) or \
            _first_snippet(_SITE_P_ONE, ("figure_caption", caption), ("methods", methods))
        if site_ev:
            evidence.append(site_ev)
        label = f"phospho-{site['residue']}{site['position']}"
    else:
        label = "phospho"
    if phospho_ab_ev:
        evidence.append(phospho_ab_ev)

    return {
        "modification_type": "phosphorylation",
        "residue": site["residue"] if site else None,
        "residue_position": site["position"] if site else None,
        "normalized_label": label,
        "status": "SUPPORTED",
        "phospho_specific_antibody": bool(phospho_ab_ev),
        "evidence": evidence,
    }


# --------------------------------------------------------------------------- #
# Loading-control & experiment-type classification
# --------------------------------------------------------------------------- #

def is_loading_control(target: str) -> bool:
    token = _token(target)
    return any(token == lc or token.startswith(lc) or lc in token for lc in LOADING_CONTROLS)


# --------------------------------------------------------------------------- #
# Non-western panels: Northern / Southern / gel stain / zymography / EMSA
# --------------------------------------------------------------------------- #
# A panel is non-western only when BOTH hold:
#   1. the PANEL says so: its row target is a nucleic-acid species (18S, 47S, U6,
#      tRNA-Met, ...) or a gel-stain subject (Coomassie, Ponceau S), or its target /
#      lane labels name the assay (zymography, EMSA, free probe); and
#   2. the paper's caption/methods names the matching technique.
# Neither alone is enough. The caption/methods channel is page-level text (a
# Northern paragraph sits on the same page as the westerns, so "Northern blot" in
# it says nothing about one row), and the model's row target is a claim, not
# ground truth. "RNA was extracted" in a methods section matches nothing here.

_RNA_SPECIES = re.compile(
    r"^(?:(?:5|5\.8|12|18|21|26|28|30|32|34|35|41|43|45|46|47)s(?:-[a-z])?\*?"  # rRNA / pre-rRNA S-values: 18S, 47S-C
    r"|[53]'?ets|its[12]"                                                       # transcribed spacers
    r"|(?:pre-?)?(?:[rtm]|sn|sno|sca|mi|lnc)rna(?:[-_]\w+)?"                    # rRNA, tRNA-Met, snoRNA, mRNA
    r"|u[1-7](?:atac)?|7sk|snord\d+\w*|mir-?\d+\w*|let-?7\w*)$",
    re.IGNORECASE,
)
# ponytail: 26S/30S also name the proteasome / bacterial ribosome; accepted because
# the caption/methods must ALSO name a Northern/RNA blot. Add a deny-list if it bites.
_DNA_SPECIES = re.compile(
    r"^(?:[gmc]?t?dna|genomic|plasmid|telomeric|restriction|fragments?|trfs?)$", re.IGNORECASE)
_STAIN_SUBJECT = re.compile(
    r"^(?:coomassie(?:[-\s]+(?:brilliant[-\s]+)?blue)?|cbb|silver|ponceau(?:\s*s)?|amido[-\s]+black|"
    r"sypro(?:[-\s]+ruby)?|stain[-\s]?free|total[-\s]+protein)(?:[-\s]+(?:stain(?:ed|ing)?|gel))*$",
    re.IGNORECASE,
)
# (panel label regex over target + lane text, caption/methods technique regex)
_NORTHERN_LABEL = re.compile(r"\bnorthern\b|\bRNA[-\s]?blot", re.IGNORECASE)
_NORTHERN_CTX = re.compile(
    r"\bnorthern[-\s]+(?:blot|blotting|analys[ie]s|hybridi[sz]ation)|\bRNA[-\s]?blot|"
    r"\bpre-?rRNA\b|\brRNA\b|ribosomal\s+RNA", re.IGNORECASE)
_SOUTHERN_LABEL = re.compile(r"\bsouthern\b|\bDNA[-\s]?blot", re.IGNORECASE)
_SOUTHERN_CTX = re.compile(
    r"\bsouthern[-\s]+(?:blot|blotting|analys[ie]s|hybridi[sz]ation)|\bDNA[-\s]?blot", re.IGNORECASE)
_ZYMO_LABEL = re.compile(r"zymogra(?:m|phy)|gelatinolytic|caseinolytic", re.IGNORECASE)
_ZYMO_CTX = re.compile(r"zymogra(?:m|phy)", re.IGNORECASE)
_EMSA_LABEL = re.compile(
    r"\bEMSA\b|gel[-\s]?shift|mobility[-\s]?shift|super-?shift|free\s+probe", re.IGNORECASE)
_EMSA_CTX = re.compile(
    r"\bEMSAs?\b|electrophoretic\s+mobility[-\s]?shift|gel[-\s]?shift", re.IGNORECASE)
_STAIN_CTX = re.compile(
    r"coomassie|\bCBB\b|silver[-\s]?stain|ponceau|amido[-\s]?black|sypro|stain[-\s]?free|"
    r"(?:total\s+)?protein\s+stain", re.IGNORECASE)


def _na_tokens(target: str) -> list[str]:
    """Target label -> tokens for the nucleic-acid lexicon ("30S (34S*)" -> ["30S"])."""
    t = re.sub(r"\([^)]*\)", " ", target or "")
    t = re.sub(r"(?<=\d)\s*['′’´]\s*(?=ets\b)", "'", t, flags=re.IGNORECASE)
    return [x for x in re.split(r"[\s/,;+&]+", t) if x]


def _is_stain_subject(target: str) -> bool:
    return bool(_STAIN_SUBJECT.match(re.sub(r"\([^)]*\)", " ", target or "").strip()))


def classify_non_western(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    lane_text: str = "",
    panel_targets: Optional[Iterable[str]] = None,
) -> Optional[dict]:
    """Is this panel row a non-western assay (see the block comment above)?

    ``panel_targets`` = every row target the model reported for the SAME panel.
    A stain row (Coomassie, Ponceau S, total protein) is the panel's subject only
    when every row of the panel is a stain; next to a protein row it is a loading
    control, and None (unknown) never flags it.

    Returns {"kind": northern_blot | southern_blot | zymography | emsa | gel_stain,
    "evidence": [{type, text}, ...]} or None.
    """
    toks = _na_tokens(raw_target)
    panel = f"{raw_target}\n{lane_text}"
    rna = bool(toks) and all(_RNA_SPECIES.match(t) for t in toks)
    dna = bool(toks) and all(_DNA_SPECIES.match(t) for t in toks)
    siblings = list(panel_targets) if panel_targets is not None else []
    stain = (_is_stain_subject(raw_target) and bool(siblings)
             and all(_is_stain_subject(t) for t in siblings))
    for kind, on_panel, ctx_rx in (
        ("northern_blot", rna or bool(_NORTHERN_LABEL.search(panel)), _NORTHERN_CTX),
        ("southern_blot", dna or bool(_SOUTHERN_LABEL.search(panel)), _SOUTHERN_CTX),
        ("zymography", bool(_ZYMO_LABEL.search(panel)), _ZYMO_CTX),
        ("emsa", bool(_EMSA_LABEL.search(panel)), _EMSA_CTX),
        ("gel_stain", stain, _STAIN_CTX),
    ):
        if not on_panel:
            continue
        ctx = _first_snippet(ctx_rx, ("figure_caption", caption), ("methods", methods))
        if ctx:
            return {"kind": kind, "evidence": [_ev("target", raw_target), ctx]}
    return None


def classify_experiment(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    modification: Optional[dict] = None,
    is_loading_control_flag: bool = False,
    lane_text: str = "",
    panel_targets: Optional[Iterable[str]] = None,
) -> dict:
    """Classify assay design from TEXT evidence (never the image alone).

    Returns:
        {
          "experiment_type": "co_ip" | "phospho_western" | "standard_western"
                             | "purified_protein" | "loading_control"
                             | "non_western" | "unknown",
          "experiment_flags": [...],     # non-exclusive; co_ip + phospho can coexist
          "confidence": float,
          "evidence": [ {type, text}, ... ],
        }
    """
    flags: list[str] = []
    evidence: list[dict] = []

    non_western = classify_non_western(raw_target, caption, methods, lane_text, panel_targets)
    if non_western:
        flags.extend(["non_western", non_western["kind"]])
        evidence.extend(non_western["evidence"])

    loading = is_loading_control_flag or is_loading_control(raw_target)
    if loading:
        flags.append("loading_control")

    co_ip_ev = _first_snippet(_CO_IP, ("methods", methods), ("figure_caption", caption))
    if co_ip_ev:
        flags.append("co_ip")
        evidence.append(co_ip_ev)

    purified_ev = _first_snippet(_PURIFIED, ("methods", methods), ("figure_caption", caption))
    if purified_ev:
        flags.append("purified_protein")
        evidence.append(purified_ev)

    is_phospho = bool(modification and modification.get("modification_type") == "phosphorylation")
    if is_phospho:
        flags.append("phospho_western")
        evidence.extend(modification.get("evidence", [])[:1])

    # Primary label precedence: assay design beats modification label.
    if "non_western" in flags:
        primary, conf = "non_western", 0.9
    elif "co_ip" in flags:
        primary, conf = "co_ip", 0.9
    elif "purified_protein" in flags:
        primary, conf = "purified_protein", 0.85
    elif "loading_control" in flags:
        primary, conf = "loading_control", 0.9
    elif "phospho_western" in flags:
        primary = "phospho_western"
        conf = 0.9 if (modification or {}).get("status") == "SUPPORTED" else 0.6
    elif _looks_like_western(caption, methods):
        primary, conf = "standard_western", 0.5
        flags.append("standard_western")
    else:
        primary, conf = "unknown", 0.2

    return {
        "experiment_type": primary,
        "experiment_flags": sorted(set(flags)),
        "confidence": conf,
        "evidence": evidence,
    }


def _looks_like_western(caption: str, methods: str) -> bool:
    text = f"{caption} {methods}".lower()
    return any(k in text for k in ("western blot", "immunoblot", "blot", "wb "))


# --------------------------------------------------------------------------- #
# Per-source modification scanning (for the evidence-hierarchy reconciler)
# --------------------------------------------------------------------------- #

def _mention_state(pre: str, post: str) -> dict:
    """Classify a single mention of a core symbol from its surrounding chars.

    Three states, not two:
      * "phosphorylation" — explicit phospho marker / site at this mention.
      * "total"           — explicit total/pan marker ("total STAT3", "T-STAT3",
                            "pan-AKT"): the text really asserts unmodified.
      * "bare"            — the symbol alone ("PI3K/AKT/mTOR signaling"). A bare
                            mention asserts NOTHING about modification state; it
                            must never be read as a total-protein claim, or any
                            pathway sentence in page text would manufacture a
                            fake conflict against a phospho row.
    """
    pre_l = pre.lower()
    is_phospho = False
    if pre_l.rstrip().endswith("phospho") or pre_l.rstrip().endswith("phospho-") or pre_l.rstrip().endswith("phospho "):
        is_phospho = True
    elif re.search(r"p-\s*$", pre):                       # "p-STAT3"
        is_phospho = True
    elif re.search(r"(^|[^A-Za-z])p$", pre):              # glued "pSTAT3"
        is_phospho = True
    site = parse_phospho_site(post) or parse_phospho_site(pre)
    if site:
        is_phospho = True
    if is_phospho:
        return {"type": "phosphorylation", "site": site}
    if re.search(r"(total\s*-?\s*|pan\s*-\s*|\bt-\s*)$", pre, re.IGNORECASE):
        return {"type": "total", "site": None}
    return {"type": "bare", "site": None}


def caption_modification_for_core(core: str, text: str) -> Optional[dict]:
    """Return the modification state a piece of text asserts for ``core``.

    Returns None (abstain) when the text mentions the core in BOTH modified and
    unmodified forms -- a shared multi-target caption is not decisive for one
    row, so it must not contaminate a total-protein row. Returns None too when
    the core is not mentioned at all.

        {"modification_type": "phosphorylation"|None, "residue": "Tyr"|None,
         "residue_position": 705|None}
    """
    core = _norm(core)
    if not core or not text:
        return None
    core_low = core.lower()
    low = text.lower()
    states: set[str] = set()
    sites: dict = {}
    idx = low.find(core_low)
    while idx != -1:
        pre = text[max(0, idx - 12): idx]
        post = text[idx + len(core): idx + len(core) + 14]
        # "pVHL" / "pRB" in a caption is the protein's NAME (core VHL / RB), not a
        # glued phospho prefix: the same exception the target-name guard uses.
        if (idx >= 1 and low[idx - 1] == "p" and (idx < 2 or not low[idx - 2].isalpha())
                and f"p{core_low}" in NON_PHOSPHO_P_NAMES):
            states.add("bare")
            idx = low.find(core_low, idx + 1)
            continue
        st = _mention_state(pre, post)
        states.add(st["type"])
        if st.get("site"):
            sites.setdefault((st["site"]["residue"], st["site"]["position"]), st["site"])
        idx = low.find(core_low, idx + 1)
    # Two DISTINCT sites for this core ("p-STAT3 Ser727 and p-STAT3 Tyr705"):
    # phosphorylation stands, but no single site is assigned.
    site_found = next(iter(sites.values())) if len(sites) == 1 else None

    # A bare mention either asserts nothing (alone: "PI3K/AKT/mTOR signaling"
    # must not become a total-protein claim) or signals the text spans multiple
    # rows (mixed with an explicit form: "pSTAT3 ... STAT3 ..." is about both a
    # phospho row and a total row) -> abstain either way.
    if "bare" in states:
        return None
    if len(states) != 1:            # no explicit claim, or conflicting -> abstain
        return None
    state = states.pop()
    if state == "phosphorylation":
        return {
            "modification_type": "phosphorylation",
            "residue": site_found["residue"] if site_found else None,
            "residue_position": site_found["position"] if site_found else None,
        }
    return {"modification_type": None, "residue": None, "residue_position": None}


def antibody_modification(antibody_target: str) -> dict:
    """Modification implied by an antibody's target string (rank-1 evidence)."""
    mod = detect_modification(antibody_target or "")
    return {
        "modification_type": mod["modification_type"],
        "residue": mod["residue"],
        "residue_position": mod["residue_position"],
    }


def core_symbol(target: str) -> str:
    """Public alias for the phospho/site-stripped gene symbol."""
    return _core_symbol(target)


# --------------------------------------------------------------------------- #
# Target-name normalization (B-12)
# --------------------------------------------------------------------------- #
# Every rule below is an explicit rewrite of the label AS PRINTED; the full table
# with rationale is tickets/b12-expected-mappings.md. Nothing is inferred from
# letters alone: a label that cannot be settled stays unresolved or AMBIGUOUS,
# and the caller always keeps the raw wording. Rule ids (the `rules` list) are the
# same ids the tests and the table use.

_FOLD = re.compile(r"[\s_\-]+")


def _fold(s: str) -> str:
    """Lowercase with spaces/hyphens removed: "Bcl-xL", "bcl xl" -> "bclxl"."""
    return _FOLD.sub("", s.lower())


# Epitope / fusion tags name the construct, not a protein.
_TAG_NAMES = r"FLAG|HA|V5|GFP|EGFP|mCherry|6xHis|His|GST"
_TAG_PREFIX = re.compile(rf"(?i)^({_TAG_NAMES})-(?=\S{{3,}})")
# "-myc" only as a SUFFIX: a bare "Myc" / "c-Myc" is the MYC protein, never a tag.
_TAG_SUFFIX = re.compile(rf"(?i)(?<=\S{{3}})-({_TAG_NAMES}|myc)$")
_BARE_TAGS = {"flag", "dykddddk", "ha", "v5", "gfp", "egfp", "mcherry", "his", "6xhis",
              "gst", "myctag", "hatag", "flagtag", "histag"}

# Viral proteins whose NAME is specific to primate lentiviruses (HIV/SIV). Tat and
# Rev are excluded (TAT is also a human gene) as are p55/p24/p17 (host proteins
# share the p-number names): those need paper context, so they are left alone.
_VIRAL = {"vpr", "vif", "nef", "vpu", "gp120", "gp41", "gp160"}

# Families whose isoform the label does not state. folded name -> (label, genes, note).
# A label is given only when the gene list is complete and short; otherwise None.
_RAS = ("HRAS/KRAS/NRAS", ("HRAS", "KRAS", "NRAS"), "Ras isoform not stated")
_JNK = ("MAPK8/MAPK9/MAPK10", ("MAPK8", "MAPK9", "MAPK10"), "JNK1/2/3 not stated")
_FAMILIES: dict[str, tuple[Optional[str], tuple[str, ...], str]] = {
    "ras": _RAS, "panras": _RAS,
    "jnk": _JNK, "sapk/jnk": _JNK,      # "/" survives _fold()
    "alphaactinin": ("ACTN1/ACTN2/ACTN3/ACTN4", ("ACTN1", "ACTN2", "ACTN3", "ACTN4"),
                     "alpha-actinin isoform not stated"),
    "alphatubulin": (None, (), "alpha-tubulin is a multi-gene family (TUBA*); isoform not stated"),
    "betatubulin": (None, (), "beta-tubulin is a multi-gene family (TUBB*); isoform not stated"),
    "myhc": (None, (), "myosin heavy chain is a multi-gene family (MYH*); isoform not stated"),
    "myosinheavychain": (None, (), "myosin heavy chain is a multi-gene family (MYH*); isoform not stated"),
}

# Common names that are not the gene symbol (UniProt `gene:` never matches them).
# Keys are _fold()ed. Each maps to exactly ONE gene; anything shared stays out.
NAME_TO_SYMBOL: dict[str, str] = {
    "vinculin": "VCL",
    "bclxl": "BCL2L1",            # the long isoform of BCL2L1
    "il18": "IL18",
    "betacatenin": "CTNNB1", "bcatenin": "CTNNB1",
    "eif2alpha": "EIF2S1",        # NOT "eif2a": EIF2A is a different gene
    "4ebp1": "EIF4EBP1",          # 4E-BP1, 4EBP1
    "mcl1": "MCL1", "bcl2": "BCL2", "beclin1": "BECN1",
    "shp1": "PTPN6", "shp2": "PTPN11",
    "survivin": "BIRC5", "cmyc": "MYC", "cyclind1": "CCND1",
}
_CASPASE = re.compile(r"caspase(\d{1,2})$")
_CASPASE_NUMBERS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14}   # human CASP genes with that number

_LC3_MENTION = re.compile(r"(?i)\blc-?3([abc])?(?![a-z0-9])")


def _lc3(s: str):
    """(stated isoform letters, form numerals) when ``s`` is ONLY LC3 mentions and
    I/II form numerals ("LC3-I/LC3-II", "LC3B I / II"), else None."""
    mentions = _LC3_MENTION.findall(s)
    if not mentions:
        return None
    rest = _LC3_MENTION.sub("", s)
    forms = [f.upper() for f in re.findall(r"(?i)\b(i{1,2})\b", rest)]
    if re.sub(r"(?i)\bi{1,2}\b|[\s/\-,]", "", rest):
        return None
    return {m.upper() for m in mentions if m}, forms


def normalize_target(raw_target: str) -> dict:
    """Rewrite a printed target label into what can be LOOKED UP, or say why not.

    Returns::

        {"raw": str,
         "lookup": "VCL" | None,      # name/symbol to send to the resolver; None = no
                                      # rule fired, callers use core_symbol(raw)
         "kind": None | "family" | "viral" | "tag",
         "family_label": "MAPK8/MAPK9/MAPK10" | None,   # kind == "family"
         "candidates": ["MAPK8", ...],                  # kind == "family"
         "notes": [str],              # tag / form / viral / family facts to keep
         "rules": [str]}              # ids of the rules that fired

    ``kind`` "family" means AMBIGUOUS (never a single guessed gene); "viral" and
    "tag" mean deliberately unresolved against human UniProt.
    """
    raw = _norm(raw_target)
    out: dict = {"raw": raw, "lookup": None, "kind": None, "family_label": None,
                 "candidates": [], "notes": [], "rules": []}
    rules, notes = out["rules"], out["notes"]

    def fire(rule: str, note: Optional[str] = None) -> None:
        rules.append(rule)
        if note:
            notes.append(note)

    # Parenthetical qualifiers ("(long exposure)", "(CASP3 p19 / CASP3 p17)") never
    # change identity; the raw label keeps them.
    s = _greek(re.split(r"\s*\(", raw)[0].strip())
    stripped = _strip_mod_prefix(s)
    if re.match(r"(?i)non[-\s]?phos", s):
        fire("non_phospho_prefix", "label is a NON-phospho-specific antibody: it reads the "
             "unphosphorylated form, not total protein (modification not asserted)")
    s = stripped

    # --- qualifiers describing the FORM, not the protein ----------------------
    m = re.match(r"(?i)(cleaved|active|activated)[-\s]+(?=\S)", s)
    if m:
        fire("form_qualifier", f"'{m.group(1)}' qualifier dropped for protein identity only; "
             "the modification layer decides what it means")
        s = s[m.end():]
    m = re.search(r"(?i)\s+cl\.$", s)           # "cl." with the dot; bare "CL" is cell lysate
    if m:
        fire("cleaved_abbreviation", "'cl.' (cleaved) dropped for protein identity only")
        s = s[:m.start()]

    # --- antibody "α-" (anti-) vs alpha as part of the name -------------------
    # Only when the rest is a caspase / gasdermin / interleukin symbol; alpha-tubulin,
    # alpha-actinin, alpha-SMA, alpha-catenin keep their alpha.
    m = re.match(r"(?i:alpha)-(?=(?:CASP\d+|GSDM[A-E]|IL-?\d+)\b)", s)
    if m:
        fire("anti_alpha_prefix", "leading 'alpha-' read as 'anti-' (antibody label)")
        s = s[m.end():]

    # --- epitope / fusion tags ------------------------------------------------
    for pat, side in ((_TAG_PREFIX, "prefix"), (_TAG_SUFFIX, "suffix")):
        m = pat.match(s) if side == "prefix" else pat.search(s)
        if m:
            fire("epitope_tag", f"{m.group(1)} tag stripped; the tagged protein is the target")
            s = s[m.end():] if side == "prefix" else s[:m.start()]

    # --- caspase / gasdermin fragment suffix ("CASP1p10") ---------------------
    m = re.fullmatch(r"(?i)(CASP\d+|GSDM[A-E])\s*p\d{1,3}(?:/\d{1,3})?", s)
    if m:
        fire("cleavage_fragment_suffix", f"fragment notation '{s[len(m.group(1)):].strip()}' dropped "
             "for protein identity; cleavage is NOT asserted from a size suffix")
        s = m.group(1)

    f = _fold(s)

    # --- things that are not (human) proteins ---------------------------------
    if f in _VIRAL:
        out["kind"] = "viral"
        fire("viral_protein", "viral protein (primate lentivirus, HIV/SIV): non-human, "
             "deliberately not resolved against human UniProt")
        return out
    if f in _BARE_TAGS:
        out["kind"] = "tag"
        fire("bare_tag", f"'{s}' is an epitope/fusion tag, not a protein; the tagged protein "
             "is not named in this label")
        return out

    # --- LC3 ------------------------------------------------------------------
    lc3 = _lc3(s)
    if lc3:
        letters, forms = lc3
        if forms:
            notes.append("LC3-I / LC3-II are forms of one protein (cytosolic / lipidated); "
                         "kept as a form note, not a modification")
        if len(letters) == 1:
            fire("lc3_isoform_stated")
            out["lookup"] = "MAP1LC3" + next(iter(letters))
        else:
            fire("lc3_isoform_unstated", "LC3 isoform (A/B/C) not stated")
            out.update(kind="family", family_label="MAP1LC3A/MAP1LC3B/MAP1LC3C",
                       candidates=["MAP1LC3A", "MAP1LC3B", "MAP1LC3C"])
        return out

    # --- ambiguous families ---------------------------------------------------
    if f in _FAMILIES:
        label, genes, note = _FAMILIES[f]
        fire("ambiguous_family", note)
        out.update(kind="family", family_label=label, candidates=list(genes))
        return out

    # --- single-gene name aliases ---------------------------------------------
    sym = NAME_TO_SYMBOL.get(f) or NAME_TO_SYMBOL.get(_fold(_core_symbol(s)))
    if not sym:
        m = _CASPASE.fullmatch(f)
        if m and int(m.group(1)) in _CASPASE_NUMBERS:
            sym = f"CASP{int(m.group(1))}"
    if sym:
        fire("name_alias")
        out["lookup"] = sym
    elif rules:
        out["lookup"] = _core_symbol(s)
    return out


# --------------------------------------------------------------------------- #
# Protein normalization (conservative, explicit ambiguity)
# --------------------------------------------------------------------------- #

def normalize_protein(raw_target: str) -> dict:
    """Resolve a raw target to a canonical symbol + UniProt where confident.

    Never overwrites the source wording -- both are returned. Ambiguity is
    surfaced, not guessed.

        {
          "raw": "pSTAT3",
          "canonical": "STAT3" | None,
          "uniprot_id": "P40763" | None,
          "status": "SUPPORTED" | "AMBIGUOUS" | "MISSING",
          "notes": [...],            # tag / form / viral facts (normalize_target)
        }
    """
    raw = _norm(raw_target)
    norm = normalize_target(raw)
    base = {"raw": raw, "canonical": None, "uniprot_id": None, "notes": norm["notes"]}
    if norm["kind"] in ("viral", "tag"):
        return {**base, "status": "MISSING"}
    if norm["kind"] == "family":
        return {**base, "canonical": norm["family_label"], "status": "AMBIGUOUS"}

    token = (norm["lookup"] or _token(raw)).lower()
    if not token:
        return {**base, "status": "MISSING"}

    if token in PROTEIN_ALIASES:
        canonical, uniprot = PROTEIN_ALIASES[token]
        # A resolved canonical name with no single UniProt (e.g. ERK1/2) is ambiguous.
        status = "AMBIGUOUS" if uniprot is None else "SUPPORTED"
        return {**base, "canonical": canonical, "uniprot_id": uniprot, "status": status}

    # Unknown to our offline map -> keep raw, flag for resolution. Not guessed.
    return {**base, "status": "MISSING"}

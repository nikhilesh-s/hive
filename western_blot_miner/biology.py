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
    "b-actin",
    "beta-actin",
    "gapdh",
    "tubulin",
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
    "erk": ("MAPK1", None),          # ERK is ambiguous (ERK1/ERK2) -> no single UniProt
    "erk1/2": ("MAPK1/MAPK3", None),
    "p38": ("MAPK14", "Q16539"),
    "gapdh": ("GAPDH", "P04406"),
    "actin": ("ACTB", "P60709"),
    "beta-actin": ("ACTB", "P60709"),
    "b-actin": ("ACTB", "P60709"),
    "egfr": ("EGFR", "P00533"),
    "parp": ("PARP1", "P09874"),
    "parp1": ("PARP1", "P09874"),
}

# Proteins whose name legitimately starts with "p" + digits and must NEVER be
# auto-classified as phospho. (Documented guard; the regex handles the general
# case, this is belt-and-suspenders for the well-known ones.)
P_NUMBER_PROTEINS = {
    "p53", "p63", "p73", "p38", "p21", "p27", "p16", "p65", "p50",
    "p130", "p107", "p120", "p62", "p45", "p90", "p70", "p110",
}

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
    "cleavage": re.compile(r"\bcleav(ed|age)\b", re.IGNORECASE),
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
_PURIFIED = re.compile(
    r"\brecombinant\b|purified\s+protein|in\s+vitro\s+(?:binding|kinase|translat)|GST[-\s]?tag|His[-\s]?tag",
    re.IGNORECASE,
)
_INPUT_BLOT = re.compile(r"\binput\b", re.IGNORECASE)

# Catalog number: "#9145", "cat. no. 9145", "ab32157", "sc-482".
_CATALOG = re.compile(
    r"(?:cat(?:alog)?\.?\s*(?:no\.?|#|number)?\s*|#)\s*([A-Za-z]{0,3}[-\s]?\d{3,7})",
    re.IGNORECASE,
)
_CATALOG_VENDORCODE = re.compile(r"\b(ab\d{3,7}|sc[-\s]?\d{3,7})\b", re.IGNORECASE)
# Antibody dilution: "1:1000".
_DILUTION = re.compile(r"\b1\s?:\s?(\d{2,6})\b")
# Molecular weight: "86 kDa", "~120 kDa".
_KDA = re.compile(r"(~?\s?\d{1,4}(?:\.\d+)?)\s?kDa", re.IGNORECASE)
# Dose: "20 ng/mL", "10 uM", "0.2 umol/L".
_DOSE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?(ng/ml|ug/ml|mg/ml|nmol/l|umol/l|mmol/l|nm|um|mm|mg/kg|ng/kg|%)\b",
    re.IGNORECASE,
)
# Duration: "30 min", "24 h", "48 hours".
_DURATION = re.compile(r"\b(\d+(?:\.\d+)?)\s?(h|hr|hrs|hour|hours|min|mins|minute|minutes|d|day|days)\b", re.IGNORECASE)
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

def _core_symbol(target: str) -> str:
    """Gene symbol with a leading phospho/p- marker and any site stripped."""
    core = re.sub(r"^(phospho[-\s]?|p[-\s]?)", "", _norm(target), flags=re.IGNORECASE)
    core = re.split(r"[\s(]", core)[0]
    return core.strip(" -()")


def _target_has_phospho_marker(target: str) -> bool:
    """True only when the TARGET NAME itself denotes phosphorylation.

    This is what prevents STAT3 (total) from being contaminated by a sibling
    'phospho-STAT3' band described in the same caption -- modification identity
    comes from the per-row target label, not the shared caption.
    """
    low = target.lower()
    token = _token(target)
    if token in P_NUMBER_PROTEINS or re.fullmatch(r"p\d{1,3}[a-z/]*", token):
        return False  # p53, p38, p21 ... never phospho by name alone
    if "phospho" in low:
        return True
    if re.search(r"\bp-\s?[A-Za-z]", target):  # p-STAT3, p-AKT
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
        while idx != -1:
            found_core = True
            window = text[max(0, idx - 10): idx + len(core) + 45]
            site = parse_phospho_site(window)
            if site:
                return site
            idx = low.find(core_low, idx + 1)
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
            label = m.group(0).lower() if mod_type == "cleavage" else mod_type
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


def classify_experiment(
    raw_target: str,
    caption: str = "",
    methods: str = "",
    modification: Optional[dict] = None,
    is_loading_control_flag: bool = False,
) -> dict:
    """Classify assay design from TEXT evidence (never the image alone).

    Returns:
        {
          "experiment_type": "co_ip" | "phospho_western" | "standard_western"
                             | "purified_protein" | "loading_control" | "unknown",
          "experiment_flags": [...],     # non-exclusive; co_ip + phospho can coexist
          "confidence": float,
          "evidence": [ {type, text}, ... ],
        }
    """
    flags: list[str] = []
    evidence: list[dict] = []

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
    if "co_ip" in flags:
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
    """Classify a single mention of a core symbol from its surrounding chars."""
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
    return {"type": "phosphorylation" if is_phospho else "none", "site": site}


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
    site_found: Optional[dict] = None
    idx = low.find(core_low)
    while idx != -1:
        pre = text[max(0, idx - 12): idx]
        post = text[idx + len(core): idx + len(core) + 14]
        st = _mention_state(pre, post)
        states.add(st["type"])
        if st.get("site") and site_found is None:
            site_found = st["site"]
        idx = low.find(core_low, idx + 1)

    if len(states) != 1:            # 0 mentions, or conflicting mentions -> abstain
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
        }
    """
    raw = _norm(raw_target)
    token = _token(raw)
    if not token:
        return {"raw": raw, "canonical": None, "uniprot_id": None, "status": "MISSING"}

    if token in PROTEIN_ALIASES:
        canonical, uniprot = PROTEIN_ALIASES[token]
        # A resolved canonical name with no single UniProt (e.g. ERK1/2) is ambiguous.
        status = "AMBIGUOUS" if uniprot is None else "SUPPORTED"
        return {"raw": raw, "canonical": canonical, "uniprot_id": uniprot, "status": status}

    # Unknown to our offline map -> keep raw, flag for resolution. Not guessed.
    return {"raw": raw, "canonical": None, "uniprot_id": None, "status": "MISSING"}

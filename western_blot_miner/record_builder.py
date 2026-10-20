"""Assemble an EvidenceRecord from model claims + deterministic biology.

This is the Stage-2/Stage-3 join point. The LLM (Bedrock, via llm_client)
produces structured *claims* about a panel -- target label, antibodies with
their targets, sample, treatment, bands. The deterministic layer (biology.py)
independently derives modification, dose/duration, catalog/vendor and protein
identity. :func:`build_evidence_record` reconciles all sources through the
evidence hierarchy (reconcile.py), resolves the protein (resolve.py), computes
antibody association confidence, and runs validation -- producing the fully
provenanced EvidenceRecord.

Deliberately model-free at this layer: give it the model's claims (or a fixture)
and it runs offline, which is how the benchmark exercises the biology.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from . import biology
from .evidence_record import (
    AMBIGUOUS,
    CONFLICTING,
    MISSING,
    NOT_RECOVERED,
    NOT_STATED,
    SUPPORTED,
    AntibodyInfo,
    AnomalyFlag,
    BandObservation,
    Candidate,
    EvidenceField,
    EvidenceRecord,
    ExtractionMeta,
    ExperimentInfo,
    FigureRef,
    MolecularWeightInfo,
    ModificationInfo,
    PaperRef,
    RANK_ANTIBODY,
    RANK_CAPTION,
    RANK_DETERMINISTIC,
    RANK_IMAGE,
    RANK_METHODS,
    RANK_MODEL_TARGET,
    RANK_REFERENCE,
    SampleInfo,
    Source,
    TargetInfo,
    TreatmentInfo,
    ValidationInfo,
)
from .reconcile import Claim, ModClaim, reconcile_field, reconcile_modification
from .resolve import ProteinResolver, LocalMapResolver
from .supabase_loader import (
    extract_antibody,
    extract_dose,
    extract_dose_series,
    extract_duration,
    extract_duration_series,
    extract_kda,
)

CELL_LINE_ORGANISM = {
    "hek293": "human", "hek293t": "human", "hela": "human", "a549": "human",
    "mcf7": "human", "mcf-7": "human", "hepg2": "human", "u2os": "human",
    "jurkat": "human", "3t3": "mouse", "nih3t3": "mouse", "raw264.7": "mouse", "cho": "hamster",
}


def build_evidence_record(
    case: dict[str, Any],
    resolver: Optional[ProteinResolver] = None,
    extraction: Optional[ExtractionMeta] = None,
) -> EvidenceRecord:
    resolver = resolver or LocalMapResolver()
    mc = case.get("model_claims", {})
    texts = case.get("texts", {})
    caption = texts.get("caption", "") or case.get("figure", {}).get("caption_text", "")
    methods = texts.get("methods", "")
    raw_target = case["raw_target"]
    core = biology.core_symbol(raw_target)

    antibodies_in = mc.get("antibodies", [])
    detection_abs = [a for a in antibodies_in if a.get("role", "detection") == "detection"]
    ip_abs = [a for a in antibodies_in if a.get("role") == "immunoprecipitation"]

    # ---- protein identity (real resolver; never guessed) -------------------
    # Scope the UniProt query to the paper's claimed organism (default human,
    # the previous unconditional behavior) so e.g. mouse Stat3 resolves to the
    # mouse accession and expected MW, not the human one.
    organism_id = biology.organism_taxon_id(mc.get("organism"))
    res = resolver.resolve(core, organism_id=organism_id)
    target_info = _target_info(raw_target, core, res, mc)

    # ---- modification: gather claims from every source, then reconcile -----
    mod_claims: list[ModClaim] = []
    for ab in detection_abs:
        m = biology.antibody_modification(ab.get("target", ""))
        conf = 0.9
        if m["modification_type"] is None and ab.get("phospho_specific"):
            # The extractor explicitly claimed this antibody is phospho-specific
            # even though its target string carries no parseable marker — e.g.
            # uppercase "P-ERK 1/2" (uppercase P- must NEVER be read as a
            # phospho marker by itself: P-selectin / P-cadherin are protein
            # names). The explicit flag is real evidence; without it the row
            # would falsely SETTLE as total against a phospho-specific
            # antibody. No site is invented; reconciliation decides.
            m = {"modification_type": "phosphorylation", "residue": None,
                 "residue_position": None}
            conf = 0.6
        mod_claims.append(ModClaim(m["modification_type"], m["residue"], m["residue_position"],
                                   "antibody", RANK_ANTIBODY, conf,
                                   ab.get("source", {}).get("text", ab.get("target", ""))))
    cap_m = biology.caption_modification_for_core(core, caption)
    if cap_m is not None:
        mod_claims.append(ModClaim(cap_m["modification_type"], cap_m["residue"], cap_m["residue_position"],
                                   "figure_caption", RANK_CAPTION, 0.7, _snippet(caption, core)))
    meth_m = biology.caption_modification_for_core(core, methods)
    if meth_m is not None:
        mod_claims.append(ModClaim(meth_m["modification_type"], meth_m["residue"], meth_m["residue_position"],
                                   "methods", RANK_METHODS, 0.6, _snippet(methods, core)))
    row_m = biology.detect_modification(raw_target)
    mod_claims.append(ModClaim(row_m["modification_type"], row_m["residue"], row_m["residue_position"],
                               "model_target", RANK_MODEL_TARGET, 0.5, raw_target))

    mod_fields = reconcile_modification(mod_claims)
    phospho_specific = _phospho_specific_field(detection_abs, mod_fields)
    modification = ModificationInfo(
        modification_type=mod_fields["modification_type"],
        residue=mod_fields["residue"],
        residue_position=mod_fields["residue_position"],
        normalized_label=mod_fields["normalized_label"],
        phospho_specific_antibody=phospho_specific,
    )

    # ---- experiment type ---------------------------------------------------
    lane_text = " | ".join(
        str(b.get("lane_condition") or "") for b in mc.get("bands", []))
    experiment = _experiment_info(core, caption, methods, mod_fields, ip_abs, lane_text=lane_text,
                                  raw_target=raw_target, panel_targets=case.get("panel_targets"))

    # ---- sample ------------------------------------------------------------
    sample = _sample_info(mc, caption)

    # ---- treatment (deterministic dose/duration; never invented) -----------
    treatment = _treatment_info(mc, caption, methods)

    # ---- antibodies with detection vs association confidence ---------------
    antibodies = [_antibody_info(ab, core, mod_fields, caption, methods) for ab in antibodies_in]

    # ---- molecular weight: reported (text) vs expected (UniProt) -----------
    molecular_weight = _mw_info(caption, methods, res, core=core)

    # ---- bands -------------------------------------------------------------
    # `core` + `caption` let band-pattern wording be scoped to THIS target so a
    # sibling row's doublet never leaks onto this one.
    bands = _bands(mc, core=core, caption=caption)

    record = EvidenceRecord(
        record_id=_record_id(case, raw_target),
        paper=_paper_ref(case.get("paper", {})),
        figure=_figure_ref(case.get("figure", {}), caption),
        target=target_info,
        modification=modification,
        experiment=experiment,
        sample=sample,
        treatment=treatment,
        antibodies=antibodies,
        molecular_weight=molecular_weight,
        bands=bands,
        extraction=extraction or ExtractionMeta(stage="deterministic+llm", backend="mock", model="fixture"),
    )
    record.validation = _validate(record, detection_abs, mod_fields)
    return record


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def _target_info(raw_target, core, res, mc) -> TargetInfo:
    aliases = mc.get("aliases", [])
    if res.status == SUPPORTED and res.uniprot_id:
        canonical = EvidenceField.supported(
            res.canonical, 0.96, [Source(type="uniprot_reference", rank=RANK_REFERENCE, text=res.uniprot_id)])
        uniprot = EvidenceField.supported(
            res.uniprot_id, 0.96, [Source(type="uniprot_reference", rank=RANK_REFERENCE, text=res.uniprot_id)])
    elif res.status == AMBIGUOUS:
        cands = [Candidate(value=c.get("uniprot_id"), source_type="uniprot_reference", rank=RANK_REFERENCE,
                           confidence=0.5, evidence=[Source(type="uniprot_reference", rank=RANK_REFERENCE,
                                                            text=str(c))]) for c in (res.candidates or [{}])]
        # An ambiguous resolution keeps a best-effort family LABEL (e.g.
        # "MAPK1/MAPK3" for ERK1/2) as the value, but MUST stay AMBIGUOUS -- a
        # multi-gene family is not a settled canonical value (invariant #3), so
        # it never renders as SUPPORTED and surfaces for review.
        canonical = EvidenceField(
            value=res.canonical, confidence=0.5, status=AMBIGUOUS,
            sources=[Source(type="uniprot_reference", rank=RANK_REFERENCE, text="ambiguous_family")],
            candidates=cands,
        ) if res.canonical else EvidenceField.ambiguous(cands)
        uniprot = EvidenceField.ambiguous(cands)   # accession NOT chosen
    else:
        # A resolver miss is an extraction/normalization limitation, not evidence
        # that the paper failed to name the protein.
        canonical = EvidenceField.not_recovered()
        uniprot = EvidenceField.not_recovered()
    return TargetInfo(raw_target_name=raw_target, canonical_target=canonical, uniprot_id=uniprot,
                      aliases_used_in_paper=aliases)


def _phospho_specific_field(detection_abs, mod_fields) -> EvidenceField:
    for ab in detection_abs:
        if ab.get("phospho_specific") is True:
            return EvidenceField.supported(True, 0.9, [Source(
                type="antibody", rank=RANK_ANTIBODY, text=ab.get("source", {}).get("text", ""))])
        m = biology.antibody_modification(ab.get("target", ""))
        if m["modification_type"] == "phosphorylation":
            return EvidenceField.supported(True, 0.85, [Source(
                type="antibody", rank=RANK_ANTIBODY, text=ab.get("target", ""))])
    return EvidenceField.missing()


def _experiment_info(core, caption, methods, mod_fields, ip_abs, lane_text: str = "",
                     raw_target: str = "", panel_targets=None) -> ExperimentInfo:
    text_blob = f"{caption}\n{methods}"
    flags: list[str] = []
    sources: list[Source] = []

    # Northern / Southern / gel stain / zymography / EMSA: panel evidence (target,
    # lane labels, sibling rows) AND caption/methods wording; see biology.classify_non_western.
    non_western = biology.classify_non_western(raw_target or core, caption, methods, lane_text, panel_targets)
    if non_western:
        flags.extend(["non_western", non_western["kind"]])
        sources.append(Source(type="model_target", rank=RANK_MODEL_TARGET, text=raw_target or core))
        ctx = non_western["evidence"][1]
        sources.append(Source(type=ctx["type"], rank=RANK_CAPTION if ctx["type"] == "figure_caption" else RANK_METHODS,
                              text=ctx["text"]))

    # co-IP requires PANEL evidence: an IP-role antibody claim, or co-IP /
    # IP:/IgG/input markers printed on the panel's own lanes. Page-level text
    # is context only, never a classification: a methods paragraph, and the
    # caption channel too -- it is the retrieval's figure-text section, which on
    # a real paper (PMC12706926) is the same results prose for 11 of 15 panels,
    # so one "Immunoprecipitation (IP) assays ..." sentence turned 47 records
    # co_ip with bait "IP". Such mentions stay a non-settling "co_ip_context" flag.
    panel_scoped = f"{caption}\n{lane_text}"
    lane_co_ip = biology._CO_IP.search(lane_text) or biology._IP_LANE.search(lane_text)
    if ip_abs:
        flags.append("co_ip")
        ab0 = ip_abs[0]
        sources.append(Source(type="antibody", rank=RANK_ANTIBODY,
                              text=ab0.get("source", {}).get("text", ab0.get("target", "IP antibody"))))
    elif lane_co_ip:
        flags.append("co_ip")
        # lane_text is the model's reading of labels printed on the image
        sources.append(Source(type="image", rank=RANK_IMAGE,
                              text=_around(lane_text, lane_co_ip.start())))
    elif biology._CO_IP.search(caption):
        m = biology._CO_IP.search(caption)
        flags.append("co_ip_context")
        sources.append(Source(type="figure_caption", rank=RANK_CAPTION, text=_around(caption, m.start())))
    elif biology._CO_IP.search(methods):
        m = biology._CO_IP.search(methods)
        flags.append("co_ip_context")
        sources.append(Source(type="methods", rank=RANK_METHODS, text=_around(methods, m.start())))
    if biology._PURIFIED.search(text_blob):
        flags.append("purified_protein")
    if biology.is_loading_control(core):
        flags.append("loading_control")

    mtype = mod_fields["modification_type"]
    mod_conflicted = mtype.status in (CONFLICTING, AMBIGUOUS)
    is_phospho = (mtype.status == SUPPORTED and mtype.value == "phosphorylation")
    if is_phospho:
        flags.append("phospho_western")

    # Primary label + confidence, degraded when the modification is unsettled.
    if "non_western" in flags:
        primary, conf, status = "non_western", 0.9, SUPPORTED
    elif "co_ip" in flags:
        primary, conf, status = "co_ip", 0.9, SUPPORTED
    elif "purified_protein" in flags:
        primary, conf, status = "purified_protein", 0.85, SUPPORTED
    elif "loading_control" in flags:
        primary, conf, status = "loading_control", 0.9, SUPPORTED
    elif mod_conflicted:
        # modification dispute propagates: don't assert phospho vs standard.
        primary, conf, status = None, 0.4, AMBIGUOUS
    elif is_phospho:
        primary, conf, status = "phospho_western", 0.9, SUPPORTED
    elif biology._looks_like_western(caption, methods):
        primary, conf, status = "standard_western", 0.55, SUPPORTED
        flags.append("standard_western")
    else:
        primary, conf, status = None, 0.0, NOT_RECOVERED

    exp_type = EvidenceField(value=primary, confidence=conf, status=status, sources=sources)
    exp_flags = EvidenceField.supported(sorted(set(flags)), conf, sources) if flags else EvidenceField.missing()

    ip_bait = EvidenceField.not_recovered() if "co_ip" in flags else EvidenceField.missing()
    if "co_ip" in flags:
        bait = None
        bait_src = None
        panel_co_ip = biology._CO_IP.search(panel_scoped)
        if ip_abs:
            bait = biology.core_symbol(ip_abs[0].get("target", ""))
            bait_src = Source(type="antibody", rank=RANK_ANTIBODY,
                              text=ip_abs[0].get("source", {}).get("text", ip_abs[0].get("target", "")))
        elif panel_co_ip:
            # best-effort bait from the panel-scoped text only (same scoping
            # rule as the classification itself).
            bait = _first_gene_after(panel_scoped, panel_co_ip.end())
            # same channel rule as the classification: caption only when the
            # co-IP wording is in the caption, otherwise the printed lane labels
            bait_src = (Source(type="figure_caption", rank=RANK_CAPTION,
                               text=_around(caption, panel_co_ip.start()))
                        if panel_co_ip.start() < len(caption) else
                        Source(type="image", rank=RANK_IMAGE,
                               text=_around(lane_text, panel_co_ip.start() - len(caption) - 1)))
        if bait:
            ip_bait = EvidenceField.supported(bait, 0.75, [bait_src])
    return ExperimentInfo(experiment_type=exp_type, experiment_flags=exp_flags, ip_bait_protein=ip_bait)


def _sample_info(mc, caption) -> SampleInfo:
    sample_val = mc.get("sample") or mc.get("cell_line")
    cell_line = mc.get("cell_line") or mc.get("sample")
    org = mc.get("organism")

    def src_for(v):
        # A caption source must name the value; otherwise it is the model's claim.
        if caption and str(v).lower() in caption.lower():
            return [Source(type="figure_caption", rank=RANK_CAPTION, text=_snippet(caption, str(v)))]
        return [Source(type="model_target", rank=RANK_MODEL_TARGET, text=str(v))]
    # A null model field cannot establish that the authors omitted the value.
    sample_f = EvidenceField.supported(sample_val, 0.9, src_for(sample_val)) if sample_val else EvidenceField.not_recovered()
    cell_f = EvidenceField.supported(cell_line, 0.9, src_for(cell_line)) if cell_line else EvidenceField.not_recovered()
    if not org and cell_line:
        org = CELL_LINE_ORGANISM.get(str(cell_line).lower())
        if org:
            organism_f = EvidenceField.supported(
                org, 0.8, [Source(type="deterministic", rank=RANK_DETERMINISTIC,
                                  text=f"{cell_line} -> {org} (cell-line table)")])
        else:
            organism_f = EvidenceField.not_recovered()
    elif org:
        organism_f = EvidenceField.supported(org, 0.85, src_for(org))
    else:
        organism_f = EvidenceField.not_recovered()
    return SampleInfo(
        sample=sample_f,
        cell_line=cell_f,
        organism=organism_f,
        # These fields are currently stubs: the pipeline does not yet perform a
        # reliable field-specific extraction for them, so NOT_STATED would be
        # scientifically unjustified.
        tissue=EvidenceField.not_recovered(),
        genotype=EvidenceField.not_recovered(),
    )


def _series_fields(values: list[dict], ctx: str, det: list[Source],
                   multi_marker: bool, source_examined: bool = False) -> tuple[EvidenceField, EvidenceField]:
    """(value_field, unit_field) for a dose or duration series.

    ONE stated value -> SUPPORTED scalar, as before.
    MORE THAN ONE (a dose-response / time course, or two agents at different
    units) -> the panel-level scalar is NOT attributable to any single lane, so
    it becomes **value=None, status=AMBIGUOUS** with every stated value kept as
    a candidate. Taking values[0] used to report the CL-E dose (60 ug/ml) as the
    IL-6 dose, and 60 min as THE duration of a 0-60 min time course. The
    lane-level values live on each BandObservation; the DB scalar goes NULL
    rather than asserting a wrong one (null > misleading value).
    """
    if not values:
        # A deterministic field-specific scan over verified paper text may
        # support NOT_STATED. A null/empty model paraphrase may not.
        absent = EvidenceField.not_stated(det) if source_examined else EvidenceField.not_recovered()
        return absent, EvidenceField.not_stated(det) if source_examined else EvidenceField.not_recovered()
    distinct = {(v["value"], v["unit"].lower()) for v in values}
    if len(distinct) == 1 and not multi_marker:
        return (EvidenceField.supported(values[0]["value"], 0.85, det),
                EvidenceField.supported(values[0]["unit"], 0.85, det))
    # source_type "lane_series": these are per-lane values of a varied design
    # (time course / dose series), NOT mutually competing claims about one
    # scalar. Consumers must render them as "varies by lane", never as a
    # pick-a-winner candidate list (manual-beta P0 finding).
    cands = [
        Candidate(value=v["value"], source_type="lane_series", rank=RANK_DETERMINISTIC,
                  confidence=0.5,
                  evidence=[Source(type="deterministic", rank=RANK_DETERMINISTIC,
                                   text=f'{v["value"]} {v["unit"]} — {ctx[:160]}')])
        for v in values
    ]
    units = {v["unit"] for v in values}
    value_f = EvidenceField(value=None, confidence=0.0, status=AMBIGUOUS,
                            sources=det, candidates=cands)
    unit_f = (EvidenceField.supported(next(iter(units)), 0.85, det) if len(units) == 1
              else EvidenceField(value=None, confidence=0.0, status=AMBIGUOUS,
                                 sources=det,
                                 candidates=[Candidate(value=u, source_type="deterministic",
                                                       rank=RANK_DETERMINISTIC, confidence=0.5)
                                             for u in sorted(units)]))
    return value_f, unit_f


def _treatment_info(mc, caption: str = "", methods: str = "") -> TreatmentInfo:
    ctx = mc.get("treatment_context") or ""
    name = mc.get("treatment_name")
    # Series-aware: enumerations ("10, 30 and 60 ug/ml", "0, 5, 10, 30, 60 min")
    # are expanded so multiplicity is visible instead of silently collapsed.
    doses = extract_dose_series(ctx)
    durs = extract_duration_series(ctx)
    # "for the indicated times/doses" says the panel varies THAT quantity per
    # lane even when only one value is parseable -> never settle that scalar.
    # Kind-specific: a time course's single stimulus concentration stays settled.
    claim_src, verbatim = _claim_source(ctx, caption, methods) if ctx else (None, False)
    src = [claim_src] if ctx else []
    # A regex over verbatim paper text is deterministic evidence; over the
    # model's own treatment wording it is still the model's reading.
    det = ([Source(type="deterministic", rank=RANK_DETERMINISTIC, text=ctx)] if verbatim else src) if ctx else []
    dose_f, dose_unit_f = _series_fields(
        doses, ctx, det, bool(biology._INDICATED_DOSE.search(ctx)), source_examined=verbatim)
    dur_f, dur_unit_f = _series_fields(
        durs, ctx, det, bool(biology._INDICATED_TIME.search(ctx)), source_examined=verbatim)
    return TreatmentInfo(
        treatment_name=EvidenceField.supported(name, 0.8, src) if name else EvidenceField.not_recovered(),
        dose=dose_f,
        dose_unit=dose_unit_f,
        duration=dur_f,
        duration_unit=dur_unit_f,
        treatment_context=EvidenceField.supported(ctx, 0.8, src) if ctx else EvidenceField.not_recovered(),
    )


# A methods sentence often lists several antibodies ("anti-p-STAT3 (CST #9145)
# and anti-actin (Santa Cruz sc-47778)"). Splitting on antibody mentions and
# keeping only the fragment that names THIS antibody's target stops the
# backstop from attaching the first catalog number to the wrong antibody.
# A "candidate protein name" is a token after `anti-`, or a token immediately
# followed by "(" or "antibod…" ("GAPDH (1:5000) and ACTB (Abcam ab8227)
# antibodies"). Generic words that take the same shape are not proteins.
# dash variants (U+2010-2015, U+2212) stay inside a token: "β‑actin", "p‑STAT3"
_AB_TOKEN = r"[^\W_](?:[\w\-\u2010-\u2015\u2212/.]*\w)?"
_AB_CANDIDATE = re.compile(
    rf"\banti-\s*({_AB_TOKEN})|({_AB_TOKEN})(?=\s*\(|\s+antibod)", re.IGNORECASE)
_AB_GENERIC = {"antibody", "antibodies", "primary", "secondary", "monoclonal", "polyclonal",
               "and", "or", "against", "with", "the", "clone"}
_AB_SENTENCE_END = re.compile(r"\.\s+(?=[A-Z])|;")


def _paren_depths(text: str) -> list[int]:
    d, out = 0, []
    for ch in text:
        if ch in ")]":
            d = max(0, d - 1)
        out.append(d)
        if ch in "([":
            d += 1
    return out


def _target_scoped_antibody(text: str, target: str) -> dict:
    """Antibody metadata from the part of `text` that belongs to `target`.

    Scope = from each top-level mention of the target (alphanumeric-bounded, so
    ERK never matches ERK5 and actin never matches alpha-actinin) to the next
    top-level mention of a DIFFERENT candidate protein, a `;`, or the sentence
    end. Parenthesised content never splits a scope. The target must be named;
    otherwise abstain ({}). Within scope, a field with more than one distinct
    value abstains (None) rather than picking the first regex hit."""
    fold = lambda s: _DASHES.sub("-", s or "").lower()   # "β‑actin" (U+2011) == "β-actin"
    keys = {fold(k) for k in (target, biology.core_symbol(target or "")) if k}
    if not text or not keys:
        return {}
    low, depth = fold(text), _paren_depths(text)            # same length: positions align
    is_target = lambda s: any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", fold(s))
                              for k in keys)
    mentions = sorted({m.start() for k in keys
                       for m in re.finditer(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", low)
                       if depth[m.start()] == 0})
    if not mentions:
        return {}
    bounds = [m.start() for m in _AB_SENTENCE_END.finditer(text) if depth[m.start()] == 0]
    for m in _AB_CANDIDATE.finditer(text):
        tok = m.group(1) or m.group(2)
        start = m.start(1) if m.group(1) else m.start(2)
        if depth[start] == 0 and tok.lower() not in _AB_GENERIC and not is_target(tok):
            bounds.append(start)
    scopes = []
    for p in mentions:
        end = min([b for b in bounds if b > p], default=len(text))
        scopes.append(text[p:end])
    # The same target named with its own parenthesised metadata in two separate
    # scopes is two antibodies ("anti-PIK3CA (4249, CST); anti-PIK3CA (sc-293172,
    # Santa Cruz)"): a value visible in one scope says nothing about which
    # antibody this record used, and a value the regexes cannot see in the other
    # scope would make a disagreement look like agreement. Abstain.
    # Retrieval overlap and nearby-page text can repeat the SAME sentence, and a
    # snippet window can truncate one copy: identical (or prefix) scopes are one
    # mention, not two antibodies.
    norm_sc = [re.sub(r"\s+", " ", fold(sc)).strip() for sc in scopes]
    distinct = [n for i, n in enumerate(norm_sc)
                if n and not any(j != i and (m.startswith(n) and (len(m) > len(n) or j < i))
                                 for j, m in enumerate(norm_sc))]
    if sum(1 for n in distinct if "(" in n) >= 2:
        return {}
    scope = " | ".join(scopes)
    quote = next((sc for sc in scopes if "(" in sc), scopes[0]).strip()   # verbatim slice of `text`

    def one(vals):
        uniq = {re.sub(r"[\s#,]", "", v).lower() for v in vals}
        return vals[0] if len(uniq) == 1 else None
    s_low = scope.lower()
    vendors = list(dict.fromkeys(label for key, label in biology.VENDORS.items() if key in s_low))
    cats = ([m.group(1).strip() for m in biology._CATALOG.finditer(scope)]
            or [m.group(1).strip() for m in biology._CATALOG_VENDORCODE.finditer(scope)])
    return {
        "target": None,
        "vendor": one(vendors),
        "catalog_number": one(cats),
        "clone": one([m.group(1) for m in re.finditer(r"\bclone\s+([A-Za-z0-9\-]+)", scope, re.IGNORECASE)]),
        "dilution": one([f"1:{m.group(1).replace(',', '')}" for m in biology._DILUTION.finditer(scope)]),
        "_quote": quote,
    }


def _antibody_info(ab, row_core, mod_fields, caption: str = "", methods: str = "") -> AntibodyInfo:
    text = ab.get("source", {}).get("text", "")
    vendor = ab.get("vendor")
    if vendor:
        for key, label in biology.VENDORS.items():
            if key in vendor.lower():
                vendor = label
                break
    catalog = ab.get("catalog")
    detection_conf = 0.6
    if catalog:
        detection_conf += 0.2
    if vendor:
        detection_conf += 0.15
    detection_conf = min(detection_conf, 0.98)

    assoc = _association_confidence(ab, row_core, mod_fields)
    claim_src, verbatim = _claim_source(text, caption, methods, methods_first=True)
    src = [claim_src] if text else []
    # Deterministic backstop over the antibody's own (target-scoped) snippet.
    # Only over text verified verbatim in the paper: a regex over the model's
    # own paraphrase is not deterministic source evidence.
    # Ranked below the model's methods evidence and never above 0.6 confidence:
    # a regex hit is weaker than a read of the sentence. It only fills a field
    # the model left empty; a disagreeing model value stays the claim and the
    # regex value is kept as a Candidate so reviewers can see the disagreement.
    # When the model's antibody text is its own paraphrase, scan the verbatim
    # methods instead (target-scoped, same abstention rules); the deterministic
    # source then quotes the matched methods window, never the paraphrase.
    det_text = text if verbatim else methods
    det = _target_scoped_antibody(det_text, ab.get("target", "")) if det_text else {}
    det_src = [Source(type="deterministic", rank=RANK_MODEL_TARGET,
                      text=text if verbatim else det.get("_quote", ""))]
    _same = lambda a, b: re.sub(r"[\s#,]", "", str(a)).lower() == re.sub(r"[\s#,]", "", str(b)).lower()

    def mk(v, c=0.9, det_v=None):
        if v:
            field = EvidenceField.supported(v, c, src)
            if det_v and not _same(v, det_v):
                field.candidates.append(Candidate(value=det_v, source_type="deterministic",
                                                  rank=RANK_MODEL_TARGET, confidence=0.6, evidence=det_src))
            return field
        if det_v:
            return EvidenceField.supported(det_v, 0.6, det_src)
        # Only call an antibody attribute NOT_STATED when a target-scoped,
        # verbatim paper snippet was actually examined by the deterministic
        # backstop. Otherwise the extractor simply failed to recover it.
        if det.get("_quote"):
            return EvidenceField.not_stated(det_src)
        return EvidenceField.not_recovered()
    ab_mod = biology.antibody_modification(ab.get("target", ""))
    phospho_specific = ab.get("phospho_specific")
    if phospho_specific is None:
        phospho_specific = ab_mod["modification_type"] == "phosphorylation"
    return AntibodyInfo(
        role=ab.get("role", "detection"),
        antibody_target=mk(ab.get("target")),
        vendor=mk(vendor, det_v=det.get("vendor")),
        catalog_number=mk(catalog, detection_conf, det_v=det.get("catalog_number")),
        clone=mk(ab.get("clone"), det_v=det.get("clone")),
        dilution=mk(ab.get("dilution"), det_v=det.get("dilution")),
        phospho_specific=EvidenceField.supported(bool(phospho_specific), 0.85, src)
        if ab.get("target") else EvidenceField.not_recovered(),
        detection_confidence=round(detection_conf, 2),
        association_confidence=round(assoc, 2),
    )


def _association_confidence(ab, row_core, mod_fields) -> float:
    ab_core = biology.core_symbol(ab.get("target", ""))
    if not ab_core:
        return 0.2
    if ab_core.lower() != row_core.lower():
        return 0.3                       # antibody is for a different protein
    ab_mod = biology.antibody_modification(ab.get("target", ""))["modification_type"]
    mtype = mod_fields["modification_type"]
    if mtype.status == CONFLICTING:
        return 0.6                       # can't confirm association while modification disputed
    row_mod = mtype.value if mtype.status == SUPPORTED else None
    if ab_mod == row_mod:
        return 0.92                      # same protein + same modification state
    return 0.5                           # same protein, modification mismatch


def _kda_hit(text: str) -> tuple[float, str] | None:
    """(kDa value, verbatim window around the match) or None."""
    m = biology._KDA.search(text or "")
    val = extract_kda(text)
    return (val, _around(text, m.start())) if m and val is not None else None


def _kda_near_core(core: str, text: str) -> tuple[float, str] | None:
    """A kDa figure counts as REPORTED for this target only when it appears
    near a mention of the target's core symbol. A page blob's first kDa number
    (ladder descriptions, other rows' masses) must never be attributed to every
    row on the page — that fabricated e.g. 'BEX2 reported 70 kDa' (vs expected
    15.3) and flagged false MW discrepancies on the co-IP paper."""
    if not core or not text:
        return None
    low, core_low = text.lower(), core.lower()
    idx = low.find(core_low)
    while idx != -1:
        window = text[max(0, idx - 30): idx + len(core) + 60]
        hit = _kda_hit(window)
        if hit is not None:
            return hit
        idx = low.find(core_low, idx + 1)
    return None


def _mw_info(caption, methods, res, core: str = "") -> MolecularWeightInfo:
    hit, src_type, src_rank = _kda_near_core(core, caption), "figure_caption", RANK_CAPTION
    if hit is None:
        hit, src_type, src_rank = _kda_near_core(core, methods), "methods", RANK_METHODS
    if hit is None and caption and core and core.lower() not in caption.lower():
        # Core absent from a short caption -> the caption is plausibly about
        # this single target row anyway (same fallback rule as _scoped_site).
        # Applies to the CAPTION only, never the page-level methods blob.
        hit, src_type, src_rank = _kda_hit(caption), "figure_caption", RANK_CAPTION
    reported = hit[0] if hit else None
    # Source text is the verbatim matched window, typed by the channel it came from.
    # A NOT_STATED claim must cite the relevant source channel that actually
    # contains this target; never attach an unrelated caption merely because a
    # caption exists while the target only appears in methods.
    missing_reported_sources: list[Source] = []
    if core and core.lower() in (caption or "").lower():
        missing_reported_sources = [
            Source(type="figure_caption", rank=RANK_CAPTION, text=_snippet(caption, core))
        ]
    elif core and core.lower() in (methods or "").lower():
        missing_reported_sources = [
            Source(type="methods", rank=RANK_METHODS, text=_snippet(methods, core))
        ]
    reported_f = EvidenceField.supported(
        reported, 0.8, [Source(type=src_type, rank=src_rank, text=hit[1])]) \
        if hit else (
            EvidenceField.not_stated(missing_reported_sources)
            if missing_reported_sources else EvidenceField.not_recovered()
        )
    expected = res.expected_mass_kda
    expected_f = EvidenceField.supported(
        expected, 0.9, [Source(type="uniprot_reference", rank=RANK_REFERENCE,
                               text=f"{res.uniprot_id} {expected} kDa (expected)")]) \
        if expected is not None else EvidenceField.not_recovered()
    recon = "not_comparable"
    if reported is not None and expected is not None:
        recon = "match" if abs(reported - expected) / expected <= 0.2 else "discrepancy"
    return MolecularWeightInfo(reported_kda=reported_f, expected_kda=expected_f, reconciliation=recon)


def _pattern_near_core(core: str, text: str) -> Optional[dict]:
    """Band-pattern wording that belongs to THIS target, not to the page.

    Same scoping discipline as reported-MW and co-IP classification: a caption
    sentence like "LC3B resolved as a doublet" must not mark the ACTB row on the
    same panel as a doublet. Only wording within a window around a mention of
    this target's core symbol counts; if the core is never mentioned, no
    page-level pattern is adopted at all.
    """
    if not core or not text:
        return None
    # Clause-scoped, not window-scoped: a sliding character window bleeds across
    # "LC3B resolved as a doublet, while ACTB was the loading control" and marks
    # ACTB a doublet. Captions delimit targets with clause punctuation and
    # contrastive conjunctions, so only the clause naming THIS target counts.
    import re as _re
    core_low = core.lower()
    # Parentheses and "and" also delimit per-target phrasing: "probed for LC3B
    # (doublet) and ACTB" must not hand ACTB the doublet (review finding).
    for clause in _re.split(r"[;.()]|,|\bwhile\b|\bwhereas\b|\band\b", text):
        if clause and core_low in clause.lower():
            hit = biology.detect_band_pattern(clause)
            if hit:
                return hit
    return None


def _band_pattern_fields(b: dict, core: str, caption: str, lane_text: str,
                         n_lanes: int = 1):
    """(pattern, count, notes) EvidenceFields for one band observation.

    Precedence: an explicit observer claim on the row, then this lane's own
    printed text, then target-scoped caption wording. Nothing is inferred from
    the protein's identity or from the number of rows in the panel.
    """
    claim = b.get("band_pattern")
    caption_derived = False
    if claim and str(claim).lower() in biology.BAND_PATTERNS:
        pattern = str(claim).lower()
        raw = str(b.get("band_notes") or claim)
        count = b.get("band_count")
        src = [Source(type="image", rank=5, text=raw)]
        conf = 0.75
        hedged = pattern == "uncertain"
    else:
        lane_hit = biology.detect_band_pattern(lane_text)
        hit = lane_hit or _pattern_near_core(core, caption)
        if not hit:
            return (EvidenceField.missing(), EvidenceField.missing(), EvidenceField.missing())
        caption_derived = lane_hit is None
        pattern, count, raw = hit["pattern"], hit["count"], hit["raw"]
        hedged = hit["hedged"]
        # lane_text is the model's reading of the lane label printed on the
        # image, not caption text: only a caption-derived hit is caption evidence
        src = ([Source(type="figure_caption", rank=RANK_CAPTION, text=raw)] if caption_derived
               else [Source(type="image", rank=RANK_IMAGE, text=raw)])
        conf = 0.6 if hedged else 0.8
    # A caption describes the PANEL; on a multi-lane panel it cannot settle any
    # single lane's pattern ("a doublet appeared after rapamycin" must not
    # stamp the DMSO lane as SUPPORTED doublet — review finding B3). Same
    # panel-vs-lane discipline as the dose/duration scalars.
    if caption_derived and n_lanes > 1:
        hedged = True
        conf = min(conf, 0.5)
    pattern_f = (EvidenceField(value=pattern, confidence=conf, status=AMBIGUOUS, sources=src)
                 if hedged or pattern == "uncertain"
                 else EvidenceField.supported(pattern, conf, src))
    count_f = (EvidenceField.supported(int(count), conf, src)
               if isinstance(count, int) else EvidenceField.missing())
    notes_f = EvidenceField.supported(raw, conf, src) if raw else EvidenceField.missing()
    return pattern_f, count_f, notes_f


def _bands(mc, core: str = "", caption: str = "") -> list[BandObservation]:
    out = []
    for b in mc.get("bands", []):
        cond = b.get("lane_condition")
        cond_text = str(cond or "")
        # Lane-specific dose/duration, read ONLY from this lane's own printed
        # condition ("30 min", "IL-6 + / CL-E 30"). Ambiguous within one lane
        # (>1 value) -> leave MISSING rather than pick one. Never inferred from
        # the panel-level blob.
        # the lane condition is read off the printed lane label on the image
        lane_src = [Source(type="image", rank=RANK_IMAGE, text=cond_text)]
        lane_doses = extract_dose_series(cond_text)
        lane_durs = extract_duration_series(cond_text)
        lane_dose_f = lane_dose_unit_f = EvidenceField.missing()
        lane_dur_f = lane_dur_unit_f = EvidenceField.missing()
        if len(lane_doses) == 1:
            lane_dose_f = EvidenceField.supported(lane_doses[0]["value"], 0.8, lane_src)
            lane_dose_unit_f = EvidenceField.supported(lane_doses[0]["unit"], 0.8, lane_src)
        if len(lane_durs) == 1:
            lane_dur_f = EvidenceField.supported(lane_durs[0]["value"], 0.8, lane_src)
            lane_dur_unit_f = EvidenceField.supported(lane_durs[0]["unit"], 0.8, lane_src)
        pattern_f, count_f, notes_f = _band_pattern_fields(
            b, core, caption, cond_text, n_lanes=len(mc.get("bands", [])))
        out.append(BandObservation(
            lane_index=b.get("lane_index", 1),
            lane_condition=EvidenceField.supported(cond, 0.8, lane_src)
            if cond else EvidenceField.missing(),
            band_state=EvidenceField.supported(
                b.get("band_state"), _band_conf(b.get("confidence")),
                [Source(type="image", rank=5, text="image")]) if b.get("band_state") else EvidenceField.missing(),
            lane_dose=lane_dose_f,
            lane_dose_unit=lane_dose_unit_f,
            lane_duration=lane_dur_f,
            lane_duration_unit=lane_dur_unit_f,
            band_pattern=pattern_f,
            band_count=count_f,
            band_notes=notes_f,
        ))
    return out


# --------------------------------------------------------------------------- #
# Validation / anomaly flags
# --------------------------------------------------------------------------- #

def _validate(record: EvidenceRecord, detection_abs, mod_fields) -> ValidationInfo:
    flags: list[AnomalyFlag] = []
    mtype = record.modification.modification_type

    if mtype.status == CONFLICTING:
        flags.append(AnomalyFlag(code="MODIFICATION_CONFLICT", severity="high",
                                 detail="Sources disagree on whether this is a modified or total protein.",
                                 evidence=[s for c in mtype.candidates for s in c.evidence][:4]))
    if record.modification.residue.status == CONFLICTING:
        flags.append(AnomalyFlag(code="RESIDUE_CONFLICT", severity="high",
                                 detail="Different phospho-sites are claimed for this target."))

    # antibody target vs reconciled modification mismatch
    row_mod = mtype.value if mtype.status == SUPPORTED else "disputed"
    for ab in detection_abs:
        ab_mod = biology.antibody_modification(ab.get("target", ""))["modification_type"]
        if mtype.status == SUPPORTED and ab_mod != mtype.value:
            flags.append(AnomalyFlag(code="ANTIBODY_TARGET_MISMATCH", severity="med",
                                     detail=f"Detection antibody implies {ab_mod or 'total'} but record "
                                            f"modification is {mtype.value or 'total'}."))
            break
        if mtype.status == CONFLICTING:
            flags.append(AnomalyFlag(code="ANTIBODY_TARGET_MISMATCH", severity="med",
                                     detail="Antibody indicates a modification that conflicts with the row label."))
            break

    # A band reported ABSENT cannot simultaneously show a visible structure
    # pattern (doublet/multiple/ladder/smear/single) — flag the contradiction
    # instead of shipping it silently (review finding B4).
    for band in record.bands:
        pat = band.band_pattern.value
        if pat and pat != "uncertain" and band.band_state.value == "absent":
            flags.append(AnomalyFlag(
                code="BAND_PATTERN_STATE_MISMATCH", severity="med",
                detail=f"Lane '{band.lane_condition.value or band.lane_index}' is "
                       f"absent yet carries band_pattern '{pat}'."))
            break

    if record.experiment.experiment_type.value == "non_western":
        flags.append(AnomalyFlag(code="NON_WESTERN_PANEL", severity="high",
                                 detail="Panel is not an immunoblot (Northern/Southern/gel stain/zymography/EMSA); "
                                        "its rows are not western evidence.",
                                 evidence=list(record.experiment.experiment_type.sources)))
    if record.experiment.experiment_type.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="EXPERIMENT_TYPE_AMBIGUOUS", severity="med",
                                 detail="Experiment type is unsettled (often downstream of a modification conflict)."))
    if record.target.canonical_target.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="PROTEIN_AMBIGUOUS", severity="med",
                                 detail="Protein name maps to more than one reviewed UniProt entry."))
    elif record.target.canonical_target.status in (MISSING, NOT_RECOVERED, NOT_STATED):
        flags.append(AnomalyFlag(
            code="PROTEIN_NOT_RECOVERED", severity="med",
            detail="HiveBlot could not reliably normalize this printed target to a reviewed protein entry.",
        ))
    if record.molecular_weight.reconciliation == "discrepancy":
        flags.append(AnomalyFlag(code="MW_DISCREPANCY", severity="med",
                                 detail="Reported migration differs from the expected (UniProt) mass."))

    severities = {f.severity for f in flags}
    if any(f.code in ("MODIFICATION_CONFLICT", "RESIDUE_CONFLICT") for f in flags):
        status = CONFLICTING
    elif ("med" in severities or record.experiment.experiment_type.status == AMBIGUOUS
          or any(f.code == "NON_WESTERN_PANEL" for f in flags)):
        status = AMBIGUOUS
    else:
        status = SUPPORTED
    return ValidationInfo(record_status=status, anomaly_flags=flags, needs_review=status != SUPPORTED)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def _paper_ref(p: dict) -> PaperRef:
    def f(key):
        v = p.get(key)
        return EvidenceField.supported(v, 0.99, [Source(type="deterministic", rank=RANK_DETERMINISTIC, text=str(v))]) \
            if v else EvidenceField.missing()
    return PaperRef(pmid=f("pmid"), pmcid=f("pmcid"), doi=f("doi"), title=f("title"),
                    authors=f("authors"), source_url=f("source_url"))


def _figure_ref(fig: dict, caption: str) -> FigureRef:
    def f(key):
        v = fig.get(key)
        return EvidenceField.supported(v, 0.95, [Source(type="figure_caption", rank=RANK_CAPTION, text=str(v))]) \
            if v else EvidenceField.missing()
    return FigureRef(figure_label=f("figure_label"), panel_label=f("panel_label"),
                     page=fig.get("page"), caption_text=caption or fig.get("caption_text", ""),
                     image_crop_ref=fig.get("image_crop_ref"))


def _band_conf(c) -> float:
    if isinstance(c, (int, float)):
        return float(c)
    return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(str(c).lower(), 0.6)


_DASHES = re.compile("[\u2010-\u2015\u2212]")


def _verbatim_in(snippet: str, text: str) -> bool:
    """`snippet` occurs in `text` modulo whitespace runs, soft hyphens and dash variants."""
    norm = lambda t: re.sub(r"\s+", " ", _DASHES.sub("-", (t or "").replace("\u00ad", ""))).strip()
    snip = norm(snippet)
    return bool(snip) and snip in norm(text)


def _claim_source(text: str, caption: str, methods: str,
                  methods_first: bool = False) -> tuple[Source, bool]:
    """(Source typed by where `text` actually occurs, verbatim?). Text found in
    neither caption nor methods is the model's own wording -> model_target."""
    chans = [("figure_caption", RANK_CAPTION, caption), ("methods", RANK_METHODS, methods)]
    for typ, rank, body in (chans[::-1] if methods_first else chans):
        if _verbatim_in(text, body):
            return Source(type=typ, rank=rank, text=text), True
    return Source(type="model_target", rank=RANK_MODEL_TARGET, text=text), False


def _snippet(text: str, needle: str, width: int = 70) -> str:
    if not text:
        return ""
    if needle:
        i = text.lower().find(needle.lower())
        if i != -1:
            return text[max(0, i - 20): i + len(needle) + width].strip()
    return text[:width].strip()


def _around(text: str, pos: int, width: int = 60) -> str:
    return text[max(0, pos - 10): pos + width].strip()


def _first_gene_after(text: str, pos: int) -> Optional[str]:
    import re
    m = re.search(r"anti-?([A-Z][A-Za-z0-9]{1,7})", text[pos: pos + 60])
    if m:
        return biology.core_symbol(m.group(1))
    # assay abbreviations are not proteins: "Immunoprecipitation (IP) assays" gave bait "IP"
    for m in re.finditer(r"\b([A-Z]{2,}[0-9]?)\b", text[pos: pos + 40]):
        if m.group(1).upper() not in {"IP", "IB", "WB", "IGG", "CO", "INPUT", "WCL", "HA"}:
            return m.group(1)
    return None


def identity_sample(mc: dict) -> str:
    """The biological system this evidence came from, normalized for identity.

    Same precedence as `_sample_info`, so the experiment identity and the
    SAMPLE the UI prints can never disagree about which system a row belongs
    to. Case- and whitespace-folded because `H1792`, `h1792` and ` H1792 ` are
    the same cell line and a reviewer re-typing one must not orphan feedback.

    Deliberately NOT applied to target labels: in this codebase case is
    semantic there (uppercase `P-` is not a phospho marker, lowercase `p-`
    is), so folding a target would merge biologically distinct rows.
    """
    val = mc.get("sample") or mc.get("cell_line") or ""
    return " ".join(str(val).split()).casefold()


def _record_id(case: dict, raw_target: str) -> str:
    """Deterministic experiment identity — the unit researcher feedback keys to.

    Every input is reviewed OBSERVATION data (what the paper printed), never a
    DB serial and never a reconciliation OUTPUT. That is the whole design:
    reconciliation results (modification_label, experiment_type, ip_bait,
    protein_status, confidence) legitimately change when the engine improves,
    and if they fed the identity every stored correction would orphan itself on
    the next fix. Display-layer text never reaches here either, so reformatting
    a lane label cannot move a key.

    Components, and why each earns its place:
      * paper (doi/pmcid/pmid) — which source
      * figure_label, panel_label, crop filename — which blot in that source
      * raw_target — which row of that blot, as printed
      * treatment_context — separates two experiments sharing one crop and one
        target label (Fig 3C vs 3D total-STAT3 in PMC12856536)
      * sample/cell line — separates two experiments sharing crop, target AND
        treatment but run in different biological systems

    The sample component fixes a P0 identity collision: crop
    `page_004_cand_0025.png` in PMC12706926 prints H1792 and A549 side by side,
    so P62, LC3B and ACTB each produced ONE id for TWO biologically distinct
    experiments (12 duplicate stable keys over 24 rows). Search grouping had
    always split those two cards on cell line while the identity did not —
    two disagreeing notions of "one experiment" was the underlying flaw, and
    feedback left on the H1792 arm could surface on the A549 arm.

    Lane identity lives OUTSIDE this hash: `stable_row_key` is
    `<record_id>:<lane_index>`. Lane index is the reviewed panel's own left-to-
    right order — stable across reseeds and immune to lane-label reformatting,
    which the printed condition text is not.
    """
    paper = case.get("paper", {})
    fig = case.get("figure", {})
    mc = case.get("model_claims", {})
    crop = fig.get("image_crop_ref")
    crop_name = str(crop).rsplit("/", 1)[-1] if crop else None
    key = "|".join(str(x) for x in [
        paper.get("doi") or paper.get("pmcid") or paper.get("pmid"),
        fig.get("figure_label"), fig.get("panel_label"), crop_name,
        raw_target, mc.get("treatment_context") or "",
        identity_sample(mc),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

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
from typing import Any, Optional

from . import biology
from .evidence_record import (
    AMBIGUOUS,
    CONFLICTING,
    MISSING,
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
from .supabase_loader import extract_dose, extract_duration, extract_kda

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
    res = resolver.resolve(core)
    target_info = _target_info(raw_target, core, res, mc)

    # ---- modification: gather claims from every source, then reconcile -----
    mod_claims: list[ModClaim] = []
    for ab in detection_abs:
        m = biology.antibody_modification(ab.get("target", ""))
        mod_claims.append(ModClaim(m["modification_type"], m["residue"], m["residue_position"],
                                   "antibody", RANK_ANTIBODY, 0.9,
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
    experiment = _experiment_info(core, caption, methods, mod_fields, ip_abs)

    # ---- sample ------------------------------------------------------------
    sample = _sample_info(mc, caption)

    # ---- treatment (deterministic dose/duration; never invented) -----------
    treatment = _treatment_info(mc)

    # ---- antibodies with detection vs association confidence ---------------
    antibodies = [_antibody_info(ab, core, mod_fields) for ab in antibodies_in]

    # ---- molecular weight: reported (text) vs expected (UniProt) -----------
    molecular_weight = _mw_info(caption, methods, res)

    # ---- bands -------------------------------------------------------------
    bands = _bands(mc)

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
        canonical = EvidenceField.missing()
        uniprot = EvidenceField.missing()
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


def _experiment_info(core, caption, methods, mod_fields, ip_abs) -> ExperimentInfo:
    text_blob = f"{caption}\n{methods}"
    flags: list[str] = []
    sources: list[Source] = []

    co_ip = biology._CO_IP.search(text_blob)
    if co_ip:
        flags.append("co_ip")
        sources.append(Source(type="methods" if biology._CO_IP.search(methods) else "figure_caption",
                              rank=RANK_METHODS, text=_around(text_blob, co_ip.start())))
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
    if "co_ip" in flags:
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
        primary, conf, status = None, 0.2, MISSING

    exp_type = EvidenceField(value=primary, confidence=conf, status=status, sources=sources)
    exp_flags = EvidenceField.supported(sorted(set(flags)), conf, sources) if flags else EvidenceField.missing()

    ip_bait = EvidenceField.missing()
    if "co_ip" in flags:
        bait = None
        if ip_abs:
            bait = biology.core_symbol(ip_abs[0].get("target", ""))
        elif co_ip:
            bait = _first_gene_after(text_blob, co_ip.end())
        if bait:
            ip_bait = EvidenceField.supported(
                bait, 0.75, [Source(type="methods", rank=RANK_METHODS, text=_around(text_blob, co_ip.start()))])
    return ExperimentInfo(experiment_type=exp_type, experiment_flags=exp_flags, ip_bait_protein=ip_bait)


def _sample_info(mc, caption) -> SampleInfo:
    sample_val = mc.get("sample") or mc.get("cell_line")
    cell_line = mc.get("cell_line") or mc.get("sample")
    org = mc.get("organism")
    src_sample = [Source(type="figure_caption", rank=RANK_CAPTION, text=_snippet(caption, str(sample_val or "")))]
    sample_f = EvidenceField.supported(sample_val, 0.9, src_sample) if sample_val else EvidenceField.missing()
    cell_f = EvidenceField.supported(cell_line, 0.9, src_sample) if cell_line else EvidenceField.missing()
    if not org and cell_line:
        org = CELL_LINE_ORGANISM.get(str(cell_line).lower())
        if org:
            organism_f = EvidenceField.supported(
                org, 0.8, [Source(type="deterministic", rank=RANK_DETERMINISTIC,
                                  text=f"{cell_line} -> {org} (cell-line table)")])
        else:
            organism_f = EvidenceField.missing()
    elif org:
        organism_f = EvidenceField.supported(org, 0.85, src_sample)
    else:
        organism_f = EvidenceField.missing()
    return SampleInfo(sample=sample_f, cell_line=cell_f, organism=organism_f,
                      tissue=EvidenceField.missing(), genotype=EvidenceField.missing())


def _treatment_info(mc) -> TreatmentInfo:
    ctx = mc.get("treatment_context") or ""
    name = mc.get("treatment_name")
    doses = extract_dose(ctx)
    durs = extract_duration(ctx)
    src = [Source(type="figure_caption", rank=RANK_CAPTION, text=ctx)] if ctx else []
    det = [Source(type="deterministic", rank=RANK_DETERMINISTIC, text=ctx)] if ctx else []
    return TreatmentInfo(
        treatment_name=EvidenceField.supported(name, 0.8, src) if name else EvidenceField.missing(),
        dose=EvidenceField.supported(doses[0]["value"], 0.85, det) if doses else EvidenceField.missing(),
        dose_unit=EvidenceField.supported(doses[0]["unit"], 0.85, det) if doses else EvidenceField.missing(),
        duration=EvidenceField.supported(durs[0]["value"], 0.85, det) if durs else EvidenceField.missing(),
        duration_unit=EvidenceField.supported(durs[0]["unit"], 0.85, det) if durs else EvidenceField.missing(),
        treatment_context=EvidenceField.supported(ctx, 0.8, src) if ctx else EvidenceField.missing(),
    )


def _antibody_info(ab, row_core, mod_fields) -> AntibodyInfo:
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
    src = [Source(type="methods", rank=RANK_METHODS, text=text)] if text else []
    mk = lambda v, c=0.9: EvidenceField.supported(v, c, src) if v else EvidenceField.missing()
    ab_mod = biology.antibody_modification(ab.get("target", ""))
    phospho_specific = ab.get("phospho_specific")
    if phospho_specific is None:
        phospho_specific = ab_mod["modification_type"] == "phosphorylation"
    return AntibodyInfo(
        role=ab.get("role", "detection"),
        antibody_target=mk(ab.get("target")),
        vendor=mk(vendor),
        catalog_number=mk(catalog, detection_conf),
        clone=mk(ab.get("clone")),
        dilution=mk(ab.get("dilution")),
        phospho_specific=EvidenceField.supported(bool(phospho_specific), 0.85, src)
        if ab.get("target") else EvidenceField.missing(),
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


def _mw_info(caption, methods, res) -> MolecularWeightInfo:
    reported = extract_kda(caption) or extract_kda(methods)
    reported_f = EvidenceField.supported(
        reported, 0.8, [Source(type="figure_caption", rank=RANK_CAPTION, text=f"{reported} kDa")]) \
        if reported is not None else EvidenceField.missing()
    expected = res.expected_mass_kda
    expected_f = EvidenceField.supported(
        expected, 0.9, [Source(type="uniprot_reference", rank=RANK_REFERENCE,
                               text=f"{res.uniprot_id} {expected} kDa (expected)")]) \
        if expected is not None else EvidenceField.missing()
    recon = "not_comparable"
    if reported is not None and expected is not None:
        recon = "match" if abs(reported - expected) / expected <= 0.2 else "discrepancy"
    return MolecularWeightInfo(reported_kda=reported_f, expected_kda=expected_f, reconciliation=recon)


def _bands(mc) -> list[BandObservation]:
    out = []
    for b in mc.get("bands", []):
        out.append(BandObservation(
            lane_index=b.get("lane_index", 1),
            lane_condition=EvidenceField.supported(
                b.get("lane_condition"), 0.8,
                [Source(type="figure_caption", rank=RANK_CAPTION, text=str(b.get("lane_condition") or ""))])
            if b.get("lane_condition") else EvidenceField.missing(),
            band_state=EvidenceField.supported(
                b.get("band_state"), _band_conf(b.get("confidence")),
                [Source(type="image", rank=5, text="image")]) if b.get("band_state") else EvidenceField.missing(),
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

    if record.experiment.experiment_type.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="EXPERIMENT_TYPE_AMBIGUOUS", severity="med",
                                 detail="Experiment type is unsettled (often downstream of a modification conflict)."))
    if record.target.canonical_target.status == AMBIGUOUS:
        flags.append(AnomalyFlag(code="PROTEIN_AMBIGUOUS", severity="med",
                                 detail="Protein name maps to more than one reviewed UniProt entry."))
    if record.molecular_weight.reconciliation == "discrepancy":
        flags.append(AnomalyFlag(code="MW_DISCREPANCY", severity="med",
                                 detail="Reported migration differs from the expected (UniProt) mass."))

    severities = {f.severity for f in flags}
    if any(f.code in ("MODIFICATION_CONFLICT", "RESIDUE_CONFLICT") for f in flags):
        status = CONFLICTING
    elif "med" in severities or record.experiment.experiment_type.status == AMBIGUOUS:
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
    m = re.search(r"\b([A-Z]{2,}[0-9]?)\b", text[pos: pos + 40])
    return m.group(1) if m else None


def _record_id(case: dict, raw_target: str) -> str:
    paper = case.get("paper", {})
    fig = case.get("figure", {})
    key = "|".join(str(x) for x in [
        paper.get("doi") or paper.get("pmcid") or paper.get("pmid"),
        fig.get("figure_label"), fig.get("panel_label"), raw_target,
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

"""Shape a full western_blot_records row (with its provenance JSONB — the
complete Evidence Record dump) into the curated RecordDetail response.

Selection principle: expose the field-level envelopes a researcher needs to
audit the biology (value + status + source snippets + competing candidates),
and drop internal implementation metadata (ranks, extraction versions,
record ids inside the envelope, ...).
"""
from __future__ import annotations

from typing import Any

from .schemas import (
    FieldEvidence,
    RecordAntibody,
    RecordBand,
    RecordDetail,
    review_reasons_from_flags,
)

# Engine-internal markers that live in the provenance envelope but are NOT
# source wording. They must never render in the "quoted from the paper" slot.
# Stored provenance is untouched; this is presentation shaping only.
_INTERNAL_SOURCE_TEXTS = {"", "{}", "ambiguous_family", "None", "none"}

# Candidate values that are internal placeholders rather than claims. The
# modification candidate "none" IS a claim (the row label says total protein)
# and is relabeled, not dropped.
_CANDIDATE_LABELS = {("modification_type", "none"): "no modification (total protein)"}

# (display key, path into the provenance envelope)
_FIELD_PATHS: list[tuple[str, tuple[str, ...]]] = [
    ("canonical_target", ("target", "canonical_target")),
    ("uniprot_id", ("target", "uniprot_id")),
    ("modification_type", ("modification", "modification_type")),
    ("residue", ("modification", "residue")),
    ("residue_position", ("modification", "residue_position")),
    ("phospho_specific_antibody", ("modification", "phospho_specific_antibody")),
    ("experiment_type", ("experiment", "experiment_type")),
    ("experiment_flags", ("experiment", "experiment_flags")),
    ("ip_bait_protein", ("experiment", "ip_bait_protein")),
    ("sample", ("sample", "sample")),
    ("cell_line", ("sample", "cell_line")),
    ("organism", ("sample", "organism")),
    ("treatment_name", ("treatment", "treatment_name")),
    ("dose", ("treatment", "dose")),
    ("dose_unit", ("treatment", "dose_unit")),
    ("duration", ("treatment", "duration")),
    ("duration_unit", ("treatment", "duration_unit")),
    ("reported_molecular_weight_kda", ("molecular_weight", "reported_kda")),
    ("expected_molecular_weight_kda", ("molecular_weight", "expected_kda")),
]


def _dig(obj: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _field_evidence(envelope: Any, name: str = "") -> FieldEvidence | None:
    if not isinstance(envelope, dict) or "status" not in envelope:
        return None
    sources = []
    for s in envelope.get("sources", []) or []:
        if not isinstance(s, dict):
            continue
        text = s.get("text")
        if not isinstance(text, str) or text.strip() in _INTERNAL_SOURCE_TEXTS:
            # Keep the provenance TYPE (e.g. "via UniProt") but never show an
            # internal marker as if it were a sentence from the paper.
            sources.append({"type": s.get("type"), "text": None})
        else:
            sources.append({"type": s.get("type"), "text": text})
    candidates = []
    for c in envelope.get("candidates", []) or []:
        if not isinstance(c, dict):
            continue
        value = c.get("value")
        if value is None:
            continue  # a null candidate carries no claim a researcher can judge
        value = _CANDIDATE_LABELS.get((name, str(value)), value)
        candidates.append({
            "value": value,
            "source_type": c.get("source_type"),
            "confidence": c.get("confidence"),
        })
    return FieldEvidence(
        value=envelope.get("value"),
        confidence=envelope.get("confidence"),
        status=envelope.get("status"),
        sources=sources,
        candidates=candidates,
    )


def _v(envelope: Any) -> Any:
    return envelope.get("value") if isinstance(envelope, dict) else None


def _measure(value: Any, unit: Any) -> str | None:
    """'30 min', not '30.0 min': lane values are stored as floats."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value}{f' {unit}' if unit else ''}"


def build_record_detail(row: dict) -> RecordDetail:
    prov = row.get("provenance") or {}

    fields: dict[str, FieldEvidence] = {}
    for name, path in _FIELD_PATHS:
        fe = _field_evidence(_dig(prov, path), name)
        if fe is not None and fe.status != "MISSING":
            fields[name] = fe
    # Keep MISSING envelopes only for fields where absence is itself
    # informative on the audit panel (modification / experiment / MW).
    for name, path in _FIELD_PATHS:
        if name in fields:
            continue
        if name in ("modification_type", "experiment_type",
                    "reported_molecular_weight_kda", "expected_molecular_weight_kda"):
            fe = _field_evidence(_dig(prov, path), name)
            if fe is not None:
                fields[name] = fe

    antibodies = []
    for ab in prov.get("antibodies", []) or []:
        if not isinstance(ab, dict):
            continue
        src = None
        tgt_env = ab.get("antibody_target")
        if isinstance(tgt_env, dict):
            srcs = tgt_env.get("sources") or []
            if srcs and isinstance(srcs[0], dict):
                src = srcs[0].get("text")
        def _status(name: str):
            env = ab.get(name)
            return env.get("status") if isinstance(env, dict) else None

        antibodies.append(RecordAntibody(
            target=_v(ab.get("antibody_target")),
            target_status=_status("antibody_target"),
            vendor=_v(ab.get("vendor")),
            vendor_status=_status("vendor"),
            catalog_number=_v(ab.get("catalog_number")),
            catalog_number_status=_status("catalog_number"),
            clone=_v(ab.get("clone")),
            clone_status=_status("clone"),
            dilution=_v(ab.get("dilution")),
            dilution_status=_status("dilution"),
            role=ab.get("role"),
            phospho_specific=_v(ab.get("phospho_specific")),
            detection_confidence=ab.get("detection_confidence"),
            association_confidence=ab.get("association_confidence"),
            source_text=src,
        ))

    bands = []
    for b in prov.get("bands", []) or []:
        if not isinstance(b, dict):
            continue
        state_env = b.get("band_state")
        # Lane-specific design values (dose-response / time course). These carry
        # the real per-lane numbers when the panel-level scalar is AMBIGUOUS.
        dose, dose_u = _v(b.get("lane_dose")), _v(b.get("lane_dose_unit"))
        dur, dur_u = _v(b.get("lane_duration")), _v(b.get("lane_duration_unit"))
        bands.append(RecordBand(
            lane_index=b.get("lane_index"),
            lane_condition=_v(b.get("lane_condition")),
            band_state=_v(state_env),
            confidence=state_env.get("confidence") if isinstance(state_env, dict) else None,
            lane_dose=_measure(dose, dose_u),
            lane_duration=_measure(dur, dur_u),
            band_pattern=_v(b.get("band_pattern")),
            band_pattern_status=(b.get("band_pattern") or {}).get("status")
            if isinstance(b.get("band_pattern"), dict) else None,
            band_count=_v(b.get("band_count")),
            band_notes=_v(b.get("band_notes")),
        ))

    validation = row.get("validation") or {}
    flags = [
        {"code": a.get("code"), "severity": a.get("severity"),
         # the engine stores the plain-language reason under `detail`
         "message": a.get("detail") or a.get("message")}
        for a in (row.get("anomaly_flags") or [])
        if isinstance(a, dict)
    ]

    return RecordDetail(
        id=row["id"],
        stable_row_key=row.get("stable_row_key"),
        paper_id=row.get("paper_id"),
        title=row.get("title"),
        doi=row.get("doi"),
        pmcid=row.get("pmcid"),
        pmid=row.get("pmid"),
        figure_label=row.get("figure_label"),
        panel_label=row.get("panel_label"),
        page=row.get("page"),
        figure_caption=row.get("figure_caption"),
        image_crop_ref=row.get("image_crop_ref"),
        raw_target_name=row.get("raw_target_name") or row.get("target"),
        canonical_target=row.get("canonical_target"),
        uniprot_id=row.get("uniprot_id"),
        modification_label=row.get("modification_label"),
        experiment_type=row.get("experiment_type"),
        cell_line=row.get("cell_line"),
        organism=row.get("organism"),
        sample=row.get("sample"),
        band_state=row.get("band_state"),
        lane_condition=row.get("lane_condition"),
        reported_molecular_weight_kda=row.get("reported_molecular_weight_kda"),
        expected_molecular_weight_kda=row.get("expected_molecular_weight_kda"),
        molecular_weight_source=row.get("molecular_weight_source"),
        fields=fields,
        antibodies=antibodies,
        bands=bands,
        record_status=validation.get("record_status"),
        needs_review=row.get("needs_review"),
        anomaly_flags=flags,
        review_reasons=review_reasons_from_flags(
            [{"code": f["code"], "severity": f["severity"], "detail": f["message"]} for f in flags]),
    )

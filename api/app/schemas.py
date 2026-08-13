from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=100, ge=1, le=500)


class WesternBlotRecord(BaseModel):
    # NOTE: fields are strictly ADDITIVE and every new one is Optional with a
    # default of None. The DB returns every column via `SELECT *`; anything not
    # declared here is silently dropped by Pydantic (that is exactly why the
    # Evidence Record columns from migration 001 never reached the browser).
    # Legacy rows have NULLs in all the new columns + needs_review=true by
    # design, so they must render as "not reported", never as fabricated data.
    id: int
    paper_id: str
    page: int | None = None
    western_blot_type: str | None = None
    sample: str | None = None
    organism: str | None = None
    treatment_context: str | None = None
    figure_label: str | None = None
    target: str | None = None
    condition: str | None = None
    band_detected: bool | None = None
    # Settled: confidence is a 0-1 score everywhere - `real` in
    # db/schema.sql, REAL in the nlp.py prompt schema, `number` in the
    # frontend (which renders it as `confidence * 100`%). An extraction
    # pipeline that produces "high"/"medium"/"low" must map to a score
    # before insert; don't reintroduce a text column on one side only.
    confidence: float | None = None

    # --- Evidence Record fields (migration 001, additive) -------------------
    # Paper provenance
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: str | None = None
    source_url: str | None = None
    # Figure
    panel_label: str | None = None
    figure_caption: str | None = None
    image_crop_ref: str | None = None
    # Protein identity
    raw_target_name: str | None = None
    canonical_target: str | None = None
    uniprot_id: str | None = None
    protein_status: str | None = None  # SUPPORTED / AMBIGUOUS / CONFLICTING / MISSING
    # Modification (phospho, cleavage, ...). value is NULL when CONFLICTING.
    modification_type: str | None = None
    residue: str | None = None
    residue_position: int | None = None
    modification_label: str | None = None  # e.g. "phospho-Tyr705"
    modification_status: str | None = None
    phospho_specific_antibody: bool | None = None
    # Experiment. experiment_flags is non-exclusive (co_ip + phospho can coexist).
    experiment_type: str | None = None
    experiment_flags: list[str] | None = None
    experiment_type_confidence: float | None = None
    # Sample extras
    cell_line: str | None = None
    tissue: str | None = None
    genotype: str | None = None
    # Treatment (deterministic parse; never invented)
    treatment_name: str | None = None
    dose: float | None = None
    dose_unit: str | None = None
    duration: float | None = None
    duration_unit: str | None = None
    # Antibody (UCSF researchers care about this a lot)
    antibody_target: str | None = None
    antibody_vendor: str | None = None
    antibody_catalog_number: str | None = None
    antibody_clone: str | None = None
    antibody_dilution: str | None = None
    # Band / MW. Keep expected != reported (never conflate); band_state is
    # categorical present/absent/uncertain, NOT densitometry.
    band_state: str | None = None
    lane_condition: str | None = None
    loading_control: bool | None = None
    reported_molecular_weight_kda: float | None = None
    expected_molecular_weight_kda: float | None = None
    molecular_weight_source: str | None = None
    # Validation / review. The full per-field `provenance` and `validation`
    # JSONB envelopes are intentionally NOT surfaced here (they are the entire
    # record dump); a dedicated record-detail endpoint serves them so list
    # responses stay small ("avoid giant internal blobs by default").
    anomaly_flags: list[dict] | None = None
    needs_review: bool | None = None
    extraction_stage: str | None = None
    extraction_model: str | None = None


class SearchResponse(BaseModel):
    question: str
    generated_sql: str
    count: int
    results: list[WesternBlotRecord]


class ProteinSearchResponse(BaseModel):
    protein: str
    count: int
    results: list[WesternBlotRecord]

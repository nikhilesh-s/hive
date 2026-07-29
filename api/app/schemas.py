from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=100, ge=1, le=500)


class WesternBlotRecord(BaseModel):
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
    # Numeric confidence (0-1) to match the frontend's DatabaseResult type.
    # If the western_blot_records.confidence column is TEXT in Supabase,
    # either cast it in the generated SQL or migrate the column - align
    # on one type before wiring this up against production data.
    confidence: float | None = None


class SearchResponse(BaseModel):
    question: str
    generated_sql: str
    count: int
    results: list[WesternBlotRecord]


class ProteinSearchResponse(BaseModel):
    protein: str
    count: int
    results: list[WesternBlotRecord]

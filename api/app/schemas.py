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
    # Settled: confidence is a 0-1 score everywhere - `real` in
    # db/schema.sql, REAL in the nlp.py prompt schema, `number` in the
    # frontend (which renders it as `confidence * 100`%). An extraction
    # pipeline that produces "high"/"medium"/"low" must map to a score
    # before insert; don't reintroduce a text column on one side only.
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

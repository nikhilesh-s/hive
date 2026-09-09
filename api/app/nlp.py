from .config import settings

# Created on first use, never at import: the experimental stack boots without
# an OpenAI key (search falls back to the deterministic parser), and a
# request that genuinely needs OpenAI fails here, clearly, not at startup.
_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.openai_key:
            raise RuntimeError("OPENAI_KEY is not configured; the NL->SQL generator is unavailable")
        from openai import OpenAI  # lazy

        _client = OpenAI(api_key=settings.openai_key)
    return _client

SQL_PROMPT = f"""
You are an expert PostgreSQL query generator.

Convert the user's natural language question into a SINGLE PostgreSQL SELECT query.

Database schema:

CREATE TABLE {settings.table_name} (
   id BIGSERIAL PRIMARY KEY,
   paper_id TEXT NOT NULL,
   page INTEGER,
   western_blot_type TEXT,
   sample TEXT,
   organism TEXT,
   treatment_context TEXT,
   figure_label TEXT,
   target TEXT,
   condition TEXT,
   band_detected BOOLEAN,
   confidence REAL  -- 0-1 score, not a "high"/"medium"/"low" label
);

Rules:
1. ONLY generate a SELECT query. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.
2. Use only the table {settings.table_name}.
3. Return all columns using SELECT *.
4. For text matching use ILIKE with '%term%'.
5. A drug, treatment, or condition term may appear in EITHER treatment_context OR condition. Match against both with OR, e.g.:
   (treatment_context ILIKE '%term%' OR condition ILIKE '%term%')
6. A sample, cell line, or tissue term may appear in EITHER sample OR organism. Match against both with OR.
7. Use only the core root of a term, not the full phrase. For "Nutlin-3" use '%nutlin%'. For "HeLa cells" use '%hela%'. Drop suffixes like numbers, "cells", "treated".
8. Combine the distinct concepts (target, sample, treatment) with AND, but each concept's column-matching uses OR as above.
9. confidence is a number between 0 and 1, never text. Compare it numerically (confidence >= 0.8), never with ILIKE.
10. Do not explain anything. Return ONLY SQL. Never wrap in markdown.

User Question:
"""


def generate_sql(question: str) -> str:
    response = _get_client().chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SQL_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )

    sql = response.choices[0].message.content or ""
    return sql.replace("```sql", "").replace("```", "").strip()

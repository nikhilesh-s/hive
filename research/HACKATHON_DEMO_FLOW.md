# HiveBlot — hackathon demo flow (~4 minutes)

**The message:** HiveBlot doesn't just find papers. It reconstructs the
biological experiment — and lets researchers verify or correct every claim.

Pre-demo checklist (2 min before):
```bash
.venv/bin/python scripts/local_db.py status        # 452 rows
cd api && .venv/bin/python -m uvicorn app.main:app --port 8000 &
cd web && npm run dev &
```
Open http://localhost:3000/search. Confirm one search works. Do NOT demo from
the home page hero (it redirects to /search anyway).

## 1. The headline search (45s)
Search: **`phospho STAT3 Tyr705`**
Say: every result is a real record from a real 2026 paper — not a text match,
a reconstructed experiment. Point at the card: STAT3 · phospho-Tyr705,
Supported badge, Hep3B, Phospho Western, CST #9145, IL-6 · 10 ng/ml, band
state, **expected 88.1 kDa labeled as reference — HiveBlot never invents a
measured MW**.

## 2. Why HiveBlot says this (60s)
Click **EVIDENCE**. Walk down:
- normalization chain `P-STAT3 (Tyr705) → STAT3 → UniProt P40763`
- field-level evidence with the actual methods/caption snippets
  ("p-STAT3 (Tyr705; 1:1,000; CST #9145)" — via antibody)
- reported MW: *not reported* — "null is better than hallucination"

## 3. Honest uncertainty (45s)
Search: **`ERK`** → open a `P-ERK 1/2` record's evidence.
Say: the paper printed "P-ERK 1/2" with a phospho-specific antibody but no
site. HiveBlot does NOT guess: modification = **CONFLICTING**, both claims
shown (phospho via antibody vs total via row label), protein = the ambiguous
MAPK1/MAPK3 family, never one wrong accession, flagged **Needs review**.
This is the trust story — disagreement is displayed, not resolved.

## 4. co-IP context (30s)
Search: **`co-IP PIK3CA`**
Point at: experiment **Co-IP**, IP bait **PIK3CA**, prey p85
(Proteintech #60225-1-Ig), Input/IgG/IP lanes in the evidence panel.

## 5. The researcher feedback loop (45s)
Still in the evidence panel:
- click 👎 on a field → type a corrected value → submit
- click **+ Missing information?** → request "antibody dilution"
- point at the search prompt "Did HiveBlot understand…"
Say: corrections are stored **beside** the AI extraction, never over it —
every AI claim → human correction pair becomes future evaluation data.

## 6. Close (15s)
"Three real papers, 91 records, every claim auditable to its sentence in the
paper. The extraction model is swappable; the biology layer — normalization,
conflict handling, provenance — is the product."

## Do NOT demo
- The home-page legacy table path (removed, but don't improvise there).
- `/proteins` endpoint (needs cloud Supabase).
- Anything implying automated model extraction is validated — say
  "expert-reviewed reference set; the automated path is staged and will be
  scored against it."
- Densitometry/quantitation of any kind — band state is categorical.

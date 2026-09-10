# Track D — densitometry: from "reading aid" to a defensible feature

Source: code audit 2026-09-09, including a local run of the current module
over the 21 reviewed crops in `api/crops/`. Nothing here is deployed; the
page runs on the experimental stack only.

## Blunt summary

A calibrated quantitative densitometry feature is **not achievable by
2026-09-16**, and the blocker is not code. Nothing in this repo maps pixel
intensity to protein amount, and 14 of 21 reviewed crops are clipped
(pure-black band cores), so for those bands no algorithm can recover a
ratio. What one week can buy is an **assisted band-reading tool that gives
lane ordering and presence with a stated uncertainty, and refuses to give a
ratio when the figure is clipped.** Refusing is the part nobody else does.
Call the feature that; do not call it densitometry until there is a
calibration.

## What exists

`western_blot_miner/densitometry.py:128-209` → `POST
/experimental-densitometry` (`api/app/experimental/densitometry_router.py`)
→ `web/app/experimental/densitometry/page.tsx`. Grayscale, whole-image
polarity guess, morphological-opening background, band-row pick by row-sum
profile, lanes = **equal-width slices of the whole crop width** when a lane
count is given (`:108-110`), plain sums per lane, `relative = corrected /
max(corrected)` within the row, saturation = fraction of pixels exactly 0 or
255. Output is never stored (`stored: false`). Copy on the page is honest
(`EXPERIMENTAL · UNCALIBRATED · NOT STORED`, disclaimer repeated).

## What is wrong, concretely

1. **The region box never reaches the API.** The page sends `region`
   (`page.tsx:79`); the Next proxy rebuilds the body without it
   (`web/app/api/experimental/densitometry/route.ts:4-6`). Every number a
   researcher has seen on that page came from whole-crop auto-detection. No
   test sends `region` through the API.
2. **Lane placement is wrong on every reviewed crop.** With the printed lane
   count (6) on `api/crops/10.1186_s12964-025-02385-8/panel_candidates/page_006_cand_0040.png`,
   lanes 1–2 land on white margin and printed labels (relative 0.00), lane 6
   on the kDa ladder text; the six real lanes all sit inside x≈500–940.
   Auto-detection finds 1–5 lanes on panels with 2–8 printed lanes and 3–14
   band rows on panels with 3–5 strips.
3. **Saturation is the norm, not an edge case.** ACTB lanes are 42–54%
   pure-black. Integrated intensity over a clipped band measures area, not
   amount. The code detects this and prints the number anyway.
4. **Not reproducible under trivial user variation.** Two boxes ~10 px apart
   around the same strip: `[0.00, 0.26, 0.47, 0.00, 0.81, 1.00]` vs `[0.00,
   0.09, 0.28, 0.01, 1.00, 0.91]`. Lane 2 moves 2.9×; the strongest lane
   flips. Ordering and zeros are stable; magnitudes are not. A box that
   includes the membrane border returns six equal "bands" with no warning.
5. **No loading-control normalization**, and the data model cannot express
   it: records carry no strip y-position, so "this ACTB row is the control
   for that LC3B row" cannot be stated. This is a data-model change, not
   image processing. Not this week.
6. **No uncertainty reporting**; two-decimal `relative` values claim a
   precision the tool does not have.
7. **The 59.7% (D1) must be retired, not just not quoted.** 404 of 424
   scored lanes are `present`, so always answering "present" scores 95.3%.
   The tool scored 59.7% and got 6 of 20 absent lanes right. The "ground
   truth" was the model's own image read of the same crop
   (`record_builder.py:583-585`); rows were paired to records by index;
   thresholds 0.35/0.20 were invented
   (`research/experiments/D1_densitometry_vs_bands.md:3-5,181`,
   `scripts/experiments/densitometry_vs_bands.py:14-15,31,64-71`).
8. **Tests are synthetic only.** `western_blot_miner/tests/test_densitometry.py`
   generates its own Gaussian bands; not one assertion touches a real crop.

## Rules that stay

`AGENTS.md` "band presence ≠ densitometry" and HANDOFF "FUTURE intensity
columns stay NULL" stand. The nine reserved columns in
`migrations/001_evidence_record.sql:100-115` stay NULL: they are gated on
ladder calibration, which does not exist. If anything is ever stored it goes
in a separate measurement-artifact table (crop hash, region, lane bounds,
parameters, code version, who drew the box), never on the Evidence Record,
and `web/app/about/page.tsx:91,115` + `web/app/learn/page.tsx:106-108`
change in the same PR. **No DB write this week.**

## Tickets (ordered by dependency)

### D-1 · Forward `region` from the web proxy to the API
- Acceptance: `region` round-trips; response `image.region` echoes the box;
  an API test posts a region and asserts every lane `x0/x1` lies inside it;
  the `page_006_cand_0040.png` case yields lanes confined to the membrane.
- Estimate: 0.5 half-day. Depends on: nothing. Owner: Srushti (Nik reviews).

### D-2 · Researcher-defined lanes; retire equal-width slicing from the user path
- Acceptance: lane dividers rendered inside the drawn region, seeded from
  the printed lane count, draggable; API accepts explicit lane boundaries;
  auto mode only behind a clearly marked diagnostic toggle; a real-crop test
  over ≥5 reviewed crops asserts every boundary lies inside the membrane.
- Estimate: 3 (2 web, 1 api). Depends on: D-1. Owner: Srushti + Nik.

### D-3 · Saturation gate on the band core
- Acceptance: clip fraction computed on the band core, with near-black
  tolerance instead of `== 0/255`; above threshold the response returns
  presence and ordering only with `quantification_refused` and no
  `relative`; threshold justified against the Butler 2019 "Misleading
  Westerns" set already catalogued as `eval/candidates.json:
  difficult-densitometry-quality-01` (PMC6360618, CC BY); fixtures for
  clipped and clean cases. Tanvi sets the threshold.
- Estimate: 2. Depends on: D-2. Owner: Nik + Tanvi.

### D-4 · Report a range, not a point
- Acceptance: API re-runs over N jittered regions and returns low/high per
  lane plus a stability flag; UI prints `0.1–0.3`, never two decimals; when
  the range is meaningless the lane shows `signal` / `no signal above
  background` instead of numbers; a test asserts the range brackets both
  boxes from finding 4.
- Estimate: 2. Depends on: D-2. Owner: Nik.

### D-5 · Retire D1; synthetic recovery study; first author-value comparison
- Acceptance: `research/experiments/D1_densitometry_vs_bands.md` gets a
  header stating the 95.3% baseline, the 6/20 absent recall, and that it
  predates D-1; a synthetic study (extend the generator in
  `test_densitometry.py:20-35` with clipping, JPEG re-encode, gradients, box
  jitter) reports recovery error vs clip fraction and vs jitter; a first
  comparison against the authors' own published LC3B-II:ACTB values in the
  three reviewed papers (`research/independent_scientific_qa.md:603-606`,
  bar charts sit in the rejected candidates under
  `western_blot_miner/data/pdf_runs/*/panel_candidates`) reported as an
  offset with n stated, "n too small" being an allowed result; HANDOFF and
  `research/DEMO_DAY_ARCHITECTURE.md:160-167` updated.
- Estimate: 3 (synthetic 1.5 Nik, author values 1.5 Tanvi). Depends on:
  D-2, D-3. Owner: Nik + Tanvi.

### D-6 · Page honesty: refusal card, method block, export, storage decision
- Acceptance: explicit refusal card for gated/unstable readings; copyable
  method block (crop, region, lane bounds, band row, kernel, clip fractions,
  code version); export-to-JSON button; **no DB write**; decision text in
  HANDOFF that the reserved columns stay NULL and any future storage is a
  separate artifact; page title and copy say "band reading", not
  "densitometry", until a calibration exists.
- Estimate: 2. Depends on: D-3, D-4. Owner: Srushti (UI) + Nik (decision).

### D-7 · Line up real ground truth (starts now, lands after 09-16)
- Acceptance: one UCSF lab agrees to run a two-fold dilution series with
  known µg per lane, captured clean and deliberately over-exposed (Tanvi
  writes the protocol); a survey of journal Source Data deposits and IDR /
  figshare "uncropped western blot" sets for paired (image, per-lane
  numbers), written up as go/no-go for a real calibration.
- Estimate: 1 to send and track, then weeks. Depends on: nothing. Owner:
  Yashvi + Tanvi.

Total D-1..D-6: 12.5 half-days. Fits one week only across two engineers and
only if D-5's author-value pass is allowed to return "n too small".

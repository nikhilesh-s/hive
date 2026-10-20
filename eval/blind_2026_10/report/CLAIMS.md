# Public-claim review, blind benchmark October 2026

Skeptical review, 2026-10-20, against the wording playbook fixed 2026-10-18. Inputs: PREREGISTRATION.md,
DEVIATIONS.md A1-A8, BENCHMARK_REPORT.md, report/RESULTS.md, report/results.json, report/AUDIT.md,
annotations/tanvi/{aliases,adjudications,confirmation,confirmation_classification}.csv.

## 1. Number check

- results.json tier (ii) ALL FIELDS: CORRECT 512, INCORRECT 30, UNSUPPORTED 11 -> 512/553 = **92.59%**. RESULTS.md matches.
- The report prints "93%" (round half up). Playbook says round down: **92%**.
- Sensitivity of P (all >= 85% except raw):

| Version | P |
|---|---|
| (i) pre-registered raw | 222/285 = 77.9% (fails P >= 85%) |
| A7 matching only, no annotator verdicts | 336/387 = 86.8% |
| (ii) headline | 512/553 = 92.6% |
| (ii) minus the 7 phospho_site cells (see below) | 505/546 = 92.5% |
| (ii) band calls only | 432/450 = 96.0% |
| (ii) everything except band calls | 80/103 = 77.7% (fails P >= 85%, N < 150) |

## 2. Tier (ii) audit: notation only?

Mostly yes. Items that are really label edits filed as notation:
- **alias_panel_id, confirmation row 26** (GAPDH row moved from Fig 3B to 3C). The annotator filed it
  under the wrong panel; this is a label correction made after seeing output. Net effect: +2 correct,
  +2 incorrect, so it lowers P slightly. Should be class B; harmless to the number.
- **alias_modification, row 14** (7 phospho sites added). She wrote "phosphorylation" with no site; the
  sites were added after unsealing. That is new label content, not notation. +7/+7; removing it gives 92.5%.
- **alias_label SOSTMI/LC31/PSMBS**: misreadings of the printed label. Same entity, so notation-like,
  but a transcription error belongs in ERRATA. Acceptable; disclose.
- **A7 lane-count exclusion** removed 104 lane calls, including 5 APP INCORRECT cells, after unsealing.
  Justified (physical lanes vs samples), but it is a post-hoc exclusion that removed errors.
- EQUIVALENT_NOTATION verdicts (AIF/AIFM1; 18 fibroblast sample cells) are legitimate notation.

None of these moves the rounded-down number. Verdict: 92% is robust; P >= 85% holds in every post-A7 version.

## 3. Caveats

| Caveat | Rating |
|---|---|
| n = 3 papers, 8 (9) labeled panels, 47 rows | must-disclose |
| One annotator, no agreement figure; she is a HiveBlot team member, not an outside biologist | must-disclose |
| 450 of 553 assertions are band calls, 370 of them from one paper; lanes are correlated, so effective N is far below 553 | must-disclose |
| Non-band fields: 80/103 (77%) | must-disclose if asked; blocks any per-field claim |
| A6-A8 matching fixes after unsealing; annotator saw system values on the confirmation sheet | must-disclose (raw 78% exists) |
| Raw pre-registered P 78% is below the 85% gate | must-disclose if the number is used |
| Inventory incomplete (11 chosen, >= 24 visible); 27 records unscored | must-disclose; kills any recall claim |
| 104 lane calls unscored for lane-count mismatch | must-disclose (in fuller version) |
| Retracted paper drawn and excluded, not replaced (4 -> 3) | fine (logged before scoring) |
| Treatment 0/11 in tier (ii) because labels were wrong | fine (penalises the system; never claim treatment accuracy) |
| Protein identity coverage 23%, precision 79% | must-disclose; never claim identity accuracy |
| Coverage 57% | must-disclose alongside P |
| claude_cli transport, not production API | fine (same model and prompts) |
| Hard, adversarial pool | fine |
| Speed: 15.4 min vs 41 s are different units | fatal if claimed; do not claim |
| "93%" | fatal under the playbook; use 92% |

## 4. Candidate claims, go / no-go

| Claim | Decision |
|---|---|
| "In a blind test against a biologist, 93% of the 553 facts HiveBlot extracted matched" | **NO-GO**. 93% is not rounded down; "a biologist" overstates a single team-member annotator; "facts extracted" implies all output (27 records unscored, 104 lanes unscored); hides coverage. |
| "92% of 553 values HiveBlot stated matched a human annotator" (with "blind", n, coverage nearby) | GO |
| Any "accuracy" wording for 92% | NO-GO |
| Panel recall 91% | NO-GO |
| Speed-up (e.g. "20x faster") | NO-GO |
| Per-field claims (identity, treatment, cell line) | NO-GO |
| Tier (iii) 98% | NO-GO (post-hoc) |

## 5. One-line claims (<= 95 characters)

1. `Pre-registered blind test: 92% of 553 values HiveBlot stated matched a human annotator` (86)
2. `Blind test, 3 papers: 92% of 553 Western blot values HiveBlot stated matched human labels` (89)
3. `Blind test, 3 papers: 92% of HiveBlot's 553 stated values matched labels; 57% coverage` (86)

## 6. Fuller version (2 sentences)

In a pre-registered blind test on 3 papers, 92% of the 553 Western-blot values HiveBlot asserted
matched labels a wet-lab annotator made from the paper alone. It filled in 57% of the labeled values
(512 of 895), mostly by declining to name gene symbols rather than guessing wrong.

## 7. "How was it measured?" (one sentence)

We pre-registered the method, sealed HiveBlot's output from 3 randomly drawn papers, had a teammate with
Western-blot experience label the blots from the PDFs alone without seeing it, then scored every value
HiveBlot stated against her labels, allowing only notation fixes she confirmed.

## 8. Must NOT say

- "93%", "accuracy", "accurate 92% of the time".
- "against a biologist" / "expert-validated" / "independent" (one annotator on the team).
- "553 facts extracted" or "all facts" (only scored assertions on 8-9 labeled panels).
- "98%" (tier iii), "91% recall", "finds 91% of blots".
- Any speed or time-saved number.
- Anything about treatment, protein-identity, or cell-line accuracy.
- "Validated", "benchmarked on the literature", "generalizes".
- 92% without "blind test", the sample size, or coverage reachable in the same place.

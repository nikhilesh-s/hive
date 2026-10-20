# B-12 expected mappings (for Tanvi's bio review, Q-3)

**Status: DRAFT. Do not merge before the blind benchmark is scored (Tue 10-20).** The PR that
carries this file changes the resolver and `biology.py`, which the frozen benchmark runs on.

**For Tanvi's bio review (Q-3).** Every row below is something the code now does to a label as
printed. Please mark each row right, wrong, or "right but needs paper context". Anything you mark
wrong or context-dependent becomes a one-line removal from the rule tables in `biology.py`.

## How to read this

- **Raw name** is the label exactly as the extractor stored it. The raw name is always kept; the
  mapping is an extra field.
- **Status** uses the existing record statuses:
  - **SUPPORTED**: one gene, one UniProt accession.
  - **AMBIGUOUS**: the label names a family or leaves the isoform open. The candidates are
    listed, no gene is chosen, and the record gets the existing `PROTEIN_AMBIGUOUS` flag, so
    `needs_review` becomes true.
  - **unresolved**: no canonical target, same as before, but now labeled (viral or tag) instead of
    silently empty.
- **Rows** is how many rows in the 16 local PDF runs carry that exact raw name (6,170 rows in
  total, 2,787 of them unresolved before this change). Local outputs only; not the live corpus.
- Accessions are UniProtKB reviewed human entries, checked against rest.uniprot.org on 2026-10-19.
  The live resolver scopes to the paper's organism; the offline fallback map is human only.
- **Rule** is the id used in `biology.normalize_target` and in
  `western_blot_miner/tests/test_target_normalization.py`.

## 1. Single gene (SUPPORTED)

| Raw name | Rows | Maps to | Accession | Also recorded | Rule | Rationale |
|---|---|---|---|---|---|---|
| Vinculin | 4 | VCL | P18206 | - | name_alias | Protein name, not the gene symbol, so `gene:` search never matched. |
| Bcl-xL | 5 | BCL2L1 | Q07817 | - | name_alias | Bcl-xL is the long isoform of BCL2L1. Mapped at gene level; the isoform is not recorded. |
| IL-18 | 24 | IL18 | Q14116 | - | name_alias | HGNC symbol has no hyphen. |
| IL-18 CL | 24 | IL18 | Q14116 | - | name_alias | Trailing "CL" is ignored for identity. It is NOT read as "cleaved" (in inflammasome papers CL is usually cell lysate vs supernatant). |
| α-IL-18 | 4 | IL18 | Q14116 | - | anti_alpha_prefix + name_alias | See question 4. |
| GFP-KRAS | 12 | KRAS | P01116 | note: GFP tag | epitope_tag | The tag names the construct. The target is the tagged protein. |
| FLAG-STAT3, GFP-STAT3 | 12 each | STAT3 | P40763 | note: tag | epitope_tag | Same. |
| LC3B | 69 | MAP1LC3B | Q9GZQ8 | - | lc3_isoform_stated | "B" is stated, so one gene. UniProt lists LC3B as MAP1LC3B. |
| LC3B-I, LC3B-II, LC3B I / II | 2, 2, 9 | MAP1LC3B | Q9GZQ8 | note: forms I/II | lc3_isoform_stated | I and II are the cytosolic and lipidated forms of one protein. Kept as a note, not as a modification (the schema has no lipidation type). |
| α-CASP1 | 4 | CASP1 | P29466 | - | anti_alpha_prefix | "α-" read as anti- (antibody label); see question 4. |
| α-CASP3 cl. (CASP3 p19 / CASP3 p17) | 9 | CASP3 | P42574 | cleavage ("cleaved") | cleaved_abbreviation + anti_alpha_prefix | "cl." is the written abbreviation of "cleaved". The parenthetical fragment list is ignored for identity. |
| α-CASP3 cl. | 4 | CASP3 | P42574 | cleavage | same | Same. |
| α-CASP7 cl. | 4 | CASP7 | P55210 | cleavage | same | Same. |
| α-GSDMD, α-GSDME | 4 each | GSDMD, GSDME | P57764, O60443 | - | anti_alpha_prefix | See question 4. |
| CASP1p10 | 4 | CASP1 | P29466 | none | cleavage_fragment_suffix | A "p10" size suffix is dropped for identity. Cleavage is NOT asserted from a size suffix (question 5). |
| Cleaved caspase-3 | 16 | CASP3 | P42574 | cleavage (already supported) | form_qualifier + name_alias | "caspase-N" maps to CASPN for N in 1-10 and 14. |
| Active β-catenin | 12 | CTNNB1 | P35222 | none | form_qualifier + name_alias | "Active" is antibody-defined (which residues are unphosphorylated is not in the label), so no modification is asserted. |
| Ph-eIF2α | 26 | EIF2S1 | P05198 | phosphorylation, no site | name_alias | "Ph-" (capital P, lowercase h, hyphen) is read as an explicit phospho abbreviation, like "p-STAT3". The site is not asserted (question 2). |
| Total-eIF2α | 24 | EIF2S1 | P05198 | none (total) | name_alias | "Total-" is a total-protein marker. "Total protein" (a loading control) is left alone. |
| Total-4EBP1 | 24 | EIF4EBP1 | Q13541 | none (total) | name_alias | Same. 4E-BP1 and 4EBP1 fold to the same key. |
| Non-Phos-4EBP1, non-phos-4EBP1 | 24, 2 | EIF4EBP1 | Q13541 | none, plus a note | non_phospho_prefix | The antibody reads the NON-phosphorylated form, which is not "total". The schema cannot say that, so the row looks like a total row plus a note (question 3). |
| β actin | 41 | ACTB | P60709 | - | (core_symbol) | Existing alias. It failed only because "β actin" with a space was cut to "beta". |
| Mcl-1 | 30 | MCL1 | Q07820 | - | name_alias | Hyphenated common name. |
| Bcl-2 | 20 | BCL2 | P10415 | - | name_alias | Same. |
| Beclin-1, Beclin 1, Beclin1 | 41, 28, 4 | BECN1 | Q14457 | - | name_alias | Same. |
| SHP-1, SHP1 | 35, 28 | PTPN6 | P29350 | - | name_alias | UniProt lists SHP-1 as PTPN6. |
| SHP2 | 8 | PTPN11 | Q06124 | - | name_alias | UniProt lists SHP-2 as PTPN11. |
| Survivin | 8 | BIRC5 | O15392 | - | name_alias | UniProt: "Apoptosis inhibitor survivin". |
| c-Myc | 8 | MYC | P01106 | - | name_alias | The protein, not the tag (a bare "Myc" is never treated as a tag). |
| Cyclin D1 | 8 | CCND1 | P24385 | - | name_alias | Common name. |

## 2. Ambiguous families (AMBIGUOUS, no gene chosen)

| Raw name | Rows | Candidates | Rule | Rationale |
|---|---|---|---|---|
| Ras, pan-Ras | 7 | HRAS, KRAS, NRAS | ambiguous_family | Isoform not stated. |
| Jnk, p-JNK, SAPK/JNK | 5 | MAPK8 (JNK1), MAPK9 (JNK2), MAPK10 (JNK3) | ambiguous_family | Isoform not stated. Same treatment as the existing ERK entry. |
| LC3, LC-3, LC3-I, LC3-II, LC3-I/LC3-II, LC3-I / LC3-II, LC3 I/LC3 II, LC3-II/LC3-I | 116, 4, 288, 288, 52, 11, 3, 10 | MAP1LC3A, MAP1LC3B, MAP1LC3C | lc3_isoform_unstated | No letter, so A, B or C. Becomes SUPPORTED when a B (or A/C) is stated. See question 1. |
| α-actinin | 47 | ACTN1, ACTN2, ACTN3, ACTN4 | ambiguous_family | Isoform not stated. |
| α-tubulin, β-tubulin | 16, - | none listed | ambiguous_family | Multi-gene families (TUBA*, TUBB*). No candidate list, so a partial list does not imply a complete one. |
| MyHC, myosin heavy chain | 14, - | none listed | ambiguous_family | Multi-gene MYH family. |

Side effect to expect: these are mostly loading controls and autophagy markers, so about 870 local
rows move from "unresolved, not flagged" to "AMBIGUOUS, needs_review true". That is the intended
direction (B-14), but it will raise the review count on loading-control rows (question 6).

## 3. Not human proteins (unresolved, now labeled)

| Raw name | Rows | Label | Rule | Rationale |
|---|---|---|---|---|
| Vpr, Nef, Vif, Vpu, gp120 | 217, 49, 48, 24, 24 | viral protein (primate lentivirus, HIV/SIV), non-human | viral_protein | Names specific to HIV/SIV. Never sent to human UniProt. Row gets a low-severity `NON_HUMAN_TARGET` flag (no change to record status). |
| Vpr-myc, Flag-Vif, Nef-HA | 92, 46, 25 | same, plus the tag noted | epitope_tag + viral_protein | Tag stripped first. |
| FLAG, mCherry (bare) | 2, 13 | epitope/fusion tag, not a protein | bare_tag | The tagged protein is not named. Row gets a low-severity `EPITOPE_TAG_TARGET` flag. |

## 4. Deliberately NOT changed (your call)

| Raw name | Rows | Why it was left alone |
|---|---|---|
| p55 | 48 | The ticket lists it as viral (HIV-1 Gag precursor), but host proteins also use "p55" (for example the TNF receptor 1 and PI3K p55 subunits). Needs paper context, not a name rule. |
| P62, Sqstm1/p62 | 42, 34 | Probably SQSTM1 in these autophagy papers, but "p62" is also used for other proteins. "Sqstm1/p62" states the symbol, so it could be mapped if you agree (question 7). |
| pTyr-STAT3, pTyr705-STAT3, pTyr-EGFR, pTyr-JAK2, pTyr-Src, pSer-Akt, pSer-STAT3, pThr/Tyr-ERK | 91 | Residue-prefixed phospho labels. Fixing the identity without the modification layer would show phospho rows as clean total rows, which is worse than unresolved. Needs modification-layer support first. |
| Tat, Rev | - | TAT is also a human gene. |
| C-PARP1 | 8 | "C-" could mean cleaved or C-terminal. |
| CASP1/4 p20/p19 | 14 | Two genes in one label. |
| Ubiquitin | 34 | Not one gene (UBB, UBC, UBA52, RPS27A); a candidate for an AMBIGUOUS family. |
| α-SMA, α-catenin, α-synuclein | - | The α is part of the name, so "α-" is read as anti- ONLY before CASP, GSDM and interleukin symbols. |
| K-Ras, H-Ras, N-Ras, JNK1/2/3, IL-1β | - | Isoform-stated forms not mapped yet. |
| RFX-1, Ki67, dg-TF, ATG12-ATG5, p85 | 30, 4, 24, 12, 4 | Next batch if you approve the style. |
| 43S, 28S, 18S, 47S... (rRNA) | over 350 | Northern blot rows; this is B-13, not a name problem. |

## 5. Questions for Tanvi

1. **LC3 without a B (question 1).** Okay to keep LC3, LC3-I and LC3-II as AMBIGUOUS across A/B/C even when
   the paper's antibody is anti-LC3B? (Using the antibody's stated isoform would settle most of
   them; not done here because that is a new evidence rule.)
2. **"Ph-" (question 2).** Confirm "Ph-eIF2α" in the Lyons paper means phospho-eIF2α, and whether
   the site (Ser51) should be asserted from the text.
3. **Non-Phos-4EBP1 (question 3).** How should a non-phospho-specific antibody row be represented? Today it
   resolves to EIF4EBP1 with no modification, plus a note.
4. **"α-" as anti- (question 4).** Confirm that in the Taabazuing labels "α-CASP1", "α-GSDMD",
   "α-IL-18" mean "anti-" and are not part of a name.
5. **Fragments (question 5).** Does "p10", "p17", "p19", "p20" count as an explicit cleavage statement? Today
   only the words "cleaved"/"cleavage" and the abbreviation "cl." do.
6. **Loading controls (question 6).** Are you fine with α-tubulin and α-actinin turning into AMBIGUOUS
   needs-review rows, or do you want a family-level canonical for them?
7. **p55, p62, Ubiquitin (question 7).** Which of these may be mapped from the paper's context?
8. **Viral wording (question 8).** "primate lentivirus (HIV/SIV)" is used because the names exist in HIV-1,
   HIV-2 and SIV. Say if a paper-specific label is preferred.

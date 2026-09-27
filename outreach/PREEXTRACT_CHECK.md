# Wave 1 pre-extracted papers: Tanvi's check sheet

Extracted 2026-09-27 with the local `claude_cli` backend into the hosted live tier
(`LIVE · UNREVIEWED`). Nothing here has been sent to anyone. **A "your paper" variant email
goes out only for a paper Tanvi marks ✅ below.** Everyone else gets the normal first email.

How to open a paper: hosted `/experimental/research` (needs the beta code), section
"Already extracted in this stack", then **Open extracted evidence**. Once Srushti ships
`?doi=` deep links, the link for each paper is
`https://hiveblot-beta.vercel.app/experimental/research?doi=<DOI>&lab=<lab_tag>&access=ACCESS_CODE`.

## What to check on each paper (15 minutes)

1. Open two or three panels. Does the crop show a western blot (not a Northern, gel stain, or
   microscopy)?
2. Target: right protein? Is the paper's main target present at all?
3. Antibody: vendor, catalog and dilution match the methods, or are honestly empty?
4. Lane readout: does band present / absent match the crop for at least one panel?
5. Would you be comfortable with the author reading this? If not, mark ❌ and say why.

## Papers

| Prospect (sender) | DOI | Rows / experiments / crops | Auto-flags from the data | Tanvi |
|---|---|---|---|---|
| Sikandar (Yashvi) | 10.17912/micropub.biology.001928 | 6 / 3 / 1 | STAT3 + ACTB found; LMO2 (the paper's subject) not extracted; "FLAG" unresolved | ☐ |
| Taabazuing (Yashvi) | 10.1371/journal.ppat.1014178 | 1230 / 136 / 10 | 12 caspase-pathway targets; cleaved fragments ("α-CASP3 cl.", "CASP1p10") unresolved; 0% needs-review looks too clean; no catalog numbers | ☐ |
| Serra-Moreno (Yashvi) | 10.1371/journal.ppat.1014020 | 1910 / 237 / 22 | Vpr, Nef, Vif, LC3-I/II unresolved (1206 rows) yet 0% needs-review | ☐ |
| Burslem (Yashvi) | 10.1038/s41467-024-50235-x | 67 / 13 / 5 | **Ras, GFP-KRAS, Bcl-xL, JNK unresolved**: the paper's main target has no canonical name | ☐ |
| Bajaj (Yashvi) | 10.1038/s41419-025-08233-4 | 36 / 6 / 1 | Only 1 crop; SLC6A6 (the paper's subject) not extracted; recall likely low | ☐ |
| Haricharan (Tanvi) | 10.1038/s41467-025-67257-8 | 113 / 11 / 4 | MLH1, PMS2, CDK6, PCNA; 101 rows with catalog numbers | ☐ |
| Albrecht (Yashvi) | 10.1038/s42255-026-01457-4 | 369 / 110 / 34 | PFKM/PFKL/PFKP present; vinculin, MyHC unresolved; no catalog numbers | ☐ |
| Sachetto (Yashvi) | 10.1016/j.rpth.2025.103016 | 118 / 17 / 7 | Tissue factor found; cell_line field carries load amounts ("BxPC-3 (1 μg)") | ☐ |
| Lyons (Tanvi) | 10.1093/nar/gkag499 | 506 / 94 / 12 | **~455 rows are rRNA species (18S, 28S, 47S): Northern blots extracted as westerns**; do not send until fixed | ☐ |

Not extracted (no downloadable open-access PDF; publisher bot check): House, Banh, Eichner,
Spangle, Janes, Akiyama, Cocco, Khambu, Courtney. Skipped by design: Vlassakis (review),
Gomes (review), Bibel (blog), Brooks and Kahn (guidelines/protocol), Hoover (core),
Mudumbi, McDonough, Adams (not open access).

The auto-flags are filed as bio-QA tickets B-12 to B-14 on `main`.

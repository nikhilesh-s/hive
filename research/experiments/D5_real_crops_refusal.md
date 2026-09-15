# D5 — refusal behaviour on the 21 reviewed crops (diagnostic geometry)

Method `hiveblot.densitometry` v0.2.0; `scripts/experiments/densitometry_real_crops.py`. No densitometry ground truth exists for these figures, so this reports only what the gates DO on real published panels: refuse, warn, or accept. Band rows and lanes are auto-detected here (diagnostic); a researcher's hand-drawn strip and lanes are the product path and will change the lane count, not the clipping.

- crops: 21 · band rows probed (up to 6 per crop): 112
- row states: ok 15, quantification_refused 78, warning 19
- crops with at least one refused row: 20 / 21
- crops with a row whose band core is clipped past the 10% gate: 21 / 21
- rows refused because the reference lane moves under perturbation: 1

| paper | crop | row | y | lanes (auto) | max clipped core | refused lanes | no-signal lanes | ranking stable | state | reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 0 | 620–661 | 3 | 92% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 1 | 278–319 | 6 | 64% | 4 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 2 | 517–553 | 4 | 46% | 3 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 3 | 394–420 | 4 | 64% | 2 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 4 | 155–164 | 5 | 48% | 5 | 4 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_004_cand_0025.png | 5 | 335–343 | 2 | 50% | 1 | 1 | False | quantification_refused | the strongest lane changes under +/-32px lane / +/-2px row perturbation; the relative scale is not defined for this geometry |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 0 | 650–736 | 2 | 77% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 1 | 390–464 | 2 | 77% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 2 | 805–853 | 2 | 70% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 3 | 537–575 | 3 | 99% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 4 | 476–504 | 2 | 98% | 2 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_005_cand_0032.png | 5 | 593–603 | 3 | 90% | 3 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 0 | 567–615 | 3 | 51% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 1 | 285–319 | 2 | 43% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 2 | 394–421 | 2 | 24% | 2 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 3 | 453–475 | 1 | 15% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 4 | 633–640 | 1 | 32% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0037.png | 5 | 529–536 | 1 | 4% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 0 | 713–751 | 3 | 41% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 1 | 341–383 | 3 | 27% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 2 | 465–507 | 3 | 43% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 3 | 604–634 | 3 | 26% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 4 | 552–559 | 2 | 29% | 2 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0039.png | 5 | 525–532 | 1 | 29% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0040.png | 0 | 338–382 | 3 | 38% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0040.png | 1 | 710–745 | 2 | 56% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_006_cand_0040.png | 2 | 610–634 | 2 | 28% | 1 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_006_cand_0040.png | 3 | 417–421 | 1 | 0% | 0 | 1 | None | quantification_refused | no lane has signal above background in the selected row |
| 10.1186_s12964-025-02385-8 | page_006_cand_0040.png | 4 | 427–530 | 1 | 12% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 0 | 433–515 | 2 | 19% | 1 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 1 | 790–832 | 3 | 33% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 2 | 562–604 | 4 | 28% | 4 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 3 | 679–714 | 2 | 21% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 4 | 422–429 | 2 | 37% | 1 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_007_cand_0045.png | 5 | 537–544 | 1 | 7% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 0 | 334–397 | 3 | 41% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 1 | 791–821 | 1 | 54% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 2 | 653–669 | 3 | 33% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 3 | 301–310 | 2 | 23% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 4 | 556–565 | 2 | 0% | 0 | 0 | True | ok |  |
| 10.1186_s12964-025-02385-8 | page_007_cand_0046.png | 5 | 413–419 | 2 | 20% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0047.png | 0 | 456–464 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.1186_s12964-025-02385-8 | page_007_cand_0047.png | 1 | 245–249 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.1186_s12964-025-02385-8 | page_007_cand_0047.png | 2 | 357–455 | 1 | 16% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_007_cand_0047.png | 3 | 270–348 | 2 | 26% | 1 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 0 | 400–484 | 1 | 11% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 1 | 926–976 | 3 | 40% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 2 | 675–723 | 3 | 38% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 3 | 799–842 | 4 | 27% | 4 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 4 | 1211–1249 | 2 | 53% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_009_cand_0055.png | 5 | 552–593 | 5 | 30% | 5 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 0 | 584–640 | 3 | 39% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 1 | 713–763 | 2 | 42% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 2 | 448–492 | 2 | 28% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 3 | 988–1024 | 2 | 47% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 4 | 330–360 | 3 | 37% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0060.png | 5 | 878–905 | 2 | 25% | 1 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 0 | 423–489 | 2 | 29% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 1 | 823–883 | 2 | 24% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 2 | 690–737 | 2 | 42% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 3 | 963–1003 | 3 | 53% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 4 | 299–342 | 2 | 25% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.1186_s12964-025-02385-8 | page_010_cand_0062.png | 5 | 565–599 | 3 | 27% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_004_cand_0028.png | 0 | 548–604 | 2 | 2% | 0 | 0 | True | ok |  |
| 10.3892_br.2026.2108 | page_004_cand_0028.png | 1 | 131–167 | 4 | 37% | 3 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_004_cand_0028.png | 2 | 288–311 | 4 | 32% | 2 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_004_cand_0028.png | 3 | 382–386 | 2 | 0% | 0 | 0 | True | ok |  |
| 10.3892_br.2026.2108 | page_004_cand_0028.png | 4 | 396–493 | 2 | 21% | 1 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_004_cand_0029.png | 0 | 125–171 | 3 | 33% | 2 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_004_cand_0029.png | 1 | 413–450 | 2 | 28% | 1 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_004_cand_0029.png | 2 | 289–313 | 2 | 31% | 1 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_004_cand_0029.png | 3 | 527–642 | 1 | 4% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.3892_br.2026.2108 | page_005_cand_0034.png | 0 | 313–407 | 2 | 2% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.3892_br.2026.2108 | page_005_cand_0034.png | 1 | 95–184 | 2 | 13% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_005_cand_0034.png | 2 | 221–296 | 2 | 3% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.3892_br.2026.2108 | page_005_cand_0035.png | 0 | 226–272 | 2 | 35% | 1 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_005_cand_0035.png | 1 | 337–377 | 1 | 46% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_005_cand_0035.png | 2 | 87–92 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_br.2026.2108 | page_005_cand_0035.png | 3 | 93–155 | 1 | 3% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.3892_br.2026.2108 | page_005_cand_0036.png | 0 | 341–382 | 1 | 45% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.3892_br.2026.2108 | page_005_cand_0036.png | 1 | 228–269 | 2 | 33% | 1 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_br.2026.2108 | page_005_cand_0036.png | 2 | 175–180 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_br.2026.2108 | page_005_cand_0036.png | 3 | 88–160 | 1 | 3% | 0 | 0 | True | warning | one or more lanes carry a warning; read the per-lane reasons |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 0 | 386–416 | 5 | 72% | 5 | 0 | None | quantification_refused | the strongest lane (5) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 1 | 313–341 | 7 | 61% | 7 | 0 | None | quantification_refused | the strongest lane (7) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 2 | 463–490 | 6 | 66% | 5 | 0 | None | quantification_refused | the strongest lane (6) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 3 | 238–259 | 5 | 49% | 4 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 4 | 419–425 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0057.png | 5 | 494–499 | 3 | 12% | 1 | 0 | True | warning | a non-reference lane is clipped and reports no relative value |
| 10.3892_ijmm.2022.5188 | page_011_cand_0058.png | 0 | 429–433 | 2 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0058.png | 1 | 438–472 | 4 | 64% | 4 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0058.png | 2 | 364–395 | 6 | 68% | 6 | 0 | None | quantification_refused | the strongest lane (5) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0058.png | 3 | 516–545 | 7 | 75% | 7 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0058.png | 4 | 289–317 | 3 | 63% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 0 | 229–272 | 2 | 31% | 2 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 1 | 389–419 | 5 | 63% | 5 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 2 | 307–331 | 4 | 63% | 4 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 3 | 211–222 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 4 | 343–353 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0060.png | 5 | 426–436 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 0 | 282–309 | 4 | 60% | 4 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 1 | 212–236 | 5 | 35% | 3 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 2 | 196–202 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 3 | 243–247 | 1 | 0% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 4 | 356–384 | 3 | 64% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0062.png | 5 | 439–466 | 4 | 64% | 4 | 0 | None | quantification_refused | the strongest lane (4) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 0 | 273–310 | 4 | 60% | 4 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 1 | 210–239 | 5 | 66% | 5 | 0 | None | quantification_refused | the strongest lane (2) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 2 | 242–253 | 1 | 55% | 1 | 0 | None | quantification_refused | the strongest lane (1) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 3 | 200–205 | 1 | 2% | 0 | 0 | True | ok |  |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 4 | 359–386 | 3 | 61% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |
| 10.3892_ijmm.2022.5188 | page_011_cand_0063.png | 5 | 439–466 | 3 | 64% | 3 | 0 | None | quantification_refused | the strongest lane (3) is clipped, so nothing can be expressed relative to it |

## Reading this

- A `quantification_refused` row is the tool working: the published panel cannot support a within-image relative number there (clipped reference, no signal, or an undefined reference under small geometry changes).
- An `ok` row means the gates passed with auto geometry; it is still an uncalibrated, within-one-image pixel measurement with no protein-amount meaning.
- Ticket D finding 3 said 14/21 reviewed crops have pure-black band cores; the clipped-core column is the same phenomenon measured per detected row with the v0.2 tolerance.
- This replaces the retired D1 agreement number (`D1_densitometry_vs_bands.md`) as the real-crop check.

# B-4 — panel inventory scaffold and CV-detector review list

`scripts/experiments/panel_inventory_review.py`. Detector counts and a review list need no ground truth. Recall / precision need a human-filled `eval/demo/<paper>/panel_inventory.json`; until then they are reported as blocked, never estimated. Thresholds are reported, not changed.

Limitation: `candidates.json` only stores crops that already passed the crop gate (0.35), so candidates rejected below it are not visible here. The review list covers panels lost between the crop gate and the model gate; a panel the detector scored below the crop gate (recorded issue M10) can only be found by the human inventory. Re-running preprocessing with the gate lowered would expose them and is deliberately not done here.

## 10.3892_br.2026.2108

55 stored candidates (all passed the crop gate 0.35), 9 sent to the model. Inventory: `eval/demo/phospho_PMC12856536/panel_inventory.json` (status: unfilled).

| page | mentions western | stored candidates | sent to model | human panel count |
|---|---|---|---|---|
| 1 | no | 8 | 0 | not filled |
| 2 | yes | 7 | 0 | not filled |
| 3 | no | 9 | 2 | not filled |
| 4 | yes | 6 | 2 | not filled |
| 5 | yes | 8 | 3 | not filled |
| 6 | no | 6 | 2 | not filled |
| 7 | no | 2 | 0 | not filled |
| 8 | no | 5 | 0 | not filled |
| 9 | no | 4 | 0 | not filled |

Recall / precision: **blocked** until a human fills the inventory.

Review list: 16 candidates on western-mentioning pages that were not sent to the model (highest score first; check each crop for a missed panel).

- page 5 · score 0.63 · `page_005_cand_0037.png`
- page 2 · score 0.52 · `page_002_cand_0008.png`
- page 4 · score 0.52 · `page_004_cand_0025.png`
- page 5 · score 0.52 · `page_005_cand_0033.png`
- page 4 · score 0.52 · `page_004_cand_0027.png`
- page 2 · score 0.51 · `page_002_cand_0009.png`
- page 4 · score 0.51 · `page_004_cand_0026.png`
- page 5 · score 0.51 · `page_005_cand_0030.png`
- page 2 · score 0.51 · `page_002_cand_0013.png`
- page 5 · score 0.51 · `page_005_cand_0031.png`
- page 4 · score 0.51 · `page_004_cand_0024.png`
- page 2 · score 0.51 · `page_002_cand_0012.png`
- page 2 · score 0.51 · `page_002_cand_0010.png`
- page 2 · score 0.51 · `page_002_cand_0011.png`
- page 2 · score 0.50 · `page_002_cand_0014.png`
- page 5 · score 0.50 · `page_005_cand_0032.png`

## 10.3892_ijmm.2022.5188

78 stored candidates (all passed the crop gate 0.35), 19 sent to the model. Inventory: `eval/demo/standard_PMC9559174/panel_inventory.json` (status: unfilled).

| page | mentions western | stored candidates | sent to model | human panel count |
|---|---|---|---|---|
| 1 | yes | 7 | 0 | not filled |
| 2 | yes | 3 | 0 | not filled |
| 3 | yes | 4 | 0 | not filled |
| 4 | no | 7 | 0 | not filled |
| 5 | yes | 7 | 0 | not filled |
| 6 | no | 5 | 1 | not filled |
| 7 | no | 3 | 3 | not filled |
| 8 | no | 14 | 5 | not filled |
| 9 | no | 1 | 0 | not filled |
| 10 | no | 0 | 0 | not filled |
| 11 | yes | 13 | 9 | not filled |
| 12 | yes | 6 | 0 | not filled |
| 13 | yes | 0 | 0 | not filled |
| 14 | no | 7 | 0 | not filled |
| 15 | no | 1 | 1 | not filled |

Recall / precision: **blocked** until a human fills the inventory.

Review list: 31 candidates on western-mentioning pages that were not sent to the model (highest score first; check each crop for a missed panel).

- page 12 · score 0.55 · `page_012_cand_0069.png`
- page 11 · score 0.54 · `page_011_cand_0061.png`
- page 12 · score 0.54 · `page_012_cand_0068.png`
- page 1 · score 0.52 · `page_001_cand_0004.png`
- page 1 · score 0.52 · `page_001_cand_0005.png`
- page 1 · score 0.52 · `page_001_cand_0002.png`
- page 11 · score 0.52 · `page_011_cand_0051.png`
- page 5 · score 0.52 · `page_005_cand_0024.png`
- page 12 · score 0.52 · `page_012_cand_0065.png`
- page 11 · score 0.52 · `page_011_cand_0052.png`
- page 5 · score 0.52 · `page_005_cand_0022.png`
- page 3 · score 0.52 · `page_003_cand_0010.png`
- page 5 · score 0.52 · `page_005_cand_0026.png`
- page 1 · score 0.52 · `page_001_cand_0003.png`
- page 2 · score 0.52 · `page_002_cand_0007.png`
- page 3 · score 0.52 · `page_003_cand_0011.png`
- page 2 · score 0.52 · `page_002_cand_0009.png`
- page 11 · score 0.51 · `page_011_cand_0059.png`
- page 3 · score 0.51 · `page_003_cand_0013.png`
- page 12 · score 0.51 · `page_012_cand_0064.png`
- page 1 · score 0.51 · `page_001_cand_0000.png`
- page 5 · score 0.51 · `page_005_cand_0023.png`
- page 5 · score 0.51 · `page_005_cand_0021.png`
- page 3 · score 0.51 · `page_003_cand_0012.png`
- page 12 · score 0.51 · `page_012_cand_0066.png`
- ... 6 more below score 0.51

## 10.1186_s12964-025-02385-8

76 stored candidates (all passed the crop gate 0.35), 15 sent to the model. Inventory: `eval/demo/coip_PMC12706926/panel_inventory.json` (status: unfilled).

| page | mentions western | stored candidates | sent to model | human panel count |
|---|---|---|---|---|
| 1 | yes | 8 | 1 | not filled |
| 2 | yes | 6 | 0 | not filled |
| 3 | no | 6 | 0 | not filled |
| 4 | yes | 6 | 1 | not filled |
| 5 | yes | 7 | 3 | not filled |
| 6 | yes | 9 | 3 | not filled |
| 7 | no | 7 | 3 | not filled |
| 8 | yes | 3 | 0 | not filled |
| 9 | yes | 6 | 2 | not filled |
| 10 | yes | 5 | 2 | not filled |
| 11 | yes | 5 | 0 | not filled |
| 12 | no | 8 | 0 | not filled |

Recall / precision: **blocked** until a human fills the inventory.

Review list: 43 candidates on western-mentioning pages that were not sent to the model (highest score first; check each crop for a missed panel).

- page 11 · score 0.59 · `page_011_cand_0064.png`
- page 5 · score 0.56 · `page_005_cand_0030.png`
- page 1 · score 0.55 · `page_001_cand_0005.png`
- page 6 · score 0.55 · `page_006_cand_0036.png`
- page 6 · score 0.54 · `page_006_cand_0038.png`
- page 9 · score 0.54 · `page_009_cand_0056.png`
- page 4 · score 0.54 · `page_004_cand_0024.png`
- page 6 · score 0.54 · `page_006_cand_0041.png`
- page 9 · score 0.54 · `page_009_cand_0057.png`
- page 10 · score 0.53 · `page_010_cand_0061.png`
- page 9 · score 0.53 · `page_009_cand_0053.png`
- page 10 · score 0.53 · `page_010_cand_0059.png`
- page 4 · score 0.53 · `page_004_cand_0023.png`
- page 1 · score 0.53 · `page_001_cand_0006.png`
- page 1 · score 0.52 · `page_001_cand_0007.png`
- page 6 · score 0.52 · `page_006_cand_0034.png`
- page 4 · score 0.52 · `page_004_cand_0021.png`
- page 5 · score 0.52 · `page_005_cand_0026.png`
- page 1 · score 0.52 · `page_001_cand_0003.png`
- page 6 · score 0.52 · `page_006_cand_0033.png`
- page 8 · score 0.52 · `page_008_cand_0050.png`
- page 2 · score 0.51 · `page_002_cand_0011.png`
- page 4 · score 0.51 · `page_004_cand_0020.png`
- page 5 · score 0.51 · `page_005_cand_0027.png`
- page 2 · score 0.51 · `page_002_cand_0008.png`
- ... 18 more below score 0.51

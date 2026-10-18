# Annotator guide: HiveBlot blind benchmark (October 2026)

You are making the **reference labels** that HiveBlot's automatic extraction will be scored
against. They need to be your own reading of each paper, and they must not be influenced by
HiveBlot in any way.

Expect about 4 hours in total: roughly 15 minutes per paper for the inventory, plus about 6
minutes per fully annotated panel. Please finish by **Mon 2026-10-20, 12:00 PT**.

## Rules (please read)

1. **Use only the PDF Nik shares with you.**
   - Use those exact files, because page numbers have to match the frozen copies. Open each
     paper in its own PDF viewer.
   - Do not use supplementary files.
2. **Do not use HiveBlot for these papers.** Do not enter these DOIs into the site, and do not
   look at HiveBlot results for them. If you see any HiveBlot output for these papers, stop and
   tell Nik.
3. **Do not use AI tools** (ChatGPT, Claude, Gemini and so on) to read figures or fill cells.
   The point is to measure the AI against a human.
4. **Do not open `eval/candidates.json`.** It contains notes written by AI agents.
5. **When the paper does not say something, write `NOT_STATED`.** Don't guess. Silence is a
   valid label.
6. **Time yourself** for each paper (see "Time log" below).
7. **Don't change your labels once you have sent them,** except to fix a typo. Log any typo fix
   in `ERRATA.csv` with the date.

## Papers (in this order)

| Order | ID | DOI | PDF pages | Panel sampling sequence (use in step 2) |
|---|---|---|---|---|
| 1 | PMC9283986 | 10.3389/fnagi.2022.921573 | 23 | 36, 31, 16, 69, 5, 21, 73, 65, 63, 54, 78, 28, 20, 80, 48, 56, 10, 71, 32, 60, 12, 53, 39, 11 |
| 2 | PMC5328321 | 10.2147/OTT.S117933 | 14 | 58, 10, 48, 78, 69, 26, 18, 8, 37, 65, 66, 2, 29, 57, 33, 70, 80, 36, 32, 62, 52, 39, 77, 6 |
| 3 | PMC7948984 | 10.1074/jbc.RA120.014479 | 13 | 73, 10, 28, 5, 16, 64, 11, 27, 6, 13, 49, 51, 20, 41, 66, 56, 79, 54, 18, 29, 57, 38, 31, 42 |
| 4 | PMC4393234 | 10.1371/journal.pone.0123604 | 17 | 31, 19, 26, 5, 54, 78, 49, 13, 64, 3, 1, 22, 6, 30, 2, 35, 36, 58, 67, 47, 15, 72, 68, 60 |

If a sequence runs out before you have chosen 6 panels, the full sequence is in `papers.json`.
Nik can also send it to you.

## Step 1: Inventory every Western blot panel (`panels.csv`)

- **What to list.** Go through the main PDF figure by figure and list **every Western blot
  panel**, including:
  - loading-control strips
  - co-IP, IP and input blots

  Do not list Northern blots, gels stained for total protein (Coomassie, silver, Ponceau),
  zymography, microscopy or charts.
- **What counts as a panel.**
  - A **panel** is one lettered sub-figure (for example "Fig 2B") that contains one or more blot
    strips.
  - If a figure has no letters, treat each separate blot image block as a panel. Number those
    blocks left to right, then top to bottom.
- **Numbering.** Use `panel_id` 1, 2, 3 and so on, in reading order: figure 1 first, then
  panel letters A, B, C within each figure.

| Column | What to write |
|---|---|
| paper_pmcid | e.g. PMC9283986 |
| panel_id | 1, 2, 3 ... |
| page | PDF page number shown by your viewer (first page = 1) |
| figure | figure number, e.g. `2` (`S1` only if a supplementary figure is printed inside the main PDF) |
| panel_letter | `A`, `B` ... or blank if the figure has no letters |
| targets_printed | every protein label printed next to the blot rows, top to bottom, separated by `;` (e.g. `p-AKT (S473); AKT; GAPDH`) |
| notes | anything odd (cropped strips, missing labels, etc.) |

## Step 2: Choose the panels to annotate fully

1. Let **N** be the number of panels in your inventory.
2. Read the paper's sampling sequence from left to right and keep each number that is **≤ N**.
3. Stop when you have **6** panels. If N is 6 or fewer, annotate every panel.

Example: N = 20 and the sequence is 36, 31, 16, 69, 5, 21, 73, 65, 63, 54, 78, 28, 20 ... The
panels are **16, 5, 20**, then the next numbers ≤ 20 in the sequence, until there are 6.

## Step 3: Annotate each chosen panel (`targets.csv`, then `lanes.csv`)

**`targets.csv`.** One row for each blot strip (target) in the panel, top to bottom.

| Column | What to write |
|---|---|
| paper_pmcid, panel_id | as in the inventory |
| row_order | 1 for the top strip, 2 for the next ... |
| target_printed | the label exactly as printed, e.g. `p-STAT3 (Y705)` |
| gene_symbol | official gene symbol of the protein, e.g. `STAT3`. For ERK1/2 write `MAPK3\|MAPK1`. For a tag (FLAG, HA, GFP) write the tag name. `NOT_STATED` if you cannot tell. |
| modification | `total`, `phospho`, `phospho:Y705`, `phospho:T202/Y204`, `cleaved`, `other:<what>`, or `NOT_STATED`. A plain protein label (no phospho or cleaved mark) is `total`. |
| cell_line_or_sample | the cell line or tissue used for this panel as the paper states it, e.g. `HEK293T`, `rat spinal cord`, `patient fibroblasts`. Synonyms with `\|`. `NOT_STATED` if not stated anywhere. |
| treatments | every agent applied in this panel: drugs, ligands, cytokines, siRNA/shRNA, transfected constructs, stimulation. Separate items with `;` and synonyms with `\|` (e.g. `IL-6\|interleukin 6; tocilizumab`). `none` if untreated, `NOT_STATED` if you cannot tell. |
| n_lanes | number of lanes in this strip |
| notes | optional |

Use the figure, its caption, and the Methods. If the caption and the Methods disagree, write
what the caption says and put the disagreement in `notes`.

**`lanes.csv`.** One row for each lane of each strip.

| Column | What to write |
|---|---|
| paper_pmcid, panel_id, row_order | as in targets.csv |
| lane_index | 1 = leftmost lane |
| lane_label_printed | the lane's label as printed (e.g. `0 min`, `siCtrl`), blank if none |
| band_call | `present`, `absent` or `uncertain`: is there a visible band at the expected position in this lane? Use `uncertain` when you honestly can't tell. |

## Time log (`timelog.csv`)

Write one row per paper per task. `task` is `inventory` (step 1) or `full` (steps 2 and 3). Fill
in `start` and `end` as clock times and `minutes` as active minutes (subtract breaks).

## Sending your work

Use the Google Sheet Nik shares, with one tab per CSV and headers exactly as in
`annotations/TEMPLATE/`. When you have finished all papers, tell Nik. He will download each tab
as CSV and commit them before anyone looks at HiveBlot's output.

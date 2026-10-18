# Team tasks: blind benchmark, 2026-10-18 to 2026-10-20

The goal is one honest, human-checked accuracy number for HiveBlot by **Tue 2026-10-20**. This
benchmark comes before every other ticket.

## Tanvi: primary annotator (about 4 h, due Mon 10-20 12:00 PT)

1. Read `ANNOTATOR_GUIDE.md` in this folder. It is self-contained.
2. Annotate papers 1 to 4 in order. Write into the Google Sheet Nik shares; it has one tab per template in
   `annotations/TEMPLATE/`.
3. While you do this:
   - Don't open HiveBlot for these papers.
   - Don't use AI tools.
   - Don't talk about the papers with Yashvi.
4. Message Nik when you are done. After he commits your sheet, he will send you
   `report/adjudication_sheet.csv`. In it, mark a cell `EQUIVALENT_NOTATION` **only** when
   HiveBlot named the same thing differently, for example "Hep3B cells" against "Hep3B". This
   takes about 20 minutes.
5. Q-1 to Q-4 are paused until this is finished.

## Second annotator (optional; anyone with Western-blot experience except Tanvi and Nik)

- Annotate **paper 1 only** (PMC9283986), steps 1 to 3 of the guide, independently of Tanvi.
- This gives an agreement figure. It takes about 1 h and is due Mon 10-20 12:00 PT.

## Yashvi: crop mapper (about 45 min, due Sun 10-19 21:00 PT)

1. Nik shares the folder `mapper_pack/`. It holds one folder per paper of cropped figure images
   (57 crops), `crop_map.csv`, and the four PDFs.
2. For each crop (one row in `crop_map.csv`):
   - Open the image.
   - Find where it comes from in the PDF. The `page` column tells you the page.
   - Fill `figure` (e.g. `3`) and `panel_letters`, with several letters separated by `;` (e.g.
     `A;B`). Leave `panel_letters` blank if the figure has no letters.
   - If the crop is not a Western blot (a chart, a micrograph, a gel stain, text), write
     `NOT_WB` in `mapping` and leave figure and panel blank.
3. You are only saying where each crop sits. Don't judge anything about its content.
4. Don't share the crops with Tanvi or discuss them with her. They show which panels the system
   picked.
5. Send the filled `crop_map.csv` to Nik.

## Srushti: protect the frozen version (no new work)

- Don't deploy changes under `western_blot_miner/` (B-3/W-2 PR #24, B-12, B-13, B-14) until Nik
  says the benchmark is scored. The benchmark measures commit `f77d311`, which is what
  production runs now.
- Web and API PRs are fine to keep going.

## Nik

1. Log in to the claude CLI (`claude auth login`) so the model stage can run. See `RUNBOOK.md`
   step 3.
2. Download PMC7948984 in a browser (see `RUNBOOK.md` step 1). Tell Claude the file path.
3. Share these by Google Drive:
   - The frozen PDFs, from `~/hive-blind-eval-private/pdfs/`, to Tanvi and to the second
     annotator.
   - `~/hive-blind-eval-private/mapper_pack/` plus the PDFs, to Yashvi.
   - Never share `~/hive-blind-eval-private/runs/` before scoring.
4. Make a Google Sheet with tabs `panels`, `targets`, `lanes`, `timelog`, `ERRATA` (headers from
   `annotations/TEMPLATE/`). Share it with Tanvi only.
5. When Tanvi and Yashvi finish, download the CSVs and run `RUNBOOK.md` steps 5 to 7.
6. UCSF adoption: send the confirmation request in
   `research/ADOPTION_STATUS_2026-10-18.md` to your UCSF contacts.

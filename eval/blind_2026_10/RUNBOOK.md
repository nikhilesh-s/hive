# Runbook: exact commands

Run everything from the eval worktree `/Users/niks/hive-blind-eval` (branch
`eval/blind-benchmark-2026-10`):

```bash
cd /Users/niks/hive-blind-eval
```

- `PY` is `/Users/niks/hive/.venv/bin/python`.
- `PRIV` is `/Users/niks/hive-blind-eval-private`. It holds the PDFs and the sealed outputs and is
  never committed.

## 0. Already done (2026-10-18)

```bash
$PY eval/blind_2026_10/draw.py                       # deterministic order, seed 20261018
$PY eval/blind_2026_10/acquire.py $PRIV              # system fetcher; ranks 1, 2, 4, 8 frozen
$PY eval/blind_2026_10/run_extraction.py $PRIV preprocess   # Stage 1 (OpenCV), no model
$PY eval/blind_2026_10/score_blind.py mapper-pack $PRIV $PRIV/mapper_pack
$PY eval/blind_2026_10/score_blind.py self-test     # scoring logic check
```

## 1. Rank 3 PDF (manual browser download)

1. Open https://pmc.ncbi.nlm.nih.gov/articles/PMC7948984/ and save the PDF.
2. Then run:

```bash
$PY eval/blind_2026_10/acquire.py $PRIV --manual PMC7948984=$HOME/Downloads/PMC7948984.pdf
$PY eval/blind_2026_10/run_extraction.py $PRIV preprocess
$PY eval/blind_2026_10/score_blind.py mapper-pack $PRIV $PRIV/mapper_pack
```

If the download is impossible, write that in `DEVIATIONS.md` (A2) and rank 8 stays.

## 2. Freeze before the model runs

```bash
git add eval/blind_2026_10 && git commit -m "Blind benchmark: final frozen paper list" && git push
```

## 3. Model stage (production model, frozen code, no uploads)

Option A is the local CLI (log in once first):

```bash
claude auth login
```

```bash
WBM_LLM_BACKEND=claude_cli WBM_MODEL=claude-opus-5 $PY eval/blind_2026_10/run_extraction.py $PRIV extract
```

Option B is the production transport. Run it yourself so the key never passes through anyone
else:

```bash
read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
```

```bash
WBM_LLM_BACKEND=anthropic WBM_MODEL=claude-opus-5 $PY eval/blind_2026_10/run_extraction.py $PRIV extract
```

Then seal the outputs. **Commit the seal before any annotation is received.**

```bash
$PY eval/blind_2026_10/run_extraction.py $PRIV seal
```

```bash
git add eval/blind_2026_10/SEALED_OUTPUTS.sha256 && git commit -m "Blind benchmark: seal outputs" && git push
```

## 4. Annotation (humans; see TEAM_TASKS.md)

Nothing to run.

## 5. Lock the human labels

1. Put Tanvi's CSVs in `eval/blind_2026_10/annotations/tanvi/`: `panels.csv`, `targets.csv`,
   `lanes.csv`, `timelog.csv`.
2. Put Yashvi's `crop_map.csv` in `eval/blind_2026_10/annotations/crop_map.csv`.
3. Then commit:

```bash
git add eval/blind_2026_10/annotations && git commit -m "Blind benchmark: lock annotations and crop map" && git push
```

## 6. Score (raw)

```bash
$PY eval/blind_2026_10/score_blind.py score $PRIV --annotator tanvi
```

This writes `report/RESULTS.md`, `report/results.json` and `report/adjudication_sheet.csv`. It
refuses to run if any sealed file changed.

## 7. Adjudicate and re-score

1. Tanvi fills the `verdict` column of `report/adjudication_sheet.csv`.
2. Save it as `annotations/tanvi/adjudications.csv`.
3. Then run:

```bash
$PY eval/blind_2026_10/score_blind.py score $PRIV --annotator tanvi --adjudications eval/blind_2026_10/annotations/tanvi/adjudications.csv
```

Optionally, if there is a second annotator, compute agreement:

```bash
$PY eval/blind_2026_10/score_blind.py agreement --annotator tanvi --second <name>
```

```bash
git add eval/blind_2026_10 && git commit -m "Blind benchmark: results" && git push
```

## Rules while this runs

- Change nothing under `western_blot_miner/` or `api/` on this branch. The scorer reports any
  diff from `f77d311`.
- Infrastructure crashes (an expired login, a network timeout before any output) may be re-run
  with the same code. Log them in `DEVIATIONS.md`.
- Every frozen paper is reported, including failures.

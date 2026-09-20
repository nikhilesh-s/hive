# HiveBlot

Experiment-level Western blot evidence, searchable and traceable back to the source.

## One-sentence summary

HiveBlot lets a researcher search a reviewed set of published Western blot experiments and see, for every value it shows, exactly where that value came from and how sure it is.

## Problem

A wet-lab researcher planning an experiment often needs to know: has this target already been detected in this cell line, with this antibody, under this treatment? The answer usually lives inside a PDF, in a figure caption or a sentence buried in the methods section. Finding it means downloading papers, opening figures one at a time, and reading captions by hand. There is no way to search across papers by antibody catalog number, phosphosite, or co-IP bait.

## Why Western Blot evidence search is hard

A Western blot is not one clean data point. A single figure panel can carry several lanes, each with its own treatment, timepoint, and loading control. The same protein name can mean different things in different papers: "p-ERK" might mean a phospho-specific antibody was used, or it might just be the label the authors printed, with no confirmation of phosphorylation state anywhere else in the text. Expected molecular weight (from a database) and reported molecular weight (what the paper printed) are not the same number and should never be treated as one. Band presence is not densitometry. A blot can show a band is there without telling you how much protein is there.

Any tool that flattens these distinctions produces answers that look precise but are not accurate. Getting this right requires treating every field as a claim with a source, not a fact.

## What HiveBlot does today

HiveBlot turns Western blot figures, captions, and methods text into structured Evidence Records. Each record captures the experiment (target, modification, antibody, cell line, treatment, band state) and, for each field, where that value came from and how confident the extraction is.

Researchers search in plain text (a protein name, a phosphosite, an antibody catalog number, a cell line, or a co-IP bait) and get back experiment cards grouped by the actual experiment they belong to, not just individual lanes. Opening a card shows the original figure crop, the caption sentence the value was drawn from, and a list of any fields still under review.

The system runs today as a hosted beta:

- Web app: https://hiveblot-beta.vercel.app
- API: https://hiveblot-api.onrender.com

## Who it is for

Wet-lab researchers, initially at UCSF, who need to check what has already been published about a protein, antibody, or experimental setup before running their own blot. It is not built for literature-wide surveys or for automated meta-analysis yet.

## Current experimental beta scope

This is an early, frozen beta over a small, reviewed corpus: 3 papers, 93 experiment groups, 475 evidence rows. Every row in the corpus was reviewed rather than pulled automatically at scale. This is enough to test whether the underlying idea, structured and sourced evidence records, works and is useful, not enough to say the tool covers the literature.

## Product experience

A search box on the home page accepts a plain query: "phospho STAT3 Tyr705", "co-IP PIK3CA", "CST 9145", "GAPDH mouse". Results come back as cards, one per experiment, grouped by an experiment identity rather than by individual lane so a multi-lane figure doesn't fragment into disconnected rows.

Each card can be expanded into an "Evidence & sources" view: the figure crop, the quoted sentence a field was drawn from, the DOI link back to the paper, and, where a field is unresolved, why. A researcher can leave feedback directly on a field, marking it correct or incorrect or adding context, without changing what the model originally said.

Because the API runs on a free hosting tier, the first search after a period of inactivity can take 30 to 60 seconds while the server wakes up. The interface says so rather than hiding it.

## Evidence and trust model

Every field in a record carries a value, a status, and its sources: the caption sentence, figure label, or methods text it was drawn from. A field can be SUPPORTED, AMBIGUOUS, CONFLICTING, or MISSING. When two sources disagree, the field is marked CONFLICTING, its value is left null, and both competing claims are kept and shown. HiveBlot does not pick a winner just to have an answer.

The system treats the model's read of a row as a claim, not as ground truth. Corrections from researchers are stored beside the original extraction in a separate feedback table, never written over it. That means the original model output and the human correction both stay visible and auditable, which matters for evaluating the model later.

A specific rule worth naming: HiveBlot does not infer phosphorylation just because a target is printed with a "p" prefix, like "p-ERK" or "p-AKT". A "p-" prefix is treated as a plain label match, not evidence of a phosphorylation event, because the underlying modification status is often genuinely unresolved in the source paper. Search still surfaces these ambiguous rows for review; it just refuses to quietly resolve them.

Expected molecular weight (from the protein's canonical sequence) and reported molecular weight (whatever the paper printed) are stored as separate fields and never merged. Band detection is categorical (present, absent, or uncertain), with no attempt at reading band intensity from the image.

## What we learned

Structured, field-level Evidence Records with real sources are workable at small scale. Whether researchers can follow the provenance trail easily is one of the things this beta is meant to find out. Grouping lanes into an experiment card, rather than showing raw rows, made results much easier to read, but getting the grouping key right took more than one attempt. An early version grouped by a composite key that didn't always match the identity the feedback system used, and two different experiments with the same cell line briefly collapsed into one card.

Being explicit about uncertainty was better received than trying to make every field look resolved. Copy that overclaimed corpus size or extraction accuracy earlier in the project needed to be walked back and rewritten in plainer, more conservative terms once it was reviewed against what could actually be demonstrated.

## Current limitations

- The corpus is small and manually reviewed: three papers, not a literature-wide index.
- There is no measured precision, recall, or accuracy number for extraction on papers outside this reviewed set. The model-reading step for these three papers ran with a human in the loop, so it is not a clean test of unsupervised extraction.
- Organism filtering is text matching, not a structured taxonomy field, by deliberate choice for now.
- There is no densitometry or quantitative band-intensity inference anywhere in the system.
- The free-tier API spins down when idle, so the first search after a quiet period is slow.
- Rate limiting runs per server instance, which would need rework if the API were scaled horizontally.
- Getting evidence into the system currently depends on manual review rather than a general pipeline. Live paper discovery and reading exists on a separate, unmerged branch and has not been folded into this frozen beta. For now, we are using Valency and PaperQA2 for paper access, but we may need broader paper access later, before the corpus can grow much past a handful of papers.

## What comes next

The immediate open decision is whether to apply a small set of known corpus corrections through a reviewed re-seed, rather than editing the live data directly. Beyond that, the natural next step is running an extraction evaluation on papers the model has not seen, once there is a safe way to do that with real credentials. Expanding paper access, moving past manual review toward the experimental live-ingestion and paper-QA work, is the path to growing the corpus, but that work should stay separate from this frozen beta branch until it has its own evaluation.

## How to run locally

The stack is three pieces: Postgres, a FastAPI backend (`api/`), and a Next.js frontend (`web/`). Locally you do not need any cloud credentials. The repo ships an embedded local Postgres you seed yourself with the same reviewed rows the hosted beta uses.

```bash
# 1. Python env + local database
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-local.txt
.venv/bin/python scripts/local_db.py up
.venv/bin/python scripts/local_db.py load eval/demo/*/supabase_rows.json

# 2. API
cp api/.env.example api/.env
# fill in api/.env: DB_READONLY_URL and DB_FEEDBACK_URL from `local_db.py status`,
# generate your own INTERNAL_API_KEY and AGENT_API_KEYS, leave SUPABASE_URL /
# SUPABASE_KEY / OPENAI_KEY empty for the deterministic search path
cd api && ../.venv/bin/uvicorn app.main:app --reload

# 3. Web
cp web/.env.example web/.env
# fill in web/.env: API_BASE_URL=http://localhost:8000 and the SAME
# INTERNAL_API_KEY you generated for api/.env
cd web && npm install && npm run dev
```

Then open the local site and try a search like "phospho STAT3 Tyr705".

Never commit a filled-in `.env` file or paste a real credential value anywhere. Variable names are documented in `DEPLOYMENT.md` and `research/team_delegation/ENV_SETUP.md`; values are generated locally or handed off through a secure channel, never through this file or any other committed one.

## Links

- Web app: https://hiveblot-beta.vercel.app
- API: https://hiveblot-api.onrender.com
- Deployment details: `DEPLOYMENT.md`
- Project state and history: `HANDOFF.md`
- Biological non-negotiables: `AGENTS.md`

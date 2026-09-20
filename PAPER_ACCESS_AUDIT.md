# Paper-access audit: hosted beta (`feature/bio-context-beta`)

Scope: the frozen hosted beta at commit
`e0d2089`. Read-only audit; nothing in this repo was changed except the
creation of this file.

Question asked: everywhere HiveBlot accesses, expects, references, downloads,
parses, or depends on papers, PDFs, PMC/PMCID content, PubMed/PMID, DOI
metadata, paper text, paper images, figure crops, paper metadata, PaperQA2,
Valencio/Valency, or any external literature retrieval.

---

## 1. Summary

The hosted beta serves a frozen, hand-reviewed corpus of three papers out of
Postgres plus 21 PNG figure crops baked into the API container image. At
hosted runtime. The Render FastAPI service and the Vercel Next.js app serving
a search. HiveBlot makes **no** request to any publisher, PMC, PubMed,
Crossref, Unpaywall, or any other literature source. It downloads no PDF,
parses no PDF, and resolves no DOI. Every paper-shaped thing the user sees is
a value already stored in a database row (`doi`, `pmcid`, `pmid`,
`figure_label`, `figure_caption`, `page`, `image_crop_ref`) or a PNG already
copied into the image. The only outbound calls the hosted API can make are to
Supabase Postgres and, optionally, to OpenAI for the natural-language-to-SQL
search path; the DOI links on the result cards and the About page are plain
`https://doi.org/...` anchors rendered in the user's browser, not server-side
fetches. All real paper access (NCBI E-utilities, the PMC BioC full-text
service, the PMC Open Access figure packages, PyMuPDF PDF rendering, OpenCV
panel cropping, UniProt resolution) lives in `western_blot_miner/` and
`scripts/`, which run only on a developer's machine during ingestion and
reseeding. Nothing in `api/` imports that package.
For now, we are using Valencio and PaperQA2, but we may need broader paper access later.

---

## 2. Current paper-access surfaces

| Surface | File | Runtime vs ingestion | What it needs |
|---|---|---|---|
| Figure-crop endpoint | `api/app/routers/internal.py:90-119` | Hosted runtime | A `.png` on the container's local disk resolving inside `CROP_BASE_DIR`. No network. Path comes from the DB column, never the client. |
| Crop base directory setting | `api/app/config.py:57-62` | Hosted runtime | Default points at `western_blot_miner/data/pdf_runs`; overridden in the image by `ENV CROP_BASE_DIR`. |
| Crops baked into the image | `api/Dockerfile:21-31` | Build time for hosted runtime | `COPY api/crops/ (sister branch) western_blot_miner/data/pdf_runs/`. Reproduces the authoring path verbatim so absolute `image_crop_ref` values resolve. `api/crops/` is tracked in git (21 PNGs, ~6 MB) because Render builds from the GitHub clone. |
| Tracked crop archive | `api/crops/**` (21 PNGs under three DOI-named directories) | Hosted runtime data | Nothing external. These are pre-extracted panel crops. |
| Crop path redaction | `api/app/schemas.py:9-13,151-154,261-264` | Hosted runtime | Public responses carry only the crop filename; the stored absolute path leaked a username and directory layout. |
| Paper metadata columns on list/detail responses | `api/app/schemas.py:80-89,229-236`; `api/app/record_detail.py:191-198` | Hosted runtime | `doi`, `pmcid`, `pmid`, `figure_label`, `figure_caption`, `page`, `image_crop_ref` read straight from the row. No lookup. |
| Paper metadata columns in schema | `migrations/001_evidence_record.sql:26-28,35-36`; `api/db/schema.sql:15-21`; `supabase/migrations/20260701000001_base_schema.sql:15-21` | Storage | Values supplied by the ingestion pipeline at seed time. |
| Web crop proxy route | `web/app/api/record/[id]/crop/route.ts:3-21` | Hosted runtime | Streams the PNG from the backend with the internal key. No literature source. |
| Crop rendering + graceful failure | `web/components/EvidencePanel.tsx:343,421-447`; `web/components/DatabaseResultCard.tsx:187,255-257,344-358` | Hosted runtime | On any crop error the UI falls back to text-only or an honest "No figure crop available for this record" placeholder. |
| Outbound DOI links | `web/components/DatabaseResultCard.tsx:379-384`; `web/components/EvidencePanel.tsx:549-552`; `web/app/about/page.tsx:60-63` | Hosted runtime, client-side only | `https://doi.org/<doi>` anchors the user clicks. HiveBlot itself does not fetch them. |
| The three-paper corpus claim | `web/app/about/page.tsx:9-13` | Hosted runtime copy | Hard-coded DOI list: `10.3892/br.2026.2108`, `10.3892/ijmm.2022.5188`, `10.1186/s12964-025-02385-8`. |
| PMC text access layer | `western_blot_miner/pmc.py` (whole module; requests at `:48`, `:80`) | Ingestion only | NCBI E-utilities `esearch` + the PMC BioC JSON full-text API. Network required. |
| NCBI endpoint config | `western_blot_miner/config.py:25,32-34` | Ingestion only | `EUTILS`, `BIOC`, `OA_SERVICE` base URLs; optional free NCBI API key. |
| PMC Open Access figure download | `western_blot_miner/images.py:22-56` | Ingestion only | Pulls the article's `.tar.gz` OA package over HTTPS and maps figure graphics to local files. Used only with `--with-images`. |
| PDF rendering and panel candidates | `western_blot_miner/pdf_preprocess.py:18 (DOI regex), :72-85, :119-124` | Ingestion only | PyMuPDF (`fitz`) to rasterize pages at 350 DPI and extract text; OpenCV to propose panel crops. Needs the PDF file locally. |
| Pipeline entry point | `western_blot_miner/pipeline.py:1-30` | Ingestion only | Takes a local PDF path: `python -m western_blot_miner.pipeline papers/example.pdf`. |
| UniProt resolution | `western_blot_miner/resolve.py:29,96` | Ingestion only | `https://rest.uniprot.org/uniprotkb/search`, disk-cached, with an offline fallback that never guesses an accession. Not literature retrieval, but an external lookup on the ingestion path. |
| Vision/LLM extraction | `western_blot_miner/llm_client.py:116-127`; `western_blot_miner/vlm_extract.py:218` | Ingestion only | Reads paper images and caption/methods text and sends them to a model endpoint. |
| Supabase loader | `western_blot_miner/supabase_loader.py:443,650` | Ingestion only | Writes the extracted records. |
| Crop staging for deploy | `scripts/stage_crops.py` | Ingestion/deploy prep | Copies only the crops referenced by `eval/demo/*/supabase_rows.json` from the local 148 MB pipeline run directory into `api/crops/`. Requires the local pipeline output; missing sources are reported, never fatal. |
| Reseed scripts | `scripts/seed_remote.py:11-12,64-67`; `scripts/local_db.py:23,150-154` | Ingestion only | Idempotent per `paper_id`; they read committed JSON, not papers. |
| Agent-in-the-loop extraction driver | `eval/tools/manual_pipeline.py:1-30` | Ingestion only | Runs Stage 1 OpenCV detection on a real PDF, then injects hand-written rows because no model credential exists locally. |
| Frozen per-paper demo artifacts | `eval/demo/{standard_PMC9559174,phospho_PMC12856536,coip_PMC12706926}/` | Ingestion input, committed | `supabase_rows.json` (seed source, carries the absolute `image_crop_ref`), `evidence_records.json`, `responses_observed.json`, `README.md` with DOI/PMCID provenance. |
| Deployment notes on crops | `DEPLOYMENT.md:149,185,190-199,240` | Docs | Documents the absolute-path trick, why `api/crops/` is tracked, and that crops are read-only in the image. |

**No hits anywhere in this branch** for: `paperqa`, `europepmc`, `unpaywall`,
`openalex`, `crossref`, `semantic scholar`, `arxiv`, `biorxiv`. The only
`valenc`/`PaperQA2` mentions are in two untracked draft files at the repo root
(`UCSF_BETA_HANDOFF_MESSAGE.md:13`, `BETA_EMAIL_WITH_TALLY_AND_BRIEF.md`) and
one forward-pointer in `HANDOFF.md:111-114`. None of them is code.

---

## 3. Runtime beta dependency

**Verdict: the hosted beta runtime does not need paper access. Only the
ingestion/reseed pipeline does.**

Evidence:

1. The hosted API's entire dependency set is `fastapi`, `uvicorn`, `asyncpg`,
   `python-dotenv`, `pydantic`, `pydantic-settings`, `openai`, `sqlglot`,
   `slowapi` (`api/requirements.txt`). There is no HTTP
   client for literature, no PDF library, no OpenCV, no `requests`.

2. Nothing under `api/app/` imports `western_blot_miner`. The only two
   references to that package name in the deployed surface are a filesystem
   path default (`api/app/config.py:61`) and the `COPY`/`ENV` pair in
   `api/Dockerfile:30-31`. Both are directory strings, not imports.

3. Grepping `api/app/` for `requests.`, `httpx`, `urllib`, `aiohttp` and
   `http(s)://` returns only a CORS default origin and `conn.fetch(...)`
   Postgres calls. The API opens no outbound HTTP to a paper source.

4. The eight hosted routes are `/health`, `/`, `/proteins`, `/search`,
   `/records/{id}`, `/records/{id}/crop`, `/records/{id}/feedback`,
   `/feedback` (`api/app/routers/internal.py`), plus `/v1/search`
   (`api/app/routers/external.py`). Every one is a Postgres read/write except
   the crop route, which is a local `FileResponse`.

5. `render.yaml` provisions only `DB_READONLY_URL`, `DB_FEEDBACK_URL`,
   `SUPABASE_KEY`, `INTERNAL_API_KEY`, `SUPABASE_URL`, `OPENAI_KEY`,
   `AGENT_API_KEYS`, `ALLOWED_ORIGINS`. No NCBI key, no Valency token, no
   literature-provider credential is configured or expected.

6. `render.yaml` states the filesystem is ephemeral and safe because "the API
   never writes to disk at runtime". Consistent with crops being read-only
   build artifacts.

7. The Next.js API routes (`web/app/api/search`, `.../record/[id]`,
   `.../record/[id]/crop`, `.../feedback`) all `fetch` only
   `${BACKEND_URL}/...`. No external host appears in the web server path.

What breaks if paper access is unavailable at hosted runtime: nothing. Search,
evidence records, field-level provenance, captions, DOIs and crops all
continue to work, because none of them is fetched live.

What breaks if the **crop archive** is unavailable (it is local, not remote):
`GET /records/{id}/crop` returns 404 and the UI degrades to text-only evidence
by design (`api/app/routers/internal.py:96-98`, `scripts/stage_crops.py`
closing note, `web/components/DatabaseResultCard.tsx:358`). This is a
deliberate degradation, not an outage.

What breaks if `OPENAI_KEY` is empty: nothing. `render.yaml` sets it to `""`
and search falls back to the deterministic `bio_query` parser
(`api/app/bio_query.py:3`, `api/app/search_service.py:25`).

---

## 4. Ingestion/reseed dependency

The pipeline that produces the corpus does need real paper access, and it runs
only on a developer's machine.

- **Discovery and full text**: `western_blot_miner/pmc.py` calls NCBI
  E-utilities `esearch` to find open-access PMC articles and the PMC BioC JSON
  API for structured full text (figure captions + methods). Both are free and
  unauthenticated; an optional NCBI key raises the rate limit
  (`western_blot_miner/config.py:25`).
- **Figure images**: `western_blot_miner/images.py` asks the PMC OA service for
  the article's `.tar.gz` package URL, rewrites the FTP host to HTTPS, and
  unpacks the figure graphics. Only used with `--with-images`; text extraction
  works without it.
- **PDF path**: `western_blot_miner/pipeline.py` takes a local PDF.
  `western_blot_miner/pdf_preprocess.py` renders pages with PyMuPDF at 350 DPI,
  pulls page text, extracts a DOI by regex, and generates OpenCV panel
  candidates. `western_blot_miner/requirements.txt` carries `PyMuPDF`,
  `opencv-python-headless`, `Pillow`, `numpy`, `requests`, `anthropic`. None
  of which the API image installs.
- **Normalization**: `western_blot_miner/resolve.py` queries UniProt, caches to
  disk, and degrades to MISSING/AMBIGUOUS offline rather than guessing.
- **Crop staging**: `scripts/stage_crops.py` must be run on the machine that
  holds the pipeline output before a deploy that refreshes figure evidence.
- **Seeding**: `scripts/seed_remote.py` and `scripts/local_db.py` load the
  committed `eval/demo/*/supabase_rows.json` into Postgres, idempotent per
  `paper_id`. Reseeding from the committed JSON needs no paper access at all;
  only re-extracting a paper does.

If NCBI, the OA service, or UniProt is unavailable, **new** papers cannot be
ingested and existing extractions cannot be re-derived. The hosted beta is
unaffected, and reseeding from the committed JSON still works.

---

## 5. Places to flag in docs/copy

These are the places where a reader could reasonably form a belief about
HiveBlot's paper access, and where the current/future boundary should be
stated.

1. `web/app/about/page.tsx:9-13, 44-76`. The corpus
   section names three DOIs and says a search returning nothing means "the
   topic is not in these three papers." This is the single most visible place
   where the frozen-corpus fact is stated. It does not currently say how
   papers get in. Candidate location for: "For now, we are using Valencio and PaperQA2, but we may need broader paper access later."
2. `web/app/about/page.tsx:26-33`. The lead claims
   HiveBlot "turns published Western blot figures, captions and methods into
   structured evidence." True of the pipeline; a reader may hear it as a live
   capability of the hosted product.
3. `web/app/learn/page.tsx:70-71, 127`. "Every panel
   links to the DOI so the paper …". Worth confirming the copy does not imply
   HiveBlot retrieves the paper; it renders a link.
4. `web/app/page.tsx:108, 122`. Home-page evidence
   claims ("traceable to the figure, caption or methods sentence") and the
   Evidence affordance ("the blot crop, sources and feedback"). Same
   current-vs-future distinction.
5. `web/app/search/page.tsx:375`. "each card links to
   its figure crop and sources."
6. `web/components/DatabaseResultCard.tsx:358` and
   `web/components/EvidencePanel.tsx:440-443`. The
   missing-crop copy ("No figure crop available for this record", "image not
   available in this deployment"). Already honest; flagged so it is not
   softened into something that implies a fetch will be retried.
7. `README.md`. Describes the repo as web + api only
   and does not mention the ingestion pipeline or its external dependencies at
   all. A newcomer would not learn that paper access exists anywhere.
8. `DEPLOYMENT.md:185, 190-199, 240`. The crop section
   is accurate. Worth adding one explicit line that the hosted runtime makes
   no literature call, so nobody provisions an NCBI or Valency credential on
   Render by mistake.
9. `AGENTS.md`. The non-negotiables list has no entry
   about paper access or the frozen-corpus boundary. Candidate place to record
   that the hosted beta must not gain a live literature call.
10. `HANDOFF.md:111-114`. Points at live DOI ingestion,
    Valency/PMC discovery and grounded paper QA on the experimental stack.
    This is the one in-repo place that already names the future direction, and
    it should say plainly that none of it is hosted on this branch. For now, we are using Valencio and PaperQA2,
    but we may need broader paper access later.

11. `UCSF_BETA_HANDOFF_MESSAGE.md:13` (untracked draft).
    Already carries the intended framing: "Some parts of getting a paper
    into the system right now depend on Valencio and PaperQA2 for paper
    access, and we expect we'll need broader paper access as this grows past
    the initial corpus." Flagged so the wording stays consistent with whatever
    lands in the tracked docs.
12. `BETA_EMAIL_WITH_TALLY_AND_BRIEF.md` (untracked
    draft). Same sentence, same consistency concern.
13. `western_blot_miner/README.md`. The ingestion
    package's own README is the natural home for the full list of external
    services the pipeline touches (NCBI E-utilities, PMC BioC, PMC OA,
    UniProt).

---

## 6. Risks

- **Absolute-path coupling.** Records store an absolute `image_crop_ref` under
  the original authoring machine's `western_blot_miner/data/pdf_runs/`, and the Dockerfile
  recreates that exact path inside the container
  (`api/Dockerfile:30-31`). Crops break if the authoring path changes, if the
  corpus is reseeded from a different machine, or if someone "cleans up" the
  odd-looking `COPY` target. The Dockerfile and `DEPLOYMENT.md:198-199`
  already name relative crop refs as the tracked follow-up.
- **Crop refresh is a manual, machine-bound step.** `scripts/stage_crops.py`
  reads the 148 MB local pipeline run directory. Only the person with that
  directory can refresh `api/crops/`. A deploy from a fresh clone cannot
  regenerate figure evidence.
- **Binary assets in git.** 21 PNGs (~6 MB) are tracked deliberately so Render
  can build from the GitHub clone. This grows linearly with the corpus and
  will not scale to a larger paper set.
- **Copy outrunning the build.** The About and Learn pages describe figure,
  caption and methods extraction in the present tense. The extraction is real;
  it just does not happen in the hosted service. A reader could infer live
  ingestion.
- **Silent crop absence.** A missing crop degrades to a placeholder rather
  than an error. Good for users, but a whole-archive omission (a bad build)
  would be invisible in monitoring. Every record would simply look
  text-only.
- **No paper access means no freshness.** The hosted beta cannot tell a user
  that a paper has been retracted, corrected, or updated. Nothing in the
  runtime revisits the source.
- **Future ingestion moves external dependencies into the product boundary.**
  Live ingestion, paper QA and Valency discovery are network calls with rate
  limits, tokens and availability characteristics that the current hosted
  runtime does not have. Adding them changes the failure surface of a service
  that currently cannot fail on a third party other than Supabase.

---

## 7. Recommended language

Plain statements that match what the code does. Use as-is or trim.

- "The hosted beta serves a frozen, hand-reviewed corpus. It does not fetch
  papers, download PDFs, or query PubMed while you search."
- "Every DOI, PMCID, caption and figure crop you see was extracted ahead of
  time and stored. Clicking a DOI takes your browser to the publisher;
  HiveBlot does not go there for you."
- "Getting a paper into HiveBlot is a separate, offline step: we retrieve the
  open-access full text and figures, extract candidate blot panels, and review
  every field by hand before it is loaded."
- "For now, we are using Valencio and PaperQA2, but we may need broader paper
  access later."
- "A search that returns nothing means the topic is not in the current corpus.
  It does not mean no such evidence exists in the literature."
- "If a figure crop is not available for a record, the evidence panel shows
  the text evidence only. We never substitute a stand-in image."
- For `DEPLOYMENT.md`: "The hosted API makes no outbound call to any
  literature source. Do not provision NCBI, Valency or publisher credentials
  on Render. They are pipeline-side only."

---

## 8. Future needs

The sister branch `experimental/ucsf-demo-2026-09-09`, adds live ingestion, grounded paper QA and Valency-based
paper discovery. **None of it is hosted**, and none of it exists on
`feature/bio-context-beta`. Noted here only so the boundary is explicit.
For now, we are using Valencio and PaperQA2, but we may need broader paper access later.

Relevant paths on that branch:

- `api/app/valency.py`. Valency Bond MCP client over
  streamable HTTP against `https://mcp.valency.io/`, server-side only, bearer
  token from `VALENCY_API_TOKEN`.
- `western_blot_miner/fulltext.py`. Open-access full text by
  DOI/PMCID via Europe PMC and Unpaywall, plus a PMC E-utilities discovery
  fallback. Papers with no open-access full text return `None` and are never
  scraped.
- `api/app/experimental/ingest.py` and
  `api/app/experimental/ask.py`. Live ingestion jobs and
  grounded paper QA.
- `web/app/api/experimental/ingest/route.ts`,
  `.../ingest/[job]/route.ts`, `.../ask/route.ts`, `.../papers/route.ts`,
  `.../live-papers/route.ts`. The web-side routes.
- `web/app/experimental/live/page.tsx`,
  `.../experimental/ask/page.tsx`, `.../experimental/research/page.tsx`. The
  UI surfaces.
- `scripts/experiments/valency_smoke.py`,
  `scripts/experiments/live_ingest_eval.py`,
  `research/experiments/L1_live_ingest_eval.md`. Smoke tests
  and evaluation.

If any of that is ever promoted into the hosted product, the runtime verdict in
§3 stops holding: the service would gain third-party dependencies, tokens, and
rate limits it does not have today.

---

## 9. Open questions

1. Will the hosted beta ever need to serve a paper HiveBlot has not already
   ingested? If yes, the runtime's zero-literature-dependency property ends,
   and the copy in §5 needs rewriting before the feature ships, not after.
2. Should crop refs become relative to `CROP_BASE_DIR`? The Dockerfile and
   `DEPLOYMENT.md` already flag it as the cleaner fix. It is a corpus change,
   which is why it was deferred.
3. Where do crops live once the corpus outgrows git. Object storage, a
   Supabase bucket, or a larger image? This decision is forced by corpus
   growth, not by the current three papers.
4. For papers with no open-access full text, what does the product say? The
   pipeline's stated policy is that they are never scraped, so they simply
   cannot be ingested. That limit is not currently surfaced in any user copy.
5. Should the About page state how papers get in at all, or is the
   frozen-corpus statement sufficient for the beta audience?
6. Does anything need to re-check the source after ingestion (retractions,
   corrections, version updates)? Nothing does today.
7. Is UniProt resolution (`western_blot_miner/resolve.py`) in scope for
   "paper access"? It is an external lookup on the ingestion path but not a
   literature source; it is listed in §2 for completeness.
8. Who owns refreshing `api/crops/` when the corpus changes, given that it
   requires the local pipeline run directory?

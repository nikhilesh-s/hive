# O-2: PDF Upload Verification

Status: implemented in `o-2-pdf-upload`; awaiting Srushti's visual acceptance,
real Google sign-in/model verification, and Nik's review. Not production-ready.
Based on W-1 (`d6bc771`); PR base must be `w-1-doi-deep-link` until PR #19 merges.
Do not merge or deploy this branch as part of this task.

## Flow and Boundaries

- Search and Research share `web/components/PdfUpload.tsx` and themed styles.
- The dialog accepts a DOI and PDF, with an open-access/own-paper attestation.
  Opening it, opening a DOI link, returning from access/sign-in, and refreshing
  never submit a file or start extraction. File selection must be repeated after
  an access/sign-in redirect; the DOI and lab tag survive.
- Explicit submission calls the beta-protected Next route, which verifies the
  Supabase user with the existing server `getUser` helper. Browser owner headers
  are ignored. The internal-key-protected API issues a five-minute capability
  bound to that DOI and verified user.
- PDF bytes go directly to FastAPI using that capability, not through a Vercel
  function. This supports the ticket's 50 MiB cap without the function body limit.
  `API_BASE_URL` must be browser-reachable; `ALLOWED_ORIGINS` must include the web
  origin. HTTPS is required for hosted use. The internal API key never reaches
  the browser. Existing beta-wide live-evidence authorization is unchanged.
- FastAPI validates authorization, rights confirmation, PDF media type, declared
  and streamed size, PDF signature, readable document, encryption and page count.
  Non-PDF/unreadable documents return 400. Missing model/storage fails explicitly.
- Existing completed/active DOI jobs are returned without spending quota or
  reprocessing. New uploads use the existing daily cap, semaphore, job state,
  OpenCV, model, reconciliation, live-row loader and crop storage. Job creation
  failures refund only the new upload's charge. No new tables or migrations.
- The PDF bypasses automatic download/access discovery. Its presence does not
  establish open access: access status/source remain unknown. Persistent
  `metadata_source=upload` and run `upload_metadata.json` identify the source.
- A detected DOI mismatch or panel extraction failure fails the job before
  storing partial evidence. A successful zero-evidence run says so explicitly.
  Uploaded source PDFs are private temporary files and removed on completion or
  failure; extracted artifacts/crops follow existing storage behavior.
- Rows are stored only as `live_unreviewed`; Search's reviewed table is untouched.
  Legacy `WBM_UPLOAD` must be disabled to prevent the pipeline's separate optional
  uploader from writing outside this boundary. Completion links use W-1.

## Local Verification

- API: 288 passed / 17 skipped (real DB checks run separately).
- PostgreSQL role/metadata/W-1 matrix: 15 passed / 1 skipped, using a separate
  disposable database; the ingest role cannot write the reviewed table.
- Frontend unit tests: 14 passed; TypeScript, lint and production build pass.
- Browser: 32 desktop/mobile checks, including both entry points, real beta gate
  and anonymous denial, DOI/lab restoration, refresh, unchanged reviewed Search,
  stored evidence, progress, processing, 503 reconnection, failure and both themes.
  The normal API's actual missing-model error is verified separately from model
  fixtures. GitHub API/miner, PostgreSQL, web and hygiene checks pass on `78f3423`.
- Miner pytest: 133 passed / 2 skipped. Biology 165, reconciliation 21, enrichment
  18, extraction 10, pipeline 13, stable-row-key 34, densitometry 116 checks pass.
  Seed benchmark: 34/34 (self-consistency, not wet-lab accuracy).
- Browser success uses a clearly identified local test identity and
  `api/tests/o2_fixture_server.py` mock model responses. The actual PDF upload,
  OpenCV preprocessing, biological reconciliation, PostgreSQL persistence, crop
  serving, Search and W-1 reads are real. This is NOT a real AI extraction test.
- Isolated preview database: 475 reviewed fixture rows before and after upload;
  one completed mock job creates two unreviewed fixture rows and stored crops.
  No hosted Supabase records or access metadata were modified.
- Screenshots: `/private/tmp/hiveblot-o2-screenshots/`, desktop and mobile Search,
  Research, dialog, upload/progress, processing, failed and completed states.

## Reproduction and Remaining Prerequisites

Local previews: `http://localhost:3022/search?q=STAT3` and
`http://localhost:3022/experimental/research`; API on port 8204. The separate
mock-model test API runs on 8205 and refuses non-local/non-O-2 database URLs.
The preview uses a local beta code, not the production code. No auth bypass is
enabled in the application. Google sign-in is deliberately unconfigured in this
preview; the dialog explains that prerequisite. Real model credentials are also
absent, and the installed Claude CLI reports logged out.

`scripts/o2_local_fixture.py` initializes a fresh `hiveblot_o2` database on the
existing embedded PostgreSQL socket, applies existing migrations and generates
`/private/tmp/hiveblot-o2-sample.pdf`. It refuses to overwrite an existing DB.
Use `web/tests/pdf-upload.browser.mjs` with `PLAYWRIGHT_MODULE`,
`PLAYWRIGHT_EXECUTABLE`, `O2_TEST_URL`, `O2_FIXTURE_API`, `O2_SAMPLE_PDF` and
`O2_INTERNAL_KEY` as appropriate. The successful test identity is supplied only
by browser test interception, never by a production auth shortcut.

Before acceptance: configure Supabase public auth variables and an allowed local
OAuth callback, sign in normally, configure a real model backend/credentials,
upload a permitted real paper, inspect its evidence, and obtain Srushti's visual
acceptance. No claim of real OAuth or real model verification is made yet.

Existing architectural limits remain: jobs/quota run in one API process and can
be interrupted by host restarts; duplicate serialization is local to that
process, not a distributed queue. A stale persisted pending job requires operator
recovery. PDF DOI detection can encounter a cited DOI and reject a valid upload;
review the mismatch rather than silently assigning scientific evidence.

Dependency audit: `npm audit --omit=dev` reports five inherited affected packages
(four high, one critical, including Next.js). Their versions were not upgraded
in this one-ticket PR. Resolve those advisories separately before production.
The default development Turbopack font resolver failed locally; the dev preview
uses `next dev --webpack`. The normal production build passed with network access.

## Operator: removing a fake or wrong upload

An upload passes when the claimed DOI is printed anywhere in page-1 text, so a
forged page 1 can still attach someone else's PDF to a DOI. To remove it:

1. Find the job and keep its audit (the delete also removes the job row):
   ```sql
   SELECT job_id, doi, status, rows, uploaded_by, uploaded_at, pdf_sha256
   FROM ingest_jobs WHERE metadata_source = 'upload' AND lower(doi) = '<doi>'
   ORDER BY created_at DESC;
   ```
2. Delete its live rows, crops and job row with the existing internal-key-only
   endpoint (409 while the job is still running):
   ```bash
   curl -X DELETE -H "Authorization: Bearer $INTERNAL_API_KEY" \
     "$API_BASE_URL/experimental/ingest/<job_id>"
   ```
3. The DOI is now free for a real upload or an open-access ingest. An
   open-access `/experimental/ingest` run of the DOI also replaces its live rows.

Never touches the reviewed corpus (`hive_ingest` has no rights on it).

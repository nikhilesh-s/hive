// Browser fixtures intercept auth/model service only. PDF bytes, preprocessing,
// reconciliation, persistence, crop retrieval and W-1 reads use the real local API.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.O2_TEST_URL || 'http://localhost:3022';
const fixture = process.env.O2_FIXTURE_API || 'http://localhost:8205';
const output = process.env.O2_TEST_OUTPUT || '/private/tmp/hiveblot-o2-screenshots';
const sample = process.env.O2_SAMPLE_PDF || '/private/tmp/hiveblot-o2-sample.pdf';
const auth = { Authorization: `Bearer ${process.env.O2_INTERNAL_KEY || 'o2-local-only'}`, 'X-Hive-User-Id': '11111111-1111-4111-8111-111111111111' };
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ ...(process.env.PLAYWRIGHT_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE } : {}) });
let checks = 0;
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    let ticketRequests = 0;
    const screen = async name => page.screenshot({ path: `${output}/${name}-${width}.png`, fullPage: false });
    await page.goto(`${base}/search?lab=o2_test`);
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    let gateModal = page.getByRole('dialog');
    await gateModal.getByLabel('DOI', { exact: true }).fill('10.1000/o2-fixture');
    await gateModal.getByLabel('PDF', { exact: false }).first().setInputFiles(sample);
    await gateModal.getByRole('checkbox').check();
    await gateModal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await gateModal.getByRole('link', { name: 'Enter beta access code' }).click();
    await page.getByLabel('Access code').fill('o2-local-test');
    await page.getByRole('button', { name: 'CONTINUE', exact: true }).click();
    gateModal = page.getByRole('dialog');
    await gateModal.waitFor();
    assert.equal(await gateModal.getByLabel('DOI', { exact: true }).inputValue(), '10.1000/o2-fixture');
    assert.equal(new URL(page.url()).searchParams.get('lab'), 'o2_test');
    assert.equal(await gateModal.getByRole('button', { name: 'Upload and extract', exact: true }).isDisabled(), true);
    checks++;
    await page.reload();
    await gateModal.waitFor();
    assert.equal(ticketRequests, 0); checks++;
    await page.goto(`${base}/experimental/research?access=o2-local-test&doi=10.1000/o2-fixture&lab=o2_test`);
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).waitFor();
    await screen('research');
    assert.equal(ticketRequests, 0); checks++;
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    const modal = page.getByRole('dialog');
    assert.equal(await modal.getByLabel('DOI', { exact: true }).inputValue(), '10.1000/o2-fixture');
    await screen('upload'); checks++;
    await modal.getByLabel('PDF', { exact: false }).first().setInputFiles(sample);
    await modal.getByRole('checkbox').check();
    // Real BFF must reject missing sign-in; no production auth bypass.
    await modal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await modal.getByRole('alert').filter({ hasText: 'Sign in' }).waitFor();
    await screen('sign-in-required'); checks++;
    // A test identity can reach the normal API, which must honestly reject
    // extraction when no real model is configured (no mocked model here).
    await modal.getByLabel('DOI', { exact: true }).fill('10.1000/o2-no-model-unextracted');
    await page.route('**/api/experimental/upload', async route => {
      const response = await context.request.post('http://localhost:8204/experimental/upload-ticket', { headers: auth, data: route.request().postDataJSON() });
      await route.fulfill({ status: response.status(), json: { ...await response.json(), upload_url: 'http://localhost:8204/experimental/uploads' } });
    });
    await modal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await modal.getByRole('alert').filter({ hasText: 'No extraction model configured' }).waitFor();
    await screen('real-model-prerequisite'); checks++;
    await page.unroute('**/api/experimental/upload');
    await modal.getByRole('button', { name: 'Close upload' }).click();
    await page.goto(`${base}/search?q=STAT3`);
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).waitFor();
    await page.getByText(/Found \d+ experiments/).waitFor();
    assert.ok(!(await page.getByText(/Found \d+ experiments/).textContent()).includes('Found 0'));
    await screen('search'); checks++;
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    assert.ok(await modal.isVisible());
    await modal.getByLabel('DOI', { exact: true }).fill('10.1000/o2-fixture');
    await modal.getByLabel('PDF', { exact: false }).first().setInputFiles(sample);
    await modal.getByRole('checkbox').check();
    // A server-issued capability for the explicitly named local test identity.
    await page.route('**/api/experimental/upload', async route => {
      ticketRequests++;
      const response = await context.request.post(`${fixture}/experimental/upload-ticket`, { headers: auth, data: route.request().postDataJSON() });
      const data = await response.json();
      await route.fulfill({ status: response.status(), json: { ...data, upload_url: `${fixture}/experimental/uploads` } });
    });
    await page.route('**/api/experimental/ingest/*', async route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      const response = await context.request.get(`${fixture}/experimental/ingest/${id}`, { headers: auth });
      await route.fulfill({ status: response.status(), json: await response.json() });
    });
    await modal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await modal.getByRole('link', { name: 'Open extracted evidence', exact: true }).waitFor({ timeout: 180000 });
    await screen('completed-mock-fixture'); checks++;
    assert.equal(ticketRequests, 1);
    await modal.getByRole('link', { name: 'Open extracted evidence', exact: true }).click();
    await page.getByRole('heading', { name: '2. Extracted evidence', exact: true }).waitFor();
    await page.getByText('O-2 MOCK FIXTURE', { exact: true }).first().waitFor();
    await screen('stored-mock-evidence'); checks++;
    await page.reload();
    await page.getByText('O-2 MOCK FIXTURE', { exact: true }).first().waitFor();
    assert.equal(ticketRequests, 1); checks++;
    // Research entry point reuses completed evidence, without a second model job.
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    await modal.getByLabel('PDF', { exact: false }).first().setInputFiles(sample);
    await modal.getByRole('checkbox').check();
    await modal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await modal.getByRole('link', { name: 'Open extracted evidence', exact: true }).waitFor();
    assert.equal(ticketRequests, 2); checks++;
    await modal.getByRole('button', { name: 'Close upload' }).click();
    // Deterministic UI-only state fixtures; not evidence or real model output.
    await page.goto(`${base}/search?q=STAT3`);
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    await modal.getByLabel('DOI', { exact: true }).fill('10.1000/ui-status-only');
    await modal.getByLabel('PDF', { exact: false }).first().setInputFiles(sample);
    await modal.getByRole('checkbox').check();
    await page.route('**/api/experimental/upload', async route => {
      await new Promise(resolve => setTimeout(resolve, 700));
      await route.fulfill({ json: { token: 'ui-only', upload_url: `${base}/o2-ui-fixture` } });
    });
    await page.route('**/o2-ui-fixture', route => route.fulfill({ json: { job_id: 'ui-only', status: 'extracting', message: 'TEST FIXTURE: processing-state preview, no AI running.' } }));
    let polls = 0;
    await page.route('**/api/experimental/ingest/ui-only', async route => {
      polls++;
      if (polls === 1) await route.fulfill({ status: 503, json: { detail: 'Transient test outage' } });
      else await route.fulfill({ json: { status: 'failed', error: 'TEST FIXTURE: extraction service unavailable. No evidence was stored.' } });
    });
    await modal.getByRole('button', { name: 'Upload and extract', exact: true }).click();
    await modal.getByText('Uploading PDF (0%)', { exact: true }).waitFor();
    await screen('uploading-ui-fixture'); checks++;
    await modal.getByText('Processing', { exact: true }).waitFor();
    await screen('processing-ui-fixture'); checks++;
    await modal.getByRole('alert').filter({ hasText: 'Reconnecting' }).waitFor(); checks++;
    await modal.getByText('Extraction failed', { exact: true }).waitFor();
    await screen('failed-ui-fixture'); checks++;
    await modal.getByRole('button', { name: 'Close upload' }).click();
    await page.getByRole('button', { name: 'Use dark theme', exact: true }).click();
    await page.getByRole('button', { name: 'Upload PDF', exact: true }).click();
    await screen('dark-upload');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    assert.deepEqual(errors, []); checks++;
    await context.close();
  }
  console.log(`${checks} O-2 desktop/mobile browser checks passed. Model responses and sign-in in successful flow are TEST FIXTURES.`);
} finally { await browser.close(); }

// Run against a local server with BETA_ACCESS_CODE set to W1_TEST_ACCESS_CODE.
// Fixture responses are browser-local; no model or hosted database is contacted.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.W1_TEST_URL || 'http://127.0.0.1:3017';
const code = process.env.W1_TEST_ACCESS_CODE;
assert.ok(code, 'Set W1_TEST_ACCESS_CODE to the local server access code');
const output = process.env.W1_TEST_OUTPUT || '/private/tmp/hiveblot-w1-browser-output';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  ...(process.env.PLAYWRIGHT_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE } : {}),
});
let checks = 0;
try {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    const calls = [];
    await page.route('**/api/experimental/**', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      calls.push({ path: url.pathname, method: request.method(), doi: url.searchParams.get('doi') });
      let data = {};
      let status = 200;
      if (url.pathname.endsWith('/status')) data = { model_backend_ready: false, ingest_db_configured: true };
      else if (url.pathname.endsWith('/live-papers')) data = { papers: [] }; // older paper absent from the recent list
      else if (url.pathname.endsWith('/stored-paper')) {
        const doi = url.searchParams.get('doi');
        if (doi === '10.1000/error') { status = 503; data = { detail: 'Stored evidence temporarily unavailable' }; }
        else if (doi === '10.1000/pending') data = { doi, status: 'pending', paper: null, results: [] };
        else if (doi === '10.1000/missing') data = { doi, status: 'not_extracted', paper: null, results: [] };
        else data = { doi, status: 'found', paper: { doi, title: 'W-1 test paper', rows: 2, experiments: 1,
          discovery_query: 'Original fixture query' }, results: [1, 2].map((id) => ({
            id, paper_id: doi, doi, target: 'STAT3', sample: 'Test fixture', cell_line: 'Test fixture',
            stable_row_key: `fixture:${id}`, review_tier: 'live_unreviewed', condition: `Lane ${id}`,
            band_state: 'uncertain', experiment_type: 'standard_western',
          })) };
        await new Promise((resolve) => setTimeout(resolve, 80));
      } else {
        throw new Error(`Unexpected request: ${request.method()} ${url.pathname}`);
      }
      await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
    });

    // Real server gate, including a failed code attempt, preserves the full next path.
    const target = '/experimental/research?doi=https%3A%2F%2Fdoi.org%2F10.1000%2FA%26B&lab=smith_lab';
    await page.goto(base + target);
    await page.getByRole('heading', { name: 'Enter your beta access code' }).waitFor();
    assert.equal(new URL(page.url()).searchParams.get('next'), target);
    await page.getByLabel('Access code').fill('incorrect-test-code');
    await page.getByRole('button', { name: 'CONTINUE', exact: true }).click();
    await page.getByRole('alert').waitFor();
    assert.equal(new URL(page.url()).searchParams.get('next'), target);
    await page.getByLabel('Access code').fill(code);
    await page.getByRole('button', { name: 'CONTINUE', exact: true }).click();
    await page.getByText('Original search: Original fixture query').waitFor();
    assert.equal(new URL(page.url()).searchParams.get('lab'), 'smith_lab');
    assert.equal(await page.getByLabel('Research topic or DOI').inputValue(), '10.1000/a&b');
    assert.equal(calls.filter((r) => r.path.endsWith('/stored-paper')).length, 1);
    await page.getByRole('heading', { name: '2. Extracted evidence' }).waitFor();
    await page.screenshot({ path: `${output}/found-${viewport.width}.png`, fullPage: true });
    checks++;

    await page.reload();
    await page.getByText('Original search: Original fixture query').waitFor();
    assert.equal(calls.filter((r) => r.path.endsWith('/stored-paper')).length, 2);
    checks++;

    for (const [doi, message] of [
      ['10.1000/missing', 'This paper has not been extracted yet.'],
      ['10.1000/pending', 'Extraction is still in progress. No completed evidence is available yet.'],
    ]) {
      await page.goto(`${base}/experimental/research?doi=${encodeURIComponent(doi)}&lab=smith_lab`);
      await page.getByRole('status').filter({ hasText: message }).waitFor();
      assert.equal(await page.getByLabel('Research topic or DOI').inputValue(), doi);
      assert.equal(await page.getByRole('button', { name: 'Check access & extract' }).count(), doi.endsWith('missing') ? 1 : 0);
      await page.screenshot({ path: `${output}/${doi.split('/')[1]}-${viewport.width}.png`, fullPage: true });
      checks++;
    }

    await page.goto(`${base}/experimental/research?doi=10.1000%2Ferror`);
    await page.getByRole('alert').filter({ hasText: 'Could not look up stored evidence' }).waitFor();
    assert.equal(await page.getByText('This paper has not been extracted yet.').count(), 0);
    checks++;

    await page.getByLabel('Research topic or DOI').fill('doi:10.1000/A&B');
    await page.getByRole('button', { name: 'Find papers', exact: true }).click();
    await page.getByText('Original search: Original fixture query').waitFor();
    assert.ok(calls.every((r) => r.method === 'GET'), 'Opening and searching stored DOIs must only read');
    assert.ok(calls.every((r) => !r.path.includes('/ingest') && !r.path.endsWith('/papers')));
    assert.deepEqual(errors, []);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Page must fit the viewport');
    checks++;
    await context.close();
  }

  const denied = await browser.newContext();
  const response = await denied.request.get(`${base}/api/experimental/stored-paper?doi=10.1000/a&lab=forged`);
  assert.equal(response.status(), 401, 'The server must reject requests without beta access');
  await denied.close();
  checks++;
  console.log(`${checks} browser scenarios passed; no extraction/discovery POSTs. Screenshots: ${output}`);
} finally { await browser.close(); }

// Controlled access cases live only in an isolated local test database/browser.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.AUDIT_URL || 'http://localhost:3021';
const output = '/private/tmp/hiveblot-w6-browser';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE });
let checks = 0;
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/api/history', (route) => route.fulfill({ json: { history: [] } }));
    for (const [query, status, label] of [
      ['phospho STAT3 Tyr705', 'open_access', 'Open access'],
      ['10.1186/s12964-025-02385-8', 'no_open_copy_found', 'No open copy found · Check institutional access'],
      ['10.3892/ijmm.2022.5188', 'unknown', 'Access unknown'],
    ]) {
      const response = await page.request.post(`${base}/api/search`, { data: { query } });
      const data = await response.json();
      assert.equal(response.status(), 200);
      assert.ok(data.results.length > 0);
      assert.ok(data.results.every((row) => row.paper_flags?.access_status === status));
      await page.goto(`${base}/search?q=${encodeURIComponent(query)}`);
      await page.getByText(label, { exact: true }).first().waitFor();
      assert.equal(await page.getByText('Paywalled · Check institutional access', { exact: true }).count(), 0);
      await page.screenshot({ path: `${output}/${status}-${width}.png`, fullPage: true });
      checks++;
    }
    for (const [status, label] of [
      ['open_access', 'Open access'],
      ['no_open_copy_found', 'No open copy found · Check institutional access'],
      [null, 'Access unknown'],
    ]) {
      await page.route('**/api/experimental/papers', (route) => route.fulfill({ json: {
        results: [{ doi: '10.9999/fixture', title: 'Access wording test fixture', access_status: status }],
        sources_used: ['pmc'], errors: {},
      } }));
      await page.goto(`${base}/experimental/research`);
      await page.getByLabel('Research topic', { exact: true }).fill('access wording fixture');
      await page.getByRole('button', { name: 'Find papers', exact: true }).click();
      await page.getByText(label, { exact: true }).waitFor();
      await page.unroute('**/api/experimental/papers');
      checks++;
    }
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(`${checks} W-6 desktop/mobile scenarios passed. Screenshots: ${output}`);
} finally { await browser.close(); }

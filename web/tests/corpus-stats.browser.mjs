// Run against this branch's local frontend/API; expected totals come from the API itself.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.AUDIT_URL || 'http://localhost:3020';
const output = path.join(os.tmpdir(), 'hiveblot-w5-browser');
await mkdir(output, { recursive: true });
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE });
let checks = 0;
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/api/history', (route) => route.fulfill({ json: { history: [] } }));
    const response = await page.request.get(`${base}/api/corpus-stats`);
    assert.equal(response.status(), 200);
    const totals = await response.json();
    const { reviewed_papers: papers, experiment_groups: groups, evidence_rows: rows } = totals;
    for (const value of [papers, groups, rows]) assert.ok(Number.isSafeInteger(value) && value >= 0);
    await page.goto(base);
    await page.locator('.hb-home-scope').filter({
      hasText: `${plural(papers, 'paper')} · ${plural(groups, 'experiment')} · ${plural(rows, 'evidence row')}`,
    }).waitFor();
    checks++;
    await page.goto(`${base}/about`);
    const stats = page.getByLabel('Current corpus size');
    for (const count of [papers, groups, rows]) await stats.getByText(String(count), { exact: true }).first().waitFor();
    checks++;
    await page.screenshot({ path: `${output}/about-${width}.png`, fullPage: true });
    await page.goto(`${base}/search?q=phospho%20STAT3%20Tyr705`);
    await page.getByText(`reviewed corpus · ${plural(papers, 'paper')}`, { exact: true }).waitFor();
    await page.getByText('Found 3 experiments (18 lane records)', { exact: true }).waitFor();
    checks++;

    let attempts = 0;
    await page.route('**/api/corpus-stats', async (route) => {
      if (++attempts === 1) await route.fulfill({ status: 503, json: { error: 'cold start fixture' } });
      else await route.continue();
    });
    await page.goto(`${base}/about`);
    await stats.getByText(String(rows), { exact: true }).first().waitFor();
    assert.equal(attempts, 2);
    checks++;
    await page.unroute('**/api/corpus-stats');
    await page.route('**/api/corpus-stats', (route) => route.fulfill({ json: {
      reviewed_papers: 7, experiment_groups: 21, evidence_rows: 99,
    } }));
    await page.reload();
    for (const count of ['7', '21', '99']) await stats.getByText(count, { exact: true }).waitFor();
    assert.equal(await stats.getByText(String(rows), { exact: true }).count(), 0);
    checks++;
    await page.goto(base);
    await page.locator('.hb-home-scope').filter({ hasText: '7 papers · 21 experiments · 99 evidence rows' }).waitFor();
    checks++;
    await page.goto(`${base}/search?q=phospho%20STAT3%20Tyr705`);
    await page.getByText('reviewed corpus · 7 papers', { exact: true }).waitFor();
    checks++;
    await page.unroute('**/api/corpus-stats');
    await page.route('**/api/corpus-stats', (route) => route.fulfill({ status: 503, json: { error: 'unavailable' } }));
    await page.goto(base);
    await page.locator('.hb-home-scope').filter({ hasText: 'Corpus statistics are temporarily unavailable.' }).waitFor();
    assert.equal(await page.locator('.hb-home-scope').filter({ hasText: plural(rows, 'evidence row') }).count(), 0);
    checks++;
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(`${checks} W-5 desktop/mobile scenarios passed. Screenshots: ${output}`);
} finally { await browser.close(); }

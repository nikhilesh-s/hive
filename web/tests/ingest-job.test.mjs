import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const { outputText } = ts.transpileModule(readFileSync(new URL('../lib/ingestJob.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext },
});
const { jobFinished, transientPoll, pollBackoffMs, POLL_LIMIT_MS } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('only terminal job statuses stop polling', () => {
  for (const s of ['done', 'failed', 'awaiting_full_text']) assert.equal(jobFinished(s), true);
  for (const s of ['queued', 'running', 'extracting', undefined]) assert.equal(jobFinished(s), false);
});

test('429 and 503 are transient; 404 and 502 keep their existing handling', () => {
  assert.deepEqual([429, 503].map(transientPoll), [true, true]);
  assert.deepEqual([404, 500, 502].map(transientPoll), [false, false, false]);
});

test('without Retry-After the wait doubles from 2 s and caps at 30 s', () => {
  assert.deepEqual([0, 1, 2, 3, 4, 10, 50].map((n) => pollBackoffMs(n)), [2000, 4000, 8000, 16000, 30000, 30000, 30000]);
  assert.equal(pollBackoffMs(0, ''), 2000);
  assert.equal(pollBackoffMs(0, 'garbage'), 2000);
});

test('Retry-After seconds or HTTP date is honoured, capped at 30 s', () => {
  assert.equal(pollBackoffMs(5, '7'), 7000);
  assert.equal(pollBackoffMs(0, '0'), 0);
  assert.equal(pollBackoffMs(0, '600'), 30000);
  const now = Date.parse('2026-10-18T12:00:00Z');
  assert.equal(pollBackoffMs(0, new Date(now + 9000).toUTCString(), now), 9000);
  assert.equal(pollBackoffMs(0, new Date(now - 9000).toUTCString(), now), 2000); // date in the past: fall back
});

test('overall limit is 20 minutes', () => {
  assert.equal(POLL_LIMIT_MS, 20 * 60 * 1000);
});

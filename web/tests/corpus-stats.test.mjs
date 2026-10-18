import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function load(globals) {
  const { outputText } = ts.transpileModule(readFileSync(new URL('../lib/corpusStatsRequest.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  });
  const exports = {};
  vm.runInNewContext(outputText, { exports, Set, Number, DOMException, ...globals });
  return exports;
}

test('counts recover from cold-start 503 and remain dynamic', async () => {
  let requests = 0;
  const helper = load({
    fetch: async (url, options) => {
      assert.equal(options.cache, 'no-store');
      return ++requests === 1 ? { ok: false, status: 503 } : {
        ok: true, json: async () => ({ reviewed_papers: 7, experiment_groups: 21, evidence_rows: 99 }),
      };
    },
    setTimeout: (callback) => { queueMicrotask(callback); return 1; }, clearTimeout() {},
  });
  assert.equal((await helper.fetchCorpusStats()).reviewed_papers, 7);
  assert.equal(requests, 2);
});

test('persistent failure has bounded retries without invented counts', async () => {
  let requests = 0;
  const helper = load({
    fetch: async () => { requests++; return { ok: false, status: 503 }; },
    setTimeout: (callback) => { queueMicrotask(callback); return 1; }, clearTimeout() {},
  });
  await assert.rejects(helper.fetchCorpusStats(), /unavailable/);
  assert.equal(requests, 4);
});

test('authentication and invalid data errors are not retried', async () => {
  for (const response of [{ ok: false, status: 401 }, { ok: true, json: async () => ({ reviewed_papers: 3 }) }]) {
    let requests = 0;
    const helper = load({ fetch: async () => { requests++; return response; } });
    await assert.rejects(helper.fetchCorpusStats());
    assert.equal(requests, 1);
  }
});

test('unmount cancels retry delay and sends no subsequent requests', async () => {
  const controller = new AbortController();
  let waiting;
  let requests = 0;
  const helper = load({
    fetch: async () => { requests++; return { ok: false, status: 503 }; },
    setTimeout: () => { waiting = true; return 1; }, clearTimeout() {},
  });
  const result = helper.fetchCorpusStats(controller.signal);
  await new Promise(setImmediate);
  assert.equal(waiting, true);
  controller.abort();
  await assert.rejects(result, { name: 'AbortError' });
  assert.equal(requests, 1);
});

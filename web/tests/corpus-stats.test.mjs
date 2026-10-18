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

test('only 429 and 503 are retried; config and upstream-auth failures are not', async () => {
  for (const [status, retried] of [[429, true], [503, true], [500, false], [502, false], [504, false], [403, false]]) {
    let requests = 0;
    const helper = load({
      fetch: async () => { requests++; return { ok: false, status }; },
      setTimeout: (callback) => { queueMicrotask(callback); return 1; }, clearTimeout() {},
    });
    await assert.rejects(helper.fetchCorpusStats(), /unavailable/);
    assert.equal(requests, retried ? 4 : 1, `status ${status}`);
  }
});

test('network errors are retried', async () => {
  let requests = 0;
  const helper = load({
    fetch: async () => {
      if (++requests === 1) throw new TypeError('network down');
      return { ok: true, json: async () => ({ reviewed_papers: 1, experiment_groups: 2, evidence_rows: 3 }) };
    },
    setTimeout: (callback) => { queueMicrotask(callback); return 1; }, clearTimeout() {},
  });
  assert.equal((await helper.fetchCorpusStats()).evidence_rows, 3);
  assert.equal(requests, 2);
});

test('abort check works without AbortSignal.throwIfAborted', async () => {
  const reason = new Error('stopped');
  const signal = { aborted: true, reason, addEventListener() {}, removeEventListener() {} };
  let requests = 0;
  const helper = load({ fetch: async () => { requests++; return { ok: false, status: 503 }; } });
  await assert.rejects(helper.fetchCorpusStats(signal), (error) => error === reason);
  await assert.rejects(helper.fetchCorpusStats({ ...signal, reason: undefined }), { name: 'AbortError' });
  assert.equal(requests, 0);
});

function loadRoute(env, upstream) {
  const { outputText } = ts.transpileModule(readFileSync(new URL('../app/api/corpus-stats/route.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  });
  const exports = {};
  const NextResponse = { json: (body, init) => ({ body, status: init?.status ?? 200 }) };
  vm.runInNewContext(outputText, {
    exports, require: () => ({ NextResponse }), process: { env }, AbortSignal: { timeout: () => undefined },
    fetch: async () => { if (upstream instanceof Error) throw upstream; return upstream; },
  });
  return exports;
}

test('proxy returns 500 for missing config, 502 for upstream auth, 503 for transient failures', async () => {
  const env = { API_BASE_URL: 'http://api', INTERNAL_API_KEY: 'k' };
  assert.equal((await loadRoute({ API_BASE_URL: 'http://api' }, null).GET()).status, 500);
  assert.equal((await loadRoute({ INTERNAL_API_KEY: 'k' }, null).GET()).status, 500);
  for (const [upstream, expected] of [
    [{ ok: false, status: 401 }, 502], [{ ok: false, status: 403 }, 502],
    [{ ok: false, status: 500 }, 503], [{ ok: false, status: 503 }, 503],
    [new Error('timeout'), 503],
    [{ ok: true, status: 200, json: async () => ({ reviewed_papers: 1 }) }, 200],
  ]) assert.equal((await loadRoute(env, upstream).GET()).status, expected);
});

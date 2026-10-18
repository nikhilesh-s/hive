import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

async function load(path) {
  const { outputText } = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.ESNext },
  });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}
const { normalizeDoi, isDoiQuery, fetchStoredPaper } = await load('../lib/storedPaper.ts');
const { safeNext } = await load('../lib/betaAccess.ts');

test('normalizes DOI links and preserves suffix punctuation', () => {
  for (const value of ['10.1000/ABC', ' https://doi.org/10.1000/ABC ', 'doi:10.1000/ABC', 'http://dx.doi.org/10.1000/ABC']) {
    assert.equal(normalizeDoi(value), '10.1000/abc');
    assert.equal(isDoiQuery(value), true);
  }
  assert.equal(normalizeDoi('10.1000/a(b);c'), '10.1000/a(b);c');
  for (const value of ['bad', '10.1/a', '10.1000/' + 'a'.repeat(200)]) {
    assert.equal(normalizeDoi(value), '');
  }
  assert.equal(isDoiQuery('STAT3 western blot'), false);
  assert.equal(isDoiQuery('10.5 mM STAT3'), false); // not a DOI: runs a topic search
});

test('normalizes like western_blot_miner.fulltext.normalize_doi', () => {
  const cases = {
    'https://doi.org/10.3892/BR.2026.2108': '10.3892/br.2026.2108',
    'doi:10.1186/s12964-025-02385-8.': '10.1186/s12964-025-02385-8',
    '10.1000/ABC).': '10.1000/abc',
    '10.1000/a,': '10.1000/a',
    '(https://doi.org/10.1000/ABC);': '10.1000/abc',
    'see doi 10.1000/ABC': '10.1000/abc',
    '10.1000/has space': '10.1000/has',
    'x10.1000/a': '10.1000/a',
    'not a doi': '',
  };
  for (const [value, expected] of Object.entries(cases)) assert.equal(normalizeDoi(value), expected, value);
});

test('encoded DOI and lab survive the access next path', () => {
  const target = '/experimental/research?doi=10.1000%2Fa%28b%29&lab=smith_lab';
  const gate = new URL('http://localhost/access');
  gate.searchParams.set('next', target);
  const restored = new URL(safeNext(gate.searchParams.get('next')), gate);
  assert.equal(normalizeDoi(restored.searchParams.get('doi')), '10.1000/a(b'); // trailing ")" dropped, as in ingest
  assert.equal(restored.searchParams.get('lab'), 'smith_lab');
});

test('found/missing/pending reads use GET, encode DOI and deduplicate in-flight requests', async () => {
  const original = globalThis.fetch;
  try {
    for (const status of ['found', 'not_extracted', 'pending']) {
      const calls = [];
      globalThis.fetch = async (url, options) => {
        calls.push({ url, options });
        return { ok: true, json: async () => ({ status, doi: '10.1000/a&b',
          paper: status === 'found' ? { doi: '10.1000/a&b', discovery_query: 'original query' } : null,
          results: status === 'found' ? [{ id: 1 }] : [] }) };
      };
      const [a, b] = await Promise.all([fetchStoredPaper('10.1000/A&B'), fetchStoredPaper('https://doi.org/10.1000/a&b')]);
      assert.equal(calls.length, 1);
      assert.equal(a.status, status);
      assert.deepEqual(a, b);
      assert.equal(new URL(calls[0].url, 'http://localhost').searchParams.get('doi'), '10.1000/a&b');
      assert.equal(calls[0].options.method, undefined); // fetch defaults to GET
      assert.equal(calls[0].options.cache, 'no-store');
      await fetchStoredPaper('10.1000/a&b');
      assert.equal(calls.length, 2); // refresh is a new read
    }
  } finally { globalThis.fetch = original; }
});

test('errors remain errors and permit a later retry', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Stored evidence unavailable' }) });
    await assert.rejects(fetchStoredPaper('10.1000/error'), /unavailable/);
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ status: 'not_extracted', results: [], paper: null }) });
    assert.equal((await fetchStoredPaper('10.1000/error')).status, 'not_extracted');
    await assert.rejects(fetchStoredPaper('invalid'), /valid DOI/);
  } finally { globalThis.fetch = original; }
});

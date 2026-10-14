import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function route(owner, fetch) {
  const { outputText } = ts.transpileModule(readFileSync(new URL('../app/api/experimental/upload/route.ts', import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } });
  const exports = {};
  vm.runInNewContext(outputText, { exports, process: { env: { API_BASE_URL: 'http://backend', INTERNAL_API_KEY: 'server-only' } }, fetch,
    require: id => ({
      'next/server': { NextResponse: { json: (data, options) => Response.json(data, options) } },
      '@/lib/savedOwner': { savedOwnerHeaders: async () => owner },
      '@/lib/storedPaper': { normalizeDoi: s => /^10\.\d{4,9}\/\S+$/.test(s) ? s.toLowerCase() : '' },
    })[id] });
  return exports.POST;
}

test('PDF upload denies anonymous or forged browser identity without contacting backend', async () => {
  const post = route({}, () => assert.fail('Anonymous request must not reach backend'));
  const response = await post({ headers: new Headers({ 'X-Hive-User-Id': 'forged' }), json: async () => ({ doi: '10.1000/a', user_id: 'forged' }) });
  assert.equal(response.status, 401);
});

test('PDF upload uses verified identity and exposes only the DOI capability, never the internal key', async () => {
  let options;
  const post = route({ 'X-Hive-User-Id': 'verified' }, async (url, init) => {
    assert.equal(url, 'http://backend/experimental/upload-ticket'); options = init;
    return Response.json({ token: 'doi-bound-capability' });
  });
  const response = await post({ json: async () => ({ doi: '10.1000/ABC', user_id: 'forged' }) });
  assert.equal(response.status, 200);
  assert.equal(options.headers['X-Hive-User-Id'], 'verified');
  assert.equal(options.headers.Authorization, 'Bearer server-only');
  assert.deepEqual(JSON.parse(options.body), { doi: '10.1000/abc' });
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const data = await response.json();
  assert.equal(data.upload_url, 'http://backend/experimental/uploads');
  assert.ok(!JSON.stringify(data).includes('server-only'));
});

test('PDF upload validates DOI and forwards unavailable/unauthorized errors', async () => {
  const invalid = route({ 'X-Hive-User-Id': 'verified' }, () => assert.fail());
  assert.equal((await invalid({ json: async () => ({ doi: 'invalid' }) })).status, 422);
  const unavailable = route({ 'X-Hive-User-Id': 'verified' }, async () => { throw new Error('offline'); });
  assert.equal((await unavailable({ json: async () => ({ doi: '10.1000/a' }) })).status, 503);
});

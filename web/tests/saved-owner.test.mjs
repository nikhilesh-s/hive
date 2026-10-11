import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function load(file, modules, globals = {}) {
  const source = readFileSync(new URL(file, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
  const exports = {};
  vm.runInNewContext(outputText, { exports, require: (id) => {
    assert.ok(id in modules, `Unexpected dependency: ${id}`);
    return modules[id];
  }, ...globals });
  return exports;
}

function ownerHelper(result, configured = true) {
  return load('../lib/savedOwner.ts', {
    '@/lib/supabase/config': { authConfig: () => configured },
    '@/lib/supabase/server': { createClient: async () => ({ auth: { getUser: async () => result } }) },
  });
}

test('ownership uses only the verified Supabase user id', async () => {
  const { savedOwnerHeaders } = ownerHelper({ data: { user: { id: 'verified-id', email: 'not-an-owner' } }, error: null });
  assert.equal((await savedOwnerHeaders())['X-Hive-User-Id'], 'verified-id');
});

test('missing session and unconfigured auth preserve anonymous access', async () => {
  for (const helper of [ownerHelper({ data: { user: null }, error: { name: 'AuthSessionMissingError' } }), ownerHelper(null, false)]) {
    assert.equal(Object.keys(await helper.savedOwnerHeaders()).length, 0);
  }
});

test('invalid sessions and verification outages fail closed, never save anonymously', async () => {
  for (const name of ['AuthApiError', 'AuthRetryableFetchError']) {
    const { savedOwnerHeaders } = ownerHelper({ data: { user: null }, error: { name } });
    await assert.rejects(savedOwnerHeaders());
  }
});

test('all Saved BFF routes ignore a forged browser owner header', async () => {
  for (const [file, method] of [
    ['../app/api/saved-results/route.ts', 'GET'],
    ['../app/api/saved-results/route.ts', 'POST'],
    ['../app/api/saved-results/route.ts', 'DELETE'],
    ['../app/api/saved-results/status/route.ts', 'POST'],
  ]) {
    let sent;
    const route = load(file, {
      'next/server': { NextResponse: { json: (data, init) => Response.json(data, init) } },
      '@/lib/savedOwner': ownerHelper({ data: { user: { id: 'verified-id' } }, error: null }),
    }, {
      process: { env: { API_BASE_URL: 'http://backend', INTERNAL_API_KEY: 'test-internal' } },
      fetch: async (_url, options) => { sent = options; return Response.json({}); },
    });
    const response = await route[method]({
      nextUrl: new URL('http://web/api/saved-results?session_id=anonymous&user_id=attacker'),
      headers: new Headers({ 'X-Hive-User-Id': 'attacker' }),
      json: async () => ({ session_id: 'anonymous', user_id: 'attacker' }),
    });
    assert.equal(response.status, 200);
    assert.equal(sent.headers['X-Hive-User-Id'], 'verified-id');
    assert.equal(sent.headers.Authorization, 'Bearer test-internal');
    assert.equal(sent.cache, 'no-store');
  }
});

test('Saved views reload for account changes, not token refreshes', () => {
  let callback;
  let reloads = 0;
  let unsubscribed = false;
  const { watchSavedOwner } = load('../lib/savedResults.ts', {
    '@/lib/feedback': { sessionId: () => 'anonymous' },
    '@/lib/supabase/config': { authConfig: () => true },
    '@/lib/supabase/client': { createClient: () => ({ auth: { onAuthStateChange: (fn) => {
      callback = fn;
      return { data: { subscription: { unsubscribe: () => { unsubscribed = true; } } } };
    } } }) },
  }, { window: { location: { reload: () => { reloads++; } } } });
  const stop = watchSavedOwner();
  callback('INITIAL_SESSION', { user: { id: 'account-a' } });
  callback('TOKEN_REFRESHED', { user: { id: 'account-a' } });
  assert.equal(reloads, 0);
  callback('SIGNED_OUT', null);
  assert.equal(reloads, 1);
  callback('SIGNED_IN', { user: { id: 'account-b' } });
  assert.equal(reloads, 2);
  stop();
  assert.equal(unsubscribed, true);
});

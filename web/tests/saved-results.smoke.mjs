// Opt-in live smoke: node tests/saved-results.smoke.mjs (local web/API running).
// Creates temporary confirmed users without sending email; always cleans up.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseEnv } from 'node:util';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import { createServerClient } from '@supabase/ssr';
import ts from 'typescript';

const web = parseEnv(readFileSync(new URL('../.env', import.meta.url), 'utf8'));
const api = parseEnv(readFileSync(new URL('../../api/.env', import.meta.url), 'utf8'));
const origin = 'http://localhost:3000';
const admin = createClient(web.NEXT_PUBLIC_SUPABASE_URL, api.SUPABASE_API_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});
const anonymous = `saved-smoke-${randomUUID()}`;
const users = [];
const clients = [];

async function checked(result) {
  const { data, error } = await result;
  if (error) throw new Error(`Supabase request failed: ${error.code || error.status || error.name}`);
  return data;
}

function browserSession() {
  const jar = new Map();
  const client = createServerClient(web.NEXT_PUBLIC_SUPABASE_URL, web.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, {
    cookies: {
      getAll: () => [...jar].map(([name, value]) => ({ name, value })),
      setAll: (values) => values.forEach(({ name, value }) => value ? jar.set(name, value) : jar.delete(name)),
    },
  });
  const session = { client, cookie: () => [...jar].map(([name, value]) => `${name}=${value}`).join('; ') };
  clients.push(session);
  return session;
}

async function request(method, path, session, body, sessionId = anonymous) {
  const response = await fetch(`${origin}/api/saved-results${path}${method === 'GET' ? `?session_id=${sessionId}` : ''}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(session ? { Cookie: session.cookie() } : {}),
      // A caller-supplied ID must never be accepted as ownership.
      'X-Hive-User-Id': 'ffffffff-ffff-4fff-8fff-ffffffffffff' },
    ...(method !== 'GET' ? { body: JSON.stringify({ session_id: sessionId, user_id: 'forged', ...body }) } : {}),
  });
  assert.equal(response.status, 200, `${method} ${path} returned ${response.status}`);
  return response.json();
}

const evidenceBefore = await checked(admin.from('western_blot_records').select('*').order('id'));
const source = readFileSync(new URL('../lib/results.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
const { groupResults } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const searchResponse = await fetch(`${origin}/api/search`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'phospho STAT3 Tyr705' }),
});
assert.equal(searchResponse.status, 200);
const group = groupResults((await searchResponse.json()).results).find((g) => g.sourceRows.length === 6 &&
  g.first.target.includes('STAT3') && JSON.stringify(g.first).includes('Tyr705'));
assert.ok(group, 'Expected real six-lane STAT3 Tyr705 fixture');
const records = group.sourceRows.map((r) => ({ record_id: r.id, stable_row_key: r.stable_row_key }));
const stable_row_keys = records.map((r) => r.stable_row_key);

try {
  await request('POST', '', null, { records });
  assert.equal((await request('POST', '/status', null, { stable_row_keys })).saved_keys.length, 6);
  assert.equal(groupResults(await request('GET', '', null)).length, 1);
  await request('DELETE', '', null, { stable_row_keys });
  assert.equal((await request('GET', '', null)).length, 0);
  // Keep an anonymous copy to prove account saves neither claim nor remove it.
  await request('POST', '', null, { records });

  for (let i = 0; i < 2; i++) {
    const email = `hive-saved-smoke-${randomUUID()}@example.com`;
    const password = randomUUID() + randomUUID();
    const created = await checked(admin.auth.admin.createUser({ email, password, email_confirm: true }));
    users.push({ id: created.user.id, email, password });
  }
  const first = browserSession();
  await checked(first.client.auth.signInWithPassword(users[0]));
  assert.equal((await request('GET', '', first)).length, 0);
  await request('POST', '', first, { records });
  await request('POST', '', first, { records });
  const accountRows = await checked(admin.from('saved_results').select('user_id,session_id,stable_row_key').eq('user_id', users[0].id));
  assert.equal(accountRows.length, 6);
  assert.ok(accountRows.every((r) => r.user_id === users[0].id && r.session_id === null));
  assert.equal((await request('POST', '/status', first, { stable_row_keys })).saved_keys.length, 6);
  const savedRows = await request('GET', '', first);
  assert.equal(savedRows.length, 6);
  assert.equal(groupResults(savedRows).length, 1);
  assert.equal((await fetch(`${origin}/saved`, { headers: { Cookie: first.cookie() } })).status, 200);
  const deviceTwo = browserSession();
  await checked(deviceTwo.client.auth.signInWithPassword(users[0]));
  assert.equal((await request('GET', '', deviceTwo, undefined, randomUUID())).length, 6);
  await checked(first.client.auth.signOut({ scope: 'local' }));
  await checked(first.client.auth.signInWithPassword(users[0]));
  assert.equal((await request('GET', '', first)).length, 6);

  const second = browserSession();
  await checked(second.client.auth.signInWithPassword(users[1]));
  assert.equal((await request('GET', '', second)).length, 0);
  await request('POST', '', second, { records });
  await request('DELETE', '', first, { stable_row_keys });
  assert.equal((await request('GET', '', first)).length, 0);
  assert.equal((await request('GET', '', second)).length, 6);
  assert.equal((await request('GET', '', null)).length, 6);
  await request('DELETE', '', second, { stable_row_keys });
  await request('DELETE', '', null, { stable_row_keys });
  assert.deepEqual(await checked(admin.from('western_blot_records').select('*').order('id')), evidenceBefore);
  console.log('PASS: anonymous lifecycle, verified account ownership, idempotent six-lane save, status, regrouping, second-device session, sign-out/sign-in persistence, two-account isolation, scoped unsave, evidence unchanged.');
} finally {
  const failures = [];
  for (const session of clients) {
    try { await session.client.auth.signOut({ scope: 'local' }); } catch { /* User deletion below revokes sessions. */ }
  }
  const anonymousCleanup = await admin.from('saved_results').delete().eq('session_id', anonymous).is('user_id', null);
  if (anonymousCleanup.error) failures.push('anonymous cleanup');
  for (const user of users) {
    const cleanup = await admin.auth.admin.deleteUser(user.id);
    if (cleanup.error) failures.push('temporary account cleanup');
  }
  assert.deepEqual(failures, [], 'Temporary test data cleanup failed');
  console.log('Temporary test accounts and saves removed.');
}

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../lib/authRedirect.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { safeNext } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('callback preserves internal paths and defaults to home', () => {
  assert.equal(safeNext(null), '/');
  assert.equal(safeNext('/search?q=STAT3#results'), '/search?q=STAT3#results');
});

test('callback rejects external and browser-normalized redirect attacks', () => {
  for (const next of ['https://evil.example', '//evil.example', '/\\evil.example', '/\n/evil.example', 'javascript:alert(1)', ' /saved']) {
    assert.equal(safeNext(next), '/');
  }
});

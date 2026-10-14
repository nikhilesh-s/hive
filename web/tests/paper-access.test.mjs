import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const { outputText } = ts.transpileModule(readFileSync(new URL('../lib/paperAccess.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext },
});
const { paperAccessLabel } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('known access statuses use conservative wording', () => {
  assert.equal(paperAccessLabel('open_access'), 'Open access');
  assert.equal(paperAccessLabel('no_open_copy_found'), 'No open copy found · Check institutional access');
});

test('missing and unsupported metadata always remain unknown', () => {
  for (const value of [null, undefined, '', 'unknown', 'unexpected']) {
    assert.equal(paperAccessLabel(value), 'Access unknown');
  }
});

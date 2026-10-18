import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const { outputText } = ts.transpileModule(readFileSync(new URL('../lib/paperAccess.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext },
});
const { paperAccessLabel, safeHttpUrl } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('known access statuses use conservative wording', () => {
  assert.equal(paperAccessLabel('open_access'), 'Open access');
  assert.equal(paperAccessLabel('no_open_copy_found'), 'No open copy found · Check institutional access');
});

test('missing and unsupported metadata always remain unknown', () => {
  for (const value of [null, undefined, '', 'unknown', 'unexpected']) {
    assert.equal(paperAccessLabel(value), 'Access unknown');
  }
});

test('access links render only for http(s) URLs', () => {
  assert.equal(safeHttpUrl('https://example.org/paper.pdf'), 'https://example.org/paper.pdf');
  assert.equal(safeHttpUrl('http://example.org/p'), 'http://example.org/p');
  for (const value of ['javascript:alert(1)', 'data:text/html,x', 'ftp://example.org/x', 'not a url', '', null, undefined]) {
    assert.equal(safeHttpUrl(value), null);
  }
});

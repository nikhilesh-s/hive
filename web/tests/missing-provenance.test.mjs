import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const src = readFileSync(new URL('../components/EvidencePanel.tsx', import.meta.url), 'utf8');

test('missing-data provenance wording stays distinct', () => {
  assert.match(src, /NOT_STATED/);
  assert.match(src, /Not reported in the paper/);
  assert.match(src, /NOT_RECOVERED/);
  assert.match(src, /Not recovered from the source/);
  assert.match(src, /status === 'MISSING'/);
  assert.match(src, /return 'Unavailable'/);
});

'use client';

// Subtle post-search prompt: "Did HiveBlot understand what you were looking
// for?" Persisted with the query so misunderstood searches become training
// signal for the search layer.
//
// On a zero-result search (zeroResults) the prompt asks what was being looked
// for instead: on a small reviewed corpus "my protein is not here" is the most
// common and most informative event, and it used to leave no trace (F-2).

import { useState } from 'react';

import { submitFeedback } from '@/lib/feedback';

const MONO = 'var(--font-mono), monospace';
const SANS = 'var(--font-sans), sans-serif';

// A new query resets the prompt: the parent renders this with key={query},
// so React remounts it instead of an effect calling setState.
export default function SearchFeedback({ query, zeroResults = false }:
  { query: string; zeroResults?: boolean }) {
  const [state, setState] = useState<'idle' | 'explain' | 'done'>(zeroResults ? 'explain' : 'idle');
  const [expected, setExpected] = useState('');
  const [failed, setFailed] = useState(false);

  if (!query) return null;
  if (state === 'done') {
    return (
      <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--accent)', padding: '10px 0' }}>
        ✓ thanks — recorded
      </div>
    );
  }

  const send = (
    type: 'understood_yes' | 'understood_partially' | 'understood_no' | 'no_results',
    comment?: string,
  ) => {
    setFailed(false);
    submitFeedback({
      feedback_scope: 'search', search_query: query, feedback_type: type,
      comment: comment || null,
      // The location doubles as the result-count signal: zero vs non-zero.
      ui_location: zeroResults ? 'search_zero_results' : 'search_results',
    }).then((ok) => {
      // F-6: a dropped submission must not render a checkmark. On failure the
      // prompt stays put so the same click can be retried.
      setFailed(!ok);
      if (ok && (type === 'understood_yes' || comment !== undefined)) setState('done');
    });
    if (type !== 'understood_yes' && comment === undefined) setState('explain');
  };

  const btn = {
    background: 'transparent', border: '1px solid var(--border-strong)',
    color: 'var(--text-secondary)', borderRadius: '4px', padding: '2px 10px',
    fontFamily: SANS, fontSize: '10px', fontWeight: 500, cursor: 'pointer',
  } as const;

  return (
    <div style={{ padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {failed && (
        <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--error)' }}>
          couldn’t save that — try again
        </div>
      )}
      {state === 'idle' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: SANS, fontSize: '12px', color: 'var(--text-subtle)' }}>
            Beta — did HiveBlot understand what you were looking for?
          </span>
          <button style={btn} onClick={() => send('understood_yes')}>Yes</button>
          <button style={btn} onClick={() => send('understood_partially')}>Partially</button>
          <button style={btn} onClick={() => send('understood_no')}>No</button>
        </div>
      )}
      {state === 'explain' && (
        <div style={{
          display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap',
          justifyContent: zeroResults ? 'center' : undefined,
        }}>
          {zeroResults && (
            <span style={{ fontFamily: SANS, fontSize: '12px', color: 'var(--text-subtle)' }}>
              Nothing found. What were you looking for?
            </span>
          )}
          <input
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
            placeholder={zeroResults ? 'e.g. phospho-ERK in primary hepatocytes' : 'What did you expect instead?'}
            style={{
              background: 'var(--input-background)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)',
              borderRadius: '4px', padding: '4px 10px', fontFamily: SANS, fontSize: '11px', width: '320px',
            }}
          />
          <button style={{ ...btn, color: 'var(--accent)', borderColor: 'var(--accent)' }}
                  onClick={() => send(zeroResults ? 'no_results' : 'understood_partially', expected)}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}

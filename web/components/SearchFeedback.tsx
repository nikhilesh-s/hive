'use client';

// Subtle post-search prompt: "Did HiveBlot understand what you were looking
// for?" Persisted with the query so misunderstood searches become training
// signal for the search layer.

import { useEffect, useState } from 'react';

import { submitFeedback } from '@/lib/feedback';

const MONO = '"IBM Plex Mono", monospace';
const SERIF = '"Newsreader", serif';

export default function SearchFeedback({ query }: { query: string }) {
  const [state, setState] = useState<'idle' | 'explain' | 'done'>('idle');
  const [expected, setExpected] = useState('');

  // A new query resets the prompt.
  useEffect(() => { setState('idle'); setExpected(''); }, [query]);

  if (!query) return null;
  if (state === 'done') {
    return (
      <div style={{ fontFamily: MONO, fontSize: '10px', color: '#4ad6b0', padding: '10px 0' }}>
        ✓ thanks — recorded
      </div>
    );
  }

  const send = (type: 'understood_yes' | 'understood_partially' | 'understood_no', comment?: string) => {
    submitFeedback({
      feedback_scope: 'search', search_query: query, feedback_type: type,
      comment: comment || null, ui_location: 'search_results',
    });
    if (type === 'understood_yes' || comment !== undefined) setState('done');
    else setState('explain');
  };

  const btn = {
    background: 'transparent', border: '1px solid rgba(255,255,255,.15)',
    color: '#a9bdb5', borderRadius: '4px', padding: '2px 10px',
    fontFamily: MONO, fontSize: '10px', cursor: 'pointer',
  } as const;

  return (
    <div style={{ padding: '14px 0', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {state === 'idle' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: SERIF, fontSize: '12px', color: '#6f857d' }}>
            Beta — did HiveBlot understand what you were looking for?
          </span>
          <button style={btn} onClick={() => send('understood_yes')}>Yes</button>
          <button style={btn} onClick={() => send('understood_partially')}>Partially</button>
          <button style={btn} onClick={() => send('understood_no')}>No</button>
        </div>
      )}
      {state === 'explain' && (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
            placeholder="What did you expect instead?"
            style={{
              background: '#0a0d0f', border: '1px solid rgba(255,255,255,.15)', color: '#e7f0ee',
              borderRadius: '4px', padding: '4px 10px', fontFamily: MONO, fontSize: '11px', width: '320px',
            }}
          />
          <button style={{ ...btn, color: '#4ad6b0', borderColor: '#4ad6b0' }}
                  onClick={() => send('understood_partially', expected)}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}

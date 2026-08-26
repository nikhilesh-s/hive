'use client';

// Unobtrusive general beta-feedback action (fixed, bottom-right). Captures
// free-form UI feedback ("keep the blot visible while I read methods",
// "too much information", ...) with page + current query context.

import { useState } from 'react';

import { submitFeedback } from '@/lib/feedback';

const MONO = 'var(--font-mono), monospace';
const SANS = 'var(--font-sans), sans-serif';

export default function BetaFeedback({ query }: { query?: string }) {
  const [state, setState] = useState<'idle' | 'open' | 'done'>('idle');
  const [text, setText] = useState('');

  if (state === 'idle') {
    return (
      <button
        onClick={() => setState('open')}
        style={{
          position: 'fixed', bottom: '18px', right: '18px', zIndex: 50,
          background: '#0a0d0f', border: '1px solid rgba(255,255,255,.15)',
          color: '#a9bdb5', borderRadius: '6px', padding: '6px 12px',
          fontFamily: MONO, fontSize: '10px', cursor: 'pointer', letterSpacing: '0.4px',
        }}
      >
        BETA FEEDBACK
      </button>
    );
  }

  return (
    <div style={{
      position: 'fixed', bottom: '18px', right: '18px', zIndex: 50, width: '320px',
      background: '#0a0d0f', border: '1px solid rgba(255,255,255,.15)',
      borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px',
    }}>
      {state === 'done' ? (
        <div style={{ fontFamily: MONO, fontSize: '11px', color: '#4ad6b0' }}>
          ✓ thank you — recorded
          <button onClick={() => { setState('idle'); setText(''); }}
                  style={{ marginLeft: '12px', background: 'none', border: 'none', color: '#6f857d', cursor: 'pointer', fontFamily: MONO, fontSize: '10px' }}>
            close
          </button>
        </div>
      ) : (
        <>
          <div style={{ fontFamily: MONO, fontSize: '10px', color: '#6f857d' }}>
            Anything — layout, missing filters, information overload, what you wish this did.
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="e.g. keep the blot visible while I inspect the methods"
            style={{
              background: '#06090c', border: '1px solid rgba(255,255,255,.12)', color: '#e7f0ee',
              borderRadius: '4px', padding: '8px', fontFamily: SANS, fontSize: '13px', resize: 'vertical',
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                if (!text.trim()) return;
                submitFeedback({
                  feedback_scope: 'ui', comment: text.trim(),
                  search_query: query || null, ui_location: 'search_page',
                });
                setState('done');
              }}
              style={{ background: 'transparent', border: '1px solid #4ad6b0', color: '#4ad6b0', borderRadius: '4px', padding: '4px 12px', fontFamily: SANS, fontSize: '10px', fontWeight: 500, cursor: 'pointer' }}
            >
              Send
            </button>
            <button
              onClick={() => setState('idle')}
              style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.15)', color: '#6f857d', borderRadius: '4px', padding: '4px 12px', fontFamily: SANS, fontSize: '10px', fontWeight: 500, cursor: 'pointer' }}
            >
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}

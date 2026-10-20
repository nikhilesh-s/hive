'use client';

// Unobtrusive general beta-feedback action (fixed, bottom-right). Captures
// free-form UI feedback ("keep the blot visible while I read methods",
// "too much information", ...) with page + current query context.
//
// F-4: also hosts the three-question end-of-session survey (DEMO.md §7), so
// the spoken close becomes queryable rows instead of meeting notes. Offered
// once per browser session, dismissible, and skipping never blocks anything.

import { useState, useSyncExternalStore } from 'react';

import { submitFeedback } from '@/lib/feedback';

const MONO = 'var(--font-mono), monospace';
const SANS = 'var(--font-sans), sans-serif';

const SURVEY_KEY = 'hiveblot_survey_done';

// One row per answered question: distinct feedback_type AND ui_location, so
// the F-1 export can pivot on either.
const SURVEY = [
  {
    type: 'survey_fields_most_useful',
    location: 'survey_q1',
    q: 'Of the fields we show — protein, phosphosite, cell line, treatment, dose, duration, antibody vendor and catalog number, molecular weight, lane-level band presence — which three matter most to you?',
  },
  {
    type: 'survey_fields_missing',
    location: 'survey_q2',
    q: 'What is missing?',
  },
  {
    type: 'survey_trust_unreviewed',
    location: 'survey_q3',
    q: 'What would you need to see before you trusted an automatically extracted row without opening the paper yourself?',
  },
] as const;

// Same client-only-storage pattern as ThemeToggle: the server snapshot says
// "already done" so the button never flashes in before hydration.
const SURVEY_EVENT = 'hiveblot-survey-change';

function subscribeSurvey(onChange: () => void) {
  window.addEventListener(SURVEY_EVENT, onChange);
  return () => window.removeEventListener(SURVEY_EVENT, onChange);
}

function surveyDoneSnapshot(): boolean {
  try { return window.localStorage.getItem(SURVEY_KEY) === '1'; } catch { return false; }
}

export default function BetaFeedback({ query }: { query?: string }) {
  const [state, setState] = useState<'idle' | 'open' | 'survey' | 'done'>('idle');
  const [text, setText] = useState('');
  const [answers, setAnswers] = useState(['', '', '']);
  // F-5: contact is stored only when the (unchecked by default) box is ticked.
  const [consent, setConsent] = useState(false);
  const [email, setEmail] = useState('');
  const [failed, setFailed] = useState(false);
  const [sent, setSent] = useState([false, false, false]);
  const surveyDone = useSyncExternalStore(subscribeSurvey, surveyDoneSnapshot, () => true);

  const contact = consent && email.trim() ? email.trim() : null;

  const closeSurvey = () => {
    try { window.localStorage.setItem(SURVEY_KEY, '1'); } catch { /* private mode */ }
    window.dispatchEvent(new Event(SURVEY_EVENT));
  };

  const input = {
    background: 'var(--background)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)',
    borderRadius: '4px', padding: '8px', fontFamily: SANS, fontSize: '13px', resize: 'vertical',
  } as const;
  const primary = {
    background: 'transparent', border: '1px solid var(--accent)', color: 'var(--accent)',
    borderRadius: '4px', padding: '4px 12px', fontFamily: SANS, fontSize: '10px', fontWeight: 500, cursor: 'pointer',
  } as const;
  const secondary = { ...primary, borderColor: 'var(--border-strong)', color: 'var(--text-subtle)' };
  const panel = {
    position: 'fixed', bottom: '18px', right: '18px', zIndex: 50, maxWidth: 'calc(100vw - 36px)',
    background: 'var(--input-background)', border: '1px solid var(--border-strong)',
    borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px',
  } as const;

  const FailNote = failed ? (
    <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--error)' }}>
      couldn’t save that — try again
    </div>
  ) : null;

  const ContactOptIn = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', fontFamily: SANS, fontSize: '11px', color: 'var(--text-subtle)', lineHeight: 1.4 }}>
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>You may follow up with me about this comment (optional).</span>
      </label>
      {consent && (
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@lab.ucsf.edu"
          style={{ ...input, resize: undefined, fontSize: '12px' }}
        />
      )}
    </div>
  );

  if (state === 'idle') {
    return (
      <div style={{ position: 'fixed', bottom: '18px', right: '18px', zIndex: 50, display: 'flex', gap: '8px' }}>
        {!surveyDone && (
          <button
            onClick={() => setState('survey')}
            style={{
              background: 'var(--input-background)', border: '1px solid var(--accent)',
              color: 'var(--accent)', borderRadius: '6px', padding: '6px 12px',
              fontFamily: MONO, fontSize: '10px', cursor: 'pointer', letterSpacing: '0.4px',
            }}
          >
            FINISHED? 3 QUESTIONS
          </button>
        )}
        <button
          onClick={() => setState('open')}
          style={{
            background: 'var(--input-background)', border: '1px solid var(--border-strong)',
            color: 'var(--text-secondary)', borderRadius: '6px', padding: '6px 12px',
            fontFamily: MONO, fontSize: '10px', cursor: 'pointer', letterSpacing: '0.4px',
          }}
        >
          BETA FEEDBACK
        </button>
      </div>
    );
  }

  if (state === 'survey') {
    return (
      <div style={{ ...panel, width: '360px', maxHeight: '80vh', overflowY: 'auto' }}>
        <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--text-subtle)' }}>
          Three questions — answer any, skip the rest. Please do not paste unpublished data.
        </div>
        {SURVEY.map((s, i) => (
          <div key={s.location} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontFamily: SANS, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {s.q}
            </label>
            <textarea
              value={answers[i]}
              rows={2}
              onChange={(e) => setAnswers(answers.map((a, j) => (j === i ? e.target.value : a)))}
              style={input}
            />
          </div>
        ))}
        {ContactOptIn}
        {FailNote}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => {
              setFailed(false);
              // An unanswered question writes no row; a question that already
              // landed is not re-sent when the researcher retries a failure.
              Promise.all(SURVEY.map((s, i) => (
                !answers[i].trim() || sent[i] ? Promise.resolve(true) : submitFeedback({
                  feedback_scope: 'ui', comment: answers[i].trim(), feedback_type: s.type,
                  search_query: query || null, ui_location: s.location, contact,
                })
              ))).then((oks) => {
                setSent(oks.map((ok, i) => sent[i] || (ok && !!answers[i].trim())));
                if (oks.some((ok) => !ok)) { setFailed(true); return; }  // F-6: never fake success
                closeSurvey();
                setState('done');
              });
            }}
            style={primary}
          >
            Send
          </button>
          <button onClick={() => { closeSurvey(); setState('idle'); }} style={secondary}>
            Not now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...panel, width: '320px' }}>
      {state === 'done' ? (
        <div style={{ fontFamily: MONO, fontSize: '11px', color: 'var(--accent)' }}>
          ✓ thank you — recorded
          <button onClick={() => { setState('idle'); setText(''); }}
                  style={{ marginLeft: '12px', background: 'none', border: 'none', color: 'var(--text-subtle)', cursor: 'pointer', fontFamily: MONO, fontSize: '10px' }}>
            close
          </button>
        </div>
      ) : (
        <>
          <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--text-subtle)' }}>
            Anything — layout, missing filters, information overload, what you wish this did.
            Please do not paste unpublished data.
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="e.g. keep the blot visible while I inspect the methods"
            style={input}
          />
          {ContactOptIn}
          {FailNote}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                if (!text.trim()) return;
                setFailed(false);
                submitFeedback({
                  feedback_scope: 'ui', comment: text.trim(),
                  search_query: query || null, ui_location: 'search_page', contact,
                }).then((ok) => (ok ? setState('done') : setFailed(true)));  // F-6
              }}
              style={primary}
            >
              Send
            </button>
            <button onClick={() => setState('idle')} style={secondary}>
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}

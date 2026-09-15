'use client';

// EXPERIMENTAL: ask a question, get an answer that may only cite the
// evidence records shown beneath it. Retrieval is deterministic; the model
// is optional (without a key the page still shows the ranked evidence).

import { useState } from 'react';

import ExperimentalNav from '@/components/ExperimentalNav';

interface Block { ref: string; tier: string; record_id: number; doi: string | null; title?: string | null; headline: string; lanes: number; text: string }
interface AskResponse { question: string; doi?: string | null; evidence: Block[]; answer: string | null; cited: string[]; model: string | null; note: string | null }

const MONO = 'var(--font-mono), monospace';
const EXAMPLES = [
  'Is STAT3 phosphorylated at Tyr705 after IL-6 in Hep3B, and which antibody was used?',
  'Which loading controls were validated in mouse submandibular gland?',
  'Does BEX2 co-immunoprecipitate with PIK3CA?',
  'Is ERK phosphorylation settled in the IL-6 time course?',
];

function renderAnswer(text: string, cited: string[]) {
  // Turn [E3] and [E1, E3] into anchors to the evidence blocks.
  return text.split(/(\[E\d+(?:\s*,\s*E\d+)*\])/g).map((part, i) => {
    if (!/^\[E\d+(?:\s*,\s*E\d+)*\]$/.test(part)) return <span key={i}>{part}</span>;
    return part.slice(1, -1).split(',').map((s) => s.trim()).map((ref) => (
      <a key={`${i}-${ref}`} href={`#${ref}`} className={`hb-ask-cite${cited.includes(ref) ? '' : ' is-bad'}`}>[{ref}]</a>
    ));
  });
}

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [doi, setDoi] = useState('');
  const [includeLive, setIncludeLive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AskResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e?: React.FormEvent, q?: string) {
    e?.preventDefault();
    const qq = (q ?? question).trim();
    if (qq.length < 3) return;
    setQuestion(qq);
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const r = await fetch('/api/experimental/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: qq, doi: doi.trim() || null, include_live: includeLive }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setRes(d);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <div className="hb-live-flag">EXPERIMENTAL · GROUNDED QA</div>
        <h1 className="hb-page-h1">Ask the evidence</h1>
        <p className="hb-page-lead">
          A question in plain language, answered <strong>only</strong> from HiveBlot evidence records. Every claim
          in the answer carries a citation you can open; conflicting fields stay conflicting; live, unreviewed
          extractions are named as such. If the records do not answer the question, it says so.
        </p>
        <ExperimentalNav />
      </section>

      <section className="hb-page-section">
        <form onSubmit={submit} className="hb-ask-form">
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={3}
            placeholder="e.g. Which antibody detected phospho-STAT3 Tyr705 in Hep3B, and was the band present at 5 min?" aria-label="Question" />
          <div className="hb-live-form">
            <input value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="Limit to one paper (DOI, optional)" aria-label="DOI filter" />
            <label className="hb-ask-check"><input type="checkbox" checked={includeLive} onChange={(e) => setIncludeLive(e.target.checked)} /> include live tier</label>
            <button type="submit" disabled={busy || question.trim().length < 3}>{busy ? 'Reading evidence…' : 'Ask'}</button>
          </div>
        </form>
        <div className="hb-search-examples" style={{ marginTop: 10 }}>
          <span>Try:</span>
          {EXAMPLES.map((ex) => <button key={ex} type="button" onClick={() => submit(undefined, ex)}>{ex}</button>)}
        </div>
        {err && <p className="hb-live-error">{err}</p>}
      </section>

      {res && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">Answer</h2>
          {res.answer ? (
            <div className="hb-ask-answer">
              <p>{renderAnswer(res.answer, res.cited)}</p>
              <div style={{ fontFamily: MONO, fontSize: 10, color: 'var(--text-subtle)' }}>
                model {res.model} · cites {res.cited.length ? res.cited.join(', ') : 'nothing'}
                {res.note ? ` · ${res.note}` : ''}
              </div>
            </div>
          ) : (
            <p className="hb-live-note">{res.note || 'No answer.'}</p>
          )}

          <h2 className="hb-page-h2" style={{ marginTop: 28 }}>Evidence shown to the model ({res.evidence.length})</h2>
          <ol className="hb-ask-evidence">
            {res.evidence.map((b) => (
              <li key={b.ref} id={b.ref} className={res.cited.includes(b.ref) ? 'is-cited' : ''}>
                <div className="hb-ask-ev-head">
                  <span className="hb-ask-ref">[{b.ref}]</span>
                  <span className="hb-ask-headline">{b.headline}</span>
                  {b.tier !== 'reviewed' && <span className="hb-live-badge">LIVE · UNREVIEWED</span>}
                  <span className="hb-result-chip">{b.lanes} lanes</span>
                  {b.doi && <a href={`https://doi.org/${b.doi}`} target="_blank" rel="noreferrer" className="hb-result-doi" style={{ fontFamily: MONO, fontSize: 11 }}>DOI {b.doi}</a>}
                </div>
                <div className="hb-ask-ev-text">{b.text}</div>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

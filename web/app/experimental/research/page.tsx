'use client';

// EXPERIMENTAL — the one-page UCSF research flow:
//   topic → find papers (Valency / PMC, source shown) → choose an open-access
//   paper → extract live or open an already-ingested copy → progress →
//   LIVE · UNREVIEWED Evidence Records with provenance → ask a question
//   scoped to that paper → cited answer + numbered evidence.
// Nothing here touches the reviewed corpus; every live row is badged.

import { useEffect, useState } from 'react';

import DatabaseResultCard from '@/components/DatabaseResultCard';
import ExperimentalNav from '@/components/ExperimentalNav';
import { groupResults, type DatabaseResult } from '@/lib/results';

interface Paper {
  title?: string | null; authors?: string[]; abstract?: string | null; doi?: string | null;
  pmcid?: string | null; year?: string | null; venue?: string | null; url?: string | null; source?: string;
  oa_pdf?: boolean; is_oa?: boolean;
}
interface Job {
  job_id: string; doi: string; status: string; message: string; pmcid?: string | null;
  candidates?: number | null; records?: number | null; rows?: number | null; backend?: string | null;
  error?: string | null; created_at: string; updated_at: string;
}
interface LivePaper { doi: string; title?: string | null; job_id?: string | null; rows: number; experiments: number; ingested_at?: string | null }
interface Status { model_backend_ready: boolean; model_backend: string; valency_configured: boolean; ingest_db_configured: boolean; live_rows: number | null }
interface Block { ref: string; tier: string; record_id: number; doi: string | null; headline: string; lanes: number; text: string }
interface AskResponse { evidence: Block[]; answer: string | null; cited: string[]; model: string | null; note: string | null }

const STAGES = ['fetching', 'preprocessing', 'extracting', 'loading', 'done'];
const MONO = 'var(--font-mono), monospace';
const TOPICS = ['STAT3 phosphorylation hepatocellular carcinoma', 'autophagy LC3B western blot lung cancer', 'GAPDH loading control mouse tissue'];

function Stepper({ status }: { status: string }) {
  const idx = STAGES.indexOf(status);
  return (
    <ol className="hb-live-steps" aria-label="Extraction progress">
      {STAGES.map((s, i) => (
        <li key={s} className={i < idx || status === 'done' ? 'is-done' : i === idx ? 'is-active' : ''}>{s}</li>
      ))}
    </ol>
  );
}

function renderAnswer(text: string, cited: string[]) {
  return text.split(/(\[E\d+(?:\s*,\s*E\d+)*\])/g).map((part, i) => {
    if (!/^\[E\d+(?:\s*,\s*E\d+)*\]$/.test(part)) return <span key={i}>{part}</span>;
    return part.slice(1, -1).split(',').map((s) => s.trim()).map((ref) => (
      <a key={`${i}-${ref}`} href={`#${ref}`} className={`hb-ask-cite${cited.includes(ref) ? '' : ' is-bad'}`}>[{ref}]</a>
    ));
  });
}

const post = (url: string, body: unknown) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export default function ResearchPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [livePapers, setLivePapers] = useState<LivePaper[]>([]);
  const [topic, setTopic] = useState('');
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [searchErr, setSearchErr] = useState<Record<string, string>>({});
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<Paper | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [startErr, setStartErr] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [rows, setRows] = useState<DatabaseResult[]>([]);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [ask, setAsk] = useState<AskResponse | null>(null);
  const [askErr, setAskErr] = useState<string | null>(null);

  const refreshLive = () => fetch('/api/experimental/live-papers').then((r) => r.json()).then((d) => setLivePapers(d.papers || [])).catch(() => {});

  useEffect(() => {
    fetch('/api/experimental/status').then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
    refreshLive();
  }, []);

  // Poll a running job every 2 s; on done, load its rows and refresh the ingested list.
  useEffect(() => {
    if (!job || job.status === 'done' || job.status === 'failed') return;
    const started = Date.parse(job.created_at);
    const id = window.setInterval(async () => {
      setElapsed(Math.round((Date.now() - started) / 1000));
      const r = await fetch(`/api/experimental/ingest/${job.job_id}`);
      if (!r.ok) return;
      const j: Job = await r.json();
      setJob(j);
      if (j.status === 'done') { loadRows(j.doi); refreshLive(); }
    }, 2000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.status]);

  const ingested = (doi?: string | null) => livePapers.find((p) => doi && p.doi.toLowerCase() === doi.toLowerCase());

  async function findPapers(e?: React.FormEvent, q?: string) {
    e?.preventDefault();
    const qq = (q ?? topic).trim();
    if (!qq) return;
    setTopic(qq);
    setSearching(true);
    setPapers([]);
    try {
      const r = await post('/api/experimental/papers', { query: qq, limit: 8 });
      const d = await r.json();
      setPapers(d.results || []);
      setSources(d.sources_used || []);
      setSearchErr(d.errors || {});
    } finally {
      setSearching(false);
    }
  }

  async function loadRows(doi: string) {
    setRowsLoading(true);
    try {
      const r = await post('/api/experimental/search', { query: doi, limit: 500 });
      const d = r.ok ? await r.json() : { results: [] };
      setRows(d.results || []);
    } finally {
      setRowsLoading(false);
    }
  }

  function choose(p: Paper) {
    setSelected(p);
    setRows([]);
    setAsk(null);
    setJob(null);
    setStartErr(null);
    if (p.doi && ingested(p.doi)) loadRows(p.doi);
  }

  async function extract(doi: string) {
    setStartErr(null);
    setRows([]);
    const r = await post('/api/experimental/ingest', { doi });
    const d = await r.json();
    if (!r.ok) { setStartErr(d.detail || d.error || `Backend returned ${r.status}`); return; }
    setElapsed(0);
    setJob(d);
  }

  async function askQuestion(e?: React.FormEvent) {
    e?.preventDefault();
    if (!selected?.doi || question.trim().length < 3) return;
    setAsking(true);
    setAskErr(null);
    setAsk(null);
    try {
      const r = await post('/api/experimental/ask', { question: question.trim(), doi: selected.doi, include_live: true });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setAsk(d);
    } catch (e2) {
      setAskErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      setAsking(false);
    }
  }

  const groups = groupResults(rows);
  const busy = !!(job && job.status !== 'done' && job.status !== 'failed');
  const selectedIngested = selected ? ingested(selected.doi) : undefined;

  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <div className="hb-live-flag">EXPERIMENTAL · LIVE RESULTS ARE UNREVIEWED</div>
        <h1 className="hb-page-h1">Research a topic</h1>
        <p className="hb-page-lead">
          Find an open-access paper, let HiveBlot read its blots in front of you, then interrogate the evidence.
          Live records go into a separate <strong>unreviewed</strong> tier and are badged; the reviewed corpus is untouched.
          Answers cite the records they came from and keep unresolved fields unresolved.
        </p>
        <ExperimentalNav />
        {status && (
          <div className="hb-live-status" aria-label="Experimental backend status">
            <span className={status.model_backend_ready ? 'ok' : 'bad'}>model: {status.model_backend}</span>
            <span className={status.valency_configured ? 'ok' : 'warn'}>discovery: {status.valency_configured ? 'Valency + PMC' : 'PMC only (Valency not configured)'}</span>
            <span className={status.ingest_db_configured ? 'ok' : 'bad'}>live tier: {status.ingest_db_configured ? `ready · ${status.live_rows ?? 0} rows` : 'not configured'}</span>
          </div>
        )}
      </section>

      <section className="hb-page-section">
        <h2 className="hb-page-h2">1. Find papers</h2>
        <form onSubmit={findPapers} className="hb-live-form" role="search">
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic, e.g. STAT3 phosphorylation hepatocellular carcinoma" aria-label="Research topic" />
          <button type="submit" disabled={searching || !topic.trim()}>{searching ? 'Searching…' : 'Find papers'}</button>
        </form>
        <div className="hb-search-examples" style={{ marginTop: 8 }}>
          <span>Try:</span>
          {TOPICS.map((t) => <button key={t} type="button" onClick={() => findPapers(undefined, t)}>{t}</button>)}
        </div>
        {sources.length > 0 && (
          <p className="hb-live-note">
            Discovery source{sources.length > 1 ? 's' : ''}: <strong>{sources.map((s) => (s === 'valency' ? 'Valency Bond' : 'PubMed Central')).join(' + ')}</strong>
            {Object.keys(searchErr).length ? ` · ${Object.entries(searchErr).map(([k, v]) => `${k}: ${v}`).join('; ')}` : ''}
          </p>
        )}
        <ul className="hb-live-papers">
          {papers.map((p, i) => {
            const have = ingested(p.doi);
            const oa = !!p.oa_pdf;                      // Europe PMC lists a downloadable open-access PDF
            return (
              <li key={`${p.doi || p.title}-${i}`} className={selected?.doi && selected.doi === p.doi ? 'is-selected' : ''}>
                <div className="hb-live-paper-title">{p.title || 'Untitled'}</div>
                <div className="hb-live-paper-meta">
                  {(p.authors || []).slice(0, 3).join(', ')}{(p.authors || []).length > 3 ? ' et al.' : ''}
                  {p.year ? ` · ${p.year}` : ''}{p.venue ? ` · ${p.venue}` : ''}
                  {p.doi ? <> · <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer">{p.doi}</a></> : ' · no DOI'}
                  <span className="hb-result-chip" style={{ marginLeft: 8 }}>{(p.source || '').startsWith('valency') ? 'Valency' : 'PMC'}</span>
                  {oa ? (
                    <span className="hb-result-chip" style={{ marginLeft: 6, color: 'var(--accent)' }}>open-access PDF · {p.pmcid}</span>
                  ) : (
                    <span className="hb-result-chip" style={{ marginLeft: 6 }}>{p.pmcid ? `${p.pmcid} · no downloadable PDF` : 'not in PMC · cannot extract'}</span>
                  )}
                  {have && <span className="hb-live-badge" style={{ marginLeft: 6 }}>ALREADY EXTRACTED · {have.experiments} exp</span>}
                </div>
                {p.abstract && <p className="hb-live-abstract">{p.abstract.slice(0, 240)}{p.abstract.length > 240 ? '…' : ''}</p>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button type="button" className="hb-evidence-toggle" disabled={!p.doi || busy || (!oa && !have)} onClick={() => choose(p)}
                    title={!oa && !have ? 'HiveBlot only reads papers with a downloadable open-access PDF' : undefined}>
                    {have ? 'Open extracted evidence' : oa ? 'Choose this paper' : 'No open-access PDF'}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>

        {livePapers.length > 0 && (
          <details className="hb-research-prewarmed">
            <summary>Already extracted in this stack ({livePapers.length}) — open without waiting</summary>
            <ul className="hb-live-papers">
              {livePapers.map((lp) => (
                <li key={lp.doi}>
                  <div className="hb-live-paper-title">{lp.title || lp.doi}</div>
                  <div className="hb-live-paper-meta">
                    <a href={`https://doi.org/${lp.doi}`} target="_blank" rel="noreferrer">{lp.doi}</a> · {lp.experiments} experiments · {lp.rows} lane rows
                    {lp.ingested_at ? ` · ${lp.ingested_at.slice(0, 10)}` : ''}
                  </div>
                  <button type="button" className="hb-evidence-toggle" onClick={() => choose({ doi: lp.doi, title: lp.title, pmcid: null, source: 'live' })}>Open extracted evidence</button>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      {selected && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">2. {selectedIngested ? 'Extracted evidence' : 'Extract'}</h2>
          <p className="hb-page-p" style={{ marginBottom: 10 }}>
            <strong>{selected.title || selected.doi}</strong>
            {selected.doi && <> · <a href={`https://doi.org/${selected.doi}`} target="_blank" rel="noreferrer" className="hb-result-doi" style={{ fontFamily: MONO, fontSize: 12 }}>{selected.doi}</a></>}
          </p>
          {!selectedIngested && !job && (
            <div className="hb-live-form">
              <button type="button" onClick={() => selected.doi && extract(selected.doi)} disabled={!selected.doi || !status?.model_backend_ready}>
                Extract this paper live
              </button>
              <span className="hb-live-note" style={{ margin: 0, alignSelf: 'center' }}>
                {status?.model_backend_ready
                  ? 'Open-access PDF → panel detection → the model reads each candidate panel (several in parallel) → deterministic biology. Roughly a minute per few panels; a figure-heavy paper can take 5–10 minutes, so an already-extracted paper is the safer live demo.'
                  : 'No model backend configured; open an already-extracted paper instead.'}
              </span>
            </div>
          )}
          {selectedIngested && !job && (
            <div className="hb-live-form">
              <span className="hb-live-note" style={{ margin: 0, alignSelf: 'center' }}>Already in the live tier ({selectedIngested.experiments} experiments, {selectedIngested.rows} lane rows).</span>
              <button type="button" onClick={() => selected.doi && extract(selected.doi)} disabled={!selected.doi || !status?.model_backend_ready}>Re-extract</button>
            </div>
          )}
          {startErr && <p className="hb-live-error">{startErr}</p>}
          {job && (
            <div className="hb-live-job" style={{ marginTop: 12 }}>
              <div style={{ fontFamily: MONO, fontSize: 12 }}>
                {job.doi}{job.pmcid ? ` · ${job.pmcid}` : ''} · job {job.job_id}{job.backend ? ` · ${job.backend}` : ''} · {elapsed}s
              </div>
              <Stepper status={job.status} />
              <p className={`hb-live-message${job.status === 'failed' ? ' is-error' : ''}`}>{job.error || job.message}</p>
              {job.status === 'failed' && livePapers.length > 0 && (
                <p className="hb-live-note">Fallback: open an already-extracted paper from the list above.</p>
              )}
            </div>
          )}

          {(rows.length > 0 || rowsLoading) && (
            <>
              <p className="hb-results-count" style={{ marginTop: 16 }}>
                {rowsLoading ? 'Loading live records…' : `${groups.length} experiment${groups.length !== 1 ? 's' : ''} (${rows.length} lane record${rows.length !== 1 ? 's' : ''}) — every value below was produced by the model + deterministic engine without human review. Open Evidence & sources for provenance.`}
              </p>
              <div className="hb-result-list">
                {groups.map((g) => <DatabaseResultCard key={g.first.id} data={g.first} lanes={g.lanes} live />)}
              </div>
            </>
          )}
        </section>
      )}

      {selected && rows.length > 0 && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">3. Ask about this paper</h2>
          <form onSubmit={askQuestion} className="hb-ask-form">
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} aria-label="Question"
              placeholder="e.g. Which targets were blotted, in which cells, and is any phosphorylation claim unresolved?" />
            <div className="hb-live-form">
              <span className="hb-live-note" style={{ margin: 0, alignSelf: 'center', flex: 1 }}>Scoped to {selected.doi}. The model may only cite the numbered records shown below the answer.</span>
              <button type="submit" disabled={asking || question.trim().length < 3}>{asking ? 'Reading evidence…' : 'Ask'}</button>
            </div>
          </form>
          {askErr && <p className="hb-live-error">{askErr}</p>}
          {ask && (
            <div style={{ marginTop: 16 }}>
              {ask.answer ? (
                <div className="hb-ask-answer">
                  <p>{renderAnswer(ask.answer, ask.cited)}</p>
                  <div style={{ fontFamily: MONO, fontSize: 10, color: 'var(--text-subtle)' }}>
                    model {ask.model} · cites {ask.cited.length ? ask.cited.join(', ') : 'nothing'}{ask.note ? ` · ${ask.note}` : ''}
                  </div>
                </div>
              ) : (
                <div className="hb-ask-answer" style={{ borderLeftColor: 'var(--warning)' }}>
                  <p style={{ fontSize: 14 }}>{ask.note || 'No model answer.'} The numbered evidence below is the deterministic result and stands on its own.</p>
                </div>
              )}
              <ol className="hb-ask-evidence" style={{ marginTop: 14 }}>
                {ask.evidence.map((b) => (
                  <li key={b.ref} id={b.ref} className={ask.cited.includes(b.ref) ? 'is-cited' : ''}>
                    <div className="hb-ask-ev-head">
                      <span className="hb-ask-ref">[{b.ref}]</span>
                      <span className="hb-ask-headline">{b.headline}</span>
                      {b.tier !== 'reviewed' && <span className="hb-live-badge">LIVE · UNREVIEWED</span>}
                      <span className="hb-result-chip">{b.lanes} lanes</span>
                    </div>
                    <div className="hb-ask-ev-text">{b.text}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

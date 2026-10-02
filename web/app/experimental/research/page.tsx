'use client';

// EXPERIMENTAL — the one-page UCSF research flow:
//   topic → find papers (Valency / PMC, source shown) → choose an open-access
//   paper → extract live or open an already-ingested copy → progress →
//   LIVE · UNREVIEWED Evidence Records with provenance → ask a question
//   scoped to that paper → cited answer + numbered evidence.
// Nothing here touches the reviewed corpus; every live row is badged.

import { useEffect, useRef, useState } from 'react';

import DatabaseResultCard from '@/components/DatabaseResultCard';
import ExperimentalNav from '@/components/ExperimentalNav';
import { groupResults, type DatabaseResult } from '@/lib/results';

interface Paper {
  title?: string | null; authors?: string[]; abstract?: string | null; doi?: string | null;
  pmcid?: string | null; year?: string | null; venue?: string | null; url?: string | null; source?: string;
  oa_pdf?: boolean; is_oa?: boolean;
  access_status?: 'open_access' | 'no_open_copy_found' | 'unknown' | null;
  access_url?: string | null; access_source?: string | null;
  relevance_status?: 'likely_relevant' | 'possibly_relevant' | 'low_relevance' | 'unknown' | null;
  relevance_score?: number | null; relevance_reason?: string | null;
  pmid?: string | null; journal?: string | null;
}
interface Job {
  job_id: string; doi: string; status: string; message: string; pmcid?: string | null;
  candidates?: number | null; records?: number | null; rows?: number | null; backend?: string | null;
  error?: string | null; created_at: string; updated_at: string;
  access_status?: string | null; access_url?: string | null; access_source?: string | null;
  relevance_status?: string | null; relevance_score?: number | null; relevance_reason?: string | null;
}
interface LivePaper { doi: string; title?: string | null; job_id?: string | null; rows: number; experiments: number; ingested_at?: string | null }
interface Status { model_backend_ready: boolean; model_backend: string; valency_configured: boolean; ingest_db_configured: boolean; live_rows: number | null }
interface Block { ref: string; tier: string; record_id: number; doi: string | null; headline: string; lanes: number; text: string }
interface AskResponse { evidence: Block[]; answer: string | null; cited: string[]; model: string | null; note: string | null }

const STAGES = ['metadata', 'checking_access', 'fetching', 'preprocessing', 'extracting', 'loading', 'done'];
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

function accessLabel(status?: string | null) {
  if (status === 'open_access') return 'Open access';
  if (status === 'no_open_copy_found') return 'Paywalled · Check institutional access';
  return 'Access unknown';
}

function relevanceLabel(status?: string | null) {
  if (status === 'likely_relevant') return 'Likely relevant';
  if (status === 'possibly_relevant') return 'Possibly relevant';
  if (status === 'low_relevance') return 'Low relevance';
  return 'Relevance unknown';
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
  const [rowsErr, setRowsErr] = useState<string | null>(null);
  const [liveErr, setLiveErr] = useState<string | null>(null);
  // Every paper-scoped request (rows, extraction start, job poll, ask) records the
  // sequence number it started with; choosing a paper or starting an extraction
  // bumps it, so a late response never lands on a newer selection.
  const seq = useRef(0);
  const pollFails = useRef(0);

  const refreshLive = () => fetch('/api/experimental/live-papers')
    .then(async (r) => {
      const d = await r.json();
      setLivePapers(d.papers || []);
      setLiveErr(d.error || d.detail || (r.ok ? null : `Backend returned ${r.status}`));
    })
    .catch(() => setLiveErr('request failed'));

  useEffect(() => {
    fetch('/api/experimental/status').then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
    refreshLive();
  }, []);

  // Poll a running job every 2 s; on done, load its rows and refresh the ingested list.
  // A job that can no longer be read (404 after an API restart, backend down) stops the poll with an error.
  useEffect(() => {
    if (!job || job.status === 'done' || job.status === 'failed' || job.status === 'awaiting_full_text') return;
    const started = Date.parse(job.created_at);
    const id = window.setInterval(async () => {
      const my = seq.current;
      setElapsed(Math.round((Date.now() - started) / 1000));
      let j: Job | null = null;
      let fail = 'backend unreachable';
      try {
        const r = await fetch(`/api/experimental/ingest/${job.job_id}`);
        if (r.ok) j = await r.json();
        else fail = r.status === 404 ? 'the job no longer exists (the API may have restarted)' : `backend returned ${r.status}`;
      } catch { /* fail stays 'backend unreachable' */ }
      if (my !== seq.current) return; // another paper was chosen meanwhile
      if (!j) {
        // a 404 is final; ride out a transient 502 / network blip for ~10 s before giving up
        if (fail.startsWith('backend') && ++pollFails.current < 5) return;
        setJob((cur) => cur && { ...cur, status: 'failed', error: `Lost track of this job: ${fail}.` });
        return;
      }
      pollFails.current = 0;
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
    setSources([]);
    try {
      const r = await post('/api/experimental/papers', { query: qq, limit: 8 });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setPapers(d.results || []);
      setSources(d.sources_used || []);
      setSearchErr(d.errors || {});
    } catch (e2) {
      setSearchErr({ search: e2 instanceof Error ? e2.message : 'request failed' });
    } finally {
      setSearching(false);
    }
  }

  // Drop every pending paper-scoped response and clear what it would have filled.
  function invalidate() {
    setRows([]); setRowsLoading(false); setRowsErr(null);
    setAsk(null); setAskErr(null); setAsking(false);
    setStartErr(null);
    return ++seq.current;
  }

  async function loadRows(doi: string) {
    const my = seq.current;
    setRowsLoading(true);
    setRowsErr(null);
    try {
      const r = await post('/api/experimental/search', { query: doi, limit: 500 });
      const d = await r.json();
      if (my !== seq.current) return; // another paper was chosen meanwhile
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setRows(d.results || []);
    } catch (e2) {
      if (my === seq.current) setRowsErr(`Could not load the live records: ${e2 instanceof Error ? e2.message : 'request failed'}`);
    } finally {
      if (my === seq.current) setRowsLoading(false);
    }
  }

  function choose(p: Paper) {
    setSelected(p);
    invalidate();
    setJob(null);
    if (p.doi && ingested(p.doi)) loadRows(p.doi);
  }

  async function extract(doi: string) {
    const my = invalidate();
    try {
      const r = await post('/api/experimental/ingest', {
        doi,
        query: topic,
        title: selected?.title,
        abstract: selected?.abstract,
        authors: selected?.authors,
        journal: selected?.journal || selected?.venue,
        year: selected?.year,
        pmid: selected?.pmid,
        pmcid: selected?.pmcid,
        source: selected?.source,
        access_status: selected?.access_status,
        access_url: selected?.access_url,
        access_source: selected?.access_source,
        relevance_status: selected?.relevance_status,
        relevance_score: selected?.relevance_score,
        relevance_reason: selected?.relevance_reason,
      });
      const d = await r.json();
      if (my !== seq.current) return; // another paper was chosen meanwhile
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setElapsed(0);
      setJob(d);
    } catch (e2) {
      if (my === seq.current) setStartErr(e2 instanceof Error ? e2.message : 'Request failed');
    }
  }

  async function askQuestion(e?: React.FormEvent) {
    e?.preventDefault();
    if (!selected?.doi || question.trim().length < 3) return;
    const my = seq.current;
    setAsking(true);
    setAskErr(null);
    setAsk(null);
    try {
      const r = await post('/api/experimental/ask', { question: question.trim(), doi: selected.doi, include_live: true });
      const d = await r.json();
      if (my !== seq.current) return; // another paper was chosen meanwhile
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      setAsk(d);
    } catch (e2) {
      if (my === seq.current) setAskErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      if (my === seq.current) setAsking(false);
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
          {TOPICS.map((t) => <button key={t} type="button" disabled={searching} onClick={() => findPapers(undefined, t)}>{t}</button>)}
        </div>
        {sources.length > 0 && (
          <p className="hb-live-note">
            Discovery source{sources.length > 1 ? 's' : ''}: <strong>{sources.map((s) => (s === 'valency' ? 'Valency Bond' : 'PubMed Central')).join(' + ')}</strong>
            {Object.keys(searchErr).length ? ` · ${Object.entries(searchErr).map(([k, v]) => `${k}: ${v}`).join('; ')}` : ''}
          </p>
        )}
        {!searching && sources.length === 0 && Object.keys(searchErr).length > 0 && (
          <p className="hb-live-error" role="alert">Paper search failed · {Object.entries(searchErr).map(([k, v]) => `${k}: ${v}`).join('; ')}</p>
        )}
        {liveErr && <p className="hb-live-error" role="alert">Could not list already-extracted papers: {liveErr}</p>}
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
                  <span className="hb-result-chip" style={{ marginLeft: 6 }}>
                    {relevanceLabel(p.relevance_status)}
                  </span>
                  <span className="hb-result-chip" style={{ marginLeft: 6, color: p.access_status === 'open_access' ? 'var(--accent)' : undefined }}>
                    {accessLabel(p.access_status)}
                  </span>
                  {have && <span className="hb-live-badge" style={{ marginLeft: 6 }}>ALREADY EXTRACTED · {have.experiments} exp</span>}
                </div>
                {p.abstract && <p className="hb-live-abstract">{p.abstract.slice(0, 240)}{p.abstract.length > 240 ? '…' : ''}</p>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button type="button" className="hb-evidence-toggle" disabled={!p.doi || busy} onClick={() => choose(p)}>
                    {have ? 'Open extracted evidence' : p.access_status === 'open_access' ? 'Choose this paper' : 'Review paper access'}
                  </button>
                  {p.access_status === 'no_open_copy_found' && p.doi && (
                    <a className="hb-evidence-toggle" href={p.access_url || `https://doi.org/${p.doi}`} target="_blank" rel="noreferrer">
                      Check institutional access
                    </a>
                  )}
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
              <button type="button" onClick={() => selected.doi && extract(selected.doi)} disabled={!selected.doi}>
                {selected.access_status === 'no_open_copy_found' ? 'Save access check' : 'Check access & extract'}
              </button>
              <span className="hb-live-note" style={{ margin: 0, alignSelf: 'center' }}>
                {selected.access_status === 'no_open_copy_found'
                  ? 'HiveBlot will save the metadata and access/relevance flags. If no open copy is available, check your institutional access; scientific extraction will not be fabricated.'
                  : status?.model_backend_ready
                    ? 'Metadata → relevance → access check → open PDF retrieval → panel detection → model extraction → deterministic biology.'
                    : 'Metadata/access checks can still run, but extraction needs a configured model backend.'}
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
          {rowsErr && <p className="hb-live-error" role="alert">{rowsErr}</p>}
          {job && (
            <div className="hb-live-job" style={{ marginTop: 12 }}>
              <div style={{ fontFamily: MONO, fontSize: 12 }}>
                {job.doi}{job.pmcid ? ` · ${job.pmcid}` : ''} · job {job.job_id}{job.backend ? ` · ${job.backend}` : ''} · {elapsed}s
              </div>
              <Stepper status={job.status} />
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                {job.relevance_status && <span className="hb-result-chip">{relevanceLabel(job.relevance_status)}</span>}
                {job.access_status && <span className="hb-result-chip">{accessLabel(job.access_status)}</span>}
              </div>
              <p className={`hb-live-message${job.status === 'failed' ? ' is-error' : ''}`}>{job.error || job.message}</p>
              {job.status === 'awaiting_full_text' && job.access_url && (
                <p><a className="hb-evidence-toggle" href={job.access_url} target="_blank" rel="noreferrer">Check institutional access</a></p>
              )}
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

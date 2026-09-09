'use client';

// EXPERIMENTAL: find a paper (Valency Bond / PubMed Central), extract it
// live through the real HiveBlot pipeline, and browse the result as
// LIVE · UNREVIEWED cards. Nothing here touches the reviewed corpus.

import { useEffect, useRef, useState } from 'react';

import DatabaseResultCard from '@/components/DatabaseResultCard';
import ExperimentalNav from '@/components/ExperimentalNav';
import { groupResults, type DatabaseResult } from '@/lib/results';

interface Paper {
  title?: string | null; authors?: string[]; abstract?: string | null; doi?: string | null;
  year?: string | null; venue?: string | null; url?: string | null; source?: string;
}
interface Job {
  job_id: string; doi: string; status: string; message: string; pmcid?: string | null;
  candidates?: number | null; records?: number | null; rows?: number | null; backend?: string | null;
  error?: string | null; created_at: string; updated_at: string;
}
interface Status {
  model_backend_ready: boolean; model_backend: string; valency_configured: boolean;
  ingest_db_configured: boolean; live_rows: number | null; jobs: Job[];
}

const STAGES = ['fetching', 'preprocessing', 'extracting', 'loading', 'done'];
const MONO = 'var(--font-mono), monospace';

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

export default function LivePage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [query, setQuery] = useState('');
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [searchErr, setSearchErr] = useState<Record<string, string>>({});
  const [searching, setSearching] = useState(false);
  const [doi, setDoi] = useState('');
  const [job, setJob] = useState<Job | null>(null);
  const [startErr, setStartErr] = useState<string | null>(null);
  const [rows, setRows] = useState<DatabaseResult[]>([]);
  const [liveQuery, setLiveQuery] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    fetch('/api/experimental/status').then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
  }, []);

  // Poll the running job every 2 s; stop on a terminal state.
  useEffect(() => {
    if (!job || job.status === 'done' || job.status === 'failed') return;
    const started = Date.parse(job.created_at);
    const id = window.setInterval(async () => {
      setElapsed(Math.round((Date.now() - started) / 1000));
      const r = await fetch(`/api/experimental/ingest/${job.job_id}`);
      if (!r.ok) return;
      const j: Job = await r.json();
      setJob(j);
      if (j.status === 'done') loadLive(j.doi);
    }, 2000);
    timer.current = id;
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.status]);

  async function searchPapers(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setPapers([]);
    try {
      const r = await fetch('/api/experimental/papers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, limit: 8 }) });
      const d = await r.json();
      setPapers(d.results || []);
      setSources(d.sources_used || []);
      setSearchErr(d.errors || {});
    } finally {
      setSearching(false);
    }
  }

  async function startIngest(target: string) {
    setStartErr(null);
    setRows([]);
    const r = await fetch('/api/experimental/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ doi: target }) });
    const d = await r.json();
    if (!r.ok) {
      setStartErr(d.detail || d.error || `Backend returned ${r.status}`);
      return;
    }
    setElapsed(0);
    setJob(d);
  }

  async function loadLive(q: string) {
    setLiveQuery(q);
    const r = await fetch('/api/experimental/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q, limit: 500 }) });
    if (!r.ok) return;
    const d = await r.json();
    setRows(d.results || []);
  }

  const groups = groupResults(rows);

  return (
    <div className="hb-page hb-live">
      <section className="hb-page-hero">
        <div className="hb-live-flag">EXPERIMENTAL · UNREVIEWED OUTPUT</div>
        <h1 className="hb-page-h1">Extract a paper live</h1>
        <p className="hb-page-lead">
          Find an open-access paper, and HiveBlot reads it in front of you: page render, panel detection,
          a model reads each blot panel, deterministic biology reconciles the claims. The result is stored in a
          separate <strong>live, unreviewed</strong> tier and badged as such. It is not part of the reviewed corpus
          and no accuracy claim is attached to it.
        </p>
        <ExperimentalNav />
        {status && (
          <div className="hb-live-status" aria-label="Experimental backend status">
            <span className={status.model_backend_ready ? 'ok' : 'bad'}>model: {status.model_backend}</span>
            <span className={status.valency_configured ? 'ok' : 'warn'}>Valency: {status.valency_configured ? 'connected' : 'not configured (PMC fallback)'}</span>
            <span className={status.ingest_db_configured ? 'ok' : 'bad'}>live store: {status.ingest_db_configured ? 'ready' : 'not configured'}</span>
            <span>live rows: {status.live_rows ?? '—'}</span>
          </div>
        )}
      </section>

      <section className="hb-page-section">
        <h2 className="hb-page-h2">1. Find a paper</h2>
        <form onSubmit={searchPapers} className="hb-live-form" role="search">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. STAT3 phosphorylation hepatocellular carcinoma western blot" aria-label="Paper search" />
          <button type="submit" disabled={searching || !query.trim()}>{searching ? 'Searching…' : 'Search papers'}</button>
        </form>
        {sources.length > 0 && <p className="hb-live-note">Sources: {sources.join(' + ')}{Object.keys(searchErr).length ? ` · errors: ${Object.entries(searchErr).map(([k, v]) => `${k}: ${v}`).join('; ')}` : ''}</p>}
        <ul className="hb-live-papers">
          {papers.map((p, i) => (
            <li key={`${p.doi || p.title}-${i}`}>
              <div className="hb-live-paper-title">{p.title || 'Untitled'}</div>
              <div className="hb-live-paper-meta">
                {(p.authors || []).slice(0, 3).join(', ')}{(p.authors || []).length > 3 ? ' et al.' : ''}
                {p.year ? ` · ${p.year}` : ''}{p.venue ? ` · ${p.venue}` : ''}
                {p.doi ? <> · <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer">{p.doi}</a></> : ' · no DOI'}
                <span className="hb-result-chip" style={{ marginLeft: 8 }}>{p.source}</span>
              </div>
              {p.abstract && <p className="hb-live-abstract">{p.abstract.slice(0, 280)}{p.abstract.length > 280 ? '…' : ''}</p>}
              <button type="button" className="hb-evidence-toggle" disabled={!p.doi || !!(job && job.status !== 'done' && job.status !== 'failed')} onClick={() => p.doi && startIngest(p.doi)}>
                Extract this paper
              </button>
            </li>
          ))}
        </ul>
        <div className="hb-live-form" style={{ marginTop: 18 }}>
          <input value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="…or paste a DOI: 10.3892/br.2026.2108" aria-label="DOI" />
          <button type="button" disabled={!doi.trim() || !!(job && job.status !== 'done' && job.status !== 'failed')} onClick={() => startIngest(doi.trim())}>Extract DOI</button>
        </div>
        {startErr && <p className="hb-live-error">{startErr}</p>}
      </section>

      {job && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">2. Extraction</h2>
          <div className="hb-live-job">
            <div style={{ fontFamily: MONO, fontSize: 12 }}>
              DOI {job.doi}{job.pmcid ? ` · ${job.pmcid}` : ''} · job {job.job_id}{job.backend ? ` · ${job.backend}` : ''} · {elapsed}s
            </div>
            <Stepper status={job.status} />
            <p className={`hb-live-message${job.status === 'failed' ? ' is-error' : ''}`}>{job.error || job.message}</p>
            {job.status === 'done' && (
              <p className="hb-live-note">
                {job.candidates ?? 0} candidate panels · {job.records ?? 0} experiment records · {job.rows ?? 0} lane rows.
                Every value below was produced by the model + deterministic engine without human review.
              </p>
            )}
          </div>
        </section>
      )}

      <section className="hb-page-section">
        <h2 className="hb-page-h2">3. Live results</h2>
        <form className="hb-live-form" onSubmit={(e) => { e.preventDefault(); if (liveQuery.trim()) loadLive(liveQuery.trim()); }} role="search">
          <input value={liveQuery} onChange={(e) => setLiveQuery(e.target.value)} placeholder="Search the live tier (a DOI, a protein, a cell line…)" aria-label="Live tier search" />
          <button type="submit" disabled={!liveQuery.trim()}>Search live tier</button>
        </form>
        {rows.length > 0 && (
          <p className="hb-results-count">Found {groups.length} experiment{groups.length !== 1 ? 's' : ''} ({rows.length} lane record{rows.length !== 1 ? 's' : ''}) in the live tier</p>
        )}
        <div className="hb-result-list">
          {groups.map((g) => (
            <DatabaseResultCard key={g.first.id} data={g.first} lanes={g.lanes} live />
          ))}
        </div>
      </section>
    </div>
  );
}

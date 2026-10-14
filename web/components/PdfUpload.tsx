'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { normalizeDoi } from '@/lib/storedPaper';
import { authConfig } from '@/lib/supabase/config';
import { createClient } from '@/lib/supabase/client';

type Job = { job_id?: string; doi?: string; status: string; message?: string; error?: string; rows?: number };

export function PdfUpload({ initialDoi = '' }: { initialDoi?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const xhr = useRef<XMLHttpRequest | null>(null);
  const [doi, setDoi] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [rights, setRights] = useState(false);
  const [sending, setSending] = useState(false);
  const [progress, setProgress] = useState(0);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [needsAccess, setNeedsAccess] = useState(false);
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [signingIn, setSigningIn] = useState(false);
  const active = !!job && !['done', 'failed', 'awaiting_full_text'].includes(job.status);
  const jobId = job?.job_id;

  useEffect(() => () => xhr.current?.abort(), []);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('upload') === 'pdf') {
      const frame = requestAnimationFrame(() => {
        setDoi(normalizeDoi(params.get('upload_doi') || ''));
        dialog.current?.showModal();
      });
      return () => cancelAnimationFrame(frame);
    }
  }, []);
  useEffect(() => {
    if (!active || !jobId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    let failures = 0;
    async function poll() {
      try {
        const response = await fetch(`/api/experimental/ingest/${jobId}`, { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error(`Status unavailable (${response.status}).`);
        const next = await response.json();
        if (stopped) return;
        failures = 0; setError(''); setJob(next);
        if (['done', 'failed', 'awaiting_full_text'].includes(next.status)) return;
      } catch (e) {
        if (stopped) return;
        failures++;
        if (failures >= 31) { setError('Status is unavailable. Your job may still be running. Retry status to reconnect.'); return; }
        setError(e instanceof Error ? e.message + ' Reconnecting...' : 'Reconnecting...');
      }
      timer = setTimeout(poll, 3000);
    }
    timer = setTimeout(poll, 1000);
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [active, jobId, retry]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = normalizeDoi(doi);
    if (!normalized) { setError('Enter a valid DOI.'); return; }
    if (!file || !/\.pdf$/i.test(file.name) || (file.type && file.type !== 'application/pdf')) { setError('Select a PDF file.'); return; }
    if (!file.size || file.size > 50 * 1024 * 1024) { setError('Select a nonempty PDF, 50 MB or smaller.'); return; }
    if (!rights) { setError('Confirm your permission to upload this PDF.'); return; }
    setSending(true); setError(''); setNeedsAccess(false); setNeedsSignIn(false); setProgress(0); setJob(null); setDoi(normalized);
    try {
      const response = await fetch('/api/experimental/upload', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ doi: normalized }),
      });
      const ticket = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          setNeedsAccess(ticket.error === 'Beta access code required');
          setNeedsSignIn(ticket.error !== 'Beta access code required');
        }
        throw new Error(typeof ticket.detail === 'string' ? ticket.detail : ticket.error || 'Upload authorization failed.');
      }
      const result = await new Promise<Job>((resolve, reject) => {
        const request = new XMLHttpRequest();
        xhr.current = request;
        request.open('POST', ticket.upload_url);
        request.setRequestHeader('Authorization', `Bearer ${ticket.token}`);
        request.setRequestHeader('Content-Type', 'application/pdf');
        request.setRequestHeader('X-Pdf-Rights', 'confirmed');
        request.timeout = 180000;
        request.upload.onprogress = e => { if (e.lengthComputable) setProgress(Math.round(e.loaded / e.total * 100)); };
        request.onload = () => {
          try {
            const data = JSON.parse(request.responseText);
            if (request.status < 200 || request.status >= 300) throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload failed.');
            resolve(data);
          } catch (e) { reject(e); }
        };
        request.onerror = () => reject(new Error('Could not reach the upload service. Check your connection and retry.'));
        request.ontimeout = () => reject(new Error('Upload timed out. Check stored evidence before retrying.'));
        request.onabort = () => reject(new Error('Upload canceled.'));
        request.send(file);
      });
      setJob(result);
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed.'); }
    finally { setSending(false); xhr.current = null; }
  }

  function evidenceUrl() {
    const params = new URLSearchParams({ doi: job?.doi || doi });
    const lab = new URLSearchParams(window.location.search).get('lab');
    if (lab) params.set('lab', lab);
    return `/experimental/research?${params}`;
  }

  function resumePath() {
    const url = new URL(window.location.href);
    url.searchParams.delete('access');
    url.searchParams.set('upload', 'pdf');
    url.searchParams.set('upload_doi', normalizeDoi(doi));
    return url.pathname + url.search;
  }

  async function signIn() {
    setSigningIn(true);
    try {
      const result = await createClient().auth.signInWithOAuth({ provider: 'google', options: {
        redirectTo: `${window.location.origin}/auth/callback?${new URLSearchParams({ next: resumePath() })}`,
      } });
      if (result.error) throw result.error;
    } catch { setError('Could not sign in. Please retry.'); }
    finally { setSigningIn(false); }
  }

  return <>
    <button className="hb-upload-button" type="button" onClick={() => {
      if (!sending && !active && !job) setDoi(normalizeDoi(initialDoi));
      dialog.current?.showModal();
    }}><Upload size={16} aria-hidden="true" />Upload PDF</button>
    <dialog className="hb-upload-dialog" ref={dialog} aria-labelledby="pdf-upload-title">
      <header><h2 id="pdf-upload-title">Upload a paper</h2>
        <button type="button" title="Close upload" aria-label="Close upload" onClick={() => dialog.current?.close()}><X size={20} aria-hidden="true" /></button></header>
      <form onSubmit={submit}>
        <label>DOI<input value={doi} onChange={e => setDoi(e.target.value)} placeholder="10.1234/example" required disabled={sending || active} /></label>
        <label>PDF <span>(maximum 50 MB)</span><input type="file" accept="application/pdf,.pdf" disabled={sending || active} onChange={e => { setFile(e.target.files?.[0] || null); setError(''); }} required /></label>
        <label className="hb-upload-rights"><input type="checkbox" checked={rights} disabled={sending || active} onChange={e => setRights(e.target.checked)} required />This PDF is open access or my own paper, and I have permission to process it.</label>
        {sending && <div role="status"><p>{progress < 100 ? `Uploading PDF (${progress}%)` : 'Validating PDF...'}</p><progress value={progress} max={100} /></div>}
        {job && <div role="status" className="hb-upload-status"><strong>{job.status === 'done' ? 'Completed' : job.status === 'failed' ? 'Extraction failed' : 'Processing'}</strong><p>{job.error || job.message}</p>
          {job.status === 'done' && !!job.rows && <a className="hb-upload-button" href={evidenceUrl()}>Open extracted evidence</a>}
          {job.status === 'done' && !job.rows && <p>No Western blot evidence was extracted from this PDF.</p>}</div>}
        {error && <p role="alert" className="hb-upload-error">{error}</p>}
        {needsAccess && <a className="hb-upload-button" href={`/access?${new URLSearchParams({ next: resumePath() })}`}>Enter beta access code</a>}
        {needsSignIn && <button type="button" className="hb-upload-button" disabled={!authConfig() || signingIn} onClick={signIn}
          title={!authConfig() ? 'Google sign-in is not configured in this preview' : undefined}>{signingIn ? 'Signing in...' : 'Continue with Google'}</button>}
        {needsSignIn && !authConfig() && <p>Google sign-in is not configured in this local preview.</p>}
        {active && error && <button className="hb-upload-button" type="button" onClick={() => setRetry(v => v + 1)}>Retry status</button>}
        <footer><button className="hb-upload-button" type="submit" disabled={sending || signingIn || active || !file || !rights}>Upload and extract</button></footer>
      </form>
    </dialog>
  </>;
}

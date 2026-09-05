'use client';

// EXPERIMENTAL densitometry: pick a reviewed record's crop (or upload an
// image), draw a box around ONE blot strip, get relative integrated
// intensities per lane. Uncalibrated by construction; nothing is stored.

import { useRef, useState } from 'react';

import ExperimentalNav from '@/components/ExperimentalNav';

interface Lane { index: number; x0: number; x1: number; raw: number; background: number; corrected: number; relative: number; saturated_fraction: number }
interface Result {
  image: { width: number; height: number; inverted_for_analysis: boolean; region: number[] | null };
  band_row: [number, number]; rows_detected: number[][]; lanes: Lane[]; warnings: string[]; disclaimer: string;
  source: { record_id?: number; tier?: string; target?: string; crop?: string; printed_lanes?: number | null; upload?: boolean };
  lanes_requested: number | null;
}

const MONO = 'var(--font-mono), monospace';

export default function DensitometryPage() {
  const [recordId, setRecordId] = useState('');
  const [live, setLive] = useState(false);
  const [lanes, setLanes] = useState('');
  const [rowIndex, setRowIndex] = useState(0);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [upload, setUpload] = useState<string | null>(null);
  const [region, setRegion] = useState<number[] | null>(null);
  const [drag, setDrag] = useState<number[] | null>(null);
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // displayed-pixels per natural-pixel, captured in event handlers (never
  // read from the ref during render)
  const [scale, setScale] = useState<{ sx: number; sy: number } | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  function captureScale() {
    const el = imgRef.current;
    if (el && el.naturalWidth) setScale({ sx: el.clientWidth / el.naturalWidth, sy: el.clientHeight / el.naturalHeight });
  }

  function loadRecord() {
    if (!/^\d+$/.test(recordId.trim())) return;
    setUpload(null);
    setRegion(null);
    setRes(null);
    setImgSrc(`${live ? '/api/experimental/record' : '/api/record'}/${recordId.trim()}/crop?t=${Date.now()}`);
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result);
      setUpload(url);
      setImgSrc(url);
      setRegion(null);
      setRes(null);
    };
    reader.readAsDataURL(f);
  }

  // Map a mouse position on the displayed image to natural-image pixels.
  function toImage(e: React.MouseEvent<HTMLImageElement>): [number, number] {
    const el = imgRef.current!;
    const r = el.getBoundingClientRect();
    const sx = el.naturalWidth / r.width;
    const sy = el.naturalHeight / r.height;
    return [Math.round((e.clientX - r.left) * sx), Math.round((e.clientY - r.top) * sy)];
  }

  async function analyze() {
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const body: Record<string, unknown> = { lanes: lanes ? Number(lanes) : null, row_index: rowIndex, region };
      if (upload) body.image_base64 = upload;
      else { body.record_id = Number(recordId); body.live = live; }
      const r = await fetch('/api/experimental/densitometry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || `Backend returned ${r.status}`);
      captureScale();
      setRes(d);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  const overlay = res && scale ? scale : null;

  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <div className="hb-live-flag">EXPERIMENTAL · UNCALIBRATED · NOT STORED</div>
        <h1 className="hb-page-h1">Densitometry on a published panel</h1>
        <p className="hb-page-lead">
          Integrated band darkness per lane, background-subtracted, relative to the strongest lane in the
          <strong> same image</strong>. A figure crop is not raw data: exposure, saturation and re-encoding are unknown,
          so treat this as a reading aid, never as a quantification. HiveBlot Evidence Records keep only categorical
          band presence; nothing from this page is written anywhere.
        </p>
        <ExperimentalNav />
      </section>

      <section className="hb-page-section">
        <h2 className="hb-page-h2">1. Pick a panel</h2>
        <div className="hb-live-form">
          <input value={recordId} onChange={(e) => setRecordId(e.target.value)} placeholder="Record id (from a search card's evidence panel), e.g. 1200" aria-label="Record id" />
          <label className="hb-ask-check"><input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} /> live tier</label>
          <button type="button" onClick={loadRecord} disabled={!/^\d+$/.test(recordId.trim())}>Load crop</button>
        </div>
        <p className="hb-live-note">…or upload a panel image: <input type="file" accept="image/png,image/jpeg" onChange={onFile} /></p>
      </section>

      {imgSrc && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">2. Draw a box around one blot strip</h2>
          <p className="hb-live-note">Click the top-left corner, then the bottom-right corner of the strip you want (exclude printed labels). Leave it unboxed to let the detector pick the strongest non-text row.</p>
          <div className="hb-dens-stage">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={imgSrc}
              alt="Panel"
              className="hb-dens-image"
              onLoad={captureScale}
              onClick={(e) => {
                const [x, y] = toImage(e);
                if (!drag) { setDrag([x, y]); setRegion(null); }
                else { setRegion([drag[0], drag[1], x, y]); setDrag(null); }
              }}
            />
            {overlay && res && (
              <svg className="hb-dens-overlay" aria-hidden="true">
                <rect x={0} y={res.band_row[0] * overlay.sy} width="100%" height={(res.band_row[1] - res.band_row[0]) * overlay.sy} className="hb-dens-row" />
                {res.lanes.map((l) => (
                  <g key={l.index}>
                    <rect x={l.x0 * overlay.sx} y={res.band_row[0] * overlay.sy} width={(l.x1 - l.x0) * overlay.sx} height={(res.band_row[1] - res.band_row[0]) * overlay.sy} className="hb-dens-lane" />
                    <text x={(l.x0 + (l.x1 - l.x0) / 2) * overlay.sx} y={res.band_row[0] * overlay.sy - 4} textAnchor="middle" className="hb-dens-label">{l.index}</text>
                  </g>
                ))}
              </svg>
            )}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: 'var(--text-subtle)', marginTop: 6 }}>
            {drag ? `first corner at (${drag[0]}, ${drag[1]}) — click the opposite corner` : region ? `region ${region.join(', ')}` : 'no region selected'}
            {region && <button type="button" className="hb-search-clear" style={{ marginLeft: 8 }} onClick={() => setRegion(null)} aria-label="Clear region">×</button>}
          </div>
          <div className="hb-live-form" style={{ marginTop: 12 }}>
            <input value={lanes} onChange={(e) => setLanes(e.target.value.replace(/\D/g, ''))} placeholder="Printed lane count (recommended)" aria-label="Lane count" style={{ maxWidth: 260 }} />
            <input value={rowIndex} onChange={(e) => setRowIndex(Number(e.target.value.replace(/\D/g, '') || 0))} placeholder="Row index" aria-label="Row index" style={{ maxWidth: 120 }} />
            <button type="button" onClick={analyze} disabled={busy}>{busy ? 'Measuring…' : 'Measure'}</button>
          </div>
          {err && <p className="hb-live-error">{err}</p>}
        </section>
      )}

      {res && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">3. Relative intensity (this image only)</h2>
          <table className="hb-dens-table">
            <thead><tr><th>lane</th><th>relative</th><th>corrected</th><th>background</th><th>saturated</th><th></th></tr></thead>
            <tbody>
              {res.lanes.map((l) => (
                <tr key={l.index}>
                  <td style={{ fontFamily: MONO }}>{l.index}</td>
                  <td style={{ fontFamily: MONO }}>{l.relative.toFixed(2)}</td>
                  <td style={{ fontFamily: MONO }}>{Math.round(l.corrected).toLocaleString()}</td>
                  <td style={{ fontFamily: MONO }}>{Math.round(l.background).toLocaleString()}</td>
                  <td style={{ fontFamily: MONO, color: l.saturated_fraction > 0.01 ? 'var(--error)' : undefined }}>{(l.saturated_fraction * 100).toFixed(1)}%</td>
                  <td style={{ width: '40%' }}><div className="hb-dens-bar" style={{ width: `${Math.max(2, l.relative * 100)}%` }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {res.warnings.length > 0 && (
            <ul className="hb-page-list" style={{ color: 'var(--warning)', marginTop: 12 }}>
              {res.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          <p className="hb-live-note">
            {res.source.record_id != null ? `record ${res.source.record_id} (${res.source.tier}) · ${res.source.target ?? ''} · ${res.source.crop ?? ''} · printed lanes ${res.source.printed_lanes ?? 'unknown'} · ` : 'uploaded image · '}
            band row y {res.band_row[0]}–{res.band_row[1]} · {res.rows_detected.length} row(s) detected · {res.image.inverted_for_analysis ? 'dark bands on light background' : 'light bands on dark background'}
          </p>
          <p className="hb-live-note" style={{ color: 'var(--warning)' }}>{res.disclaimer}</p>
        </section>
      )}
    </div>
  );
}

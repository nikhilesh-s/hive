'use client';

// EXPERIMENTAL densitometry: pick a reviewed record's crop (or upload an
// image), drag a box around ONE blot strip, place lane dividers inside it,
// get background-corrected integrated intensities relative to the strongest
// lane in the same image. Uncalibrated by construction; nothing is stored.

import { useEffect, useRef, useState } from 'react';

import ExperimentalNav from '@/components/ExperimentalNav';

type Quality = 'ok' | 'warning' | 'quantification_refused';
interface Stability { relative_min: number; relative_median: number; relative_max: number }
interface Lane {
  index: number; label: string | null; x0: number; x1: number; y0: number; y1: number;
  raw: number; background: number; corrected: number; relative: number | null; clipped_fraction: number;
  quality: Quality; reasons: string[]; stability: Stability | null;
}
interface Result {
  method: { name: string; version: string; steps: string; params: Record<string, number | string> };
  image: { width: number; height: number; inverted_for_analysis: boolean; region: number[] | null };
  band_row: [number, number]; rows_detected: number[][];
  lane_mode: 'explicit' | 'equal_width' | 'auto';
  lanes: Lane[];
  quality: { state: Quality; reasons: string[] };
  stability: { perturbation_px: { x: number; y: number }; runs: number; ranking_stable: boolean } | null;
  warnings: string[]; disclaimer: string;
  source: { record_id?: number; tier?: string; target?: string; crop?: string; printed_lanes?: number | null; upload?: boolean };
  lanes_requested: number | null; stored: boolean;
}
type Box = [number, number, number, number];
type Pt = [number, number];

const MONO = 'var(--font-mono), monospace';
const QUALITY_LABEL: Record<Quality, string> = {
  ok: 'Valid within-image relative measurement',
  warning: 'Warning — read the caveats',
  quantification_refused: 'Quantification refused',
};
const QUALITY_CLASS: Record<Quality, string> = { ok: 'is-ok', warning: 'is-warning', quantification_refused: 'is-refused' };

function laneBounds(region: Box, dividers: number[]): [number, number][] {
  const xs = [region[0], ...dividers, region[2]];
  return xs.slice(1).map((x, i) => [xs[i], x] as [number, number]);
}
function seedDividers(region: Box, n: number): number[] {
  const w = region[2] - region[0];
  return Array.from({ length: Math.max(0, n - 1) }, (_, i) => Math.round(region[0] + (w * (i + 1)) / n));
}
function csvCell(v: unknown): string {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function download(name: string, type: string, text: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
const stamp = () => new Date().toISOString().replace(/[:.]/g, '-');
const relText = (l: Lane) => l.relative == null ? '—' : l.stability ? `${l.stability.relative_min.toFixed(1)}–${l.stability.relative_max.toFixed(1)}` : l.relative.toFixed(2);
const relBar = (l: Lane) => l.relative == null ? null : l.stability ? l.stability.relative_median : l.relative;

export default function DensitometryPage() {
  const [recordId, setRecordId] = useState('');
  const [live, setLive] = useState(false);
  const [rowIndex, setRowIndex] = useState(0);
  const [stability, setStability] = useState(true);
  const [diagnostic, setDiagnostic] = useState(false);
  const [laneCount, setLaneCount] = useState('');
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [upload, setUpload] = useState<string | null>(null);
  // natural size + displayed-per-natural scale, captured in handlers (never read from the ref during render)
  const [dims, setDims] = useState<{ w: number; h: number; sx: number } | null>(null);
  const [region, setRegion] = useState<Box | null>(null);
  const [draft, setDraft] = useState<Box | null>(null);
  const [dividers, setDividers] = useState<number[]>([]);
  const [labels, setLabels] = useState<string[]>([]);
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const ptr = useRef<{ kind: 'box' | 'divider'; idx: number; start: Pt; client: Pt; moved: boolean } | null>(null);

  function captureDims() {
    const el = imgRef.current;
    if (el && el.naturalWidth) setDims({ w: el.naturalWidth, h: el.naturalHeight, sx: el.clientWidth / el.naturalWidth });
  }
  useEffect(() => {
    window.addEventListener('resize', captureDims);
    return () => window.removeEventListener('resize', captureDims);
  }, []);

  function resetGeometry() {
    setRegion(null); setDraft(null); setDividers([]); setLabels([]); setRes(null); setErr(null);
  }

  function loadRecord() {
    if (!/^\d+$/.test(recordId.trim())) return;
    setUpload(null);
    resetGeometry();
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
      resetGeometry();
    };
    reader.readAsDataURL(f);
  }

  // Map a pointer position on the displayed image to natural-image pixels (clamped).
  function toImage(clientX: number, clientY: number): Pt {
    const el = imgRef.current!;
    const r = el.getBoundingClientRect();
    const x = Math.round(((clientX - r.left) / r.width) * el.naturalWidth);
    const y = Math.round(((clientY - r.top) / r.height) * el.naturalHeight);
    return [Math.min(el.naturalWidth, Math.max(0, x)), Math.min(el.naturalHeight, Math.max(0, y))];
  }

  function applyRegion(a: Pt, b: Pt) {
    const box: Box = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
    if (box[2] - box[0] < 4 || box[3] - box[1] < 4) return;
    setRegion(box);
    const n = Number(laneCount) || 0;
    setDividers(n > 1 ? seedDividers(box, n) : []);
    setLabels([]);
    setRes(null);
  }

  function onLaneCount(v: string) {
    const digits = v.replace(/\D/g, '');
    setLaneCount(digits);
    if (region) { setDividers(Number(digits) > 1 ? seedDividers(region, Number(digits)) : []); setRes(null); }
  }

  const inRegion = (p: Pt) => !!region && p[0] > region[0] && p[0] < region[2] && p[1] >= region[1] && p[1] <= region[3];
  function nearestDivider(p: Pt): number {
    if (!region || !dims || !inRegion(p)) return -1;
    const tol = 6 / dims.sx;
    let best = -1, bestD = tol;
    dividers.forEach((d, i) => { const dd = Math.abs(d - p[0]); if (dd <= bestD) { best = i; bestD = dd; } });
    return best;
  }

  function onPointerDown(e: React.PointerEvent<HTMLImageElement>) {
    if (!imgRef.current || e.button !== 0) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    const p = toImage(e.clientX, e.clientY);
    const idx = nearestDivider(p);
    ptr.current = { kind: idx >= 0 ? 'divider' : 'box', idx, start: p, client: [e.clientX, e.clientY], moved: false };
  }
  function onPointerMove(e: React.PointerEvent<HTMLImageElement>) {
    const s = ptr.current;
    if (!s) return;
    if (!s.moved && Math.hypot(e.clientX - s.client[0], e.clientY - s.client[1]) < 3) return;
    s.moved = true;
    const p = toImage(e.clientX, e.clientY);
    if (s.kind === 'box') {
      setDraft([Math.min(s.start[0], p[0]), Math.min(s.start[1], p[1]), Math.max(s.start[0], p[0]), Math.max(s.start[1], p[1])]);
    } else if (region) {
      const lo = (s.idx > 0 ? dividers[s.idx - 1] : region[0]) + 1;
      const hi = (s.idx < dividers.length - 1 ? dividers[s.idx + 1] : region[2]) - 1;
      const x = Math.min(hi, Math.max(lo, p[0]));
      setDividers((d) => d.map((v, i) => (i === s.idx ? x : v)));
      setRes(null);
    }
  }
  function onPointerUp(e: React.PointerEvent<HTMLImageElement>) {
    const s = ptr.current;
    ptr.current = null;
    setDraft(null);
    if (!s) return;
    const p = toImage(e.clientX, e.clientY);
    if (s.kind === 'box') {
      if (s.moved) applyRegion(s.start, p);
      else if (inRegion(p)) { setDividers((d) => [...d, p[0]].sort((a, b) => a - b)); setRes(null); }
    } else if (!s.moved) {
      setDividers((d) => d.filter((_, i) => i !== s.idx));
      setLabels((l) => l.filter((_, i) => i !== s.idx + 1));
      setRes(null);
    }
  }

  const bounds = region ? laneBounds(region, dividers) : [];
  const canMeasure = !!imgSrc && !busy && (diagnostic || !!region);

  async function analyze() {
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const anyLabel = labels.some((l) => l.trim());
      const body: Record<string, unknown> = {
        region,
        lane_bounds: diagnostic ? null : bounds,
        lane_labels: diagnostic || !anyLabel ? null : bounds.map((_, i) => (labels[i] ?? '').trim()),
        lanes: diagnostic ? Number(laneCount) || null : null,
        row_index: rowIndex,
        stability,
      };
      if (upload) body.image_base64 = upload;
      else { body.record_id = Number(recordId); body.live = live; }
      const r = await fetch('/api/experimental/densitometry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) {
        const detail = d.detail ?? d.error;
        throw new Error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `Backend returned ${r.status}`);
      }
      captureDims();
      setRes(d);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  function exportJson() {
    if (!res) return;
    download(`hiveblot-densitometry-${stamp()}.json`, 'application/json', JSON.stringify({ ...res, exported_at: new Date().toISOString(), page: '/experimental/densitometry' }, null, 2));
  }
  function exportCsv() {
    if (!res) return;
    const head = `# ${res.method.name} v${res.method.version}; region=${res.image.region?.join(' ') ?? 'none'}; band_row=${res.band_row.join(' ')}; quality=${res.quality.state}`;
    const cols = 'index,label,x0,x1,y0,y1,raw,background,corrected,relative,relative_min,relative_median,relative_max,clipped_fraction,quality,reasons';
    const rows = res.lanes.map((l) => [
      l.index, l.label, l.x0, l.x1, l.y0, l.y1, l.raw, l.background, l.corrected, l.relative,
      l.stability?.relative_min, l.stability?.relative_median, l.stability?.relative_max, l.clipped_fraction, l.quality, l.reasons.join('; '),
    ].map(csvCell).join(','));
    download(`hiveblot-densitometry-${stamp()}.csv`, 'text/csv', [head, cols, ...rows].join('\n') + '\n');
  }

  const refused = res?.quality.state === 'quantification_refused';
  const fs = dims ? 11 / dims.sx : 11; // 11 displayed px, expressed in natural units for the viewBox overlay
  const band = res ? [res.image.region?.[0] ?? 0, res.image.region?.[2] ?? res.image.width] : null;

  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <div className="hb-live-flag">EXPERIMENTAL · UNCALIBRATED · NOT STORED</div>
        <h1 className="hb-page-h1">Experimental densitometry</h1>
        <p className="hb-page-lead">
          Pixel-derived, background-corrected band intensity per lane, relative to the strongest lane in the
          <strong> same image</strong>. No units, not a protein amount, not comparable across images, not
          loading-control normalized. A figure crop is not raw data: exposure, clipping and re-encoding are unknown,
          so treat this as a reading aid, never as a quantification. Nothing from this page is stored anywhere.
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
          <h2 className="hb-page-h2">2. Box one blot strip, then place lane dividers</h2>
          <p className="hb-live-note">
            Drag a rectangle around the strip you want (exclude printed labels). Then set a lane count to seed equal dividers,
            click inside the box to add a divider, click a divider to remove it, or drag one to move it.
          </p>
          <div className="hb-dens-stage">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={imgSrc}
              alt="Panel"
              className="hb-dens-image"
              draggable={false}
              onLoad={captureDims}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={() => { ptr.current = null; setDraft(null); }}
            />
            {dims && (
              <svg className="hb-dens-overlay" viewBox={`0 0 ${dims.w} ${dims.h}`} preserveAspectRatio="none" aria-hidden="true">
                {res ? (
                  <>
                    {res.image.region && <rect x={res.image.region[0]} y={res.image.region[1]} width={res.image.region[2] - res.image.region[0]} height={res.image.region[3] - res.image.region[1]} className="hb-dens-region" />}
                    {band && <rect x={band[0]} y={res.band_row[0]} width={band[1] - band[0]} height={res.band_row[1] - res.band_row[0]} className="hb-dens-row" />}
                    {res.lanes.map((l) => (
                      <g key={l.index}>
                        <rect x={l.x0} y={l.y0} width={l.x1 - l.x0} height={l.y1 - l.y0} className={`hb-dens-lane ${QUALITY_CLASS[l.quality]}`} />
                        <text x={l.x0 + (l.x1 - l.x0) / 2} y={l.y0 + fs + 2} fontSize={fs} textAnchor="middle" className={`hb-dens-label ${QUALITY_CLASS[l.quality]}`}>{l.label || l.index}</text>
                      </g>
                    ))}
                  </>
                ) : (
                  <>
                    {draft && <rect x={draft[0]} y={draft[1]} width={draft[2] - draft[0]} height={draft[3] - draft[1]} className="hb-dens-draft" />}
                    {region && <rect x={region[0]} y={region[1]} width={region[2] - region[0]} height={region[3] - region[1]} className="hb-dens-region" />}
                    {region && dividers.map((d, i) => <line key={i} x1={d} x2={d} y1={region[1]} y2={region[3]} className="hb-dens-divider" />)}
                    {region && bounds.map(([x0, x1], i) => (
                      <text key={i} x={x0 + (x1 - x0) / 2} y={region[1] + fs + 2} fontSize={fs} textAnchor="middle" className="hb-dens-label">{labels[i]?.trim() || i + 1}</text>
                    ))}
                  </>
                )}
              </svg>
            )}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: 'var(--text-subtle)', marginTop: 6 }}>
            {region ? `region ${region.join(', ')} · ${bounds.length} lane(s)` : 'no region — drag a box on the image'}
            {region && <button type="button" className="hb-search-clear" style={{ marginLeft: 8 }} onClick={resetGeometry} aria-label="Clear region">×</button>}
          </div>

          <div className="hb-dens-controls">
            <label className="hb-ask-check">Lane count <input value={laneCount} onChange={(e) => onLaneCount(e.target.value)} placeholder="e.g. 6" aria-label="Lane count" inputMode="numeric" /></label>
            <label className="hb-ask-check">Row index <input value={rowIndex} onChange={(e) => setRowIndex(Number(e.target.value.replace(/\D/g, '') || 0))} aria-label="Row index" inputMode="numeric" /></label>
            <label className="hb-ask-check"><input type="checkbox" checked={stability} onChange={(e) => setStability(e.target.checked)} /> stability study</label>
            <label className="hb-ask-check"><input type="checkbox" checked={diagnostic} onChange={(e) => setDiagnostic(e.target.checked)} /> auto / equal-width lanes (diagnostic only)</label>
          </div>
          {region && !diagnostic && bounds.length > 0 && (
            <div className="hb-dens-labels">
              {bounds.map((_, i) => (
                <label key={i}>{i + 1}<input value={labels[i] ?? ''} onChange={(e) => setLabels((l) => { const n = bounds.map((__, j) => l[j] ?? ''); n[i] = e.target.value; return n; })} placeholder="label" aria-label={`Lane ${i + 1} label`} maxLength={24} /></label>
              ))}
            </div>
          )}
          {diagnostic && <p className="hb-live-note" style={{ color: 'var(--warning)' }}>Diagnostic mode: lanes are sliced equal-width from the box (or auto-detected without a box) instead of using your dividers. Lane geometry is a guess; do not report these numbers.</p>}
          <div className="hb-live-form" style={{ marginTop: 12 }}>
            <button type="button" onClick={analyze} disabled={!canMeasure}>{busy ? 'Measuring…' : 'Measure'}</button>
          </div>
          {err && <p className="hb-live-error">{err}</p>}
        </section>
      )}

      {res && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">3. Relative intensity (this image only)</h2>
          <div className={`hb-dens-quality ${QUALITY_CLASS[res.quality.state]}`}>
            <h3>{QUALITY_LABEL[res.quality.state]}</h3>
            {res.quality.reasons.length > 0 && <ul className="hb-page-list">{res.quality.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
            <p className="hb-live-note">
              {res.method.name} v{res.method.version} · lanes: {res.lane_mode} · band row y {res.band_row[0]}–{res.band_row[1]} · {res.rows_detected.length} row(s) detected ·{' '}
              {res.image.inverted_for_analysis ? 'dark bands on light background' : 'light bands on dark background'}
              {res.stability && ` · stability: ±${res.stability.perturbation_px.x}px lanes / ±${res.stability.perturbation_px.y}px row × ${res.stability.runs} runs, ranking ${res.stability.ranking_stable ? 'stable' : 'UNSTABLE'}`}
            </p>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="hb-dens-table">
              <thead>
                <tr>
                  <th>lane</th><th>label</th>{!refused && <th>relative</th>}<th>corrected</th><th>background</th><th>clipped</th><th>quality</th>{!refused && <th></th>}
                </tr>
              </thead>
              <tbody>
                {res.lanes.map((l) => {
                  const bar = relBar(l);
                  return (
                    <tr key={l.index}>
                      <td style={{ fontFamily: MONO }}>{l.index}</td>
                      <td style={{ fontFamily: MONO }}>{l.label ?? ''}</td>
                      {!refused && <td style={{ fontFamily: MONO, whiteSpace: 'nowrap' }}>{relText(l)}</td>}
                      <td style={{ fontFamily: MONO }}>{Math.round(l.corrected).toLocaleString()}</td>
                      <td style={{ fontFamily: MONO }}>{Math.round(l.background).toLocaleString()}</td>
                      <td style={{ fontFamily: MONO, color: l.clipped_fraction > 0.02 ? 'var(--error)' : undefined }}>{(l.clipped_fraction * 100).toFixed(1)}%</td>
                      <td>
                        <span className={`hb-dens-q ${QUALITY_CLASS[l.quality]}`}>{l.quality === 'quantification_refused' ? 'refused' : l.quality}</span>
                        {l.reasons.length > 0 && <span className="hb-dens-reasons"> {l.reasons.join('; ')}</span>}
                      </td>
                      {!refused && <td style={{ width: '30%' }}>{bar != null && <div className="hb-dens-bar" style={{ width: `${Math.max(2, Math.min(100, bar * 100))}%` }} />}</td>}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="hb-live-note">
            {!refused && 'Relative = corrected ÷ strongest lane. A range means min–max across geometry perturbations; the bar is the median. '}
            Clipped = fraction of pixels at the sensor/encoding limit (red above 2%).
          </p>
          {res.warnings.length > 0 && (
            <ul className="hb-page-list" style={{ color: 'var(--warning)', marginTop: 12 }}>
              {res.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          <div className="hb-live-form" style={{ marginTop: 12 }}>
            <button type="button" onClick={exportJson}>Export JSON</button>
            <button type="button" onClick={exportCsv}>Export CSV</button>
          </div>
          <p className="hb-live-note">
            {res.source.record_id != null ? `record ${res.source.record_id} (${res.source.tier}) · ${res.source.target ?? ''} · ${res.source.crop ?? ''} · printed lanes ${res.source.printed_lanes ?? 'unknown'}` : 'uploaded image'}
            {' · '}nothing stored
          </p>
          <p className="hb-live-note" style={{ color: 'var(--warning)' }}>{res.disclaimer}</p>
        </section>
      )}
    </div>
  );
}

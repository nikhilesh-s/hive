'use client';

// EXPERIMENTAL densitometry: pick a reviewed record's crop (or upload an
// image), drag a box around ONE blot strip, place lane dividers inside it,
// get background-corrected integrated intensities relative to the strongest
// lane in the same image. Uncalibrated by construction; nothing is stored.

import { useEffect, useRef, useState } from 'react';

import ExperimentalNav from '@/components/ExperimentalNav';

type Quality = 'ok' | 'warning' | 'quantification_refused';
interface Stability { relative_min: number; relative_median: number; relative_max: number }
interface Profile { y0: number; values: number[]; flank: [number, number][] }
interface Lane {
  index: number; label: string | null; x0: number; x1: number; y0: number; y1: number;
  raw: number; background: number; corrected: number; relative: number | null; clipped_fraction: number;
  flank_baseline?: number; flank_rows?: number; profile?: Profile;
  quality: Quality; reasons: string[]; stability: Stability | null;
}
interface Result {
  method: { name: string; version: string; steps: string; params: Record<string, number | string> };
  image: { width: number; height: number; inverted_for_analysis: boolean; region: number[] | null };
  band_row: [number, number]; rows_detected: number[][]; rows_text_like?: boolean[];
  lane_mode: 'explicit' | 'equal_width' | 'auto';
  lanes: Lane[];
  quality: { state: Quality; reasons: string[] };
  stability: { perturbation_px: { x: number; y: number }; runs: number; ranking_stable: boolean; reference_tie_lanes?: number[] } | null;
  warnings: string[]; disclaimer: string;
  source: { record_id?: number; tier?: string; target?: string; crop?: string; printed_lanes?: number | null; upload?: boolean };
  lanes_requested: number | null; stored: boolean;
}
interface PairLane {
  index: number; label: string | null;
  target_relative: number | null; control_relative: number | null;
  ratio: number | null; ratio_min: number | null; ratio_median: number | null; ratio_max: number | null;
  normalized: number | null; normalized_min: number | null; normalized_max: number | null;
  quality: Quality; reasons: string[];
}
interface PairResult {
  method: Result['method']; target: Result; control: Result; lanes: PairLane[];
  quality: { state: Quality; reasons: string[] }; warnings: string[]; disclaimer: string; source: Result['source']; stored: boolean;
}
type Box = [number, number, number, number];
type Pt = [number, number];
// Geometry of the strip a loading-control strip will be divided by (same image).
interface Target { region: Box; lane_bounds: [number, number][]; lane_labels: string[] | null; band_row: [number, number] | null; row_index: number; res: Result }

const MONO = 'var(--font-mono), monospace';
const QUALITY_LABEL: Record<Quality, string> = {
  ok: 'Valid within-image relative measurement',
  warning: 'Warning — read the caveats',
  quantification_refused: 'Quantification refused',
};
const PAIR_LABEL: Record<Quality, string> = {
  ok: 'Valid within-image target ÷ loading-control ratio',
  warning: 'Warning — read the caveats',
  quantification_refused: 'Normalization refused',
};
const QUALITY_CLASS: Record<Quality, string> = { ok: 'is-ok', warning: 'is-warning', quantification_refused: 'is-refused' };
// Fixed colours for the exported PNG (light footer, theme-independent): light-theme accent / warning / error.
const PNG_COLOR: Record<Quality, string> = { ok: '#087f6d', warning: '#b8761e', quantification_refused: '#d64545' };

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
function download(name: string, type: string, part: BlobPart) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([part], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
const stamp = () => new Date().toISOString().replace(/[:.]/g, '-');
const relText = (l: Lane) => l.relative == null ? '—' : l.stability ? `${l.stability.relative_min.toFixed(1)}–${l.stability.relative_max.toFixed(1)}` : l.relative.toFixed(2);
const relBar = (l: Lane) => l.relative == null ? null : l.stability ? l.stability.relative_median : l.relative;
// Point value, or min–max range when the stability study produced one.
const rangeText = (v: number | null, lo: number | null, hi: number | null, dp: number) => v == null ? '—' : lo != null && hi != null ? `${lo.toFixed(dp)}–${hi.toFixed(dp)}` : v.toFixed(dp);
const pct = (v: number) => Math.max(0, Math.min(100, v * 100));

// Vertical profile sparkline: opening-corrected row means over the band row
// plus the flank rows the baseline came from; y runs top->bottom like the image.
function Sparkline({ l, vmax }: { l: Lane; vmax: number }) {
  const p = l.profile;
  if (!p || p.values.length < 2 || vmax <= 0) return null;
  const W = 120, H = 40, n = p.values.length;
  const x = (i: number) => (i / (n - 1)) * W;
  const y = (v: number) => H - 2 - (Math.max(0, v) / vmax) * (H - 4);
  const pts = p.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const span = (a: number, b: number, cls: string) => {
    const i0 = Math.max(0, a - p.y0), i1 = Math.min(n - 1, b - p.y0);
    return i1 > i0 ? <rect x={x(i0)} y={0} width={x(i1) - x(i0)} height={H} className={cls} /> : null;
  };
  const base = l.flank_baseline ?? 0;
  return (
    <svg className="hb-dens-spark" viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-label={`Vertical profile of lane ${l.index}`} role="img">
      {p.flank.map(([a, b], i) => <g key={i}>{span(a, b, 'hb-dens-spark-flank')}</g>)}
      {span(l.y0, l.y1, 'hb-dens-spark-band')}
      {base > 0 && <line x1={0} x2={W} y1={y(base)} y2={y(base)} className="hb-dens-spark-base" />}
      <polyline points={pts} className="hb-dens-spark-line" />
    </svg>
  );
}

export default function DensitometryPage() {
  const [recordId, setRecordId] = useState('');
  const [live, setLive] = useState(false);
  const [rowIndex, setRowIndex] = useState(0);
  const [fullRow, setFullRow] = useState(false); // band row = full box height instead of detecting inside it
  const [usedFullRow, setUsedFullRow] = useState(false); // mode the current result was measured with
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
  const [target, setTarget] = useState<Target | null>(null);
  const [pair, setPair] = useState<PairResult | null>(null);
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

  // Dividers survive a region change while a target is set (the control strip
  // shares the target's lanes); a new image drops the target with everything else.
  function resetGeometry(newImage = false) {
    setRegion(null); setDraft(null); setLabels([]); setRes(null); setPair(null); setErr(null);
    if (newImage || !target) setDividers([]);
    if (newImage) setTarget(null);
  }

  function loadRecord() {
    if (!/^\d+$/.test(recordId.trim())) return;
    setUpload(null);
    resetGeometry(true);
    setImgSrc(`${live ? '/api/experimental/record' : '/api/record'}/${recordId.trim()}/crop?t=${Date.now()}`);
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const url = String(reader.result);
      const browserShows = /^image\/(png|jpeg|gif|webp|bmp)$/.test(f.type);
      if (browserShows) {
        setUpload(url);
        setImgSrc(url);
        resetGeometry(true);
        return;
      }
      // TIFF and other imager exports: ask the backend for an 8-bit PNG preview
      // and measure that PNG (identical to what the analyzer derives itself).
      setBusy(true);
      setErr(null);
      try {
        const r = await fetch('/api/experimental/densitometry/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image_base64: url }) });
        const d = await r.json();
        if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : d.error || `Backend returned ${r.status}`);
        setUpload(d.png_base64);
        setImgSrc(d.png_base64);
        resetGeometry(true);
      } catch (e2) {
        setErr(e2 instanceof Error ? e2.message : 'Could not decode that file');
      } finally {
        setBusy(false);
      }
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
    // ponytail: with a target set, keep the dividers that fall inside the new box (drop, not clamp — clamping stacks them on an edge)
    setDividers(target ? dividers.filter((d) => d > box[0] && d < box[2]) : n > 1 ? seedDividers(box, n) : []);
    setLabels([]);
    setRes(null); setPair(null);
  }

  function onLaneCount(v: string) {
    const digits = v.replace(/\D/g, '');
    setLaneCount(digits);
    if (region) { setDividers(Number(digits) > 1 ? seedDividers(region, Number(digits)) : []); setRes(null); setPair(null); }
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
      setRes(null); setPair(null);
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
      else if (inRegion(p)) { setDividers((d) => [...d, p[0]].sort((a, b) => a - b)); setRes(null); setPair(null); }
    } else if (!s.moved) {
      setDividers((d) => d.filter((_, i) => i !== s.idx));
      setLabels((l) => l.filter((_, i) => i !== s.idx + 1));
      setRes(null); setPair(null);
    }
  }

  const bounds = region ? laneBounds(region, dividers) : [];
  const canMeasure = !!imgSrc && !busy && (diagnostic || !!region);
  const sourceBody = () => upload ? { image_base64: upload } : { record_id: Number(recordId), live };
  const throwDetail = (d: { detail?: unknown; error?: unknown }, status: number): never => {
    const detail = d.detail ?? d.error;
    throw new Error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `Backend returned ${status}`);
  };

  async function analyze(rowOverride?: number, regionOverride?: Box) {
    const rowIdx = rowOverride ?? rowIndex;
    const reg = regionOverride ?? region;
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const anyLabel = labels.some((l) => l.trim());
      const useFullRow = fullRow && !!reg;
      const lb = reg ? laneBounds(reg, dividers) : [];
      const body: Record<string, unknown> = {
        region: reg,
        lane_bounds: diagnostic ? null : lb,
        lane_labels: diagnostic || !anyLabel ? null : lb.map((_, i) => (labels[i] ?? '').trim()),
        lanes: diagnostic ? Number(laneCount) || null : null,
        row_index: rowIdx,
        stability,
      };
      if (useFullRow) body.band_row = [reg![1], reg![3]];
      Object.assign(body, sourceBody());
      const r = await fetch('/api/experimental/densitometry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throwDetail(d, r.status);
      captureDims();
      setUsedFullRow(useFullRow);
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
  function exportPng() {
    const img = imgRef.current;
    if (!res || !img?.naturalWidth) return;
    try {
      const W = img.naturalWidth, H = img.naturalHeight;
      const s = Math.max(1, W / 800); // stroke/font scale so large crops stay legible
      const foot = Math.round(60 * s);
      const c = document.createElement('canvas');
      c.width = W; c.height = H + foot;
      const g = c.getContext('2d');
      if (!g) throw new Error('Canvas unavailable');
      g.drawImage(img, 0, 0, W, H);
      const reg = res.image.region;
      g.lineWidth = 1.5 * s; g.strokeStyle = PNG_COLOR.ok;
      if (reg) g.strokeRect(reg[0], reg[1], reg[2] - reg[0], reg[3] - reg[1]);
      const bx = reg ? [reg[0], reg[2]] : [0, W];
      g.setLineDash([4 * s, 3 * s]); g.lineWidth = s; g.fillStyle = 'rgba(74, 214, 176, 0.08)';
      g.fillRect(bx[0], res.band_row[0], bx[1] - bx[0], res.band_row[1] - res.band_row[0]);
      g.strokeRect(bx[0], res.band_row[0], bx[1] - bx[0], res.band_row[1] - res.band_row[0]);
      g.font = `600 ${11 * s}px ui-monospace, Menlo, monospace`; g.textAlign = 'center';
      for (const l of res.lanes) {
        const col = PNG_COLOR[l.quality];
        g.setLineDash(l.quality === 'quantification_refused' ? [3 * s, 2 * s] : []);
        g.strokeStyle = col; g.lineWidth = s;
        g.strokeRect(l.x0, l.y0, l.x1 - l.x0, l.y1 - l.y0);
        const text = String(l.label || l.index), tx = (l.x0 + l.x1) / 2, ty = l.y0 - 3 * s < 11 * s ? l.y0 + 12 * s : l.y0 - 3 * s;
        g.setLineDash([]); g.lineWidth = 3 * s; g.strokeStyle = '#ffffff'; g.strokeText(text, tx, ty);
        g.fillStyle = col; g.fillText(text, tx, ty);
      }
      g.fillStyle = '#f5f5f2'; g.fillRect(0, H, W, foot);
      g.fillStyle = '#222222'; g.textAlign = 'left'; g.font = `${11 * s}px ui-monospace, Menlo, monospace`;
      g.fillText(`${res.method.name} v${res.method.version} · quality=${res.quality.state} · region=[${reg?.join(', ') ?? ''}] · band_row=[${res.band_row.join(', ')}] · ${new Date().toISOString()}`, 8 * s, H + 22 * s);
      g.fillText(res.disclaimer.split(/\.\s/)[0].replace(/\.?$/, '.'), 8 * s, H + 42 * s);
      c.toBlob((b) => {
        if (b) download(`hiveblot-densitometry-overlay-${stamp()}.png`, 'image/png', b);
        else setErr('Overlay PNG export failed');
      }, 'image/png');
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Overlay PNG export failed');
    }
  }

  function setAsTarget() {
    if (!res?.image.region) return;
    const reg = res.image.region as Box;
    const anyLabel = res.lanes.some((l) => l.label);
    setTarget({
      region: reg,
      lane_bounds: res.lanes.map((l) => [l.x0, l.x1] as [number, number]),
      lane_labels: anyLabel ? res.lanes.map((l) => l.label ?? '') : null,
      band_row: usedFullRow ? [reg[1], reg[3]] : null,
      row_index: rowIndex,
      res,
    });
    setPair(null);
  }

  async function analyzePair() {
    if (!target || !region) return;
    setBusy(true);
    setErr(null);
    setPair(null);
    try {
      const { region: tr, lane_bounds, lane_labels, band_row, row_index } = target;
      const body = {
        ...sourceBody(),
        target: { region: tr, lane_bounds, lane_labels, band_row, row_index },
        control: { region, lane_bounds: laneBounds(region, dividers), band_row: fullRow ? [region[1], region[3]] : null, row_index: rowIndex },
        stability,
      };
      const r = await fetch('/api/experimental/densitometry/pair', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throwDetail(d, r.status);
      captureDims();
      setPair(d);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  function exportPairJson() {
    if (!pair) return;
    download(`hiveblot-densitometry-pair-${stamp()}.json`, 'application/json', JSON.stringify({ ...pair, exported_at: new Date().toISOString(), page: '/experimental/densitometry' }, null, 2));
  }
  function exportPairCsv() {
    if (!pair) return;
    const head = `# ${pair.method.name} v${pair.method.version}; target_region=${pair.target.image.region?.join(' ') ?? 'none'}; control_region=${pair.control.image.region?.join(' ') ?? 'none'}; quality=${pair.quality.state}`;
    const cols = 'index,label,target_relative,control_relative,ratio,ratio_min,ratio_median,ratio_max,normalized,normalized_min,normalized_max,quality,reasons';
    const rows = pair.lanes.map((l) => [
      l.index, l.label, l.target_relative, l.control_relative, l.ratio, l.ratio_min, l.ratio_median, l.ratio_max,
      l.normalized, l.normalized_min, l.normalized_max, l.quality, l.reasons.join('; '),
    ].map(csvCell).join(','));
    download(`hiveblot-densitometry-pair-${stamp()}.csv`, 'text/csv', [head, cols, ...rows].join('\n') + '\n');
  }

  const refused = res?.quality.state === 'quantification_refused';
  const pairRefused = pair?.quality.state === 'quantification_refused';
  const controlRegion = pair?.control.image.region;
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
        <p className="hb-live-note">…or upload a panel image: <input type="file" accept="image/png,image/jpeg,image/tiff,.tif,.tiff,image/bmp,image/webp" onChange={onFile} /> <span style={{ color: 'var(--text-subtle)' }}>(PNG, JPEG, or a TIFF straight from the imager — 16-bit is shown and measured as 8-bit, no stretch)</span></p>
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
                    {band && !usedFullRow && res.rows_detected.map(([a, b], i) => (a === res.band_row[0] && b === res.band_row[1]) ? null : (
                      <rect key={`alt-${i}`} x={band[0]} y={a} width={band[1] - band[0]} height={b - a} className={`hb-dens-row-alt${res.rows_text_like?.[i] ? ' is-text' : ''}`} />
                    ))}
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
                {target && (
                  <g>
                    <rect x={target.region[0]} y={target.region[1]} width={target.region[2] - target.region[0]} height={target.region[3] - target.region[1]} className="hb-dens-region-target" />
                    <text x={target.region[0] + 3} y={target.region[1] - 3} fontSize={fs} className="hb-dens-label hb-dens-label-target">target</text>
                  </g>
                )}
                {target && controlRegion && (
                  <g>
                    <rect x={controlRegion[0]} y={controlRegion[1]} width={controlRegion[2] - controlRegion[0]} height={controlRegion[3] - controlRegion[1]} className="hb-dens-region-target is-control" />
                    <text x={controlRegion[0] + 3} y={controlRegion[1] - 3} fontSize={fs} className="hb-dens-label hb-dens-label-target">control</text>
                  </g>
                )}
              </svg>
            )}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: 'var(--text-subtle)', marginTop: 6 }}>
            {region ? `region ${region.join(', ')} · ${bounds.length} lane(s)` : 'no region — drag a box on the image'}
            {region && <button type="button" className="hb-search-clear" style={{ marginLeft: 8 }} onClick={() => resetGeometry()} aria-label="Clear region">×</button>}
          </div>

          <div className="hb-dens-controls">
            <label className="hb-ask-check">Lane count <input value={laneCount} onChange={(e) => onLaneCount(e.target.value)} placeholder="e.g. 6" aria-label="Lane count" inputMode="numeric" /></label>
            <label className="hb-ask-check">Row index <input value={rowIndex} onChange={(e) => setRowIndex(Number(e.target.value.replace(/\D/g, '') || 0))} aria-label="Row index" inputMode="numeric" /></label>
            <label className="hb-ask-check">Band row{' '}
              <select value={fullRow ? 'full' : 'detect'} onChange={(e) => { setFullRow(e.target.value === 'full'); setRes(null); }} aria-label="Band row mode" className="hb-dens-select">
                <option value="detect">detect inside the box</option>
                <option value="full">use the full box height</option>
              </select>
            </label>
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
            <button type="button" onClick={() => analyze()} disabled={!canMeasure}>{busy ? 'Measuring…' : 'Measure'}</button>
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
              {res.method.name} v{res.method.version} · lanes: {res.lane_mode} · band row y {res.band_row[0]}–{res.band_row[1]} ({usedFullRow ? 'full box height' : 'detected'}) · {res.rows_detected.length} row(s) detected{res.rows_text_like?.filter(Boolean).length ? ` (${res.rows_text_like.filter(Boolean).length} look like printed text)` : ''} ·{' '}
              {res.image.inverted_for_analysis ? 'dark bands on light background' : 'light bands on dark background'}
              {res.stability && ` · stability: ±${res.stability.perturbation_px.x}px lanes / ±${res.stability.perturbation_px.y}px row × ${res.stability.runs} runs, ranking ${res.stability.ranking_stable ? 'stable' : res.stability.reference_tie_lanes?.length ? `near tie between lanes ${res.stability.reference_tie_lanes.join('/')}` : 'UNSTABLE'}`}
            </p>
            {!usedFullRow && res.rows_detected.length > 1 && (
              <p className="hb-live-note hb-dens-rows">
                The box contains several band rows (faint dashed in the overlay). Click one to re-box that strip alone (its height plus a margin) and measure it:{' '}
                {res.rows_detected.map(([a, b], i) => {
                  const current = a === res.band_row[0] && b === res.band_row[1];
                  return (
                    <button key={i} type="button" className={current ? 'is-active' : ''} disabled={busy} onClick={() => {
                      const r0 = res.image.region ?? [0, 0, dims?.w ?? 0, dims?.h ?? 0];
                      const m = b - a;
                      const boxed: Box = [r0[0], Math.max(r0[1], a - m), r0[2], Math.min(r0[3], b + m)];
                      setRegion(boxed); setRowIndex(0); analyze(0, boxed);
                    }} aria-label={`Re-box and measure band row ${i}`}>
                      row {i}: y {a}–{b}{res.rows_text_like?.[i] ? ' (text?)' : ''}{current ? ' (measured)' : ''}
                    </button>
                  );
                })}
              </p>
            )}
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="hb-dens-table">
              <thead>
                <tr>
                  <th>lane</th><th>label</th>{!refused && <th>relative</th>}<th>corrected</th><th>background</th><th>clipped</th><th>profile</th><th>quality</th>{!refused && <th></th>}
                </tr>
              </thead>
              <tbody>
                {res.lanes.map((l) => {
                  const bar = relBar(l);
                  const vmax = Math.max(...res.lanes.map((k) => Math.max(...(k.profile?.values ?? [0]))));
                  return (
                    <tr key={l.index}>
                      <td style={{ fontFamily: MONO }}>{l.index}</td>
                      <td style={{ fontFamily: MONO }}>{l.label ?? ''}</td>
                      {!refused && <td style={{ fontFamily: MONO, whiteSpace: 'nowrap' }}>{relText(l)}</td>}
                      <td style={{ fontFamily: MONO }}>{Math.round(l.corrected).toLocaleString()}</td>
                      <td style={{ fontFamily: MONO }}>{Math.round(l.background).toLocaleString()}</td>
                      <td style={{ fontFamily: MONO, color: l.clipped_fraction > 0.02 ? 'var(--error)' : undefined }}>{(l.clipped_fraction * 100).toFixed(1)}%</td>
                      <td><Sparkline l={l} vmax={vmax} /></td>
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
            {'Profile = row means of the background-corrected signal, top to bottom: shaded band row, faint flank rows (where the dashed per-lane baseline comes from). '}
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
            <button type="button" onClick={exportPng}>Export overlay PNG</button>
          </div>
          <p className="hb-live-note">
            {res.source.record_id != null ? `record ${res.source.record_id} (${res.source.tier}) · ${res.source.target ?? ''} · ${res.source.crop ?? ''} · printed lanes ${res.source.printed_lanes ?? 'unknown'}` : 'uploaded image'}
            {' · '}nothing stored
          </p>
          <p className="hb-live-note" style={{ color: 'var(--warning)' }}>{res.disclaimer}</p>
        </section>
      )}

      {imgSrc && (target || (res && !refused)) && (
        <section className="hb-page-section">
          <h2 className="hb-page-h2">4. Normalize to a loading control (optional)</h2>
          <p className="hb-page-lead">
            Divides the target strip&apos;s per-lane reading by the loading-control strip&apos;s. Both are uncalibrated within-image pixel
            readings, so the ratio is comparable only between lanes of this image, is not a protein amount, and is only meaningful if
            both strips come from the same membrane and exposure — which a figure cannot prove.
          </p>
          <div className="hb-live-form">
            {res && !refused && <button type="button" onClick={setAsTarget} disabled={busy}>Use this measurement as the target</button>}
            {target && <button type="button" onClick={analyzePair} disabled={busy || !region || diagnostic}>{busy ? 'Measuring…' : 'Measure as loading control'}</button>}
          </div>
          {target && (
            <>
              <div style={{ fontFamily: MONO, fontSize: 11, color: 'var(--text-subtle)', marginTop: 6 }}>
                Target set: region {target.region.join(', ')} · {target.lane_bounds.length} lanes
                <button type="button" className="hb-search-clear" style={{ marginLeft: 8 }} onClick={() => { setTarget(null); setPair(null); }} aria-label="Clear target">×</button>
              </div>
              <p className="hb-live-note">
                Now drag a box around the loading-control strip of the SAME image (e.g. β-actin). The lane dividers are kept; adjust
                them only if the control strip is offset.{diagnostic ? ' Turn off diagnostic mode to pair.' : ''}
              </p>
            </>
          )}
          {pair && (
            <>
              <div className={`hb-dens-quality ${QUALITY_CLASS[pair.quality.state]}`}>
                <h3>{PAIR_LABEL[pair.quality.state]}</h3>
                {pair.quality.reasons.length > 0 && <ul className="hb-page-list">{pair.quality.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
                <p className="hb-live-note">
                  {pair.method.name} v{pair.method.version} · target region {pair.target.image.region?.join(', ')} ({pair.target.quality.state}) · control region {pair.control.image.region?.join(', ')} ({pair.control.quality.state})
                </p>
                {pair.warnings.length > 0 && (
                  <ul className="hb-page-list" style={{ color: 'var(--warning)', fontWeight: 600 }}>
                    {pair.warnings.map((w) => <li key={w}>{w}</li>)}
                  </ul>
                )}
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="hb-dens-table">
                  <thead>
                    <tr>
                      <th>lane</th><th>label</th><th>target rel</th><th>control rel</th>
                      {!pairRefused && <><th>ratio</th><th>normalized</th></>}<th>quality</th>{!pairRefused && <th></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {pair.lanes.map((l) => {
                      const lo = l.normalized_min ?? l.normalized, hi = l.normalized_max ?? l.normalized;
                      return (
                        <tr key={l.index}>
                          <td style={{ fontFamily: MONO }}>{l.index}</td>
                          <td style={{ fontFamily: MONO }}>{l.label ?? ''}</td>
                          <td style={{ fontFamily: MONO }}>{l.target_relative == null ? '—' : l.target_relative.toFixed(2)}</td>
                          <td style={{ fontFamily: MONO }}>{l.control_relative == null ? '—' : l.control_relative.toFixed(2)}</td>
                          {!pairRefused && <td style={{ fontFamily: MONO, whiteSpace: 'nowrap' }}>{rangeText(l.ratio, l.ratio_min, l.ratio_max, 2)}</td>}
                          {!pairRefused && <td style={{ fontFamily: MONO, whiteSpace: 'nowrap' }}>{rangeText(l.normalized, l.normalized_min, l.normalized_max, 1)}</td>}
                          <td>
                            <span className={`hb-dens-q ${QUALITY_CLASS[l.quality]}`}>{l.quality === 'quantification_refused' ? 'refused' : l.quality}</span>
                            {l.reasons.length > 0 && <span className="hb-dens-reasons"> {l.reasons.join('; ')}</span>}
                          </td>
                          {!pairRefused && (
                            <td style={{ width: '30%' }}>
                              {lo != null && hi != null && <div className="hb-dens-bar" style={{ marginLeft: `${pct(lo)}%`, width: `${Math.max(2, pct(hi) - pct(lo))}%` }} />}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="hb-live-note">
                Target rel / control rel = each strip&apos;s corrected ÷ its own strongest lane. Ratio = target ÷ control; normalized = ratio ÷ the largest median ratio in this image.
                A range means min–max across geometry perturbations; the bar spans that range.
              </p>
              <div className="hb-live-form" style={{ marginTop: 12 }}>
                <button type="button" onClick={exportPairJson}>Export pair JSON</button>
                <button type="button" onClick={exportPairCsv}>Export pair CSV</button>
              </div>
              <p className="hb-live-note" style={{ color: 'var(--warning)' }}>{pair.disclaimer}</p>
            </>
          )}
        </section>
      )}
    </div>
  );
}

'use client';

// Optional advanced biological filters. Natural-language search stays primary;
// this composes a structured query string that the backend's deterministic
// biological parser (bio_query.py) already understands — no new API surface.

import { useState } from 'react';

const MONO = '"IBM Plex Mono", monospace';
const LABEL = '#6f857d';

const EXPERIMENT_TYPES = [
  ['', 'any experiment'],
  ['phospho', 'phospho-Western'],
  ['co-IP', 'co-IP'],
  ['loading control', 'loading control'],
] as const;

export default function FiltersBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [open, setOpen] = useState(false);
  const [protein, setProtein] = useState('');
  const [site, setSite] = useState('');
  const [expType, setExpType] = useState('');
  const [cellLine, setCellLine] = useState('');
  const [vendor, setVendor] = useState('');
  const [catalog, setCatalog] = useState('');
  const [needsReview, setNeedsReview] = useState(false);

  const apply = () => {
    const parts = [
      expType,                     // 'phospho' also acts as the modification filter
      protein.trim(),
      site.trim(),                 // Tyr705 / S473
      cellLine.trim(),
      vendor.trim(),
      catalog.trim() ? `#${catalog.trim().replace(/^#/, '')}` : '',
      needsReview ? 'needs review' : '',
    ].filter(Boolean);
    if (parts.length) onSearch(parts.join(' '));
  };

  const input = {
    background: '#0a0d0f', border: '1px solid rgba(255,255,255,.12)', color: '#e7f0ee',
    borderRadius: '4px', padding: '4px 8px', fontFamily: MONO, fontSize: '11px', width: '120px',
  } as const;

  return (
    <div style={{ marginTop: '10px' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: LABEL, cursor: 'pointer',
          fontFamily: MONO, fontSize: '10px', letterSpacing: '0.4px', padding: 0,
        }}
      >
        {open ? '▾ hide filters' : '▸ advanced filters'}
      </button>
      {open && (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginTop: '8px' }}>
          <input style={input} placeholder="protein (STAT3)" value={protein} onChange={(e) => setProtein(e.target.value)} />
          <input style={input} placeholder="site (Tyr705)" value={site} onChange={(e) => setSite(e.target.value)} />
          <select value={expType} onChange={(e) => setExpType(e.target.value)}
                  style={{ ...input, width: '150px' }}>
            {EXPERIMENT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input style={input} placeholder="cell line (Hep3B)" value={cellLine} onChange={(e) => setCellLine(e.target.value)} />
          <input style={input} placeholder="vendor (CST)" value={vendor} onChange={(e) => setVendor(e.target.value)} />
          <input style={input} placeholder="catalog # (9145)" value={catalog} onChange={(e) => setCatalog(e.target.value)} />
          <label style={{ fontFamily: MONO, fontSize: '10px', color: LABEL, display: 'flex', gap: '4px', alignItems: 'center', cursor: 'pointer' }}>
            <input type="checkbox" checked={needsReview} onChange={(e) => setNeedsReview(e.target.checked)} />
            needs review
          </label>
          <button
            onClick={apply}
            style={{
              background: 'transparent', border: '1px solid #4ad6b0', color: '#4ad6b0',
              borderRadius: '4px', padding: '3px 12px', fontFamily: MONO, fontSize: '10px', cursor: 'pointer',
            }}
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

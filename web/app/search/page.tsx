'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { SearchInput } from '@/components/SearchInput';
import DatabaseResultCard, { type LaneSummary } from '@/components/DatabaseResultCard';
import FiltersBar from '@/components/FiltersBar';
import SearchFeedback from '@/components/SearchFeedback';
import BetaFeedback from '@/components/BetaFeedback';

interface DatabaseResult {
  id: number;
  paper_id: string;
  page: number | null;
  western_blot_type: string;
  sample: string;
  organism: string | null;
  treatment_context: string | null;
  figure_label: string | null;
  target: string;
  condition: string;
  band_detected: boolean;
  confidence: number | null;
  // Evidence Record extras used for grouping / lane display (optional —
  // legacy rows simply lack them).
  image_crop_ref?: string | null;
  lane_condition?: string | null;
  band_state?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  modification_label?: string | null;
}

// One card per EXPERIMENT, not per lane row: a 6-lane time course reads as one
// result with a lane strip, not 6 near-identical cards.
//
// The key must never merge biologically distinct rows. Panel + target alone is
// NOT enough: one crop in PMC12706926 (page_004_cand_0025) holds two cell lines
// side by side (H1792 | A549), so cell line is part of the identity. Modification
// label separates a phospho row from its total row when both print the same
// target string. Verified against all 374 demo rows: 77 groups, zero groups
// containing >1 distinct target / canonical target / modification / residue /
// experiment type / UniProt / figure / cell line / catalog / organism.
interface ResultGroup {
  first: DatabaseResult;
  lanes: LaneSummary[];
}

function groupResults(rows: DatabaseResult[]): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const r of rows) {
    const key = [
      r.paper_id,
      r.image_crop_ref ?? `p${r.page}`,
      r.target,
      r.experiment_type ?? '',
      r.cell_line ?? r.sample ?? '',
      r.modification_label ?? '',
    ].join('|');
    const lane: LaneSummary = {
      condition: r.lane_condition ?? r.condition ?? null,
      band_state: r.band_state ?? (r.band_detected == null ? null : r.band_detected ? 'present' : 'absent'),
    };
    const g = groups.get(key);
    if (g) g.lanes.push(lane);
    else groups.set(key, { first: r, lanes: [lane] });
  }
  return [...groups.values()];
}

interface SearchResponse {
  count: number;
  results: DatabaseResult[];
  question?: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<DatabaseResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Support /search?q=… (home-page searches route here so there is ONE
  // results surface — the Evidence Record card, not the legacy table).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) handleSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = async (searchQuery: string) => {
    setQuery(searchQuery);
    if (!searchQuery.trim()) {
      setShowResults(false);
      setResults([]);
      return;
    }

    // Submitted searches are shareable/refreshable: reflect the query in the
    // URL (replaceState — no history spam; only SUBMITTED queries land here,
    // typing never does).
    const url = new URL(window.location.href);
    url.searchParams.set('q', searchQuery);
    window.history.replaceState(null, '', url.toString());

    setLoading(true);
    setError(null);
    setShowResults(true);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data: SearchResponse = await response.json();
      setResults(data.results || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#06090c', paddingTop: '40px' }}>
      {/* Search Bar */}
      <div style={{ padding: '40px 56px 24px', borderBottom: '1px solid rgba(255,255,255,.07)' }}>
        <SearchInput
          placeholder="Search for a protein or experimental condition (e.g., 'phospho STAT3 Tyr705' or 'co-IP PIK3CA')"
          onSearch={handleSearch}
          initialValue={query}
        />
        <div style={{ maxWidth: '760px', margin: '0 auto' }}>
          <FiltersBar onSearch={handleSearch} />
        </div>
      </div>

      {/* Results Section */}
      <div style={{ padding: '60px 56px', maxWidth: '1000px', margin: '0 auto' }}>
        {showResults ? (
          <div>
            {/* Results Header */}
            <div style={{ marginBottom: '40px' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '16px' }}>
                <span style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '16px', fontWeight: 600, color: '#4ad6b0' }}>RESULTS</span>
                <span style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '16px', fontWeight: 600, color: '#6f857d' }}>-</span>
                <span style={{ fontFamily: '"Newsreader", serif', fontSize: '20px', fontWeight: 400, color: '#e7f0ee' }}>Western Blot Evidence</span>
              </div>
              <p style={{ fontFamily: '"Newsreader", serif', fontSize: '14px', color: '#a9bdb5', lineHeight: 1.6, marginTop: '12px' }}>
                {loading
                  ? 'Searching database...'
                  : (() => {
                      const n = groupResults(results).length;
                      return `Found ${n} experiment${n !== 1 ? 's' : ''} (${results.length} lane record${results.length !== 1 ? 's' : ''})`;
                    })()}
              </p>
            </div>

            {/* Loading State */}
            {loading && (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <div style={{ fontFamily: '"Newsreader", serif', fontSize: '16px', color: '#a9bdb5' }}>
                  Querying database...
                </div>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div
                style={{
                  padding: '24px',
                  backgroundColor: 'rgba(255, 107, 107, 0.1)',
                  border: '1px solid rgba(255, 107, 107, 0.3)',
                  borderRadius: '8px',
                  color: '#ff6b6b',
                  fontFamily: '"Newsreader", serif',
                  fontSize: '14px',
                  marginBottom: '40px',
                }}
              >
                Error: {error}
              </div>
            )}

            {/* Results Cards */}
            {!loading && results.length > 0 && (
              <>
                <SearchFeedback query={query} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {groupResults(results).map((g) => (
                    <DatabaseResultCard key={g.first.id} data={g.first} lanes={g.lanes} />
                  ))}
                </div>
              </>
            )}

            {/* No Results */}
            {!loading && results.length === 0 && !error && (
              <div style={{ textAlign: 'center', paddingTop: '40px', color: '#a9bdb5' }}>
                <p style={{ fontFamily: '"Newsreader", serif', fontSize: '16px', lineHeight: 1.6 }}>
                  No results found for your query.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', paddingTop: '80px', color: '#a9bdb5' }}>
            <p style={{ fontFamily: '"Newsreader", serif', fontSize: '18px', lineHeight: 1.6 }}>
              Enter a natural language query to search for western blot evidence
            </p>
            <p style={{ fontFamily: '"Newsreader", serif', fontSize: '14px', marginTop: '12px', color: '#6f857d' }}>
              Example: "Show western blot evidence for phospho-TBK1 in p53 wild-type versus p53 knockout mouse embryonic fibroblasts."
            </p>
          </div>
        )}
      </div>
      <BetaFeedback query={query} />
    </div>
  );
}

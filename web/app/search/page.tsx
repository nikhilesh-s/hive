'use client';

import { useState, useEffect, useRef } from 'react';
import { SearchInput } from '@/components/SearchInput';
import DatabaseResultCard from '@/components/DatabaseResultCard';
import FiltersBar, {
  activeFilterChips,
  buildFilterQuery,
  clearFilter,
  emptySearchFilters,
  hasFilters,
  type SearchFilterKey,
  type SearchFilters,
} from '@/components/FiltersBar';
import SearchFeedback from '@/components/SearchFeedback';
import BetaFeedback from '@/components/BetaFeedback';
import { recordSearchHistory } from '@/lib/history';
import { groupResults, type DatabaseResult, type ResultGroup } from '@/lib/results';
import { getSavedStatus, removeSavedResultRecords, saveResultRecords } from '@/lib/savedResults';

interface SearchResponse {
  count: number;
  results: DatabaseResult[];
  question?: string;
  truncated?: boolean;
}

type SavedState = 'checking' | 'saved' | 'unsaved' | 'unavailable';

function groupKey(group: ResultGroup): string | null {
  return group.first.experiment_key || group.first.stable_row_key?.split(':')[0] || null;
}

function rowKeys(group: ResultGroup): string[] {
  return group.sourceRows.map((row) => row.stable_row_key).filter((key): key is string => Boolean(key));
}

function deriveSavedStates(groupsToCheck: ResultGroup[], saved: Set<string>): Record<string, SavedState> {
  return Object.fromEntries(groupsToCheck.flatMap((group) => {
    const key = groupKey(group);
    const keys = rowKeys(group);
    if (!key) return [];
    return [[key, keys.length > 0 && keys.every((rowKey) => saved.has(rowKey)) ? 'saved' : 'unsaved']];
  }));
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<DatabaseResult[]>([]);
  const [truncated, setTruncated] = useState(false);
  // Each search takes the next sequence number; a response that comes back
  // after a newer search (or a clear) started is dropped.
  const seq = useRef(0);
  const [loading, setLoading] = useState(false);
  // Set ~4 s into a search: the only slow path is the free-tier API waking up.
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [draftFilters, setDraftFilters] = useState<SearchFilters>(emptySearchFilters);
  const [appliedFilters, setAppliedFilters] = useState<SearchFilters>(emptySearchFilters);
  const [savedStates, setSavedStates] = useState<Record<string, SavedState>>({});
  const [savedBusyKeys, setSavedBusyKeys] = useState<string[]>([]);
  const [savedErrors, setSavedErrors] = useState<Record<string, string>>({});
  const savedKeysRef = useRef<string[]>([]);
  const savedGroupsRef = useRef<ResultGroup[]>([]);

  useEffect(() => {
    if (!filtersOpen) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFiltersOpen(false);
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [filtersOpen]);

  const clearSearchUrl = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('q');
    window.history.replaceState(null, '', url.toString());
  };

  const clearResults = () => {
    setQuery('');
    seq.current++;
    setShowResults(false);
    setResults([]);
    setTruncated(false);
    setError(null);
    setSavedStates({});
    setSavedErrors({});
    setLoading(false);
    clearSearchUrl();
  };

  async function refreshSavedStatus(keys: string[], searchSequence: number, groupsToCheck = groupResults(results)) {
    if (!keys.length) return;
    try {
      const saved = await getSavedStatus(keys);
      if (searchSequence !== seq.current) return;
      setSavedStates((current) => ({ ...current, ...deriveSavedStates(groupsToCheck, saved) }));
    } catch {
      if (searchSequence !== seq.current) return;
      const unavailable: Record<string, SavedState> = Object.fromEntries(groupsToCheck.flatMap((group) => {
        const key = groupKey(group);
        return key ? [[key, 'unavailable']] : [];
      }));
      setSavedStates((current) => ({ ...current, ...unavailable }));
      setSavedErrors((current) => ({ ...current, ...Object.fromEntries(Object.keys(unavailable).map((key) => [key, 'Saved status unavailable'])) }));
    }
  }

  async function handleSavedToggle(group: ResultGroup) {
    const key = groupKey(group);
    if (!key) return;
    const keys = rowKeys(group);
    if (!keys.length) return;
    const state = savedStates[key] ?? 'checking';
    if (state === 'checking' || savedBusyKeys.includes(key)) return;
    if (state === 'unavailable') {
      setSavedStates((current) => ({ ...current, [key]: 'checking' }));
      setSavedErrors((current) => ({ ...current, [key]: '' }));
      void refreshSavedStatus(keys, seq.current, [group]);
      return;
    }

    setSavedBusyKeys((current) => [...current, key]);
    setSavedErrors((current) => ({ ...current, [key]: '' }));
    try {
      if (state === 'saved') await removeSavedResultRecords(keys);
      else await saveResultRecords(group.sourceRows.map((row) => ({ record_id: row.id, stable_row_key: row.stable_row_key || '' })));
      setSavedStates((current) => ({ ...current, [key]: state === 'saved' ? 'unsaved' : 'saved' }));
    } catch {
      setSavedErrors((current) => ({ ...current, [key]: state === 'saved' ? 'Could not remove; retry.' : 'Could not save; retry.' }));
    } finally {
      setSavedBusyKeys((current) => current.filter((item) => item !== key));
    }
  }

  async function handleSearch(searchQuery: string, submittedFilters: SearchFilters = emptySearchFilters()) {
    setQuery(searchQuery);
    if (!searchQuery.trim()) {
      clearResults();
      return;
    }

    // Submitted searches are shareable/refreshable: reflect the query in the
    // URL (replaceState — no history spam; only SUBMITTED queries land here,
    // typing never does).
    const url = new URL(window.location.href);
    url.searchParams.set('q', searchQuery);
    window.history.replaceState(null, '', url.toString());

    const my = ++seq.current;
    setLoading(true);
    setSlow(false);
    setError(null);
    setShowResults(true);
    const slowTimer = window.setTimeout(() => setSlow(true), 4000);

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
      void recordSearchHistory(searchQuery, submittedFilters).catch(() => undefined);
      if (my !== seq.current) return; // a newer search started meanwhile
      const nextResults = data.results || [];
      setResults(nextResults);
      setTruncated(data.truncated === true);
      const nextGroups = groupResults(nextResults);
      const groupKeys = nextGroups.map(groupKey).filter((key): key is string => Boolean(key));
      const keys = [...new Set(nextGroups.flatMap(rowKeys))];
      setSavedStates((current) => ({ ...current, ...Object.fromEntries(groupKeys.map((key) => [key, 'checking'])) }));
      void refreshSavedStatus(keys, my, nextGroups);
    } catch (err) {
      if (my !== seq.current) return;
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults([]);
      setTruncated(false);
    } finally {
      window.clearTimeout(slowTimer);
      if (my === seq.current) {
        setSlow(false);
        setLoading(false);
      }
    }
  }

  // Support /search?q=… (home-page searches route here so there is ONE
  // results surface — the Evidence Record card, not the legacy table).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    // One-shot mount read of ?q=; the search sets its own loading state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (q) handleSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePrimarySearch = (searchQuery: string) => {
    setDraftFilters(emptySearchFilters());
    setAppliedFilters(emptySearchFilters());
    handleSearch(searchQuery, emptySearchFilters());
  };

  const handleApplyFilters = () => {
    const filterQuery = buildFilterQuery(draftFilters);
    if (!filterQuery) return;
    setAppliedFilters({ ...draftFilters });
    setFiltersOpen(false);
    handleSearch(filterQuery, draftFilters);
  };

  const handleClearDraftFilter = (key: SearchFilterKey) => {
    setDraftFilters((current) => clearFilter(current, key));
  };

  const handleClearAppliedFilter = (key: SearchFilterKey) => {
    const next = clearFilter(appliedFilters, key);
    setDraftFilters(next);
    setAppliedFilters(next);
    const filterQuery = buildFilterQuery(next);
    if (filterQuery) handleSearch(filterQuery, next);
    else clearResults();
  };

  const handleResetFilters = () => {
    setDraftFilters(emptySearchFilters());
    if (hasFilters(appliedFilters)) {
      setAppliedFilters(emptySearchFilters());
      clearResults();
    }
  };

  const groups = groupResults(results);
  const filterChips = activeFilterChips(appliedFilters);

  useEffect(() => {
    const currentGroups = groupResults(results);
    savedGroupsRef.current = currentGroups;
    savedKeysRef.current = [...new Set(currentGroups.flatMap(rowKeys))];
  }, [results]);

  useEffect(() => {
    const revalidateSaved = async () => {
      const keys = savedKeysRef.current;
      const currentSequence = seq.current;
      if (!keys.length) return;
      const currentGroups = savedGroupsRef.current;
      const groupKeys = currentGroups.map(groupKey).filter((key): key is string => Boolean(key));
      setSavedStates((current) => ({ ...current, ...Object.fromEntries(groupKeys.map((key) => [key, 'checking'])) }));
      try {
        const saved = await getSavedStatus(keys);
        if (currentSequence !== seq.current) return;
        setSavedStates((current) => ({ ...current, ...deriveSavedStates(currentGroups, saved) }));
      } catch {
        if (currentSequence !== seq.current) return;
        setSavedStates((current) => ({ ...current, ...Object.fromEntries(groupKeys.map((key) => [key, 'unavailable'])) }));
      }
    };
    window.addEventListener('focus', revalidateSaved);
    window.addEventListener('pageshow', revalidateSaved);
    return () => {
      window.removeEventListener('focus', revalidateSaved);
      window.removeEventListener('pageshow', revalidateSaved);
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--background)', paddingTop: '16px' }}>
      {/* Search Bar */}
      <div className="hb-search-workspace-header">
        <div className="hb-search-workspace-grid">
          <div className="hb-search-sidebar-spacer" aria-hidden="true" />
          <SearchInput
            heading="Search Western blot evidence"
            placeholder="Search protein, phosphosite, antibody, cell line..."
            onSearch={handlePrimarySearch}
            initialValue={query}
            examples={['phospho STAT3 Tyr705', 'co-IP PIK3CA', 'CST 9145', 'GAPDH mouse', 'needs review']}
            loading={loading}
          />
        </div>
      </div>

      <div className="hb-search-body">
        <button
          type="button"
          className={`hb-filter-backdrop${filtersOpen ? ' is-open' : ''}`}
          onClick={() => setFiltersOpen(false)}
          aria-label="Close filters"
          tabIndex={filtersOpen ? 0 : -1}
        />
        <FiltersBar
          filters={draftFilters}
          onChange={setDraftFilters}
          onApply={handleApplyFilters}
          onClearField={handleClearDraftFilter}
          onReset={handleResetFilters}
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
        />

        {/* Results Section */}
        <main className="hb-search-results">
          <button
            type="button"
            className="hb-mobile-filter-trigger"
            onClick={() => setFiltersOpen(true)}
            aria-expanded={filtersOpen}
            aria-controls="hb-search-filters"
          >
            <svg aria-hidden="true" viewBox="0 0 20 20" focusable="false">
              <path d="M3 5h14M5.5 10h9M8 15h4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6" />
            </svg>
            <span>Filters</span>
            {filterChips.length > 0 && <span className="hb-mobile-filter-count">{filterChips.length}</span>}
          </button>
        {showResults ? (
          <div>
            {/* Results Header */}
            <div className="hb-results-header">
              <div className="hb-results-title">
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: '16px', fontWeight: 600, color: 'var(--accent)' }}>RESULTS</span>
                <span style={{ fontFamily: 'var(--font-serif), serif', fontSize: '20px', fontWeight: 500, color: 'var(--text-primary)' }}>Western blot evidence</span>
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: '10px', color: 'var(--text-subtle)' }}>reviewed corpus · 3 papers</span>
              </div>
              <p className="hb-results-count">
                {loading
                  ? 'Searching the reviewed corpus…'
                  : (() => {
                      const n = groups.length;
                      return `Found ${n} experiment${n !== 1 ? 's' : ''} (${results.length} lane record${results.length !== 1 ? 's' : ''})`;
                    })()}
              </p>
              {!loading && truncated && (
                <p className="hb-live-note">
                  Showing the first {groups.length} experiment{groups.length !== 1 ? 's' : ''}; refine the search to see the rest.
                </p>
              )}
              {filterChips.length > 0 && (
                <div className="hb-active-filters" aria-label="Active filters">
                  {filterChips.map((chip) => (
                    <button
                      key={chip.key}
                      type="button"
                      className="hb-active-filter-chip"
                      onClick={() => handleClearAppliedFilter(chip.key)}
                      aria-label={`Clear ${chip.label}`}
                    >
                      <span>{chip.value}</span>
                      <span aria-hidden="true">x</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Loading State */}
            {loading && (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <div style={{ fontFamily: 'var(--font-serif), serif', fontSize: '16px', color: 'var(--text-secondary)' }}>
                  Querying the database…
                </div>
                {slow && (
                  <p className="hb-search-slow-note">
                    Still working. The beta API runs on a free tier that sleeps after about 15 minutes
                    idle; the first search after that can take 30–60 seconds while it wakes up. Later
                    searches are fast.
                  </p>
                )}
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div
                style={{
                  padding: '24px',
                  backgroundColor: 'var(--error-soft)',
                  border: '1px solid var(--error-border)',
                  borderRadius: '8px',
                  color: 'var(--error)',
                  fontFamily: 'var(--font-serif), serif',
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
                <div className="hb-search-feedback-wrap">
                  <SearchFeedback key={query} query={query} />
                </div>
                <div className="hb-result-list">
                  {groups.map((g) => (
                    <DatabaseResultCard
                      key={g.first.experiment_key || g.first.id}
                      data={g.first}
                      lanes={g.lanes}
                      savedState={groupKey(g) ? (savedStates[groupKey(g) as string] ?? 'checking') : 'unavailable'}
                      saveBusy={groupKey(g) ? savedBusyKeys.includes(groupKey(g) as string) : false}
                      saveError={groupKey(g) ? savedErrors[groupKey(g) as string] : 'Experiment identity unavailable'}
                      onSaveToggle={groupKey(g) ? () => void handleSavedToggle(g) : undefined}
                    />
                  ))}
                </div>
              </>
            )}

            {/* No Results */}
            {!loading && results.length === 0 && !error && (
              <div style={{ textAlign: 'center', paddingTop: '40px', color: 'var(--text-secondary)' }}>
                <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '16px', lineHeight: 1.6 }}>
                  No matching Western blot evidence was found in the current HiveBlot
                  beta dataset (3 reviewed papers). This does not mean no such evidence
                  exists in the literature — the beta corpus is deliberately small.
                </p>
                <div className="hb-search-feedback-wrap">
                  <SearchFeedback key={query} query={query} zeroResults />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', paddingTop: '80px', color: 'var(--text-secondary)' }}>
            <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '18px', lineHeight: 1.6 }}>
              Search a reviewed corpus of experiment-level Western blot evidence:
              3 papers · 93 experiments · 475 evidence rows.
            </p>
            <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '14px', marginTop: '12px', color: 'var(--text-subtle)', lineHeight: 1.6 }}>
              Type a protein, a phosphosite (Tyr705), an antibody vendor and catalog number (CST 9145),
              a cell line (Hep3B), or a design word such as co-IP, loading control or needs review, then
              press Enter. Results group lanes into experiments; each card links to its figure crop and sources.
            </p>
          </div>
        )}
        </main>
      </div>
      <BetaFeedback query={query} />
    </div>
  );
}

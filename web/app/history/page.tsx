'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { activeFilterChips } from '@/components/FiltersBar';
import {
  clearSearchHistory,
  deleteSearchHistory,
  loadSearchHistory,
  type SearchHistoryEntry,
} from '@/lib/history';

function formatSearchedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date unavailable';
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();
  if (sameDay) {
    return `Today, ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  }
  if (isYesterday) {
    return `Yesterday, ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function HistoryPage() {
  const [items, setItems] = useState<SearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSearchHistory()
      .then(setItems)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'History could not be loaded');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: number) => {
    setBusyId(id);
    setError(null);
    try {
      await deleteSearchHistory(id);
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'History item could not be deleted');
    } finally {
      setBusyId(null);
    }
  };

  const handleClear = async () => {
    if (!window.confirm('Clear all search history from this browser session?')) return;
    setClearing(true);
    setError(null);
    try {
      await clearSearchHistory();
      setItems([]);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'History could not be cleared');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="hb-history-page">
      <div className="hb-history-shell">
        <header className="hb-history-header">
          <div>
            <div className="hb-history-kicker">HISTORY</div>
            <h1>Search history</h1>
            <p>Submitted searches from this browser session, kept separate from saved evidence.</p>
          </div>
          {items.length > 0 && (
            <button type="button" className="hb-history-clear" onClick={handleClear} disabled={clearing}>
              {clearing ? 'CLEARING...' : 'CLEAR HISTORY'}
            </button>
          )}
        </header>

        {error && <div className="hb-history-error" role="alert">{error}</div>}

        {loading ? (
          <div className="hb-history-state">Loading recent searches...</div>
        ) : items.length === 0 ? (
          <div className="hb-history-empty">
            <div className="hb-history-empty-label">NO SEARCHES YET</div>
            <p>Your submitted HiveBlot searches will appear here.</p>
            <Link href="/search" className="hb-history-search-link">GO TO SEARCH</Link>
          </div>
        ) : (
          <section aria-labelledby="recent-searches-heading">
            <div className="hb-history-section-heading" id="recent-searches-heading">Recent searches</div>
            <div className="hb-history-list">
              {items.map((item) => {
                const chips = activeFilterChips(item.filters);
                return (
                  <div className="hb-history-row" key={item.id}>
                    <Link
                      className="hb-history-entry"
                      href={`/search?q=${encodeURIComponent(item.query)}`}
                      aria-label={`Run search: ${item.query}`}
                    >
                      <span className="hb-history-query">{item.query}</span>
                      <span className="hb-history-meta">
                        {formatSearchedAt(item.last_searched_at)}
                        {chips.length > 0 && ` · ${chips.map((chip) => `${chip.label}: ${chip.value}`).join(' · ')}`}
                      </span>
                    </Link>
                    <button
                      type="button"
                      className="hb-history-delete"
                      onClick={() => handleDelete(item.id)}
                      disabled={busyId === item.id || clearing}
                      aria-label={`Delete search: ${item.query}`}
                    >
                      {busyId === item.id ? '...' : 'DELETE'}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
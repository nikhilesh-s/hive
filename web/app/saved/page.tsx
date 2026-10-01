'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import DatabaseResultCard from '@/components/DatabaseResultCard';
import { groupResults, type DatabaseResult, type ResultGroup } from '@/lib/results';
import { loadSavedResults, removeSavedResultRecords } from '@/lib/savedResults';

function formatSavedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Saved date unavailable';
  return date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export default function SavedPage() {
  const [rows, setRows] = useState<DatabaseResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyKeys, setBusyKeys] = useState<string[]>([]);
  const [itemErrors, setItemErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      setRows(await loadSavedResults());
    } catch {
      setLoadError('Saved results could not be loaded. Try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    loadSavedResults()
      .then((savedRows) => { if (active) setRows(savedRows); })
      .catch(() => { if (active) setLoadError('Saved results could not be loaded. Try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function groupKey(group: ResultGroup): string {
    return group.first.experiment_key || group.first.stable_row_key?.split(':')[0] || String(group.first.id);
  }

  function rowKeys(group: ResultGroup): string[] {
    return group.sourceRows.map((row) => row.stable_row_key).filter((key): key is string => Boolean(key));
  }

  const remove = async (group: ResultGroup) => {
    const key = groupKey(group);
    if (busyKeys.includes(key)) return;
    const keys = rowKeys(group);
    setBusyKeys((current) => [...current, key]);
    setItemErrors((current) => ({ ...current, [key]: '' }));
    try {
      await removeSavedResultRecords(keys);
      setRows((current) => current.filter((row) => !keys.includes(row.stable_row_key || '')));
    } catch {
      setItemErrors((current) => ({ ...current, [key]: 'Could not remove this saved result. Retry.' }));
    } finally {
      setBusyKeys((current) => current.filter((item) => item !== key));
    }
  };

  const groups = groupResults(rows);

  return (
    <div className="hb-history-page">
      <div className="hb-history-shell">
        <header className="hb-history-header">
          <div>
            <div className="hb-history-kicker">SAVED</div>
            <h1>Saved Western blot evidence</h1>
            <p>Experiments you saved, separate from searches in History.</p>
          </div>
          {!loading && !loadError && groups.length > 0 && (
            <span className="hb-saved-count">{groups.length} saved experiment{groups.length === 1 ? '' : 's'}</span>
          )}
        </header>

        {loading ? (
          <div className="hb-history-state" role="status">Loading saved experiments…</div>
        ) : loadError ? (
          <div className="hb-history-error" role="alert">
            {loadError}{' '}
            <button type="button" className="hb-saved-retry" onClick={() => void load()}>Retry</button>
          </div>
        ) : groups.length === 0 ? (
          <div className="hb-history-empty">
            <div className="hb-history-empty-label">NO SAVED RESULTS YET</div>
            <p>Save a result from Search and it will appear here.</p>
            <Link href="/search" className="hb-history-search-link">SEARCH EVIDENCE</Link>
          </div>
        ) : (
          <section aria-label="Your saved experiments" className="hb-saved-list">
            {groups.map((group) => {
              const key = groupKey(group);
              return (
                <div className="hb-saved-card" key={key}>
                  {group.first.saved_at && <div className="hb-saved-date">Saved {formatSavedAt(group.first.saved_at)}</div>}
                  <DatabaseResultCard
                    data={group.first}
                    lanes={group.lanes}
                    savedState="saved"
                    saveBusy={busyKeys.includes(key)}
                    saveError={itemErrors[key]}
                    onSaveToggle={() => void remove(group)}
                  />
                </div>
              );
            })}
          </section>
        )}
      </div>
    </div>
  );
}

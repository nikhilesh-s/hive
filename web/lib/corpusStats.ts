'use client';

import { useEffect, useState } from 'react';

export interface CorpusStats {
  reviewed_papers: number;
  experiment_groups: number;
  evidence_rows: number;
}

export async function fetchCorpusStats(signal?: AbortSignal): Promise<CorpusStats> {
  const response = await fetch('/api/corpus-stats', { cache: 'no-store', signal });
  if (!response.ok) throw new Error('Corpus statistics are unavailable');
  const data = await response.json();
  if (!data || !['reviewed_papers', 'experiment_groups', 'evidence_rows'].every(
    (key) => Number.isSafeInteger(data[key]) && data[key] >= 0,
  )) throw new Error('Invalid corpus statistics');
  return data;
}

export function useCorpusStats() {
  const [stats, setStats] = useState<CorpusStats | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetchCorpusStats(controller.signal)
      .then((data) => { if (!controller.signal.aborted) setStats(data); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, []);
  return { stats, error };
}

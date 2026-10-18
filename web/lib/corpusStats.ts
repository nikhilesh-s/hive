'use client';

import { useEffect, useState } from 'react';
import { fetchCorpusStats, type CorpusStats } from './corpusStatsRequest';
export { fetchCorpusStats, type CorpusStats } from './corpusStatsRequest';

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

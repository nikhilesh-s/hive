export interface CorpusStats {
  reviewed_papers: number;
  experiment_groups: number;
  evidence_rows: number;
}

const RETRY_DELAYS = [1000, 3000, 8000];
// 502 is the proxy's non-retryable upstream-auth failure; only 429/503 are retried.
const TRANSIENT = new Set([429, 503]);

// signal.throwIfAborted() is missing on older Safari/Chrome.
function checkAborted(signal?: AbortSignal) {
  if (signal?.aborted) throw signal.reason ?? new DOMException('Aborted', 'AbortError');
}

function pause(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    checkAborted(signal);
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException('Aborted', 'AbortError'));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort);
      resolve();
    }, ms);
    signal?.addEventListener('abort', abort, { once: true });
  });
}

export async function fetchCorpusStats(signal?: AbortSignal): Promise<CorpusStats> {
  for (let attempt = 0; ; attempt++) {
    checkAborted(signal);
    let response: Response;
    try {
      response = await fetch('/api/corpus-stats', { cache: 'no-store', signal });
    } catch (error) {
      if (signal?.aborted || attempt >= RETRY_DELAYS.length) throw error;
      await pause(RETRY_DELAYS[attempt], signal);
      continue;
    }
    if (!response.ok) {
      if (TRANSIENT.has(response.status) && attempt < RETRY_DELAYS.length) {
        await pause(RETRY_DELAYS[attempt], signal);
        continue;
      }
      throw new Error('Corpus statistics are unavailable');
    }
    const data = await response.json();
    if (!data || !['reviewed_papers', 'experiment_groups', 'evidence_rows'].every(
      (key) => Number.isSafeInteger(data[key]) && data[key] >= 0,
    )) throw new Error('Invalid corpus statistics');
    return data;
  }
}

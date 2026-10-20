export interface StoredPaper {
  doi: string;
  title?: string | null;
  job_id?: string | null;
  discovery_query?: string | null;
  rows: number;
  experiments: number;
}

export interface StoredPaperLookup<Row> {
  status: 'found' | 'not_extracted' | 'pending';
  doi: string;
  paper: StoredPaper | null;
  results: Row[];
}

export function normalizeDoi(value: string): string {
  // Mirrors western_blot_miner.fulltext.normalize_doi: first DOI inside the text,
  // trailing ".,;)" dropped, lowercased. Keep the two in step.
  const m = /10\.\d{4,9}\/\S+/i.exec(value.trim());
  const doi = m ? m[0].replace(/[.,;)]+$/, '').toLowerCase() : '';
  return doi.length <= 200 ? doi : '';
}

export function isDoiQuery(value: string): boolean {
  return normalizeDoi(value) !== '';
}

// Share only in-flight reads (including React's development effect replay).
// Settled results are not cached: a later visit may have newly completed evidence.
const pending = new Map<string, Promise<StoredPaperLookup<unknown>>>();

export function fetchStoredPaper<Row>(value: string): Promise<StoredPaperLookup<Row>> {
  const doi = normalizeDoi(value);
  if (!doi) return Promise.reject(new Error('Enter a valid DOI.'));
  let request = pending.get(doi);
  if (!request) {
    request = fetch(`/api/experimental/stored-paper?${new URLSearchParams({ doi })}`, { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || `Backend returned ${response.status}`);
        if (!['found', 'not_extracted', 'pending'].includes(data.status) || !Array.isArray(data.results)
          || (data.status === 'found' && (!data.paper || !data.results.length))) {
          throw new Error('Invalid stored evidence response');
        }
        return data;
      })
      .finally(() => pending.delete(doi));
    pending.set(doi, request);
  }
  return request as Promise<StoredPaperLookup<Row>>;
}

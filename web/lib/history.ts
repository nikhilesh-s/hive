import type { SearchFilters } from '@/components/FiltersBar';
import { sessionId } from '@/lib/feedback';

export interface SearchHistoryEntry {
  id: number;
  query: string;
  filters: SearchFilters;
  created_at: string;
  last_searched_at: string;
}

function emptyFilters(): SearchFilters {
  return {
    protein: '',
    site: '',
    expType: '',
    cellLine: '',
    vendor: '',
    catalog: '',
    needsReview: false,
  };
}

function parseEntry(value: unknown): SearchHistoryEntry | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  if (typeof item.id !== 'number' || typeof item.query !== 'string') return null;
  return {
    id: item.id,
    query: item.query,
    filters: { ...emptyFilters(), ...(item.filters && typeof item.filters === 'object' ? item.filters : {}) },
    created_at: typeof item.created_at === 'string' ? item.created_at : '',
    last_searched_at: typeof item.last_searched_at === 'string' ? item.last_searched_at : '',
  };
}

export async function loadSearchHistory(): Promise<SearchHistoryEntry[]> {
  const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId())}`, {
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('History could not be loaded');
  const data = await response.json() as { items?: unknown };
  return Array.isArray(data.items)
    ? data.items.map(parseEntry).filter((entry): entry is SearchHistoryEntry => entry !== null)
    : [];
}

export async function recordSearchHistory(query: string, filters: SearchFilters): Promise<void> {
  await fetch('/api/history', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId(), query, filters }),
  });
}

export async function deleteSearchHistory(id: number): Promise<void> {
  const response = await fetch(`/api/history/${id}?session_id=${encodeURIComponent(sessionId())}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('History item could not be deleted');
}

export async function clearSearchHistory(): Promise<void> {
  const response = await fetch(`/api/history?session_id=${encodeURIComponent(sessionId())}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('History could not be cleared');
}
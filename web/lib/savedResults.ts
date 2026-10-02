import type { DatabaseResult } from '@/lib/results';
import { sessionId } from '@/lib/feedback';
import { createClient } from '@/lib/supabase/client';
import { authConfig } from '@/lib/supabase/config';

// Remount account-specific views on identity changes, including another tab's
// sign-out. This also discards in-flight results belonging to the previous owner.
export function watchSavedOwner(): () => void {
  if (!authConfig()) return () => {};
  let owner: string | null | undefined;
  const { data: { subscription } } = createClient().auth.onAuthStateChange((_event, session) => {
    const nextOwner = session?.user.id ?? null;
    if (owner !== undefined && owner !== nextOwner) window.location.reload();
    owner = nextOwner;
  });
  return () => subscription.unsubscribe();
}

export interface SavedRecordInput {
  record_id: number;
  stable_row_key: string;
}

async function checkedJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error('Saved results request failed');
  return response.json() as Promise<T>;
}

export async function getSavedStatus(stableRowKeys: string[]): Promise<Set<string>> {
  if (!stableRowKeys.length) return new Set();
  const data = await checkedJson<{ saved_keys: string[] }>(await fetch('/api/saved-results/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify({ session_id: sessionId(), stable_row_keys: stableRowKeys }),
  }));
  return new Set(data.saved_keys);
}

export async function saveResultRecords(records: SavedRecordInput[]): Promise<Set<string>> {
  const data = await checkedJson<{ saved_keys: string[] }>(await fetch('/api/saved-results', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId(), records }),
  }));
  return new Set(data.saved_keys);
}

export async function removeSavedResultRecords(stableRowKeys: string[]): Promise<void> {
  await checkedJson(await fetch('/api/saved-results', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId(), stable_row_keys: stableRowKeys }),
  }));
}

export async function loadSavedResults(): Promise<DatabaseResult[]> {
  return checkedJson<DatabaseResult[]>(
    await fetch(`/api/saved-results?session_id=${encodeURIComponent(sessionId())}`, { cache: 'no-store' }),
  );
}

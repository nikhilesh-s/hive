import { authConfig } from '@/lib/supabase/config';
import { createClient } from '@/lib/supabase/server';

// Only server route handlers may assert an owner to the internal API.
export async function savedOwnerHeaders(): Promise<Record<string, string>> {
  if (!authConfig()) return {};
  const client = await createClient();
  const { data, error } = await client.auth.getUser();
  if (error && error.name !== 'AuthSessionMissingError') throw error;
  return data.user ? { 'X-Hive-User-Id': data.user.id } : {};
}

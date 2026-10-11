export function authConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  // Only the public publishable key is accepted by the browser auth client.
  return url && key?.startsWith('sb_publishable_') ? { url, key } : null;
}

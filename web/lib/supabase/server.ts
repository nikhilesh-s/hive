import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { authConfig } from './config';

export async function createClient() {
  const config = authConfig();
  if (!config) throw new Error('Google sign-in is not configured.');
  const store = await cookies();
  return createServerClient(config.url, config.key, {
    cookies: {
      getAll: () => store.getAll(),
      setAll: (values) => {
        values.forEach(({ name, value, options }) => store.set(name, value, options));
      },
    },
  });
}

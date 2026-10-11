'use client';

import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/client';
import { authConfig } from '@/lib/supabase/config';

export function AuthControl() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!authConfig()) return;
    const client = createClient();
    let active = true;
    const { data: { subscription } } = client.auth.onAuthStateChange((_event, session) => {
      if (active) { setUser(session?.user ?? null); setReady(true); }
    });
    client.auth.getUser().then(({ data }) => {
      if (active) { setUser(data.user); setReady(true); }
    }).catch(() => { if (active) setReady(true); });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  async function act() {
    setBusy(true);
    setError('');
    try {
      const client = createClient();
      const result = user
        ? await client.auth.signOut()
        : await client.auth.signInWithOAuth({ provider: 'google', options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        } });
      if (result.error) throw result.error;
      if (user) setUser(null);
    } catch {
      setError(user ? 'Could not sign out. Retry.' : 'Could not sign in. Retry.');
    } finally { setBusy(false); }
  }
  return <div className="hb-auth-control">
    {user && <span title={user.email}>{user.email ?? user.user_metadata?.full_name ?? 'Signed in'}</span>}
    <button type="button" className="vt-navlink" disabled={!ready || busy} onClick={act}
      title={!authConfig() ? 'Google sign-in is not configured' : undefined}>
      {busy ? 'Please wait...' : user ? 'Sign out' : 'Continue with Google'}
    </button>
    {error && <span role="alert">{error}</span>}
  </div>;
}

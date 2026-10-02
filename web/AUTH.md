# Google Authentication

Authentication uses `@supabase/supabase-js` with `@supabase/ssr` cookie storage.
Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
in `web/.env` locally and the Vercel environment before building. The key must
be the public `sb_publishable_` key, never the API's secret/service-role key.
Without these variables the login button is disabled; anonymous search works.

In Supabase Authentication URL Configuration, allow both redirect URLs:
- `http://localhost:3001/auth/callback`
- `https://hiveblot-beta.vercel.app/auth/callback`

Google's authorized redirect URI stays
`https://zafombwswztvnjikcsdm.supabase.co/auth/v1/callback`.
Supabase Google provider credentials are configured in Supabase, not Next.js.

The navigation's `AuthControl` uses `signInWithOAuth` with Google and
`redirectTo: window.location.origin + '/auth/callback'`. The browser client in
`lib/supabase/client.ts` persists the PKCE verifier in cookies. The callback
uses `lib/supabase/server.ts` to exchange the temporary code and verifier for
a session and write session cookies. It redirects to `/` by default; optional
`next` accepts internal paths only. Failure goes to `/auth/error`.

`proxy.ts` refreshes cookies with a validated `getUser()` call, preserving the
experimental beta gate. `AuthControl` reads `getUser()` and subscribes to auth
changes: the returned user exposes `id` (Supabase auth UUID), `email`, and
`user_metadata`. Sign out calls `auth.signOut()` and handles errors visibly.
Auth cookies are distinct from the existing anonymous localStorage session.
Saved Results, Search History, and all scientific tables are unchanged.

Verification: run `node --test tests/auth-redirect.test.mjs`, lint, typecheck,
and build from `web`. Then sign in with an allowed Google user, confirm the
callback succeeds, refresh, check Supabase Authentication Users, and sign out.
Repeat against production after deployment. An actual Google account is needed
to verify this full flow; automated redirect tests do not prove provider setup.

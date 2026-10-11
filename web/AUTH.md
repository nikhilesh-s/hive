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
Search History and all scientific tables are unchanged.

## Saved Results ownership

Saved Results uses the existing browser session ID for anonymous visitors and
the verified Supabase `user.id` for signed-in users. The browser still sends
`session_id`; Next.js verifies the cookie session with `auth.getUser()` and
sets `X-Hive-User-Id` itself on requests to the internal FastAPI endpoints.
Browser headers, query parameters, body `user_id`, and email cannot select an
account owner. The backend accepts this identity only alongside the server-only
`INTERNAL_API_KEY`. Invalid sessions or verification failures fail the request
instead of silently saving to an anonymous session.

All four operations (status, save, list, unsave) use the same ownership scope:
account operations use `user_id`; anonymous operations use `session_id` plus
`user_id IS NULL`. New account rows leave `session_id` null. Each source lane
is still saved by its record ID and stable row key; grouping is unchanged.
Unsave deletes only matching rows in `saved_results`. Search and Saved reload
on identity changes so the previous owner's saved state does not remain visible.

The linked Supabase table already has nullable `session_id`/`user_id`, a foreign
key to `auth.users(id)`, separate unique owner/key indexes, and RLS enabled.
No new migration is required for the current server-only REST path. Direct
Postgres deployments using `DB_FEEDBACK_URL` must apply the existing migration
008 grants/policies; these were absent on the linked project when inspected.
Do not grant browser `anon`/`authenticated` roles broad table access. The
server owns authorization; the browser never queries this table directly.
Deploy the backend before the frontend, as the old backend ignores account
ownership headers.

Account saves persist across devices using the same Supabase account. Anonymous
saves are deliberately separate and are not claimed on login. A future claim
flow needs explicit user consent, proof of the anonymous session, a verified
account, and a transactional, idempotent copy/deduplication of all lane keys.
Only remove anonymous rows after the account copy succeeds. The existing
localStorage session ID is a bearer identifier, not strong proof of ownership;
strengthening that proof requires a separate design.

Automated ownership tests: `node --test tests/saved-owner.test.mjs` and the API
pytest suite. With local web/API running, `node tests/saved-results.smoke.mjs`
uses the uncommitted local env files to create temporary Supabase test accounts
without sending email, exercise both ownership modes through Next.js, compare
the scientific table before/after, and remove its test accounts/saves. It tests
real Supabase sessions, not the interactive Google consent screen.

Verification: run `node --test tests/auth-redirect.test.mjs`, lint, typecheck,
and build from `web`. Then sign in with an allowed Google user, confirm the
callback succeeds, refresh, check Supabase Authentication Users, and sign out.
Repeat against production after deployment. An actual Google account is needed
to verify this full flow; automated redirect tests do not prove provider setup.

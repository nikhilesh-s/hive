import { NextRequest, NextResponse } from 'next/server';
import { ACCESS_COOKIE, accessCookieOptions } from '@/lib/betaAccess';
import { refreshSession } from '@/lib/supabase/proxy';

// Beta password on everything that spends model credits (live extraction,
// paper Q&A). An invite link carries ?access=<code> once; after that the
// cookie does. BETA_ACCESS_CODE unset => no gate (local development).
export async function proxy(request: NextRequest) {
  if (!request.nextUrl.pathname.startsWith('/experimental/') &&
      request.nextUrl.pathname !== '/experimental' &&
      !request.nextUrl.pathname.startsWith('/api/experimental/')) return refreshSession(request);
  const code = process.env.BETA_ACCESS_CODE;
  if (!code) return refreshSession(request);

  const url = request.nextUrl.clone();
  if (url.searchParams.get('access') === code) {
    url.searchParams.delete('access');
    const res = NextResponse.redirect(url);
    res.cookies.set(ACCESS_COOKIE, code, accessCookieOptions);
    return res;
  }
  if (request.cookies.get(ACCESS_COOKIE)?.value === code) return refreshSession(request);

  if (url.pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Beta access code required' }, { status: 401 });
  }
  url.searchParams.delete('access');
  const gate = new URL('/access', request.url);
  gate.searchParams.set('next', url.pathname + url.search);
  return NextResponse.redirect(gate);
}

export const config = {
  matcher: ['/((?!api/|_next/|auth/callback|favicon.ico|.*\\..*).*)', '/api/experimental/:path*'],
};

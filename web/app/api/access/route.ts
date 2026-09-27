import { NextRequest, NextResponse } from 'next/server';
import { ACCESS_COOKIE, accessCookieOptions, safeNext } from '@/lib/betaAccess';

// Form target for /access: a correct beta code sets the cookie proxy.ts checks.
export async function POST(request: NextRequest) {
  const form = await request.formData().catch(() => null);
  const next = safeNext(form?.get('next'));
  const code = process.env.BETA_ACCESS_CODE;
  if (!code || String(form?.get('code') ?? '').trim() !== code) {
    const back = new URL('/access', request.url);
    back.searchParams.set('next', next);
    back.searchParams.set('error', '1');
    return NextResponse.redirect(back, 303);
  }
  const res = NextResponse.redirect(new URL(next, request.url), 303);
  res.cookies.set(ACCESS_COOKIE, code, accessCookieOptions);
  return res;
}

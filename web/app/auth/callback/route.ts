import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { safeNext } from '@/lib/authRedirect';

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code');
  if (code && !request.nextUrl.searchParams.has('error')) {
    try {
      const client = await createClient();
      const { error } = await client.auth.exchangeCodeForSession(code);
      if (!error) {
        const response = NextResponse.redirect(new URL(safeNext(request.nextUrl.searchParams.get('next')), request.url));
        response.headers.set('Cache-Control', 'private, no-store');
        return response;
      }
    } catch {
      // Do not expose authorization codes or provider error details.
    }
  }
  return NextResponse.redirect(new URL('/auth/error', request.url));
}

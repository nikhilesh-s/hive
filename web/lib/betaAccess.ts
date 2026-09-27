export const ACCESS_COOKIE = 'hb_access';

export const accessCookieOptions = {
  httpOnly: true,
  secure: true,
  sameSite: 'lax' as const,
  path: '/',
  maxAge: 60 * 60 * 24 * 60,
};

// Only same-site paths, never '//host' (open redirect).
export function safeNext(next: unknown): string {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//')
    ? next
    : '/experimental/research';
}

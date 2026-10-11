export function safeNext(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\x00-\x20]/.test(value)) return '/';
  const base = 'https://hiveblot.invalid';
  try {
    const url = new URL(value, base);
    return url.origin === base ? url.pathname + url.search + url.hash : '/';
  } catch {
    return '/';
  }
}

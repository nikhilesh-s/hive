export function paperAccessLabel(status?: string | null): string {
  if (status === 'open_access') return 'Open access';
  if (status === 'no_open_copy_found') return 'No open copy found · Check institutional access';
  return 'Access unknown';
}

/** Return the URL only if it is a well-formed http(s) link; otherwise null. */
export function safeHttpUrl(value?: string | null): string | null {
  try {
    const url = new URL(String(value ?? ''));
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

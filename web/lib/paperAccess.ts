export function paperAccessLabel(status?: string | null): string {
  if (status === 'open_access') return 'Open access';
  if (status === 'no_open_copy_found') return 'No open copy found · Check institutional access';
  return 'Access unknown';
}

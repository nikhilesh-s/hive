import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
import { normalizeDoi } from '@/lib/storedPaper';

export async function GET(request: NextRequest) {
  const doi = normalizeDoi(request.nextUrl.searchParams.get('doi') || '');
  if (!doi) return NextResponse.json({ detail: 'Not a DOI' }, { status: 422 });
  const response = await proxyJson(`/experimental/live/paper?${new URLSearchParams({ doi })}`);
  response.headers.set('Cache-Control', 'private, no-store');
  return response;
}

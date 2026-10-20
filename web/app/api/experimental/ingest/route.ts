import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';

export async function GET() { return proxyJson('/experimental/ingest'); }

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object') {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }
  // Only the DOI, flags and discovery query go to the API; paper metadata is derived server-side.
  const { doi, force, reuse, query } = body as Record<string, unknown>;

  return proxyJson('/experimental/ingest', {
    method: 'POST',
    body: { doi, force: Boolean(force), reuse: Boolean(reuse), query },
  });
}

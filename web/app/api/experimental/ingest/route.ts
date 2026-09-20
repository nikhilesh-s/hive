import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function GET() { return proxyJson('/experimental/ingest'); }
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object') return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  const { doi, force } = body;
  return proxyJson('/experimental/ingest', { method: 'POST', body: { doi, force: Boolean(force) } });
}

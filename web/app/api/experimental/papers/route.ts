import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object') return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  const { query, limit, source } = body;
  return proxyJson('/experimental/papers/search', { method: 'POST', body: { query, limit, source } });
}

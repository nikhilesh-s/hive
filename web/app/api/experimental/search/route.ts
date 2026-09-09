import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const { query, limit } = await request.json();
  if (!query || !String(query).trim()) return NextResponse.json({ error: 'Query is required' }, { status: 400 });
  const cap = Math.min(500, Math.max(1, Number(limit) || 100));
  return proxyJson('/experimental/search', { method: 'POST', body: { query, limit: cap } });
}

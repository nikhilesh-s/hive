import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const { query } = await request.json();
  if (!query || !String(query).trim()) return NextResponse.json({ error: 'Query is required' }, { status: 400 });
  return proxyJson('/experimental/search', { method: 'POST', body: { query } });
}

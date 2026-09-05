import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const { question, doi, include_live } = await request.json();
  if (!question || String(question).trim().length < 3) return NextResponse.json({ error: 'Question is required' }, { status: 400 });
  return proxyJson('/experimental/ask', { method: 'POST', body: { question, doi: doi || null, include_live: include_live !== false } });
}

import { NextRequest } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const { query, limit, source } = await request.json();
  return proxyJson('/experimental/papers/search', { method: 'POST', body: { query, limit, source } });
}

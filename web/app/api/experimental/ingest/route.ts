import { NextRequest } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function GET() { return proxyJson('/experimental/ingest'); }
export async function POST(request: NextRequest) {
  const { doi, force } = await request.json();
  return proxyJson('/experimental/ingest', { method: 'POST', body: { doi, force: Boolean(force) } });
}

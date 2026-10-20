import { NextResponse } from 'next/server';

export async function GET() {
  const base = process.env.API_BASE_URL;
  const key = process.env.INTERNAL_API_KEY;
  const headers = { 'Cache-Control': 'no-store' };
  const fail = (status: number) =>
    NextResponse.json({ error: 'Corpus statistics are unavailable' }, { status, headers });
  // 500/502 are config/auth faults the client must not retry; 503 means transient.
  if (!base || !key) return fail(500);
  try {
    const response = await fetch(`${base}/corpus-stats`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    });
    if (response.status === 401 || response.status === 403) return fail(502);
    if (!response.ok) return fail(503);
    return NextResponse.json(await response.json(), { headers });
  } catch {
    return fail(503);
  }
}

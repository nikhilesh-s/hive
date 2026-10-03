import { NextResponse } from 'next/server';

export async function GET() {
  const base = process.env.API_BASE_URL;
  const key = process.env.INTERNAL_API_KEY;
  const headers = { 'Cache-Control': 'no-store' };
  if (!base || !key) {
    return NextResponse.json({ error: 'Corpus statistics are unavailable' }, { status: 503, headers });
  }
  try {
    const response = await fetch(`${base}/corpus-stats`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error('Corpus lookup failed');
    return NextResponse.json(await response.json(), { headers });
  } catch {
    return NextResponse.json({ error: 'Corpus statistics are unavailable' }, { status: 503, headers });
  }
}

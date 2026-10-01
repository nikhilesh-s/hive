import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_BASE_URL;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!BACKEND_URL || !INTERNAL_API_KEY) {
    return NextResponse.json({ error: 'Saved results are not configured' }, { status: 500 });
  }
  try {
    const upstream = await fetch(`${BACKEND_URL}/saved-results/status`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${INTERNAL_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
    const data = await upstream.json().catch(() => ({}));
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: 'Saved status could not be loaded' }, { status: 502 });
  }
}

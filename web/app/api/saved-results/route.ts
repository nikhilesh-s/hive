import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_BASE_URL;
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

function configured() {
  return BACKEND_URL && INTERNAL_API_KEY
    ? null
    : NextResponse.json({ error: 'Saved results are not configured' }, { status: 500 });
}

export async function GET(request: NextRequest) {
  const missing = configured();
  if (missing) return missing;
  const session = request.nextUrl.searchParams.get('session_id') || '';
  try {
    const upstream = await fetch(`${BACKEND_URL}/saved-results?session_id=${encodeURIComponent(session)}`, {
      headers: { Authorization: `Bearer ${INTERNAL_API_KEY}` },
      cache: 'no-store',
    });
    const data = await upstream.json().catch(() => ({}));
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ error: 'Saved results could not be loaded' }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const missing = configured();
  if (missing) return missing;
  const body = await request.json().catch(() => null);
  try {
    const upstream = await fetch(`${BACKEND_URL}/saved-results`, {
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
    return NextResponse.json({ error: 'Result could not be saved' }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  const missing = configured();
  if (missing) return missing;
  const body = await request.json().catch(() => null);
  try {
    const upstream = await fetch(`${BACKEND_URL}/saved-results`, {
      method: 'DELETE',
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
    return NextResponse.json({ error: 'Saved result could not be removed' }, { status: 502 });
  }
}

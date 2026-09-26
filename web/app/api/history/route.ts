import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

function backendHeaders() {
  return {
    'Content-Type': 'application/json',
    ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
  };
}

function configuredResponse() {
  return BACKEND_URL
    ? null
    : NextResponse.json({ error: 'History is not configured' }, { status: 500 });
}

export async function GET(request: NextRequest) {
  const missing = configuredResponse();
  if (missing) return missing;
  const session = request.nextUrl.searchParams.get('session_id');
  if (!session) return NextResponse.json({ error: 'Session id is required' }, { status: 400 });
  try {
    const response = await fetch(
      `${BACKEND_URL}/history?session_id=${encodeURIComponent(session)}&limit=50`,
      { headers: backendHeaders(), cache: 'no-store' },
    );
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Failed to reach history backend' }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const missing = configuredResponse();
  if (missing) return missing;
  const raw = await request.json().catch(() => null) as Record<string, unknown> | null;
  if (!raw || typeof raw.session_id !== 'string' || typeof raw.query !== 'string') {
    return NextResponse.json({ error: 'Session id and query are required' }, { status: 400 });
  }
  try {
    const response = await fetch(`${BACKEND_URL}/history`, {
      method: 'POST',
      headers: backendHeaders(),
      body: JSON.stringify({
        session_id: raw.session_id,
        query: raw.query,
        filters: raw.filters && typeof raw.filters === 'object' ? raw.filters : {},
      }),
    });
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Failed to reach history backend' }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  const missing = configuredResponse();
  if (missing) return missing;
  const session = request.nextUrl.searchParams.get('session_id');
  if (!session) return NextResponse.json({ error: 'Session id is required' }, { status: 400 });
  try {
    const response = await fetch(
      `${BACKEND_URL}/history?session_id=${encodeURIComponent(session)}`,
      { method: 'DELETE', headers: backendHeaders() },
    );
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Failed to reach history backend' }, { status: 502 });
  }
}
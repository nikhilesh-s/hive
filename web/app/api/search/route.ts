import { NextRequest, NextResponse } from 'next/server';
import { clientIpHeader } from '@/lib/clientIp';

// Server-only env vars: never exposed to the client bundle since this file
// only runs in the Next.js API route handler (Node runtime), not in the browser.
// Calls the backend's *internal* endpoint (see api/app/routers/internal.py) -
// this key must match the backend's INTERNAL_API_KEY, not an agent key.
const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

export async function POST(request: NextRequest) {
  if (!BACKEND_URL) {
    console.error('API_BASE_URL is not configured');
    return NextResponse.json({ error: 'Search is not configured' }, { status: 500 });
  }

  try {
    const raw = await request.json().catch(() => null);
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
    }
    const { query } = raw as { query?: unknown };

    if (typeof query !== 'string' || query.trim() === '') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    const backendResponse = await fetch(`${BACKEND_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
        ...(await clientIpHeader()),
      },
      // 500 = backend maximum; above it the backend drops the trailing partial
      // experiment and sets `truncated`, which the search page surfaces.
      body: JSON.stringify({ query, limit: 500 }),
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error('Backend error:', backendResponse.status, errorText);
      return NextResponse.json(
        { error: `Backend returned ${backendResponse.status}` },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: 'Failed to reach search backend' },
      { status: 502 }
    );
  }
}

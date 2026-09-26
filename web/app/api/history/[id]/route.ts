import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  if (!BACKEND_URL) return NextResponse.json({ error: 'History is not configured' }, { status: 500 });
  const session = request.nextUrl.searchParams.get('session_id');
  const { id } = await context.params;
  if (!session || !/^\d+$/.test(id)) {
    return NextResponse.json({ error: 'Session id and history id are required' }, { status: 400 });
  }
  try {
    const response = await fetch(
      `${BACKEND_URL}/history/${id}?session_id=${encodeURIComponent(session)}`,
      {
        method: 'DELETE',
        headers: {
          ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
        },
      },
    );
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Failed to reach history backend' }, { status: 502 });
  }
}
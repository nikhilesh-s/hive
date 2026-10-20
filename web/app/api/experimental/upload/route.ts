import { NextRequest, NextResponse } from 'next/server';
import { savedOwnerHeaders } from '@/lib/savedOwner';
import { normalizeDoi } from '@/lib/storedPaper';

export async function POST(request: NextRequest) {
  try {
    const owner = await savedOwnerHeaders();
    if (!owner['X-Hive-User-Id']) return NextResponse.json({ detail: 'Sign in with Google before uploading a PDF.' }, { status: 401 });
    const body = await request.json().catch(() => null);
    const doi = typeof body?.doi === 'string' ? normalizeDoi(body.doi) : '';
    if (!doi) return NextResponse.json({ detail: 'Enter a valid DOI.' }, { status: 422 });
    const base = process.env.API_BASE_URL;
    const key = process.env.INTERNAL_API_KEY;
    if (!base || !key) return NextResponse.json({ detail: 'Uploads are not configured.' }, { status: 503 });
    const response = await fetch(`${base}/experimental/upload-ticket`, {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}`, ...owner },
      body: JSON.stringify({ doi }),
    });
    const data = await response.json();
    return NextResponse.json(response.ok ? { ...data, upload_url: `${base}/experimental/uploads` } : data,
      { status: response.status, headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ detail: 'Could not verify your session or reach the upload service. Please retry.' }, { status: 503 });
  }
}

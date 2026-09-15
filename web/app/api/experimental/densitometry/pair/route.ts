import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
// Loading-control pairing: target strip ÷ control strip of the SAME image. The body is forwarded whole.
export async function POST(request: NextRequest) {
  const body = await request.json();
  if (body?.record_id == null && !body?.image_base64) return NextResponse.json({ error: 'record_id or image_base64 required' }, { status: 400 });
  return proxyJson('/experimental-densitometry/pair', { method: 'POST', body });
}

import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
// TIFF and other imager exports: the backend decodes them and returns an 8-bit PNG data URL for display.
export async function POST(request: NextRequest) {
  const { image_base64 } = await request.json();
  if (!image_base64) return NextResponse.json({ error: 'image_base64 required' }, { status: 400 });
  return proxyJson('/experimental-densitometry/preview', { method: 'POST', body: { image_base64 } });
}

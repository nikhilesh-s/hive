import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
export async function POST(request: NextRequest) {
  const { record_id, live, image_base64, region, lane_bounds, lane_labels, lanes, row_index, stability } = await request.json();
  if (record_id == null && !image_base64) return NextResponse.json({ error: 'record_id or image_base64 required' }, { status: 400 });
  return proxyJson('/experimental-densitometry', {
    method: 'POST',
    body: {
      record_id: record_id ?? null,
      live: Boolean(live),
      image_base64: image_base64 ?? null,
      region: region ?? null,
      lane_bounds: lane_bounds ?? null,
      lane_labels: lane_labels ?? null,
      lanes: lanes ?? null,
      row_index: row_index ?? 0,
      stability: stability ?? true,
    },
  });
}

import { NextRequest, NextResponse } from 'next/server';
import { proxyPng } from '@/lib/experimentalProxy';
export async function GET(_r: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return NextResponse.json({ error: 'Invalid record id' }, { status: 400 });
  return proxyPng(`/experimental/records/${id}/crop`);
}

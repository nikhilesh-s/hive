import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';
const OK = /^[a-z0-9]{6,32}$/;
export async function GET(_r: NextRequest, { params }: { params: Promise<{ job: string }> }) {
  const { job } = await params;
  if (!OK.test(job)) return NextResponse.json({ error: 'Invalid job id' }, { status: 400 });
  return proxyJson(`/experimental/ingest/${job}`);
}
export async function DELETE(_r: NextRequest, { params }: { params: Promise<{ job: string }> }) {
  const { job } = await params;
  if (!OK.test(job)) return NextResponse.json({ error: 'Invalid job id' }, { status: 400 });
  return proxyJson(`/experimental/ingest/${job}`, { method: 'DELETE' });
}

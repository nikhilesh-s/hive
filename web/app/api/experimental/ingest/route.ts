import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '@/lib/experimentalProxy';

export async function GET() { return proxyJson('/experimental/ingest'); }

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object') {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }
  const {
    doi, force, reuse, query, title, abstract, authors, journal, year, pmid, pmcid, source,
    access_status, access_url, access_source,
    relevance_status, relevance_score, relevance_reason,
  } = body as Record<string, unknown>;

  return proxyJson('/experimental/ingest', {
    method: 'POST',
    body: {
      doi,
      force: Boolean(force),
      reuse: Boolean(reuse),
      query,
      title,
      abstract,
      authors,
      journal,
      year,
      pmid,
      pmcid,
      source,
      access_status,
      access_url,
      access_source,
      relevance_status,
      relevance_score,
      relevance_reason,
    },
  });
}

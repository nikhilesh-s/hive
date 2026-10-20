import { NextResponse } from 'next/server';
import { clientIpHeader } from './clientIp';

// Server-side proxy helper for the EXPERIMENTAL backend routes. Same trust
// model as the beta proxies: INTERNAL_API_KEY never reaches the browser.
const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

export async function proxyJson(path: string, init?: { method?: string; body?: unknown }) {
  if (!BACKEND_URL) return NextResponse.json({ error: 'Not configured' }, { status: 500 });
  try {
    const resp = await fetch(`${BACKEND_URL}${path}`, {
      method: init?.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
        ...(await clientIpHeader()),
      },
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
    });
    const data = await resp.json().catch(() => ({}));
    const retryAfter = resp.headers.get('Retry-After'); // the job poll honours it
    return NextResponse.json(data, { status: resp.status, headers: retryAfter ? { 'Retry-After': retryAfter } : undefined });
  } catch {
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 502 });
  }
}

export async function proxyPng(path: string) {
  if (!BACKEND_URL) return NextResponse.json({ error: 'Not configured' }, { status: 500 });
  try {
    const resp = await fetch(`${BACKEND_URL}${path}`, {
      headers: {
        ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
        ...(await clientIpHeader()),
      },
    });
    if (!resp.ok) return NextResponse.json({ error: `Backend returned ${resp.status}` }, { status: resp.status });
    return new NextResponse(resp.body, { status: 200, headers: { 'Content-Type': 'image/png', 'Cache-Control': 'private, max-age=3600' } });
  } catch {
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 502 });
  }
}

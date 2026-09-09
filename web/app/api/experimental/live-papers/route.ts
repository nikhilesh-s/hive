import { proxyJson } from '@/lib/experimentalProxy';
export async function GET() { return proxyJson('/experimental/live/papers'); }

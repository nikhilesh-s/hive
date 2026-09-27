import { headers } from 'next/headers';

// Every API call reaches Render from this server, so without this header all
// researchers share one rate-limit bucket. The API trusts it only alongside
// INTERNAL_API_KEY (api/app/limiter.py). Vercel sets x-real-ip itself.
export async function clientIpHeader(): Promise<Record<string, string>> {
  const h = await headers();
  const ip = h.get('x-real-ip') || h.get('x-forwarded-for')?.split(',')[0]?.trim();
  return ip ? { 'X-Hive-Client-IP': ip } : {};
}

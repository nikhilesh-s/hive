export interface OutreachAttribution {
  lab_tag?: string;
  utm_source?: string;
}

const LAB_KEY = 'hiveblot_lab_tag';
const UTM_SOURCE_KEY = 'hiveblot_utm_source';
const LAB_RE = /^[a-z0-9_]{1,40}$/;
const UTM_RE = /^[A-Za-z0-9_.-]{1,80}$/;

function storage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function clean(value: string | null, pattern: RegExp): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  return pattern.test(trimmed) ? trimmed : undefined;
}

export function captureAttributionFromUrl(search = typeof window !== 'undefined' ? window.location.search : ''): OutreachAttribution {
  const store = storage();
  if (!store || !search) return {};
  const params = new URLSearchParams(search);
  const labTag = clean(params.get('lab'), LAB_RE);
  const utmSource = clean(params.get('utm_source'), UTM_RE);
  if (labTag) store.setItem(LAB_KEY, labTag);
  if (utmSource) store.setItem(UTM_SOURCE_KEY, utmSource);
  return getAttribution();
}

export function getAttribution(): OutreachAttribution {
  const store = storage();
  if (!store) return {};
  const labTag = clean(store.getItem(LAB_KEY), LAB_RE);
  const utmSource = clean(store.getItem(UTM_SOURCE_KEY), UTM_RE);
  const attribution: OutreachAttribution = {};
  if (labTag) attribution.lab_tag = labTag;
  if (utmSource) attribution.utm_source = utmSource;
  return attribution;
}

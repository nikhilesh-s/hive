// Ingest job statuses that never change again (see STAGES in
// api/app/experimental/ingest.py). Polling stops and the paper buttons unlock.
export const jobFinished = (status: string | undefined) =>
  status === 'done' || status === 'failed' || status === 'awaiting_full_text';

// 429 (rate limited) and 503 (cold start) while polling mean "ask again later",
// not "job lost": the job keeps running server-side.
export const transientPoll = (httpStatus: number) => httpStatus === 429 || httpStatus === 503;
// Stop riding out throttling once the job is this old.
export const POLL_LIMIT_MS = 20 * 60 * 1000;
// Wait before the next poll after a 429/503: Retry-After (seconds or HTTP date) if sent,
// else 2 s doubling per consecutive hit; capped at 30 s either way.
export function pollBackoffMs(attempt: number, retryAfter?: string | null, now = Date.now()) {
  const secs = retryAfter?.trim() ? Number(retryAfter) : NaN;
  const until = retryAfter && Number.isNaN(secs) ? Date.parse(retryAfter) - now : NaN;
  const ms = secs >= 0 ? secs * 1000 : until >= 0 ? until : 2000 * 2 ** attempt;
  return Math.min(ms, 30000);
}

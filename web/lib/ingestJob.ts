// Ingest job statuses that never change again (see STAGES in
// api/app/experimental/ingest.py). Polling stops and the paper buttons unlock.
export const jobFinished = (status: string | undefined) =>
  status === 'done' || status === 'failed' || status === 'awaiting_full_text';

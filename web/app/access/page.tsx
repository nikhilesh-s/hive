import { safeNext } from '@/lib/betaAccess';

export const metadata = { title: 'Beta access · HiveBlot' };

export default async function AccessPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { next, error } = await searchParams;
  return (
    <div className="hb-history-page">
      <div className="hb-history-shell">
        <header className="hb-history-header">
          <div>
            <div className="hb-history-kicker">BETA ACCESS</div>
            <h1>Enter your beta access code</h1>
            <p>
              Live extraction and paper Q&amp;A run paid model calls, so they need the code from
              your invite email. Search over the reviewed papers is open to everyone.
            </p>
          </div>
        </header>
        {error && <div className="hb-history-error" role="alert">That code didn&apos;t match. Check your invite email.</div>}
        <form method="post" action="/api/access" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input type="hidden" name="next" value={safeNext(next)} />
          <input id="code" name="code" type="password" autoComplete="off" required autoFocus
                 aria-label="Access code"
                 placeholder="Access code" style={{ padding: '8px 10px', minWidth: 220, fontSize: 16 }} />
          <button type="submit" className="hb-history-clear">CONTINUE</button>
        </form>
      </div>
    </div>
  );
}

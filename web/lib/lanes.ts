// Display-only lane-label formatting (semantics untouched): " / " separators
// become interpuncts and a TRAILING +/− state marker gets a colon, so
// "IL-6 + / CL-E -" reads "IL-6: + · CL-E: −". A "+" that joins a drug name
// ("CL-E + Bis II") is a conjunction and is left alone.
export function formatLaneLabel(c?: string | null): string {
  if (!c) return '';
  return c
    .replace(/(\S+) ([+-])(?=$| \/ )/g, (_m, name, sign) => `${name}: ${sign === '-' ? '−' : '+'}`)
    .replace(/ \/ /g, ' · ');
}

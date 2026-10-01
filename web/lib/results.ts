// Shared result-row typing and experiment grouping for the search page and
// the experimental live-extraction page. One card per EXPERIMENT (the hash
// half of stable_row_key), never one card per lane row.

import type { LaneSummary } from '@/components/DatabaseResultCard';

export interface DatabaseResult {
  id: number;
  paper_id: string;
  page: number | null;
  western_blot_type: string;
  sample: string;
  organism: string | null;
  treatment_context: string | null;
  figure_label: string | null;
  target: string;
  condition: string;
  band_detected: boolean;
  confidence: number | null;
  image_crop_ref?: string | null;
  lane_condition?: string | null;
  band_state?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  modification_label?: string | null;
  stable_row_key?: string | null;
  experiment_key?: string | null;
  saved_at?: string | null;
  review_tier?: string | null;
  job_id?: string | null;
}

export interface ResultGroup {
  first: DatabaseResult;
  lanes: LaneSummary[];
  sourceRows: DatabaseResult[];
}

export function groupResults(rows: DatabaseResult[]): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const r of rows) {
    const key = r.experiment_key || (
      r.stable_row_key
        ? r.stable_row_key.split(':')[0]
        : [r.paper_id, r.image_crop_ref ?? `p${r.page}`, r.target, r.experiment_type ?? '', r.cell_line ?? r.sample ?? '', r.modification_label ?? ''].join('|')
    );
    const lane: LaneSummary = {
      condition: r.lane_condition ?? r.condition ?? null,
      band_state: r.band_state ?? (r.band_detected == null ? null : r.band_detected ? 'present' : 'absent'),
    };
    const g = groups.get(key);
    if (g) {
      g.lanes.push(lane);
      g.sourceRows.push(r);
    } else {
      groups.set(key, { first: r, lanes: [lane], sourceRows: [r] });
    }
  }
  return [...groups.values()];
}

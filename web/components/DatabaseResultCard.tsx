'use client';

import { useState, type ReactNode } from 'react';

import EvidencePanel from '@/components/EvidencePanel';

// NOTE: every Evidence Record field below is OPTIONAL. Legacy rows (pre-migration
// 001) simply omit them and the card falls back to the original base fields, so
// existing search never breaks. New fields render only when present -- a missing
// value shows as "not reported", never as fabricated data.
interface DatabaseResult {
  id: number;
  paper_id: string;
  page: number | null;
  western_blot_type: string | null;
  sample: string | null;
  organism: string | null;
  treatment_context: string | null;
  figure_label: string | null;
  target: string;
  condition: string | null;
  band_detected: boolean | null;
  confidence: number | null;
  // --- Evidence Record additions (all optional) ---
  canonical_target?: string | null;
  uniprot_id?: string | null;
  protein_status?: string | null;
  modification_label?: string | null;
  modification_status?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  treatment_name?: string | null;
  dose?: number | null;
  dose_unit?: string | null;
  duration?: number | null;
  duration_unit?: string | null;
  antibody_vendor?: string | null;
  antibody_catalog_number?: string | null;
  antibody_dilution?: string | null;
  band_state?: string | null;
  reported_molecular_weight_kda?: number | null;
  expected_molecular_weight_kda?: number | null;
  figure_caption?: string | null;
  needs_review?: boolean | null;
  anomaly_flags?: Array<{ code?: string; message?: string }> | null;
  doi?: string | null;
  pmcid?: string | null;
  title?: string | null;
}

export interface LaneSummary {
  condition: string | null;
  band_state: string | null;
}

interface DatabaseResultCardProps {
  data: DatabaseResult;
  // When search results are grouped into one card per experiment (paper +
  // panel + target), `lanes` carries every lane of the group so a researcher
  // reads ONE experiment instead of N near-identical rows. Optional: a card
  // without it renders the single row exactly as before.
  lanes?: LaneSummary[];
}

const MONO = '"IBM Plex Mono", monospace';
const SERIF = '"Newsreader", serif';
const LABEL = '#6f857d';
const TEXT = '#e7f0ee';
const TEAL = '#4ad6b0';
const GOLD = '#e0b23c';
const RED = '#ff6b6b';
const DIMTEXT = '#a9bdb5';

function titleCase(s?: string | null): string {
  if (!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

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

// Deterministic experiment-design tag derived ONLY from the group's own lane
// labels (data-backed, never invented): ≥3 pure-timepoint lanes = a time
// course; ≥3 lanes sharing a prefix with distinct trailing numbers = a dose
// series. Anything else: no tag.
export function deriveDesignTag(lanes?: LaneSummary[]): string | null {
  if (!lanes || lanes.length < 3) return null;
  const conds = lanes.map((l) => (l.condition || '').trim()).filter(Boolean);
  if (conds.length < 3) return null;
  const timepoints = conds.filter((c) => /^\d+(\.\d+)?\s*(min|mins|h|hr|hrs|d)$/i.test(c));
  if (timepoints.length >= 3) return 'time course';
  const trailing = conds
    .map((c) => /^(.*?)(\d+(?:\.\d+)?)$/.exec(c))
    .filter((m): m is RegExpExecArray => !!m && m[1].trim().length > 0);
  if (trailing.length >= 3) {
    const prefixes = new Set(trailing.map((m) => m[1].trim()));
    const numbers = new Set(trailing.map((m) => m[2]));
    if (prefixes.size === 1 && numbers.size >= 3) return 'dose series';
  }
  return null;
}

// Supported / Needs review / Conflicting -- derived, never asserted beyond evidence.
function reviewState(d: DatabaseResult): { label: string; color: string } | null {
  const statuses = [d.protein_status, d.modification_status];
  if (statuses.includes('CONFLICTING')) return { label: 'Conflicting', color: RED };
  if (d.needs_review === true || statuses.includes('AMBIGUOUS')) return { label: 'Needs review', color: GOLD };
  if (d.needs_review === false) return { label: 'Supported', color: TEAL };
  return null;
}

function Field({ label, value, mono, color }: { label: string; value: ReactNode; mono?: boolean; color?: string }) {
  return (
    <div>
      <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: LABEL, marginBottom: '4px', letterSpacing: '0.4px' }}>
        {label}
      </div>
      <div style={{ fontFamily: mono ? MONO : SERIF, fontSize: mono ? '13px' : '14px', color: color || TEXT, lineHeight: 1.3 }}>
        {value}
      </div>
    </div>
  );
}

export default function DatabaseResultCard({ data, lanes }: DatabaseResultCardProps) {
  const [expanded, setExpanded] = useState(false);

  const headline = data.canonical_target || data.target;
  const headlineMod = data.modification_label ? ` · ${data.modification_label}` : '';
  const review = reviewState(data);
  const blotType = data.experiment_type || data.western_blot_type;
  const sampleText = data.cell_line || data.sample;
  const bandText = data.band_state || (data.band_detected == null ? null : data.band_detected ? 'present' : 'absent');
  const antibody = [data.antibody_vendor, data.antibody_catalog_number ? `#${data.antibody_catalog_number}` : null]
    .filter(Boolean)
    .join(' · ');
  // Structured name·dose·duration only. The verbatim treatment_context now has
  // its own identity line under the headline — falling back to it here printed
  // the same sentence twice on cards with no parsed treatment name.
  const treatment =
    data.treatment_name || data.dose != null
      ? [
          data.treatment_name,
          data.dose != null ? `${data.dose}${data.dose_unit || ''}` : null,
          data.duration != null ? `${data.duration}${data.duration_unit || ''}` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;
  const mw =
    data.reported_molecular_weight_kda != null || data.expected_molecular_weight_kda != null
      ? [
          data.reported_molecular_weight_kda != null ? `reported ${data.reported_molecular_weight_kda} kDa` : null,
          data.expected_molecular_weight_kda != null ? `expected ${data.expected_molecular_weight_kda} kDa` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  const bandColor = bandText === 'present' ? TEAL : bandText === 'absent' ? RED : GOLD;
  const hasEvidence = Boolean(data.figure_caption || antibody || treatment || mw || data.uniprot_id);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'rgba(255,255,255,.07)',
        borderRadius: '6px',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,.06)',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 56px', gap: '0' }}>
      <div style={{ backgroundColor: '#06090c', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Biological headline + review badge */}
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ fontFamily: SERIF, fontSize: '19px', color: TEAL, lineHeight: 1.2 }}>
            {headline}
            <span style={{ color: TEXT }}>{headlineMod}</span>
          </div>
          {review && (
            <span
              style={{
                fontFamily: MONO,
                fontSize: '10px',
                fontWeight: 600,
                color: review.color,
                border: `1px solid ${review.color}`,
                borderRadius: '4px',
                padding: '2px 8px',
                letterSpacing: '0.4px',
                whiteSpace: 'nowrap',
              }}
            >
              {review.label}
            </span>
          )}
        </div>
        {/* raw label when it differs from the canonical headline */}
        {data.canonical_target && data.target && data.canonical_target !== data.target && (
          <div style={{ fontFamily: MONO, fontSize: '11px', color: LABEL, marginTop: '-12px' }}>as printed: {data.target}</div>
        )}
        {/* Experiment identity: WHY this card is distinct from its siblings.
            Design tag is derived only from this group's own lane labels; the
            context text is the reviewed record's treatment_context verbatim
            (truncated). Nothing here is invented. */}
        {(deriveDesignTag(lanes) || data.treatment_context) && (
          <div style={{ fontFamily: SERIF, fontSize: '12px', color: DIMTEXT, marginTop: '-8px', fontStyle: 'italic' }}>
            {deriveDesignTag(lanes) && (
              <span style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: TEAL, fontStyle: 'normal', letterSpacing: '0.4px', marginRight: '8px' }}>
                {deriveDesignTag(lanes)!.toUpperCase()}
              </span>
            )}
            {data.treatment_context && (
              data.treatment_context.length > 110
                ? data.treatment_context.slice(0, 110) + '…'
                : data.treatment_context
            )}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {sampleText && <Field label="SAMPLE" value={sampleText} />}
            {blotType && <Field label="EXPERIMENT" value={titleCase(blotType)} />}
            {antibody && <Field label="ANTIBODY" value={antibody} mono />}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {treatment && <Field label="TREATMENT" value={treatment} />}
            {lanes && lanes.length > 1 ? (
              <Field
                label={`LANES (${lanes.length})`}
                value={
                  <span style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                    {lanes.slice(0, 8).map((l, i) => (
                      <span key={i} style={{
                        fontFamily: MONO, fontSize: '10px', padding: '2px 7px', borderRadius: '4px',
                        border: '1px solid rgba(255,255,255,.1)',
                        color: l.band_state === 'present' ? TEAL : l.band_state === 'absent' ? RED : GOLD,
                      }}>
                        {formatLaneLabel(l.condition) || `lane ${i + 1}`}
                      </span>
                    ))}
                    {lanes.length > 8 && (
                      <span style={{ fontFamily: MONO, fontSize: '10px', color: LABEL }}>
                        +{lanes.length - 8} more
                      </span>
                    )}
                  </span>
                }
              />
            ) : (
              bandText && <Field label="BAND" value={titleCase(bandText)} color={bandColor} />
            )}
            {mw && <Field label="MOLECULAR WEIGHT" value={mw} mono />}
          </div>
        </div>

        {/* Metadata footer */}
        {(data.organism || data.figure_label || data.page || data.paper_id) && (
          <div style={{ paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,.08)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              {data.figure_label && (
                <div>
                  <span style={{ color: LABEL, fontSize: '10px', fontWeight: 600 }}>Figure: </span>
                  <span style={{ color: TEXT, fontSize: '12px' }}>{data.figure_label}</span>
                </div>
              )}
              {data.organism && !data.cell_line && (
                <div>
                  <span style={{ color: LABEL, fontSize: '10px', fontWeight: 600 }}>Organism: </span>
                  <span style={{ color: TEXT, fontSize: '12px' }}>{data.organism}</span>
                </div>
              )}
              {data.paper_id && (
                <div>
                  <span style={{ color: LABEL, fontSize: '10px', fontWeight: 600 }}>Paper: </span>
                  <span style={{ color: '#a9bdb5', fontFamily: MONO, fontSize: '12px' }}>{data.paper_id}</span>
                </div>
              )}
              {data.page && (
                <div>
                  <span style={{ color: LABEL, fontSize: '10px', fontWeight: 600 }}>Page: </span>
                  <span style={{ color: TEXT, fontSize: '12px' }}>{data.page}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Evidence toggle rail. The evidence itself renders as a full-width
          accordion below (captions + field audits need horizontal room; the
          old 300px rail truncated them). */}
      <button
        aria-expanded={expanded}
        aria-label={expanded ? 'Hide evidence' : 'Show evidence — why HiveBlot says this'}
        onClick={() => setExpanded(!expanded)}
        style={{
          backgroundColor: '#0a0d0f',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderLeft: '1px solid rgba(255,255,255,.06)',
          border: 'none',
          cursor: 'pointer',
          padding: '8px',
        }}
      >
        <span
          style={{
            fontFamily: MONO,
            fontSize: '9px',
            fontWeight: 600,
            color: TEAL,
            writingMode: 'vertical-rl',
            textOrientation: 'mixed',
            letterSpacing: '0.8px',
          }}
        >
          {expanded ? 'CLOSE' : 'EVIDENCE'}
        </span>
      </button>
      </div>

      {/* Full-width provenance + per-field feedback accordion */}
      {expanded && <EvidencePanel recordId={data.id} />}
    </div>
  );
}

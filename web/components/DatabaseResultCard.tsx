'use client';

import { useState, type ReactNode } from 'react';

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

interface DatabaseResultCardProps {
  data: DatabaseResult;
}

const MONO = '"IBM Plex Mono", monospace';
const SERIF = '"Newsreader", serif';
const LABEL = '#6f857d';
const TEXT = '#e7f0ee';
const TEAL = '#4ad6b0';
const GOLD = '#e0b23c';
const RED = '#ff6b6b';

function titleCase(s?: string | null): string {
  if (!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
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

export default function DatabaseResultCard({ data }: DatabaseResultCardProps) {
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
  const treatment =
    data.treatment_name || data.dose != null || data.treatment_context
      ? [
          data.treatment_name,
          data.dose != null ? `${data.dose}${data.dose_unit || ''}` : null,
          data.duration != null ? `${data.duration}${data.duration_unit || ''}` : null,
        ]
          .filter(Boolean)
          .join(' · ') || data.treatment_context
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
        display: 'grid',
        gridTemplateColumns: expanded ? '1fr 300px' : '1fr 56px',
        gap: '0',
        backgroundColor: 'rgba(255,255,255,.07)',
        borderRadius: '6px',
        overflow: 'hidden',
        transition: 'grid-template-columns 0.25s ease',
        border: '1px solid rgba(255,255,255,.06)',
      }}
    >
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

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {sampleText && <Field label="SAMPLE" value={sampleText} />}
            {blotType && <Field label="EXPERIMENT" value={titleCase(blotType)} />}
            {antibody && <Field label="ANTIBODY" value={antibody} mono />}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {treatment && <Field label="TREATMENT" value={treatment} />}
            {bandText && <Field label="BAND" value={titleCase(bandText)} color={bandColor} />}
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

      {/* Evidence / provenance panel */}
      <div
        style={{
          backgroundColor: '#0a0d0f',
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid rgba(255,255,255,.06)',
          cursor: 'pointer',
          overflow: 'hidden',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px 18px', gap: '14px', overflowY: 'auto' }}>
            <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: TEAL, letterSpacing: '0.6px' }}>
              WHY HIVEBLOT SAYS THIS
            </div>
            {data.uniprot_id && (
              <Field label="UNIPROT" value={data.uniprot_id} mono />
            )}
            {mw && <div style={{ fontFamily: SERIF, fontSize: '12px', color: '#a9bdb5' }}>MW — {mw} (expected from UniProt reference; reported = as stated in paper)</div>}
            {antibody && (
              <div style={{ fontFamily: SERIF, fontSize: '12px', color: '#a9bdb5' }}>
                Antibody — {antibody}
                {data.antibody_dilution ? ` · ${data.antibody_dilution}` : ''}
              </div>
            )}
            {treatment && <div style={{ fontFamily: SERIF, fontSize: '12px', color: '#a9bdb5' }}>Treatment — {treatment}</div>}
            {data.figure_caption && (
              <div>
                <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: LABEL, marginBottom: '4px' }}>CAPTION</div>
                <div style={{ fontFamily: SERIF, fontSize: '12px', color: TEXT, lineHeight: 1.4 }}>{data.figure_caption}</div>
              </div>
            )}
            {data.anomaly_flags && data.anomaly_flags.length > 0 && (
              <div>
                <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: GOLD, marginBottom: '4px' }}>FLAGS</div>
                {data.anomaly_flags.map((a, i) => (
                  <div key={i} style={{ fontFamily: MONO, fontSize: '11px', color: GOLD }}>{a.code || a.message}</div>
                ))}
              </div>
            )}
            {(data.doi || data.pmcid) && (
              <div style={{ marginTop: 'auto', fontFamily: MONO, fontSize: '11px', color: '#a9bdb5' }}>
                {data.pmcid ? `${data.pmcid}` : ''}
                {data.doi ? ` · ${data.doi}` : ''}
              </div>
            )}
            {!hasEvidence && (
              <div style={{ fontFamily: SERIF, fontSize: '12px', color: '#a9bdb5' }}>
                No structured evidence on this legacy record yet.
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '8px' }}>
            <div
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
              EVIDENCE
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

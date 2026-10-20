'use client';

// Teaches what HiveBlot actually reports: field-level evidence statuses,
// categorical band presence (no densitometry), expected vs reported MW, and
// the terms a result card uses. Generic blot theory is kept to the minimum a
// non-blot user needs to read a card.

const MONO = 'var(--font-mono), monospace';

const STATUSES: { name: string; color: string; badge: string; text: string }[] = [
  {
    name: 'SUPPORTED', color: 'var(--accent)', badge: 'Supported',
    text: 'The available sources agree on the value, and no validation or ambiguity flag remains.',
  },
  {
    name: 'AMBIGUOUS', color: 'var(--warning)', badge: 'Needs review',
    text: 'More than one interpretation remains plausible, or the value legitimately varies within the panel (a time course, a dose series, a label that maps to a protein family such as ERK1/2 = MAPK1/MAPK3). The value is retained with an ambiguity flag rather than presented as a settled fact.',
  },
  {
    name: 'CONFLICTING', color: 'var(--error)', badge: 'Conflicting',
    text: 'Credible sources actively disagree. HiveBlot records no value at all, shows every competing claim with where it came from, and explains why it did not pick one. This is a feature: it is what makes the Supported badge mean something.',
  },
  {
    name: 'NOT_STATED', color: 'var(--text-subtle)', badge: 'Not reported',
    text: 'HiveBlot examined the relevant available paper text for this field and found no stated value. This is a claim about what the available source says, so it is only used when source coverage supports that conclusion.',
  },
  {
    name: 'NOT_RECOVERED', color: 'var(--warning)', badge: 'Not recovered',
    text: 'HiveBlot could not reliably recover or associate the value from the available source. This is an extraction limitation, not a claim that the authors omitted the information.',
  },
  {
    name: 'MISSING', color: 'var(--text-subtle)', badge: 'Unavailable',
    text: 'Legacy records may use MISSING when the reason for an unavailable value was not recorded. HiveBlot does not reinterpret those historical nulls as "not reported".',
  },
];

const GLOSSARY: [string, string][] = [
  ['IgG', 'Immunoglobulin G, the antibody class used for detection and immunoprecipitation. In a co-IP figure the "IgG" lane is the negative control: a non-specific antibody of the same class, so anything it pulls down is background rather than a real interaction.'],
  ['IP bait', 'The protein an immunoprecipitation antibody captures out of the lysate (printed as "IP: PIK3CA" on the figure). Proteins that come down with it and are blotted in the IP lanes are the readouts, i.e. candidate interaction partners.'],
  ['Input', 'A sample of the lysate taken before immunoprecipitation and run beside the IP lanes. It shows the proteins were present to begin with and that loading was comparable; it says nothing about interaction on its own.'],
  ['phospho / site', 'A phospho-specific antibody recognizes a protein only when a particular residue is phosphorylated; the site names that residue (Tyr705 = tyrosine 705, Ser473 = serine 473). HiveBlot records phosphorylation only when the antibody or the printed label states it. A "p-" or "P-" prefix on its own is not evidence (P-selectin and P-cadherin are not phosphoproteins), which is why some rows stay Conflicting.'],
  ['loading control', 'An reference protein (β-actin/ACTB, GAPDH, tubulin) blotted on the same membrane to show that comparable amounts of protein were loaded in each lane. It supports the comparison; it says nothing about the target itself.'],
  ['doublet', 'Two closely spaced bands for one target. HiveBlot records a doublet or smear as a description of what the blot shows and never assigns the second band to an isoform, cleavage product or modification.'],
  ['kDa', 'Kilodalton, the unit of molecular mass. A band position is reported in kDa by reading it against the marker ladder run on the same gel.'],
  ['expected vs reported MW', 'Expected molecular weight is the reference mass computed from the UniProt sequence for the resolved protein. Reported molecular weight is only what the paper itself printed for the band. They are kept apart because they legitimately differ (modifications, glycosylation, running behavior), and HiveBlot never reads mass off an image without a printed ladder calibration.'],
  ['as printed', 'The target label exactly as it appears in the figure. It is always kept beside the normalized name so you can check the normalization yourself.'],
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="hb-page-section">
      <h2 className="hb-page-h2">{title}</h2>
      {children}
    </section>
  );
}

export default function Learn() {
  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <h1 className="hb-page-h1">How to read a HiveBlot result</h1>
        <p className="hb-page-lead">
          A result is one Western blot experiment: one panel, one target, one sample,
          one treatment design, with every lane listed. This page explains what each
          part of a card and its evidence panel means, and what HiveBlot deliberately
          does not claim.
        </p>
      </section>

      <Section title="What one result represents">
        <p className="hb-page-p">
          Searching returns experiments, not sentences. Each card is one blot panel for one target within a specific experimental context: the normalized protein name (with the
          label <em>as printed</em> underneath when they differ), a status badge, the
          sample or cell line and organism, the experiment type (Western, phospho
          Western, co-IP, loading control), the treatment and dose/duration when the
          paper states them, every lane with its printed condition, the antibody and
          catalog number, molecular weight, the UniProt accession and the DOI. Open{' '}
          <strong>Evidence</strong> on a card to see the figure crop, the field-level
          sources and the feedback controls.
        </p>
      </Section>

      <Section title="Evidence statuses">
        <p className="hb-page-p">
          Every important field carries a status. The card badge summarizes the record;
          the evidence panel shows the status per field.
        </p>
        <div className="hb-status-grid">
          {STATUSES.map((s) => (
            <div key={s.name} className="hb-status-card" style={{ borderLeftColor: s.color }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '6px' }}>
                <span style={{ fontFamily: MONO, fontSize: '12px', fontWeight: 600, color: s.color }}>{s.name}</span>
                <span style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--text-subtle)' }}>badge: {s.badge}</span>
              </div>
              <p className="hb-page-p" style={{ margin: 0, fontSize: '14px' }}>{s.text}</p>
            </div>
          ))}
        </div>
        <p className="hb-page-p">
          <strong>Needs review</strong> on a card means at least one field is
          Ambiguous or a validation flag fired. The card lists the reason (for example
          <em> Protein name maps to more than one reviewed UniProt entry</em>) so you can
          decide whether it matters for your question without opening the evidence panel.
        </p>
      </Section>

      <Section title="What a lane tells you (and what it does not)">
        <p className="hb-page-p">
          Each lane is shown with its printed condition and a categorical band state:
          <span style={{ color: 'var(--accent)' }}> present</span>,
          <span style={{ color: 'var(--error)' }}> absent</span> or
          <span style={{ color: 'var(--warning)' }}> uncertain</span>. HiveBlot does
          not measure band intensity, does not report fold changes, and does not call a
          protein up- or down-regulated. That is densitometry, and it is out of scope by
          design: an intensity read off a figure without the original exposure is not a
          measurement. If a lane is faint or hard to judge from the published image it is
          marked uncertain rather than guessed. The band reading page is the
          one exception, and it is kept apart from the records: it reports uncalibrated,
          within-one-image relative band darkness with a quality state, refuses clipped or
          unstable readings, and writes nothing back.
        </p>
        <p className="hb-page-p">
          When a panel is a time course or dose series, the panel-level dose or duration
          is shown as varying by lane and the per-lane values live on the lanes
          themselves. When one panel mixes several agents with different units, the
          panel-level dose stays unsettled and the treatment context describes the design.
        </p>
      </Section>

      <Section title="Where each value comes from">
        <p className="hb-page-p">
          The evidence panel tags each field with its source: <span style={{ fontFamily: MONO }}>caption</span>,{' '}
          <span style={{ fontFamily: MONO }}>methods</span>, <span style={{ fontFamily: MONO }}>antibody</span> (the reagent
          entry), <span style={{ fontFamily: MONO }}>model reading</span> (the extractor&apos;s own wording or its reading of the
          printed row label, used when the words are not found verbatim in the caption or methods),{' '}
          <span style={{ fontFamily: MONO }}>image</span> (the panel itself, for lane conditions and band presence) or{' '}
          <span style={{ fontFamily: MONO }}>UniProt</span> (canonical name, accession, expected mass). Where the source is
          a sentence from the paper, the sentence is quoted; a model reading is labelled as one and is never shown as a quote. Every panel links to the DOI so the paper
          is one click away. Corrections you submit are stored beside the extraction as
          an auditable pair and are never applied over it.
        </p>
      </Section>

      <Section title="Western blot basics, briefly">
        <div className="hb-two-col">
          <div>
            <h3 className="hb-page-h3">1. Extraction and loading</h3>
            <p className="hb-page-p">Proteins are extracted from cells or tissue and loaded onto a gel, often with comparable amounts so differences between lanes can be interpreted in context.</p>
            <h3 className="hb-page-h3">2. Separation by size</h3>
            <p className="hb-page-p">An electric field moves proteins through the gel; smaller proteins travel further. A marker ladder gives the size scale in kDa.</p>
          </div>
          <div>
            <h3 className="hb-page-h3">3. Transfer to a membrane</h3>
            <p className="hb-page-p">Proteins are transferred onto a nitrocellulose or PVDF membrane for detection.</p>
            <h3 className="hb-page-h3">4. Antibody detection</h3>
            <p className="hb-page-p">A primary antibody binds the target; a labeled secondary antibody makes the band visible. The antibody is why the same target can look different across papers.</p>
          </div>
        </div>
      </Section>

      <Section title="Glossary">
        <dl className="hb-glossary">
          {GLOSSARY.map(([term, def]) => (
            <div key={term} className="hb-glossary-row">
              <dt>{term}</dt>
              <dd>{def}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </div>
  );
}

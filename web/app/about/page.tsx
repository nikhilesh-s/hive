'use client';

// Every number and capability claim on this page must be traceable to
// HANDOFF.md / research/TEAM_BETA_HANDOFF.md. Nothing here may imply
// literature-wide coverage, automated ingestion accuracy, or densitometry.

const MONO = 'var(--font-mono), monospace';

const PAPERS: [string, string][] = [
  ['10.3892/br.2026.2108', 'phospho-STAT3 / IL-6 time course and inhibitor matrix in Hep3B cells (human)'],
  ['10.3892/ijmm.2022.5188', 'loading-control validation across mouse submandibular gland development and duct ligation'],
  ['10.1186/s12964-025-02385-8', 'BEX2 / PIK3CA co-immunoprecipitation in H1792, H1299 and A549 cells (human)'],
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="hb-page-section">
      <h2 className="hb-page-h2">{title}</h2>
      {children}
    </section>
  );
}

export default function About() {
  return (
    <div className="hb-page">
      <section className="hb-page-hero">
        <h1 className="hb-page-h1">About HiveBlot</h1>
        <p className="hb-page-lead">
          HiveBlot turns published Western blot figures, captions and methods into
          structured, searchable, auditable <em>experiment-level</em> evidence: which
          protein, modified where, in which cells, under what treatment, detected with
          which antibody, and what the blot showed lane by lane.
        </p>
      </section>

      <Section title="Who it is for">
        <p className="hb-page-p">
          Wet-lab researchers who need to locate and compare experiment-level Western
          blot evidence. The sharpest questions it is built for: has this antibody or
          catalog number already appeared in published work, and what did the blot look
          like? Has this protein been blotted in this cell line under this treatment?
          Can I trust this row, and where exactly did each value come from?
        </p>
      </Section>

      <Section title="What the beta contains today">
        <div className="hb-stat-row" aria-label="Current corpus size">
          <div className="hb-stat"><div className="hb-stat-n">3</div><div className="hb-stat-l">REVIEWED PAPERS</div></div>
          <div className="hb-stat"><div className="hb-stat-n">93</div><div className="hb-stat-l">EXPERIMENT GROUPS</div></div>
          <div className="hb-stat"><div className="hb-stat-n">475</div><div className="hb-stat-l">EVIDENCE ROWS</div></div>
        </div>
        <p className="hb-page-p">
          The corpus is intentionally small and reviewed. Every row was checked
          field-by-field by a human and then by an independent scientific QA pass. One
          row is one lane of one blot panel; rows group into experiments. The three
          papers:
        </p>
        <ul className="hb-page-list">
          {PAPERS.map(([doi, what]) => (
            <li key={doi}>
              <a href={`https://doi.org/${doi}`} target="_blank" rel="noreferrer" style={{ fontFamily: MONO, color: 'var(--accent)' }}>
                {doi}
              </a>
              <span style={{ color: 'var(--text-secondary)' }}> — {what}</span>
            </li>
          ))}
        </ul>
        <p className="hb-page-p">
          A search that returns nothing usually means the topic is not in these three
          papers. It does not mean no such evidence exists in the literature, and the
          search page says so.
        </p>
      </Section>

      <Section title="What an Evidence Record is">
        <p className="hb-page-p">
          Not a single answer, but a container. Each important field (protein identity,
          phosphosite, cell line, organism, treatment, dose, duration, antibody,
          molecular weight) carries its own value, a status, the source it came from
          (caption, methods, antibody entry, the row label, UniProt) and the wording
          that supports it. The normalized value and the wording as printed in the
          paper are both kept, so every normalization is auditable and reversible.
        </p>
      </Section>

      <Section title="What HiveBlot refuses to do">
        <ul className="hb-page-list">
          <li><strong>It does not guess.</strong> When credible sources disagree, the field is marked <em>Conflicting</em>, keeps no value, and shows both claims.</li>
          <li><strong>It does not fill gaps.</strong> A value the paper never states is shown as <em>not reported</em>, never as a plausible number.</li>
          <li><strong>It does not measure intensity.</strong> Band presence is categorical (present / absent / uncertain). Evidence Records carry no densitometry, and multiplicity such as a doublet is recorded descriptively only. (An experimental, uncalibrated densitometry page exists under <em>Experimental</em>; it measures within one image, refuses clipped or unstable readings, and stores nothing.)</li>
          <li><strong>It does not read mass off an image.</strong> Expected molecular weight comes from the UniProt sequence; reported weight comes only from what the paper printed. They are stored separately.</li>
          <li><strong>It does not overwrite itself.</strong> Researcher corrections are stored beside the extraction as an auditable pair, never applied over it.</li>
        </ul>
      </Section>

      <Section title="What this beta proves, and what it does not">
        <div className="hb-two-col">
          <div>
            <h3 className="hb-page-h3" style={{ color: 'var(--accent)' }}>Demonstrated on the reviewed corpus</h3>
            <ul className="hb-page-list">
              <li>Structured Evidence Records with field-level provenance</li>
              <li>Experiment-level search (protein, phosphosite, antibody, cell line, co-IP, loading control)</li>
              <li>Explicit uncertainty and abstention</li>
              <li>Conflicts preserved rather than silently resolved</li>
              <li>Researcher feedback stored beside model output and surviving reloads</li>
            </ul>
          </div>
          <div>
            <h3 className="hb-page-h3" style={{ color: 'var(--warning)' }}>Not demonstrated yet</h3>
            <ul className="hb-page-list">
              <li>Coverage of the wider literature (the corpus is three papers)</li>
              <li>Automated extraction accuracy on papers HiveBlot has not been shown; the model-reading step for these three papers ran with a human in the loop</li>
              <li>Precision, recall or F1 on unseen papers: no such number exists yet</li>
              <li>Densitometry or any quantitative band-intensity inference</li>
            </ul>
          </div>
        </div>
        <p className="hb-page-p">
          The reviewed corpus is the baseline that automated extraction will be measured
          against. Until that evaluation runs, no accuracy claim about new papers is made
          anywhere on this site.
        </p>
      </Section>

      <Section title="Beta hosting note">
        <p className="hb-page-p">
          The beta runs on free-tier hosting. The first search after a quiet spell can
          take 30–60 seconds while the API wakes up; everything after that is fast.
          A slow first search is the hosting plan, not the product.
        </p>
      </Section>
    </div>
  );
}

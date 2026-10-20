# Third-party notice

The MIT license in [`LICENSE`](LICENSE) covers HiveBlot's own source code and
documentation. It does not cover the third-party material described here.

## Figure crops (not MIT, not in release archives)

The image files under `api/crops/` are crops of figure panels from three
published papers:

| DOI | Link |
|---|---|
| 10.3892/br.2026.2108 | https://doi.org/10.3892/br.2026.2108 |
| 10.3892/ijmm.2022.5188 | https://doi.org/10.3892/ijmm.2022.5188 |
| 10.1186/s12964-025-02385-8 | https://doi.org/10.1186/s12964-025-02385-8 |

These images are not licensed under MIT. They remain under the license and
copyright terms set by each paper's publisher and authors. Check each
article's page for its terms before reusing them. The crops are excluded from
release archives (`export-ignore` in `.gitattributes`), so a downloaded
archive does not contain them. To reproduce the figure-level results, obtain
the papers from their publishers and run the pipeline on your own copies.

## Quoted passages from the same papers

The extracted records in `eval/demo/` store short passages quoted from those
three papers (caption and methods wording) as the source of each field. These
quotes are attributed to their papers by DOI. They are included as provenance
evidence for the extraction, and the copyright in the quoted text remains with
the original authors and publishers.

## Candidate-paper references (citations only)

`eval/candidates.json` lists candidate papers considered for benchmarking.
Those entries are bibliographic citations (authors, title, journal, DOI)
with brief descriptive notes and short caption excerpts attributed by DOI. The
papers themselves, their figures and their full text are not included in this
repository and are not covered by the MIT license.

## Software dependencies

Python and JavaScript dependencies are installed separately from
`api/requirements.txt`, `western_blot_miner/requirements.txt`,
`requirements-local.txt` and `web/package.json`. Each keeps its own license.

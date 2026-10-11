# Product tickets

## W-0.4

**`/experimental/research?doi=<DOI>` opens an already-extracted paper directly.** Owner: Srushti (Codex).

Why: outreach emails are meant to link a researcher straight to their own extracted paper. Today
the research page reads no URL parameters, so a link only opens the empty page.

- When `doi` is present and normalizes to a DOI already in the live tier
  (`western_blot_records_live` / `ingest_jobs` with records), open that paper's evidence view on
  load, the same view as "Open extracted evidence".
- When the DOI is not extracted, prefill the DOI box and show the normal "extract this paper" path.
  Do not start a paid extraction automatically.
- Keep the existing `access` gate (an `?access=` code still works on the same link). `lab` and
  `utm_source` must still be captured (`web/lib` outreach attribution).
- Reject anything that is not a DOI shape; never put it into SQL or HTML unescaped.
- Tests: one with an extracted DOI that opens the evidence, one with an unknown DOI that only
  prefills, and one with a malformed value that is ignored.
- Done when the link pattern in `outreach/PREEXTRACT_CHECK.md` (branch `outreach/oct20`) works on
  the hosted site after O-9.

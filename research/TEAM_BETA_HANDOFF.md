# HiveBlot internal beta — read this first

**For:** the HiveBlot team and the UCSF wet-lab reviewers testing the beta.
**Updated:** 2026-08-17.
**You do not need to know anything about the codebase to use this document.**

---

## Where the beta lives

| | |
|---|---|
| **Web app** | _to be filled in when the frontend is deployed_ |
| **API** | _to be filled in when the API is deployed_ |
| **Database** | Supabase project `zafombwswztvnjikcsdm` — schema applied, 475 reviewed rows loaded, verified |

The database is live and fully verified. The two hosted URLs are pending one
account login (see *Current status* at the bottom). Until they exist, HiveBlot
runs locally against the same cloud database — ask Nikhilesh for the two-command
bring-up.

---

## What HiveBlot currently does

HiveBlot turns Western blot figures, captions, methods and biological context
into **structured, searchable, auditable experimental evidence**.

A published Western blot is a picture plus a caption plus a paragraph buried in
Methods. To know what a band actually means you have to reassemble: which
protein, phosphorylated where, in which cells, under what treatment, at what
dose and for how long, detected with which antibody. HiveBlot does that
reassembly and keeps every claim attached to the wording it came from.

Three things make it different from a normal search tool:

1. **Every field carries its own evidence.** Not one confidence score per
   record — per *field*: the value, where it came from (caption / methods /
   antibody / image / UniProt), and the verbatim source text.
2. **It refuses to guess.** When credible sources disagree, HiveBlot records
   **no value** and shows you both competing claims instead of picking one.
   When something isn't reported, it says "not reported" rather than inventing
   a plausible number.
3. **Your corrections are stored beside the AI's claim, never over it.** Every
   piece of feedback is an auditable "AI said X → human said Y" pair. Nothing
   you submit silently rewrites the extraction.

---

## Current beta scope — please read this carefully

The hosted beta contains a **reviewed reference corpus**:

- **3 papers**
- **91 experiments**
- **475 lane rows**

Every one of those rows was reviewed field-by-field by a human, across several
sessions, plus an independent scientific QA pass.

**This is NOT yet evidence that arbitrary literature ingestion is automatically
biologically accurate.** It is the opposite: it is a carefully checked baseline
we will later measure automated extraction *against*. The three papers went
through the real pipeline, but the model-reading step was done by a human in
the loop because no model credentials were available. So what you are testing
is the **representation, search and review experience** on trustworthy data —
not the accuracy of an automated reader on new papers.

Please don't quote a coverage or accuracy number from this beta. If a search
returns nothing, that usually means the topic isn't in these three papers, not
that no such evidence exists in the literature — the app says so explicitly on
zero-result searches.

The three papers:

| Paper | What it is |
|---|---|
| `10.3892/br.2026.2108` | phospho-STAT3 / IL-6 time course and inhibitor matrix, Hep3B |
| `10.3892/ijmm.2022.5188` | mouse submandibular gland development + duct ligation |
| `10.1186/s12964-025-02385-8` | BEX2 / PIK3CA co-immunoprecipitation, H1792 / H1299 / A549 |

---

## Good searches to try

Type the query and press **Enter** or click **SEARCH** — typing alone does not
search, by design.

| Query | What you should see |
|---|---|
| `phospho STAT3 Tyr705` | 3 experiments (18 lanes). Cards labelled TIME COURSE, an inhibitor matrix, and DOSE SERIES. CST #9145, expected 88.1 kDa. |
| `co-IP PIK3CA` | 4 co-IP experiments. Cards say **co-IP** and show an **IP BAIT** field. Input / IgG / bait lanes intact. |
| `CST 9145` | Antibody/catalog search — returns the same three STAT3 experiments. |
| `GAPDH mouse` | 5 experiments. Loading Control. Developmental panels tagged DEVELOPMENTAL SERIES; the duct-ligation panels are deliberately **untagged**. |
| `needs review` | Everything HiveBlot is not confident about. |
| `P-ERK` | `MAPK1/MAPK3`, badge **Conflicting**. The modification stays unsettled on purpose — see below. |

**Why `P-ERK` stays unresolved** — and why that is the correct answer. The row
is printed `P-ERK 1/2`. The antibody (CST #4370) is phospho-specific, which
argues phosphorylation. The row label gives no site, and an uppercase `P-` is
not by itself evidence of phospho (P-selectin, P-cadherin). Two credible
sources disagree, so HiveBlot records **no modification**, shows both claims,
and explains why. `ERK 1/2` also resolves to the **MAPK1/MAPK3 family** rather
than one accession, because picking one would be a false precision. If you
think we should settle it, that judgment is exactly what the feedback buttons
are for.

---

## What we would like you to test

### Biology QA — the priority
Open a card, expand **EVIDENCE**, and check each field against the paper:

- **Target** — is the protein right, and is the canonical/UniProt mapping right?
- **Phosphosite** — residue and position (Tyr705, Ser473…), and whether a
  phospho claim is justified at all.
- **Cell line / sample / organism** — including mouse vs human.
- **Treatment** — agent, dose, duration. Check the **per-lane** values, not
  just the panel summary: a time course should say "varies by lane", never one
  number.
- **Antibody** — vendor, catalog number, and whether the antibody was correctly
  associated with *that* row.
- **co-IP** — is the bait right, and is the readout distinguished from the bait?
- **Conflicts** — when HiveBlot says "unsettled", do you agree it is genuinely
  unsettled? When it says "Supported", is it actually supported?
- **Molecular weight** — expected (UniProt reference) and reported (what the
  paper printed) are separate fields on purpose. Flag any conflation.

A false "Supported" is a much worse bug than an unnecessary "needs review".
Please report those first.

### Product
Search clarity, whether the cards are readable, whether the evidence panel is
navigable, whether the figure crops are the right crops, and whether the
feedback controls are obvious enough to actually use.

### Search / eval
Query parsing (does it understand what you meant?), irrelevant matches,
zero-result behaviour, and the advanced-filters bar.

---

## How to report problems

**Use the built-in feedback first** — it is the fastest path and it lands in
the database attached to the exact field you were looking at:

- ✓ / ✗ / *not useful* on any field in the evidence panel
- *suggest a correction* when you know the right value
- **+ Missing information?** when a field we don't show should exist
- **⚑ Flag this result** for record-level problems
- the **BETA FEEDBACK** widget for anything about the interface
- the post-search *"did HiveBlot understand?"* prompt

Nothing you submit changes the extraction. It is stored beside it, and it
survives a database reload, so your corrections are not lost when we re-seed.

**For anything the buttons can't capture,** send a message including:

1. a **screenshot**
2. the exact **search query** you typed
3. the **record or figure** (the DOI + figure/page shown on the card)
4. what you **expected**
5. what you **observed**

Points 4 and 5 matter more than they sound — for a biology bug, "expected" is
usually a sentence from the paper, and quoting it saves us an hour.

---

## Known limitations — please don't re-report these

- **Three papers only.** Coverage gaps are expected, not bugs.
- **No automated model reading yet.** Model credentials are still pending, so
  no accuracy claim about new papers can be made.
- **No densitometry.** Band presence is categorical (present / absent /
  uncertain). We never infer intensity from an image, and band multiplicity
  (doublet, smear) is descriptive only — never an isoform or cleavage call.
- **Molecular weight is never read off an image** without a real ladder
  calibration.
- **Some fields are deliberately blank.** "Not reported" means the paper didn't
  say. That is a finding, not a gap.
- **Duplicate feedback identity on 3 co-IP records.** In the co-IP paper, one
  crop prints H1792 and A549 side by side; for three targets (P62, LC3B, ACTB)
  the two cell lines currently share a feedback identity, so feedback on one
  can appear on the other. 24 of 475 rows. Known, tracked, being fixed.

---

## Current status

The database is **live, migrated, seeded and verified** — schema, security
roles, 475 rows, all seven flagship searches, record detail, figure crops,
feedback submission and feedback rehydration were all tested end-to-end
against the cloud database.

The **hosted URLs are pending one account login** for the API host. Until then,
testing runs locally against the same cloud database. Ask Nikhilesh, and see
`DEPLOYMENT.md` for the exact steps.

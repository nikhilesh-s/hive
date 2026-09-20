# HiveBlot beta

A one-page guide for UCSF beta testers.

## What it is

HiveBlot turns published Western blot figures, captions and methods into structured, searchable evidence records. Each result is one blot experiment: the protein, the cell line, the treatment, the antibody, and what each lane actually showed. Every field is backed by a quote from the paper it came from, so you can check it yourself.

## Why we built it

Wet-lab researchers often need to know whether an antibody, a target, or an experimental setup has already appeared in published work. Digging through papers by hand to answer that is slow. HiveBlot is a first attempt at making that search fast, while being honest about what it does and does not know. This is an early, experimental beta. The dataset is small on purpose: 3 papers, reviewed field by field, rather than a large automated scrape. The goal right now is not broad literature coverage. It is to find out whether researchers trust the evidence HiveBlot shows and understand why it reached each answer.

## What to try

Try a few searches:

- `phospho STAT3 Tyr705`
- `GAPDH mouse`
- `co-IP PIK3CA`

Open a result card and click **Evidence** to see the figure crop, the source sentence for each field, and the lane-by-lane readout. Try submitting a correction on a field and reloading the page to see it stored alongside the original.

## What to look for

For each field, ask: does the quoted source actually support this value? Does the confidence status match how sure you would be reading the paper yourself? When a value is missing or marked "conflicting," is the explanation clear, or confusing? We especially want to know if the evidence panel makes you trust a result more, or less.

## What this beta is not

This is not a literature search engine. It only covers 3 reviewed papers, not the wider literature. It does not measure band intensity (no densitometry, no fold-change, no up/down-regulation calls). It does not guess: when sources disagree, HiveBlot shows both claims instead of picking one.

## Known limitations

The corpus is intentionally small, so most searches outside these 3 papers will return nothing. Automated extraction accuracy on papers HiveBlot has not seen has not been measured yet. The free-tier hosting means the first search after a quiet period can take 30-60 seconds. For paper access, we are currently using Valencio and PaperQA2 to pull in papers; broader access to the literature may come later as the beta grows.

## Feedback link

Please tell us what worked and what did not: [TALLY_LINK]

## Contact / next steps

Beta link: [BETA_LINK]

Questions or issues: [CONTACT_EMAIL]

Your feedback shapes what we build next. Thank you for testing this early.

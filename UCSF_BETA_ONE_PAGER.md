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

This link is not yet the live literature search. It covers 3 reviewed papers, chosen so we can check every field by hand. It does not guess: when sources disagree, HiveBlot shows both claims instead of picking one.

Built and running on our side, coming in the next drop once hosted: live literature search (give a target or DOI, HiveBlot finds open-access papers through Valency and PMC and extracts the blots, shown as unreviewed), question answering over a paper with citations, and a first densitometry tool that measures relative band intensity from a crop and refuses when the image is clipped.

## Known limitations

The corpus is intentionally small, so most searches outside these 3 papers will return nothing. Automated extraction accuracy on papers HiveBlot has not seen has not been measured yet. The free-tier hosting means the first search after a quiet period can take 30-60 seconds. Paper access in the live search runs through Valency and PMC open access; paywalled papers are reported as such, not scraped. Broader access may be needed later.

## Feedback link

Please tell us what worked and what did not: https://tally.so/r/A7kzWB

## Contact / next steps

Beta link: https://hiveblot-beta.vercel.app

Questions or issues: [CONTACT_EMAIL]

Your feedback shapes what we build next. Thank you for testing this early.

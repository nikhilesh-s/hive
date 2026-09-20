# Tanvi — questions and future work (parking lot)

DO NOT WORK ON THESE ITEMS BEFORE THE UCSF DEMO.
These are questions, technical ideas, and future investigation areas from Tanvi. Preserve them for later. Do not implement, test, redesign, or alter the current demo based on these notes unless Nik explicitly asks in a future task.

---

## Western blot normalization / extraction pipeline

- Have you run into any issues with normalizing across Western blot images?

Current / proposed pipeline ideas:

1. Score whether an image is a Western blot without using AI.
2. If it passes a certain score/threshold, then run it through the LLM.
3. When extracting information, check multiple places: figure itself; figure
   caption; methods.
4. Assign confidence / evidence status such as: supported; not supported;
   ambiguous; contradicting.
5. Escalate to a stronger model if the result is ambiguous or conflicting.
6. Use regex to normalize biology-related text.

## Missing data vs failed normalization

Question: How do we test whether a regex/normalization step failed versus the
information actually being absent from the paper?

Example: `antibody_vendor = null`

Future ideas: Let's test this explicitly. Could an LLM act as a second
claim/check when deterministic normalization returns null?

## Protein aliases

- UniProt resolution to account for protein aliases.

## Database and search

- Extracted information gets stored in the database.
- Search terms can then be parsed into SQL requests to search the database and
  retrieve matching rows.

## Paper retrieval / PaperQA

Question: How do we plan on retrieving papers for PaperQA?

## Problems we should address in the future

Reference: https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3001783

Tanvi will add notes soon. Do not investigate this paper during the current
demo-preparation task.

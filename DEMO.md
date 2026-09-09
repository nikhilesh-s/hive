# UCSF demo — 2026-09-09 — run of show

Team-facing source of truth for the presentation. Read this in the ten minutes
before the meeting. Exact technical path and fallbacks live in
`research/UCSF_DEMO_2026-09-09.md`; this file is who says what, when, and what
Nik clicks.

People: **Nik** (engineering + product lead, narrator, the only person driving
the screen), **Srushti** (frontend / product interface), **Tanvi** (biological
QA and scientific validity), **Yashvi** (outreach, researcher relationships,
feedback and follow-up).

---

## 1. Presentation objective

UCSF should leave understanding one thing: HiveBlot turns published Western
blot figures, captions and methods into structured, searchable,
**experiment-level** evidence, where every field carries its status and the
wording it came from. Since the QBI work we have a reviewed corpus of 3 papers
/ 93 experiments / 475 evidence rows that a human checked field by field, plus
a hosted beta a researcher can search today. What is new is the experimental
workflow: a researcher gives a topic, HiveBlot finds an open-access paper,
reads its blots live, and the resulting records land in a separate unreviewed
tier that is badged everywhere it appears — and questions about that paper are
answered only from those records, with citations. Provenance and abstention are
the product: unresolved evidence stays unresolved. What we want from UCSF is
researcher feedback and papers to be evaluated against.

HiveBlot is not an AI chatbot. It is an evidence extraction and search system
that happens to use a model as one step, and shows you every place it did.

---

## 2. Run of show

**Total: 6 minutes 20 seconds spoken + demo.** That leaves slack inside a 5–7
minute slot. If we are running long, cut section 3 (Srushti) and shorten
section 8 to reading one citation.

| # | Section | Who | Time | Screen |
|---|---|---|---|---|
| 1 | Problem and what HiveBlot is | Nik | 0:40 | `hiveblot-beta.vercel.app` home |
| 2 | Reviewed corpus and the trust model | Nik | 1:10 | `/search` — `P-ERK`, then `phospho STAT3 Tyr705` |
| 3 | How the evidence is meant to be read | Srushti | 0:25 | Evidence panel still open |
| 4 | The scientific rules behind the statuses | Tanvi | 0:30 | Same panel; Conflicting card visible |
| 5 | Transition to live research; topic to papers | Nik | 0:45 | local `/experimental/research`, section 1 |
| 6 | Start a live extraction, then move on | Nik | 0:30 | Stepper running |
| 7 | Pre-warmed paper: LIVE · UNREVIEWED + provenance | Nik | 0:50 | Live cards + `Evidence & sources` |
| 8 | Ask the paper a question, follow a citation | Nik | 0:50 | Section "3. Ask about this paper" |
| 9 | Close and what we want from UCSF | Yashvi | 0:40 | Answer with `[E#]` links still on screen |

Cumulative: 0:40 · 1:50 · 2:15 · 2:45 · 3:30 · 4:00 · 4:50 · 5:40 · 6:20.

---

## 3. Speaker assignments

Nik drives the screen for all nine sections. Nobody else touches the laptop.

| # | Speaker | Time | One-line summary | On screen |
|---|---|---|---|---|
| 1 | Nik | 0:40 | Finding a specific blot result in the literature is manual; HiveBlot makes it structured evidence you can search. | Hosted beta home |
| 2 | Nik | 1:10 | Here is the reviewed corpus, here is a conflict it refused to resolve, here is where every value came from. | `/search` results and evidence panel |
| 3 | Srushti | 0:25 | The card is one experiment, not one row; provenance is one click away, and live evidence is read-only by design. | Evidence panel open |
| 4 | Tanvi | 0:30 | Statuses are derived, not asserted: Supported, Needs review, Conflicting. Conflicting keeps no value and shows both claims. Reviewed and unreviewed never mix. | Conflicting card |
| 5 | Nik | 0:45 | Same engine, new front door: a topic, open-access papers only, and we say which source found them. | Research page, discovery list |
| 6 | Nik | 0:30 | This is a real extraction starting now; it takes minutes, so we will not watch it. | Stepper |
| 7 | Nik | 0:50 | A paper this stack already read: same record shape, badged unreviewed, crop and quoted caption behind every field. | Live cards |
| 8 | Nik | 0:50 | The question is scoped to this paper and answered only from these records; each citation is a link to the record. | Ask section |
| 9 | Yashvi | 0:40 | What we want from you: feedback on the fields, and papers to evaluate against. | Answer and evidence list |

Time split: Nik 4:45, Yashvi 0:40, Tanvi 0:30, Srushti 0:25.

---

## 4. Verbal script

Short sentences. No hype. Nothing here claims accuracy we have not measured.

**1. Nik — problem (0:40)**

> If you want to know whether a protein has already been blotted in your cell
> line, under your treatment, with your antibody, you read papers and look at
> figures one at a time. There is no way to search that.
>
> HiveBlot reads published blot figures, their captions and the methods, and
> turns them into experiment-level records. One protein, modified where, in
> which cells, under what treatment, with which antibody, and what the blot
> showed lane by lane. Every field keeps its own status and the wording it came
> from.

**2. Nik — reviewed corpus and trust (1:10)**

> This is the hosted beta. The corpus behind it is deliberately small: three
> papers, ninety-three experiments, four hundred and seventy-five evidence
> rows, all human-reviewed field by field.
>
> Search `P-ERK`. These two cards are marked Conflicting. The sources in the
> paper disagree about what was blotted, so HiveBlot records no value and shows
> you both claims. "Why conflicting" is generated from the candidates
> themselves; it does not pick a winner.
>
> Now `phospho STAT3 Tyr705`. Open "Evidence & sources" on this card. That is
> the panel crop from the published figure, the caption as printed, the
> antibody with its catalog number, and the lanes with band presence. Every
> value on the card traces back to something here.

**3. Srushti — interface (0:25)**

> One card is one experiment, not one row — a six-lane time course reads as one
> result with a lane strip, not six near-identical rows.
>
> Provenance is one click, never a separate page, because a researcher decides
> whether to trust a row in the same place they read it. On the live side that
> panel is read-only: you can read everything, and there is nothing to correct
> yet, because those rows have not been reviewed.

**4. Tanvi — scientific rules (0:30)**

> The statuses are derived from evidence, not asserted. Supported, Needs
> review, Conflicting.
>
> Conflicting is the important one. When credible sources disagree, the field
> keeps no value and both claims stay visible. A value the paper never states
> shows as "not reported" — never as a plausible number. Band presence is
> categorical: present, absent, uncertain.
>
> And reviewed and unreviewed evidence never mix. Everything you are about to
> see on the live side is badged.

**5. Nik — transition and discovery (0:45)**

> Everything so far is the reviewed corpus. This next part runs on my laptop
> and it is experimental — the banner says so.
>
> The status line tells you the model backend, the discovery source and the
> live tier. Topic: `autophagy LC3B western blot lung cancer`.
>
> These are the papers. The source chip says where each one came from — today
> that is PubMed Central; we have a second discovery source wired up but its
> token is not on this machine. This chip means the paper has a downloadable
> open-access PDF. Papers without one say "No open-access PDF" and cannot be
> chosen. We only read what we are allowed to download.

**6. Nik — start extraction (0:30)**

> I will start a real extraction on this one. Fetching, preprocessing,
> extracting, loading — the model reads each candidate panel and the biology is
> deterministic after that.
>
> It takes about a minute per few panels, and a figure-heavy paper can take
> five to ten minutes. So I am not going to make you watch it. It keeps running
> and I will open one this machine already read.

**7. Nik — live evidence and provenance (0:50)**

> "Already extracted in this stack" — open this one.
>
> Same cards, same fields, and every one of them carries LIVE · UNREVIEWED.
> Nobody checked these. That badge is the only difference between this and what
> you saw on the hosted beta.
>
> "Evidence & sources" on this card: the crop comes from the PDF we just
> downloaded, the caption is quoted, the lanes are listed, and the panel is
> read-only because these rows are not part of the reviewed corpus.

**8. Nik — paper-scoped question (0:50)**

> Now a question about this paper only: *Which targets were blotted, in which
> cells, and is any phosphorylation claim unresolved?*
>
> The answer is written only from the numbered records underneath it. Each
> bracketed citation is a link — click one and it takes you to the record it
> came from, and that record is badged unreviewed too. If a field was
> unresolved in the evidence, it stays unresolved in the answer.
>
> If the model call fails, the numbered evidence still renders. That list is
> the deterministic result and it stands on its own.

**9. Yashvi — close (0:40)**

> That is where HiveBlot is today: a small reviewed corpus we trust, and a live
> path that reads a new paper in front of you and marks it as unreviewed until
> a person looks at it.
>
> What we want next is the part we cannot do ourselves. We want researchers to
> tell us which fields matter, which ones we got wrong, and which papers we
> should be evaluated against. If any of you are willing to spend twenty
> minutes with it, we will bring it to your lab, and we will use the feedback.

### Language rules while speaking

- The reviewed corpus is **human-reviewed**. Say that phrase.
- Live extraction is **LIVE · UNREVIEWED** and must be visibly badged whenever
  it is on screen. Never call a live row a result.
- Unresolved or conflicting evidence **stays unresolved**. Never say "it picked
  the right one".
- QA answers come **only from the shown Evidence Records** and cite `[E#]`.
- **Do not mention densitometry.** If asked: a reading aid, uncalibrated, never
  stored. Do not quote any number from it.
- **Do not claim extraction accuracy on unseen papers.** If pressed, the only
  honest line is: *the only number we have is a self-consistency check against
  a paper we had already reviewed — that is not unseen-paper accuracy, and we
  do not have that number yet.* Do not quote its figures.

---

## 5. Exact demo clicks (Nik)

### Pre-demo startup, 10 minutes before

```bash
.venv/bin/python scripts/local_db.py up        # embedded Postgres, 475 reviewed rows
# API on :8010 — .claude/launch.json → "hiveblot-api-demo" (WBM_LLM_BACKEND=claude_cli)
npm --prefix web run dev                       # web on :3000
.venv/bin/python scripts/demo_check.py         # expect 0 FAIL; 2 WARN = Valency token absent
```

Have two browser windows ready: hosted `https://hiveblot-beta.vercel.app` and
local `http://localhost:3000`. Run one hosted search before the meeting so the
free-tier API is awake.

### Hosted reviewed beta — the trust anchor

1. Open `https://hiveblot-beta.vercel.app/search`.
2. Type `P-ERK`, press Enter. Header reads `RESULTS · Western blot evidence ·
   reviewed corpus · 3 papers` with the experiment / lane-record count.
3. Point at the two cards badged **Conflicting** and read the **Why
   conflicting** list under the title.
4. Search `phospho STAT3 Tyr705`.
5. On one card click **Evidence & sources**. Show, in order: **WHY HIVEBLOT
   SAYS THIS**, **FIGURE EVIDENCE** (crop plus the quoted caption),
   **FIELD-LEVEL EVIDENCE**, **ANTIBODIES**, **LANES (band presence —
   categorical, not densitometry)**, and the DOI link.
6. Hand off to Srushti, then Tanvi, with the panel still open.

### Local experimental stack

7. Switch to `http://localhost:3000/experimental/research`. Banner reads
   **EXPERIMENTAL · LIVE RESULTS ARE UNREVIEWED**; heading **Research a topic**.
8. Read the status strip: `model: claude_cli` · `discovery: PMC only (Valency
   not configured)` · `live tier: ready · N rows`.
9. Under **1. Find papers**, type `autophagy LC3B western blot lung cancer` (or
   click it in the **Try:** row) and press **Find papers**.
10. Point at the note **Discovery source: PubMed Central**, then at one paper's
    **open-access PDF · PMCxxxxx** chip, and at a paper whose button reads **No
    open-access PDF**.
11. On a paper that has the open-access chip, click **Choose this paper**.
12. In section **2. Extract**, click **Extract this paper live**. The stepper
    starts at `fetching`. Narrate the stages. **Do not wait.** If the paper is
    already in the live tier the button reads **Re-extract** — that is fine,
    say so and move on.
13. Scroll back to **Already extracted in this stack (N) — open without
    waiting** and expand it. N is the number of papers in the local live
    tier (2 before the meeting; 3 once step 12 finishes).
14. Click **Open extracted evidence** on `10.1186/s12931-015-0285-4`
    (PMC4640373, 17 experiments / 143 lane rows). Use
    `10.1111/1759-7714.13925` (PMC8088950, 97 experiments / 334 lane rows) only
    if you want the larger set.
15. Cards render with the **LIVE · UNREVIEWED** badge. Read the line above them
    about no human review.
16. Click **Evidence & sources** on one live card. Point at the crop and the
    read-only note: *live extraction — unreviewed; feedback is collected on the
    reviewed corpus only.*
17. In **3. Ask about this paper**, type: `Which targets were blotted, in which
    cells, and is any phosphorylation claim unresolved?` and press **Ask**.
18. When the answer appears, click one `[E#]` citation — it jumps to that
    numbered evidence block below, which carries its own **LIVE · UNREVIEWED**
    badge and lane count. Leave this on screen for Yashvi.

---

## 6. Fallbacks

| If | Nik says | Then |
|---|---|---|
| Valency discovery unavailable | "Discovery is running on PubMed Central today; our second source is wired up but its token isn't on this laptop." | Nothing. Discovery works. Continue. |
| Live extraction is slow or fails | "That's a real extraction and it takes minutes, so let's look at one this machine already read." | Open **Already extracted in this stack** → **Open extracted evidence**. |
| The model answer fails | "The model call didn't come back — the numbered evidence below is the deterministic result and it stands on its own." | Read two evidence blocks aloud. |
| The local stack is down | "The experimental stack is on my laptop and it's unhappy; the reviewed product is hosted, so let's stay there." | Return to `hiveblot-beta.vercel.app` and continue on the reviewed corpus. |

---

## 7. Close and UCSF questions

Yashvi closes on feedback, not on the product. The point of the meeting is to
leave with named researchers, named papers and a reason to come back.

> We are not asking you to adopt anything. We are asking whether the fields we
> extract are the fields you would actually use, and what would have to be true
> for you to trust a row nobody reviewed. If a few of you will sit with it for
> twenty minutes, we will bring it to your lab and turn what you say into the
> next version.

Questions to ask, in priority order. Ask three; keep the rest in reserve.

1. In a Western blot literature review, where does the time actually go —
   finding the papers, finding the right panel in a paper, or pulling out the
   conditions and antibodies?
2. Of the fields we show — protein, phosphosite, cell line, treatment, dose,
   duration, antibody vendor and catalog number, molecular weight, lane-level
   band presence — which three matter most to you, and what is missing?
3. What would you need to see before you trusted an automatically extracted row
   without opening the paper yourself?
4. Which papers or datasets would make good evaluation cases — ideally ones you
   know well enough to catch us being wrong?
5. Which labs or people at UCSF should we put this in front of next?

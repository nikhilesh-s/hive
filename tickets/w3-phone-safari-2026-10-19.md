# W-3 phone and Safari pass, 2026-10-19

Site tested: https://hiveblot-beta.vercel.app (deployed 10-18 at `edd95f5`).
Ticket: `oct-push.md` section W-3. Srushti was unavailable, so this was run by Claude.

**Real-device Safari was not available.** Everything below comes from Playwright 1.64 WebKit
(the Safari engine) with device emulation: iPhone 14 (390 x 664), iPhone SE (320 x 568),
iPad gen 7 portrait (810 x 1080) and Desktop Safari (1280 x 720). Touch, viewport and user
agent are emulated; iOS-only behaviours (zoom on focus, dynamic toolbar, safe areas, Low
Power Mode video) are not reproduced and are listed under "Not verified".

Result key: PASS = nothing to fix, PASS* = works but has minor items below, FAIL = content
cut off or the page is materially harder to use.

## 1. Result matrix, hosted site as deployed

| Page | iPhone 14 | iPhone SE | iPad | Desktop Safari |
|---|---|---|---|---|
| `/` | FAIL (W-8, W-9, W-14) | FAIL (W-8, W-9, W-14) | PASS* (W-14, W-15) | PASS* (W-14, W-16) |
| `/search?q=phospho STAT3 Tyr705` (cards, evidence, drawer, feedback) | FAIL (W-9, W-10, W-11, W-13) | FAIL (W-9, W-10, W-12, W-13) | PASS* (W-10, W-11, W-13, W-15) | PASS* (W-13) |
| `/about` | FAIL (W-9) | FAIL (W-9) | PASS* (W-10, W-15) | PASS |
| `/learn` | FAIL (W-9) | FAIL (W-9) | PASS* (W-10, W-15) | PASS |
| `/saved` (signed out) | FAIL (W-9) | FAIL (W-9) | PASS* (W-10, W-15) | PASS |
| `/experimental/research` (redirects to the `/access` gate) | FAIL (W-9, W-11) | FAIL (W-9, W-11) | PASS* (W-10, W-15) | PASS |

Totals: 12 FAIL, 8 PASS*, 4 PASS (24 cells). Every phone cell fails on the same sticky
navigation bar (W-9); the page-specific failures are the Home headline (W-8) and, on a
320 px screen, the feedback panels (W-12).

Checks that passed on every page and device:
- No horizontal overflow (`scrollWidth` equals `innerWidth`) and nothing positioned beyond
  the viewport, apart from the Home headline (W-8).
- No broken images. The result-card figure crops loaded on all four devices.
- No failed requests, HTTP errors or page errors. The only console errors are the two
  invalid SVG attributes on Home (W-14).
- Theme toggle: switches `data-theme`, page background and `aria-pressed`, and stores the
  choice, on every page and device. No overflow appears after switching.
- Filter drawer (iPhone 14, iPhone SE, iPad): the Filters button opens it, it slides fully
  into view, the backdrop shows, body scroll locks, and it closes with the X, the backdrop
  and Escape. The drawer is fixed with `top: 0; bottom: 0`, so it should follow the iOS
  toolbar. Apply sits below the fold on short phones and is reached by scrolling the drawer
  (see W-17). On desktop the sidebar is inline and the Filters button is hidden.
- Evidence panel (the record detail view; there is no standalone record page): expands
  inside the card with no overflow at 320 px.
- Search came back in about 2 s (API warm). `/experimental/research` redirects to
  `/access?next=...` and the gate renders without overflow on all four devices. No code was
  entered and nothing was bypassed.
- Sign-in: the "Continue with Google" button renders and is 33 px tall. The OAuth flow was
  not exercised (see "Not verified").

## 2. Findings

### Fixed in this PR (CSS and layout only, no behaviour change)

**W-8. Home headline cut off on phones.** The typewriter line "Experiment-level evidence,
searchable." is `nowrap` and 368 px wide at 26 px, inside a 278 px column (56 px side
padding). On iPhone 14 it runs to x = 424 on a 390 px screen, so "searchable." is clipped by
the hero's `overflow: hidden`. On iPhone SE it is cut after about "evidence,". Steps: open `/` on
a phone, wait 3 s. Screenshot: `iphone14-home-top.png`. Fix: hero side padding is now
`clamp(16px, 5vw, 56px)` and the h2 is `clamp(18px, 5.6vw, 62px)`. Desktop size is unchanged
(62 px cap). After: headline spans x = 45 to 345 (iPhone 14) and 41 to 279 (iPhone SE).

**W-9. Sticky nav is 175 px tall on phones.** At 390 px the logo, six links and the
theme/sign-in controls take four rows. The bar is `position: sticky`, so it covers 26% of
the iPhone 14 viewport (31% on iPhone SE) on every page and hides the top of whatever is
scrolled to (visible in `iphone14-search-card.png`). Fix, at 520 px and below: row 1 is
logo, theme toggle and sign-in; row 2 is the links in a single row that scrolls sideways
(scrollbar hidden). Bar height is now 97 px. On a 390 px screen "RESEARCH" is partly off the
right edge as a scroll cue.

**W-10. Tap targets under 32 px in the nav and on Save.** Nav links were 20 px tall, the
theme buttons 28 x 28 and the Save checkbox 28 px. Fix, at 900 px and below: links
min-height 32, theme buttons 32 x 32, Save 36. The rest of the small targets are in W-18.

**W-11. Inputs under 16 px (iOS Safari zooms the page on focus).** Measured font sizes:
search box 14 px on phones and 15 px on iPad, all filter-drawer fields 11 px, access-code
field 11 px. Fix: search and filter fields are 16 px at 900 px and below; the access-code
field is 16 px. Still open: the inline-styled fields (search feedback "what did you
expect", the Beta Feedback panel, field feedback in the Evidence panel, and the research
page search box at 14 px). The zoom itself could not be reproduced without a real iPhone;
only the font sizes were measured.

**W-12. Feedback panels cut off on a 320 px screen.** The Beta Feedback panel is a fixed
320 px and the survey panel 360 px, both anchored `right: 18px`. On iPhone SE they start at
x = -18 and x = -58, so the left edge and text are off-screen. Fix: `maxWidth:
calc(100vw - 36px)` on the shared panel style. After: both panels span x = 18 to 302.

**W-14. Two console errors on every Home load.** The hero logo used
`width="clamp(50px, 8vw, 88px)"` as an SVG attribute, which WebKit logs as invalid (it
still sizes the logo from it). Fix: moved the same values into `style`. Rendered size is
unchanged (50, 64.8 and 88 px).

**W-19. "Try:" example chips almost invisible in light theme.** The chips use
`rgba(169, 189, 181, 0.82)` with no light-theme override, which is roughly 1.6:1 against
the light background. Fix: light-theme override to `var(--text-secondary)`. Affects every
device.

### Open (needs a decision or a larger change)

**W-13. Text under 12 px everywhere.** Result cards and the Evidence panel use 10 to 11 px
mono labels: 112 text nodes on the search page at phone width (lane pills, metadata labels,
status badges, DOI line, "as printed", feedback buttons). About, Learn, Saved and the gate
have 2 to 8 each (stat labels, badge labels, kickers). Suggest a 12 px floor for labels at
900 px and below.

**W-15. iPad portrait nav wraps.** At 810 px "Continue with Google" drops to its own row
(114 px bar). Suggest hiding the "WESTERN BLOT EVIDENCE · BETA" subtitle or moving sign-in
into the theme group at 900 px and below.

**W-16. Desktop headline is wider than its column.** At 1280 px the h2 is 957 px inside an
800 px container, so it sits about 78 px right of centre (not clipped). Suggest capping the
font at about 52 px or letting the container grow.

**W-17. Filter drawer polish.** The Experiment select is 19 px tall against 34 px inputs
(WebKit ignores `min-height` on a native select). Apply is at y = 702 and needs a scroll
inside the drawer on short screens. Suggest `appearance: none` plus a caret for the select
and a sticky Apply footer.

**W-18. Remaining small tap targets and floating buttons.** Yes / Partially / No (19 px),
example chips (17 px), field-feedback check, cross and "not useful" (20 to 22 px), search
clear (28 px), DOI links (15 px), and the floating "FINISHED? 3 QUESTIONS" and "BETA
FEEDBACK" pills (27 px). On a phone the pills take 278 of 390 px and sit over card content
(`iphone14-search-card.png`). Suggest one collapsed button at 520 px and below, and 32 px
minimums.

**W-20. Home hero text contrast in light theme.** The paragraph is dark teal-grey on the
hero video; the video's dark centre shows through the 25% light overlay and the middle of
the paragraph is hard to read on every device (`desktop-safari-home-light-settled.png`).
Not measured. Suggest a higher centre alpha for the light `--hero-overlay`.

## 3. After the fixes

Same WebKit script, run against a local production build of this branch (`next start`).
The local build has no API key, so `/api/search`, `/api/corpus-stats`, `/api/record/*` and
the saved-status calls were passed through to the hosted site and feedback POSTs were
mocked (nothing was posted).

- Home, Search, About, Learn, Saved, Access gate: no overflow at 320, 390, 810 and 1280.
  All 12 phone cells move from FAIL to PASS* (W-13 and W-18 remain).
- Nav 97 px on phones (was 175); nav links 32 px; theme buttons 32 px; Save 36 px.
- Every field on `/`, `/search` and the gate that is styled by CSS is now 16 px on phones.
- Home headline fully inside the viewport; Home has no console errors.
- Beta Feedback and survey panels fit on a 320 px screen.
- The ungated research page (local only, no access code needed) has no overflow at 320 px.
  Its search box is 14 px and its tab pills 29 px tall (open under W-11 and W-18).

## 4. Not verified

- Real iPhone and iPad Safari: zoom on focus, the dynamic toolbar and `100vh` behaviour,
  safe-area insets, `backdrop-filter` on the nav (the build emits the `-webkit-` form, but
  headless screenshots show the nav as plainly translucent), video autoplay in Low Power
  Mode, momentum scrolling.
- Google sign-in, sign-out and session survival (cannot sign in from here).
- Saving and removing a result (needs a signed-in session). The Save checkbox renders and
  is now 36 px.
- The research page from a real access link (gate only; no code was entered).
- Field-level feedback (check and cross buttons) was not clicked. Search feedback
  "Partially" and the Beta Feedback and survey panels were opened with the network mocked.
- Dark theme was screenshotted but not audited for contrast.

## 5. Reproduce

Scripts are not in the repo. They live in `/tmp/w3` on the machine that ran this:
`check.mjs` (full pass; `BASE=http://localhost:3123` for a local build), `panels.mjs`,
`home2.mjs`, `verify.mjs`. Setup: `npm i playwright@1 && npx playwright install webkit`.
Screenshots (not committed): `/tmp/w3/shots` (hosted, before) and `/tmp/w3/shots-after`
(local, after), named `<device>-<page>-<view>.png`.

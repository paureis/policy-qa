# Case page at desktop: design brief (Impeccable shape, Oct 26, 2026)

Decided with Alvaro in the shape interview on Oct 26 (evening, local session). This brief governs the
Wednesday build of the desktop case page and its siblings. It inherits the world committed in
`web/intake-brief.md` ("The Notice, Answered": Public Sans, paper and bond, the federal-blue band,
stamp blue for the verdict, gold only on fields to check, one postmark) and the tokens in
`web/src/app/globals.css`. It is a redesign of the case page's structure at 1024 px and up, not a new
visual identity. The phone keeps its single column with the outcome moved up (done Oct 26).

Inputs: `web/design-critique.md` (direction B, the hierarchy findings, the AI slop list, the
accessibility regressions to avoid), `PRODUCT.md`, the three existing briefs, and the five small fixes
already shipped on Oct 26 (outcome first in DOM order, one postmark, chips as references, trust as a
receipt, "Could not verify" as a filled ink tag, band aligned to the content).

## 1. Job and audience

The desktop reader is a caregiver at a laptop, and, for nine days, a hackathon judge watching the
same screen. Mode: Read. The visitor must understand one thing fast, "does this denial hold, and
what do I send?", then read the letter with its proof. Billing-staff density is explicitly not the
target; facts stay available, not persistent.

## 2. Outcome and proof

Primary task: read the verdict, read the appeal letter, copy or download it, know the deadline and
where to file. Success: the verdict headline, the two verification counts, and the day count are in
the first viewport at 1280 x 800; the letter begins in the second viewport; every claim sentence has
its cited quote beside it; the proof (findings verified, sentences verified, struck sentences kept
visible) is read with the claim, not after it.

Product truth that must stay visible: the three verdict phrasings verbatim; struck findings and
struck sentences stay on the page with their reason; abstention is an outcome, not an error; the
counts come from the case record, never typed in.

## 3. Selected direction: B, the Annotated Letter

Thesis: the product's one claim, "every sentence carries a verified citation", becomes the layout.
The letter sits on a bond sheet; each paragraph's cited quotes sit in a margin column beside that
paragraph, like a brief with margin citations. It reuses the intake reviewing pattern (a document
beside its source), which Alvaro rated the best screen.

Borrowed from A: the outcome summary as a full-width heading block above the sheet (verdict headline
at 44 to 48 px, the two verification counts and the deadline with day count on one line under it,
the one postmark at the sheet's top right corner). Borrowed from C: the seven-step stage header
during the live run only.

Sequence at desktop, finished case with a letter, top to bottom:

1. Band (aligned to the 1,120 px frame).
2. Case header, one line of facts (payer, service, the letter's reason, program) with "Show the full
   case card" as a disclosure; no rows grid.
3. Outcome heading block: headline, counts and day count line, the rule and the gap in two short
   paragraphs, "What would change it", the steelman as a disclosure ("The payer's best argument").
4. The letter sheet (bond on paper ground) with To, Re, body, signature lines, Copy and Download; the
   margin column beside it carries the citations per paragraph; struck sentences stay in place,
   struck, with "Could not verify" as the ink tag.
5. Evidence checklist and the filing path on the sheet's footer register (deadline repeated as text
   with its citation).
6. "How the case was investigated": the findings as the record, compact (question and one-line
   answer, expand for citations), two columns at desktop (findings left, struck citations and reasons
   right).
7. Self-check (how the letter checked itself), then the trust receipt and the trace.

Focal moment: the letter sheet with a margin note open, the quoted rule beside the sentence it proves.

## 4. Scope and boundaries

Everything, in this order of priority:

1. Finished case with a letter (inconsistent), 1024 px and up. The deliverable.
2. Siblings without a letter: consistent and not settled. Same frame: the outcome block, then an
   explanation sheet (the plain explanation and "what would have made it covered", or the open
   question and what would settle it) with the rule quotes in the margin, then the record. Not settled
   keeps ink, not gray, with an open-ring mark; it must not read as disabled.
3. The live run (investigating to drafting): the stage header from C ticks across the top of the
   frame (Intake, Routing, Investigation, Steelman, Verdict, Action, Trust, stepped ticks, no fade);
   findings arrive in one 640 px column under it; the verifier's strike draws left to right. At
   `decided` the page becomes the Annotated Letter in place (same element tree, no remount; already
   enforced), the stage header collapses into the outcome block.
4. Landing and intake at desktop: the paste box is the main surface (the desk); photo and file are two
   secondary doors beside it; the postmark and the band stay; the three stacked cards disappear at
   desktop. The landing page gets the same frame and one sample case link; no marketing copy is added.

Untouched: the phone layout (390 to 767 px) beyond what the shared components change; all copy and
verdict phrasings; the data contract in `src/lib/case.ts`; the page viewer's dialog semantics; fixture
mode and its ids; the API.

Anti-goals: no rail that duplicates the body; no kanban feel; no gradients, shadows, rounded cards,
illustration, emoji, confidence percentages; no second stamp; no overline on every block; no counters
that animate up; no skeleton shimmer; no dark mode.

## 5. States and ranges

- Findings: 3 to 8, each supported, not settled, unsupported (struck quote kept), or error; dual
  program cases show two routes side by side (two record columns).
- Letter: 3 to 6 paragraphs; 0 to 3 struck sentences; 1 to 4 citations per paragraph, identical
  (document, page) pairs merged; citation titles are long (up to 120 characters) and are shown short
  with the page folio, the full title in the note.
- Verdict: three outcomes; the counts range "0 of n" to "n of n"; day count may be unknown (letter
  gives none, policy gives none) and then reads "deadline not stated" with the filing path.
- Failed stage: the chain can fail at any step; earlier stages render, the failed stage shows its
  error in the outcome block's place.
- Refusal (out of scope) never reaches this page.
- Self-check: skipped, done with 0 to 3 issues, error; a rejected revision shows the draft.
- Page viewer: not located, checking, done (agrees or not), unavailable, no PDF (manifest link).

## 6. Interaction and layout

- Frame: paper ground (`--paper`) as the desk at desktop; bond white for the objects on it (case
  header strip, the sheet, the receipt). 1,120 px frame centered; margins 32 px at 1024, free at 1280
  and up (the 27-inch monitor: the frame stays 1,120, the desk fills the width; nothing stretches).
- Sheet and margin: main 620 px, margin 420 px, 48 px gutter. Each letter paragraph is its own grid
  row (`grid-template-columns: 620px 420px`, one row per paragraph) so notes align to their paragraph
  without JavaScript. Margin notes are the current chips, restyled as references (done), stacked per
  paragraph; a note shows the short title, page folio, and the quote; "See the page" expands that note
  in place to the page image with the gold box and the vision line (Alvaro's choice: one thing at a
  time, the letter never moves). Only one note is expanded at a time; expanding another collapses the
  first. Escape collapses and returns focus to the note's button.
- Keyboard and reading order: the note's button sits in the DOM immediately after its paragraph;
  `aria-expanded`; the margin never changes DOM order between columns; at 200 percent zoom and under
  1024 px the margin collapses under each paragraph (the phone pattern).
- Type scale at desktop: 14 overline and captions, 17 body, 18 in the letter body (older low-vision
  readers), 20 h3, 28 h2, 44 to 48 verdict; weight 700 only on the verdict and h2; tabular numerals
  on counts, day count, page folios.
- Motion, transform or stepped only, 120 to 150 ms, all off under reduced motion: the stamp lands
  once when the case opens; the strike draws left to right when a finding or sentence is struck; stage
  ticks step from ring to filled; letter paragraphs land one by one as drafted; the expanded note
  grows from its row. Nothing fades.
- Feedback: Copy shows "Copied" inline for two seconds; Download gives the text file; the trace opens
  as the receipt's back.

## 7. Constraints and decisions a builder must not invent

- WCAG 2.1 AA as the briefs commit: contrast from the existing tokens only; 44 px targets; focus
  visible on the band (white ring, done); DOM order equals visual order; no color-only state; reflow
  at 320 px with no horizontal scroll; sticky nothing except the expanded note's image at desktop,
  unstuck under 700 px height.
- Public Sans only; system mono for ids and model names; no new colors, no new tokens except layout
  sizes.
- Next.js 16, React 19, Tailwind 4; fixture mode must render every state above for screenshots at
  390, 768, 1280 and 1920.
- Screenshot hygiene: `devIndicators` off (done), clean state before capture.
- Decided, not open: direction B; the note expands in place; stage header then settle into B; paste
  box as the intake's main surface; the phone stays as it is.
- Decided Oct 26, late: the trace stays inline, a button on the trust receipt that opens the
  receipt's back; no new route.
- Component sources: 21st.dev (the Magic MCP server, free tier) may be searched for mechanics only:
  a stepped stage header, a note that expands in place, a sheet with a signature register, keyboard
  and focus handling. Anything taken is rewritten into this world's tokens, type, and motion rules;
  no visual style, gradient, glass, glow, shadow, or fade is copied. Alvaro decided this on Oct 26.
- Open, ask Alvaro: the exact landing copy (no new copy may be written without him).

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

## 8. Round 3 decisions (Oct 27, 2026, after the round 2 evaluation and the Impeccable critique)

Decided by Alvaro on Oct 27 by decision prompt. Round 2 (commit 2ed5dd5) stays as the base. The
Impeccable critique of that round scored 24 of 40 and read the page as the softest rendition of the
right world: the claim shown, the proof hidden (`.impeccable/critique/2026-10-27T15-32-03Z__web-src-app-case-id-page-tsx.md`).
Round 3 raises the rendition within the committed world. Nothing below changes the world, the API,
the data contract, or the phone layout.

Three moves, in this order of priority, all in round 3:

1. **The exhibit pair** (P0). Under the verdict headline and the counts line, in place of "The rule"
   and "The gap" as two text columns: two facing exhibits on bond, about 520 px each, 1 px ink edge,
   no shadow. Left, overline "The letter says": the payer's stated reason verbatim at 22 px with the
   source line under it in 14 px muted (payer name, "letter dated <date>"). Right, overline "The
   policy says": a crop of the real page image showing only the highlighted lines, drawn large enough
   to read (about 1.5x the viewer's scale), with the existing gold box; under it the folio ("Rule
   59G-4.261, PDF page 5 (printed page 3)") and the vision-check sentence as a 15 px caption, labeled
   as the Muse Spark vision check. The rule and the gap paragraphs stay, set under the exhibits in
   one column at 17 px. The exhibit pair must sit inside the first viewport at 1280 x 800 together
   with the headline and the counts; the letter still begins in the second viewport. When the page
   image is not located or unavailable, the right exhibit shows the quote as text on bond with the
   same folio and the viewer's existing state copy.
2. **The letter as a real document** (P1). The sheet keeps US Letter proportion (620 wide, pages of
   802, a folio "Page 1 of n" at each page foot) and gets a date line. The placeholders ([Your name],
   [Relationship to member], member ID, signature, date) become gold-wash fields labeled "Fill in",
   using the existing gold token; gold is reserved for fields to check and this is that. A print
   stylesheet scoped to the sheet, so printing the page prints the letter alone. Copy the letter,
   Download as text, and the deadline line move into the margin beside the sheet head (today they sit
   below the last paragraph). Each margin note carries its verification state as words: "Found on
   page 5" with a small stamp-blue tick; a struck sentence's note carries "Could not verify" as today.
3. **The notice register at the top** (P1). The four-line case header becomes a ruled reference
   box at the top right of the outcome block, tabular, label and value: Member, Plan, Letter dated,
   Service and code, Amount, Case (mono). The one postmark moves into the first viewport, overlapping
   that box's corner, and becomes the only carrier of the day count up there; the deadline no longer
   repeats four times (once in the postmark, once in the filing panel with its citation, once in the
   letter). The band carries the case number at the right in mono. "Show the full case card" stays
   as the disclosure.

Also decided, same day:

- Open note: **overlay**. The expanded quote and the page image open over the margin column below
  the note (absolute, within the margin), never growing the row; the letter never moves. One thing
  open at a time across quotes and pages; Escape closes it and returns focus.
- Margin mechanics: **sidenote floats** replace the one-grid-row-per-paragraph rule in section 6.
  Each note floats in the margin, clears the one above, and stacks downward past its paragraph when
  the notes are taller than the paragraph; a paragraph never stretches and no blank sheet opens.
- The margin note shows the **full quote** (no two-line clamp, no "more" or "less").
- The investigation record is **compact** as section 3 item 6 says: question and the answer's first
  sentence, expand a finding for the full answer and its citations; two columns only when there are
  struck citations; the record, the self-check, and the receipt take an appendix register (hairline
  rule, 20 px titles) under the numbered openings.
- Section 3 "What to send and where to file" stays its own section; the gray desk token stays.
- Copy approved by Alvaro: the section titles of round 2; "page N" as the page link; "The letter
  says" and "The policy says"; "Found on page N"; "PDF page N (printed page M)" where the printed
  folio differs; "Fill in". "more" and "less" go away with the full quote.
- The six contract failures from the round 2 evaluation are fixed in the same pass: heading names
  carry their number for screen readers ("1. Verdict"); one note open at a time across quotes and
  pages; Escape collapses an expanded note; the footnote hit area does not overlap the letter text;
  72 px sheet margins from 1024; footnote numbers at 14 px and the receipt lines inside the type
  scale (no 24 px, 700 only on the verdict and h2). The verdict headline is a heading (h1 names the
  outcome, the payer's name is not the h1).
- A demo case with one struck sentence, so the verifier is seen acting: the fixture that has a struck
  sentence must render the strike at desktop; the live cases of Oct 26 had 61 of 61 verified, so a
  live struck case is not forced.

## 9. Direction contract (Oct 27, 2026, after the direction round)

Decided by Alvaro on Oct 27 at about 5:40 pm after a round-3 look ("better, still not it; judges will
see a normal-looking web page") and an Impeccable direction round (seven grounded worlds, the roll
assigned candidate 6, six catalog challengers weighed, one competitive; decision page cards with
first-viewport sketches under `.impeccable/mocks/decision/`, gitignored). This replaces "The Notice,
Answered" as the visual world of the whole product; the intake brief's world paragraph is superseded
by OWN-WORLD below, and its structure and copy decisions stand.

THESIS: A denial becomes a case, and the page is the open folder with the documents clipped inside
it. It refuses the category's two arrangements: the white portal with rounded cards and a blue
button, and the government-notice replica (federal blue band, bond, Public Sans) that round 3 wore.

OWN-WORLD: manila ground #e6d3a3 is the folder; kraft tones of the same hue for the index tabs;
bond white #ffffff sheets with a 1 px ink edge for every document (the top sheet, the exhibits, the
letter pages, the receipt); ink #1b1b1b for all text; one red #b3261e for the rubber stamp and the
highlight only. Archivo (variable grotesque, Google Fonts): the stamp in condensed caps (width about
62 percent, weight 850); everything else normal width, 400 and 600; system mono for the case id,
the folder tab, and tokens. Marks, not hues, for state: a tick for verified, a strike for struck, an
open ring for not settled; a drawn paper clip holds a clipped sheet; a stamp is inked unevenly (SVG
noise filter), turned about -2.6 degrees, one per sheet. No shadows beyond the 1 px edge, no
gradients, no radius, no second accent, no illustration.

STORY: a caregiver opens their case folder, reads the stamp, sees the payer's sentence and the
policy page face to face, reads the letter inside the folder, and knows what to send and by when; a
judge sees a case, not a web page, and the stamp is the screenshot they keep.

FIRST VIEWPORT (1280 x 800): the band is the folder's top edge in manila with the tab at the left
("CASE c_824f9b · Sample Health Plan · opened Oct 26, 2026" in mono; the opened date is created_at in the reader's local time) and the status line at the
right; the white top sheet starts about 100 px down and runs to the fold; the stamp with the verdict
sits at the sheet's top left, the counts as marks under it; the deadline (Appeal by Dec 6, 2026, 41
days left) and the reference rows at the top right; the two exhibits as clipped sheets side by side
below, the letter says and the policy says (the page crop with the red highlight, the folio, the
Muse Spark vision check); the six index tabs down the sheet's right edge, the current one darker;
the rule and the gap under the exhibits. The letter sheet begins in the second viewport. The
composition the build matches is `.impeccable/mocks/decision/assigned.html` (the locked sketch);
round 3's structure (section 8) stays underneath it: the exhibit pair, the two-page letter with
margin notes and overlays, the checklist and filing section, the compact record, the appendix
register, the fixture states, the phone layout's structure.

FORM: The Case File, candidate 6 of 7 on the grounded list (ranked: the annotated evidence file, the
appellate brief and record, certified mail, the auditor's ledger, the legal-aid pamphlet, the case
file, the notice register); assigned by the roll. seed:de806ea490aaaeca. Raises from the declined
hand: state is a mark never a hue (cutting bench); one grotesque at full scale, exhibits numbered
like plates with corner marks (plate section); one signal color, rank by scale (cracktro queue).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
verdict, DESIGN.md, and every shipping raster carrying its provenance.

Recorded after the first evaluation of the build (Oct 27, evening): the rule and the gap sit in two
columns under their exhibits, as the locked sketch has them (this overrides section 8's one column);
gold stays on the Fill-in fields as the reader's own mark, the one exception to "one signal color";
the verdict stamp is 38 px at 1280 (the sketch's 46 px wraps the longer phrasings); the status line
sits in the band's right; every section at tabs sizes (1280 px wide and 760 px tall and up) is a
bond sheet whose head carries its title while the index tabs carry the numbers, and the receipt stays
a slip; under 1024 px the structure of round 3 stands as it is.

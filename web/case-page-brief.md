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

## 10. Piece 2 decisions (Oct 27, 2026)

The siblings without a letter (consistent, not settled) in The Case File at 1024 px and up. Made by
the orchestrator within this brief and DESIGN.md (D1 to D8), then by the builder where marked.

- D1. The folder frame is every finished case at 1024 px and up. `annotated` now means "the chain has
  finished" (the letter stage done); `hasLetter` says whether a letter exists. A sibling's sections:
  1 Verdict, 2 the explanation sheet ("Why the denial holds" or "Why no letter was drafted"), 3 "If you
  still want to appeal" (its own bond sheet, register layout), 4 Investigation record, 5 Receipt. No
  self-check section and no evidence checklist; the index tabs carry exactly those five.
- D2. The top sheet is the letter case's: band tab, status line in the band (the existing stage line,
  "Verdict reached. No appeal letter was drafted."), reference block with the Lead deadline, the red
  stamp as h1, the counts as marks, the exhibit pair, the rule and the gap under it, the steelman.
  "What would change it" is not on the top sheet at desktop for either sibling.
- D3. Section 2 is a document: a 620 px bond sheet, 1 px ink edge, 72 px inner margins, in the
  letter's 620 : 420 : 48 grid. On it the h2, the explanation at 18 px / 1.6, then "What would have
  made it covered" (consistent) or "What would change it" (not settled). In the margin, anchored to
  the explanation paragraph, the rule's citations as sidenotes with the letter's mechanics and look;
  the steelman's citations are not added. Not settled carries an open ring and "The documents do not
  settle this" at the margin's head.
- D4. Not settled stays ink everywhere (measured: explanation, what would change it, margin head and
  quotes all #1b1b1b at full opacity); the only state signal is the open ring with its words.
- D5. `c_dual` keeps its two record columns inside the 1,088 px record sheet; nothing else changes.
- D6. Fixture `c_notsettled*` (kind `notsettled`): the sample route, findings, card and letter text, a
  not-settled verdict on the sample's own facts (modeled on dc-010's pattern), rule citations
  f_2[0] and f_1[0], no letter (explanation in LETTER_DUAL's register), FILING_SAMPLE, the self-check
  skipped with the dual's reason. `c_dual` is unchanged.
- D7. Under 1024 px nothing changes on any case; `c_sample` does not change at any width (captures
  before and after are pixel-identical).
- D8. The live run is piece 3. The no-remount rule holds: the top sheet, stamp, verdict, findings and
  receipt are the same DOM nodes from drafting to reviewed on all four cases.

Decided by the builder, with the reason:

- The sidenote pieces (footnote number, margin note, the overlay placement) moved from
  `AppealLetter.tsx` into `letter/Sidenotes.tsx` unchanged, so both sheets share one implementation
  and one look; the letter case's captures are pixel-identical after the move.
- The expanded quote needs a control in the text, as in the letter: the explanation paragraph ends in
  one footnote number per margin note (desktop only), kept on one line with the paragraph's last word.
- "Found on page N" with the tick shows for every rule citation unless the verifier struck the rule
  (then "Could not verify", as a struck letter note). The tick means the verifier found the quote on
  the cited page, as in the letter, not that the page image located the highlight.
- Section 3's register in the letter's grid: the deadline (date, day count, source, note) in the
  620 px column, the filing path (where, how, citations) label over value in the 420 px column, so
  the sheet reads as the letter case's section 3 without the checklist. The date is 20 px at 600 at
  desktop (24 px on the phone, unchanged).
- The skipped self-check's one line ("Self-check skipped: ...") stays on the phone and is not shown
  at desktop, where D1 says there is no self-check section; the receipt shows no self-check step.
- The steelman disclosure keeps 32 px above it at desktop when nothing sits between it and the rule
  and gap (both siblings), the spacing "What would change it" has on the letter case.
- The band's status line may take two lines (it was cut to one with an ellipsis): the siblings' stage
  line does not fit beside the folder tab at 1280 px and up. The letter case's line fits on one, so
  it renders exactly as before.

Fix pass after the evaluation (Oct 27, 2026):

- The explanation sheet stands at least as tall as its margin notes: when the notes run past the
  text, the sheet stretches (white space at its foot), so both columns end on one foot and the 96 px
  gap to section 3 is measured from it. An open overlay still grows the frame below the sheet.
- `VERDICT_CONSISTENT`'s rule citations are now f_2[0] then f_2[1], so the consistent case's policy
  exhibit and note 1 show the located Rule 59G-4.261 page 5 crop; page 38 (not located on its image)
  stays as note 2, where the "not located" state is still shown at desktop, as it is on the letter
  case's steelman chip. Fixture data only.
- Not changed, by decision: the footnote number's 14 by 16 px target (the letter case's since round 3;
  the inline-text exception of WCAG 2.5.8 applies).
- Not changed, by decision: the band's status line may wrap to two lines.
- Not changed, by decision: an open page overlay that runs past the sheet grows the frame below it.

## 11. Piece 3 decisions (Oct 27, 2026)

The live run (investigating to reviewed) in The Case File at 1024 px and up: the clerk works the
folder in front of the reader. Made by the orchestrator within this brief and DESIGN.md (P1 to P8),
then by the builder where marked.

- P1. The folder is open from the first poll at 1024 px and up: the band with the case tab (payer and
  opened date at 1280 and up), the manila ground, the top sheet with the reference block at its top
  right and the deadline stamp as its one stamp before the verdict. No index tabs and no verdict
  stamp while the case runs.
- P2. The routing slip is the stage header: Intake, Routing, Investigation, Steelman, Verdict, Action,
  Trust, each a mark and a word; an open ring for a stage not reached, a tick (stepped in) for a stage
  done, and for the stage in progress the ring with its live words ("Question 3 of 5…", "Weighing the
  payer's side…", "Drafting the appeal letter…", "Checking the letter against itself…"). A stage that
  stopped keeps its ring and its failure words. Labels 14 px ink, live words 17 px, tabular numerals;
  one row at 1280, two allowed at 1024. One polite, atomic live region for the whole slip.
- P3. The record sheet is a bond sheet under the top sheet from the start, its head "Investigation
  record"; the findings land one by one (the 6 px land) in a 640 px column in the record's compact
  form; the column lifts to the record's full layout when the chain finishes. A struck citation's
  strike and a struck finding's strike draw left to right on arrival (150 ms, transform only, off
  under reduced motion). The route line leads the record.
- P4. At decided the stamp is pressed on the top sheet where it stays; the counts under it; the slip,
  then the exhibit pair, the rule and the gap under the slip; the deadline stamp gives way to the Lead
  line in the reference block. The slip stays through drafting, drafted and reviewing and folds into
  the band's status line when the chain finishes (display: none, no remount). The stamp's y is the
  same at decided and at reviewed.
- P5. No remount: the top sheet, the case header, the verdict section, the slip and its live region,
  the findings list and every finding, the record sheet and the receipt are the same DOM nodes from
  the first poll to the end (measured on all eight fixture cases).
- P6. `c_fail` keeps the slip with the Investigation ring and "Stopped after question 2 of 5.", the
  failed section on a bond sheet under the record; a verdict or letter failure keeps the stamp and the
  slip with that stage's ring and the failed section's heading as its words. No red but the stamps.
- P7. Under 1024 px nothing changes at any status; the six finished cases are pixel-identical at
  every width.
- P8. Everything reads the case record (route, investigation, verdict, letter, critique, status),
  never a timer, so a live case behaves as the fixtures do.

Decided by the builder, with the reason:

- The slip sits under the stamp and the counts, not above them. The stamp must not move between
  decided and reviewed, and the slip folds away at the end; anything above the stamp that folds away
  would move it. Before the verdict the slip sits under the deadline stamp and the reference rows, so
  it is the sheet's top row of content below the head; at decided the stamp is pressed above it.
- Before the verdict the deadline stamp is pressed at the top sheet's top left, where the verdict
  stamp will land (one stamp per sheet, in the stamp's place). The reference block holds the Lead
  line's slot from the first poll (laid out, unseen, its rule transparent) and the Lead line shows in
  it at decided, so the rows never move (fix pass, below).
- The deadline stamp keeps its solid inner frame during the run: on the case page the card was
  confirmed at intake (the phone header has always pressed it landed), so the dashed state belongs
  to the intake card only.
- The payer's name stays the page's h1 before the verdict (visually hidden at desktop, where the
  folder tab names the payer at 1280 and up), so the page always has one h1.
- The slip and its live region live inside the verdict section, which is mounted from the first poll
  (empty, display: none under 1024 px, until the verdict exists); that is what lets the stamp be
  pressed above the slip without remounting it. The live region is a visually hidden line beside the
  slip, not inside it, so the last line ("Letter checked: 2 of 2 issues fixed.") is still announced
  after the slip folds away. The phone's two live lines are display: none at desktop. It is the one
  live region for the chain at desktop: the band's status line is plain text (fix pass).
- The in-progress stage is set at 600 as well as carrying its words, so a running stage without
  words (Trust on a case without a letter, where Action already carries "Verdict reached. No appeal
  letter was drafted.") still reads as running. A failed verdict puts the failure words on Verdict.
- The index tabs, the section numbers and the letter's sheets arrive when the letter stage is done
  (drafted), as before: the sheets exist from then, and the tabs point at them. Only the slip waits
  for the end of the chain (reviewed, or any end the API reports) before it folds into the band.
- The receipt is the finished case's slip (bond, dashed tear line, 560 px, under the "Receipt"
  appendix head) from the first poll at desktop (fix pass); its left edge and width never change.
- The record sheet sits 80 px under the top sheet during the run, the gap the top sheet keeps to the
  next document on the finished case.
- `c_dual` keeps its two record columns during the run (section 5 and D5): one 640 px column applies to
  a single route.
- The strike draws once the finding has landed (after the 120 ms land), one ink line per line box,
  in 150 ms across all lines, then the text's own line-through takes over (measured at 3x: the drawn
  line and the line-through sit on the same pixel rows). With no script or with reduced motion the
  strike is the plain line-through, as before.
- The record section and the record sheet do not take the 6 px land at decided or at drafted at
  desktop (each finding has already landed); on the phone they land as before.

Fix pass after the evaluation (Oct 28, 2026), by the orchestrator's list, built as follows:

- The reader's place is kept. Before every change the chain makes to the page (a poll's new record,
  the slip folding) the view notes the first blocks at or below the window's top (a finding, a letter
  block, a heading, an exhibit, a table) and their offsets; in a layout effect after the commit it
  scrolls by however far the first one still on the page moved. A reader at scrollY 0 never scrolls; a
  change below the reader needs no correction. Whole blocks, not lines: a line inside a finding
  reflows when the record's column lifts, and anchoring to it let the finding drift 25 px.
- No drop at decided: the reference block holds the Lead line's slot from the first poll, and the
  stamp's area before the verdict holds the verdict stamp and the counts (169 px at tabs sizes, 168 px
  from 1024; a headline that sets on three lines at 1024 is taller, but the reference block is the
  taller column at every case measured, so the slip does not move). The slip sits at the same y from
  the first poll to the end.
- At decided the verdict section no longer lands as a whole at desktop: the stamp is pressed, and
  the counts, the exhibits and the rule and the gap land; the slip stays still.
- From 1024 to 1279 px the slip holds its two-row height (82 px) from the start, so a stage line that
  wraps moves nothing.
- The Trust tick is seen: when the chain reaches its final state the slip shows it for one poll
  interval (POLL_MS) before it folds into the band line, also under reduced motion (a pause, not a
  transition). A case already finished when it opens folds at once. A failed self-check keeps the
  Trust ring with the stage line's words.
- In the compact record during the run the struck citations sit in the answer's column (the 28 px
  indent under the question), not at the card's edge.
- The failed section's heading is 28 px at desktop (26 on the phone, as before).

Not changing, by decision (fix pass):

- The run's findings land below the fold at 1280 x 800: the presenter scrolls; the top of the page is
  the slip's show.
- The letter's sheets arrive at drafted, when the letter exists.
- On a case without a letter "What would change it" shows on the top sheet from decided to drafted and
  moves to the explanation sheet when the letter stage reports no letter; the page does not guess.
- `c_dual` keeps its two record columns during the run.
- The strike draws on every mount, including a finished case opened fresh.

Decided after Alvaro's look and the first live run in the folder (Oct 28, 2026, session 8):

- The Lead deadline line shows from the first poll (Alvaro's choice among three: keep the empty slot,
  show the line, let the rows drop). The deadline is known at intake, the rows never move at decided,
  and the top sheet is not empty while the case runs; during the run it repeats the deadline stamp on
  the sheet's left, and once the verdict lands it is the sheet's only deadline. `Register` in
  `CaseHeader.tsx` no longer takes a `lead` flag.
- The policy exhibit and the page viewer key their highlight-and-vision effect on the citation's
  `doc_id`, `page` and `quote`, not on the citation object. Every poll rebuilds the record, and the
  object-keyed effect re-ran the highlight and the Muse Spark vision check on each poll: nine vision
  calls (about $0.006 and 6 s each) on the first live case, and the exhibit's caption flickered between
  "Checking the highlight…" and the result, its height moving 41 px each time. One check per exhibit
  now; the caption settles once.
- The root font size is pinned to 16 px in `globals.css`. The world sets every size in px, so only
  Tailwind's rem spacing followed a reader's font-size setting; at Chrome's "Large" (20 px) the sheet's
  insets grew to 50 px, the stamp wrapped to three lines and dropped under the reference block. Found
  on Alvaro's own browser, reproduced in Playwright at 20 px.
- Recorded, not changed: the Lead line's mark is the open ring, not the calendar mark DESIGN.md names;
  the `c_notsettled` fixture's chain runs about 24 s before the slip folds (the letter case's runs 12).

## 12. Piece 4 decisions (Oct 28, 2026)

The intake and the landing at desktop in The Case File. Section 4 item 4 sets the shape (the paste box
as the main surface, photo and file as two doors beside it, the postmark and the band stay, the three
stacked cards go at desktop; the landing gets the same frame and one sample case link, no marketing
copy added), section 9 the world, `web/intake-brief.md` the structure, states, ranges and copy (its
world paragraph is superseded). Made by the orchestrator within those and DESIGN.md (E1 to E12), then
by the builder where marked. Under 1024 px nothing changes on either page (E12).

- E1. Frame. Both pages use the case page's folder frame at 1024 px and up: the kraft band with the
  wordmark (no folder tab: there is no case yet), the manila ground, one bond top sheet 1,088 px wide
  with the 32 / 40 / 40 insets, 1 px ink edge, square corners, starting about 100 px from the top of
  the window. The band's right keeps the page's links as today. `Band` is shared with the case page
  and must render there exactly as before (full-page captures of `c_sample` pixel-identical).
- E2. The intake's entry state is the desk. The sheet's head is the h1 "Start with your letter"
  (Headline, 28 px, 600) with the intro paragraph under it (body, 70ch cap), copy as today. Under them
  the letter's grid, 620 : 420 across a 48 px gutter: the paste box in the 620 px column, open from the
  start (no "Paste text" door at desktop), with its label ("Text of the letter"), the textarea at
  about 14 rows, the character count line and the "Read this letter" primary button (ink, 48 px, auto
  width) under it. The textarea is a square field on bond: 1 px pencil-edge border at rest, ink on
  focus with the 3 px ink focus ring, ink caret, 17 px Archivo. No wash and no gold: the gold field is
  the letter's fill-in, not this box.
- E3. The two doors sit in the 420 px column, level with the paste box's top: "Take a photo" and
  "Choose a PDF or image" as secondary buttons (bond, 1 px ink border, 48 px, full width of the column,
  ink text at 600), each with its one-line hint under it in 14 px faded ink (the hints are today's
  copy). A short label over the pair in 14 px faded ink: "Or add the letter as a file". The camera
  and file inputs stay the hidden inputs they are.
- E4. The scope line ("Recourse reads coverage denials and drafts appeals. It does not give medical
  advice.") closes the sheet at its foot, 15 px faded ink over a hairline, as today.
- E5. Processing. The sheet keeps its head; the 620 column shows the letter as given (the source
  panel: the text excerpt or the thumbnail) on the sheet; the 420 column shows the three stages
  (reading the letter, finding the program, filling the card) as the routing slip's idiom from
  `investigation/RoutingSlip.tsx`: a mark and a word per stage, an open ring for a stage not reached,
  a tick stepped in for a stage done, the running stage at 600; one polite live region; "Cancel" as a
  text action under them; at 30 s the timeout line with "Retry" in the same column. Copy as today.
- E6. Errors. The notice takes the 420 column (where the stages were) with the letter still in the
  620 column, so the reader sees what was read beside what went wrong; copy, headings and actions as
  today (retake, choose again, the scope refusal with what the product does instead, unreachable).
  No red: the notice is ink on bond with a 4 px ink left rule.
- E7. Reviewing. "Desktop shows the letter beside the card" (intake brief, decided): the letter as read
  in the 420 px column as a clipped exhibit ("The letter as read", the paper clip, the text at 15 px
  in a scrolling frame capped at about 60 vh, sticky from 1024 and up when the window is over 700 px
  tall); the case card in the 620 px column as the sheet's document: the one-paragraph reading, the
  postmark (the deadline stamp as today, dashed until confirmed), "Check these details" with the ten
  rows, the gold Check bar and label on flagged rows (the reader's own mark), "Show the letter as
  read" hidden at desktop since the letter is beside the card, and "Confirm" as the primary button at
  the card's foot, auto width, not sticky. The row layout, selects, inputs and validation are unchanged.
- E8. Confirming and confirmed. As today: the card locks, the postmark lands solid and turned, the
  investigation call fires and the page goes to the case, where piece 3 takes over. The save-error
  copy stays.
- E9. The landing. The same frame and the same top sheet. On the sheet: the h1 (Lead, 30 px, 600), the
  paragraph (body, 70ch), the scope line (15 px faded ink), then the primary button "Start with your
  letter" and beside it one text action to the sample case, "See a sample case" to `/case/c_sample`
  (the fixture opens in both intake modes; the builder confirms). Copy decided by Alvaro by prompt
  (Oct 28): today's h1, paragraph and scope line stay word for word; the link reads "See a sample
  case". Nothing else: no second sheet, no stamp, no feature list, no screenshots.
- E10. Motion. State changes step, nothing fades (intake brief). The stages' ticks step in as on the
  slip; reduced motion stops them. No land on the sheet.
- E11. Accessibility. Every control at least 44 by 44 px; focus rings as the world's; the stages' live
  region polite and atomic; the textarea labelled; the doors are buttons with their hints read as
  descriptions; contrast as DESIGN.md measures (pencil edge is a control boundary at 3:1, never text).
- E12. Untouched: the phone and tablet layouts (under 1024 px: today's one column, three stacked ways,
  the paste panel that opens, the sticky foot actions); all copy and the ten-field contract in
  `src/lib/case.ts`; fixture mode and its ids; the API; the case page.

Verification the builder owes before reporting: `tsc --noEmit` and `npm run lint` clean; Playwright
full-page captures at 390, 768, 1024 and 1280 by 800 of the landing and of every intake state (entry,
processing, each of the four errors, reviewing with flagged rows, confirming, confirmed) in fixture
mode; `c_sample`, `c_notsettled` and `c_consistent` at 1280 pixel-identical to captures taken before
the change; the live flow driven once through the real API in fixture mode is not required (no
credits). A fresh evaluator grades E1 to E12 with the captures before the orchestrator looks.

Decided by the builder, with the reason:

- The frame is shared, not copied: `components/intake/Frame.ts` holds the case page's numbers (band and
  page 1,152 px with 32 px padding, so 1,088 px of content; 36 px of ground under the 65 px band, so the
  sheet starts at 101 px; the 32 / 40 / 40 insets), every class `lg:`-prefixed. `Band` is not edited:
  both pages pass the case page's width to its existing `widthClass`, so the wordmark and the sheet share
  one edge (measured x = 96 at 1280, 32 at 1024).
- The letter's grid on the sheet is the `desk-cols` utility (620 : 420 across 48 px) inside the sheet's
  1,008 px, so the columns measure 571 and 387 px at 1280: the ratio the case page keeps below 1,088 px,
  not two fixed widths that would overflow the insets.
- The sheet keeps its head through processing and the errors: "Start with your letter" and the intro stay
  at the top of the sheet (desktop only) and the desk under them changes, so the step from entry to
  processing moves nothing above the desk. The head is a paragraph in those states, not a second h1:
  the stages' "Reading your letter" and the error's title stay the page's one h1, as on the phone.
- In the 420 px column the stages' and the notice's headings are 20 px (the Title size of a sheet's head,
  DESIGN.md), not the phone's 26 px: one 28 px head per sheet.
- The doors' label uses the paste box label's style (14 px, 600, uppercase, faded ink), so "Text of the
  letter" and "Or add the letter as a file" read as one row and the first door is level with the
  textarea's top (both measured at y 289 at 1280).
- The doors are named by their title alone (`aria-label`) and described by their hint (`aria-describedby`
  to the hint under the button) at every width; on the phone the hint inside the panel is `aria-hidden`
  so it is not read twice. Pixels under 1024 px are unchanged.
- The source order stays the phone's (the ways, then the paste panel they open), so at desktop the
  keyboard reaches the two doors before the paste box. Moving the panel first would have put it ahead of
  the "Paste text" door that opens it on the phone, the primary device.
- The paste box is 14 lines tall by CSS (`calc(14lh + 18px)`, 405 px) at desktop; the `rows` attribute
  stays 9 for the phone. On focus its border goes ink under the world's 3 px ink ring.
- The stages at desktop draw the slip's marks (`Mark`: open ring for a stage not reached or running, a
  tick with the slip's `tick-step` for a stage done) and sit between two hairlines like the slip; the
  phone's squares are `lg:hidden` and the marks `hidden lg:block`, so the phone renders as before. Every
  stage is ink at desktop (the phone keeps faded ink for stages not current).
- The notice's 4 px ink left rule replaces its sheet edge at desktop, with 24 px between rule and text;
  its actions keep their sizes.
- The case card's heading is 28 px at desktop on the intake (the sheet's head size); `bare` (the case
  page's full card) is unchanged.
- "The letter as read" exhibit has the paper clip and the corner marks but no "Exhibit N" folio: the
  letter is not yet an exhibit of a case, and the spec adds only the head. Its hairline under the head is
  the sheet head's rule. The scrolling frame is a focusable region (`tabIndex=0`, labelled by the head),
  so the keyboard can scroll it.
- The exhibit's sticky offset is 32 px, not the page image's 16 px, so the paper clip (22 px above the
  edge) stays on screen while it sticks; sticky only at 1024 px and up when the window is over 700 px
  tall (measured: y 32 after scrolling at 1280 by 800; static at 1280 by 680).
- Confirm sits 32 px under the last row at desktop, auto width, with its help line left-aligned under it
  (centered on the phone, as before).
- The landing's "See a sample case" is shown at 1024 px and up only (E12: nothing changes under 1024 px),
  44 px tall, 32 px right of the button. The scope line is 15 px at desktop (16 px on the phone).

Recorded, not changed:

- `/case/c_sample` opens in fixture mode and in live mode on the dev server (`isFixtureCase`), but a
  production build in live mode serves it from the API, which answers 404 ("No case c_sample"). The fix
  is in `src/lib/case.ts`, outside this piece.
- A file of the wrong type shows a broken image in "Your letter" (the preview treats every non-PDF as an
  image) at every width; fixing it changes the phone, which E12 forbids in this piece.
- The list's label "Three ways to add the letter" stays as copy while desktop shows two doors (the third
  is display: none there, so a screen reader hears two items).
- The confirmed card shows two rules (the last row's and the "Case opened" block's) at every width, as
  before.
- In reviewing, focus reaches the letter before the card at desktop: the source order is the phone's
  (the letter, then the card), and reading the letter before checking the card is the job.
- The deadline stamp turns -2.6 degrees both before and after Confirm (`DeadlineStamp` is untouched);
  DESIGN.md's -1.4 then -2.6 describes the sketch, not the code.

Fix pass after the evaluation (Oct 28, 2026):

1. World labels at desktop (Alvaro's decision). From 1024 px every field label and hint on the desk
   and the card is DESIGN.md's label: "Text of the letter", "Or add the letter as a file", "Your
   letter", the ten field labels, "First day" and "Last day", and the help lines (measured at 1280:
   14 px, 400, text-transform none, letter-spacing normal, #4e493d). The flagged row's mark is the word
   "Check" in sentence case, 14 px, 600, in ink, underlined 2 px in the gold #ffbe2e (offset 4 px); the
   6 px gold bar stays (measured 6 px, #ffbe2e). The word is ink, not gold, because gold text on the
   wash measures about 1.5:1; the gold is the reader's-pen mark under it, as on the letter's fill-in
   fields. The phone keeps the uppercase register and the gold tag (lg: overrides only).
2. The fixture cases are served in a production build: `isFixtureCase` and the synthetic-quote gate
   in `src/lib/case.ts` no longer check NODE_ENV (`FIXTURE_ID` still excludes real ids, c_ plus six
   hex). Proved with `npm run build` (NEXT_PUBLIC_INTAKE_MODE=live, exit 0) and `next start -p 3100`:
   the landing's link reads /case/c_sample; the page renders "Sunshine Health", the band's "sample
   case", the stamp "The denial appears inconsistent with the policy." and the policy exhibit's crop,
   with zero calls to the API. The server on 3100 was stopped after.
3. Heading levels: "Start with your letter" is the h1 in every pre-review state where it is in the
   DOM (the sheet's head in processing and the errors is now an h1, display: none under 1024 px);
   "Reading your letter" and the error notice's title are h2 at every width, same classes. This
   replaces the builder bullet above that made the head a paragraph. Accessibility tree: at 1280,
   processing and the scope error expose heading level 1 "Start with your letter" then level 2; at
   390, the level 2 heading alone.
4. The letter-as-read frame has its own scrollbar (scrollbar-color ink on bond, thin; scoped to the
   frame) and 8 px of padding at its sides and foot inside the 1 px hairline, so the 3 px ink focus ring
   (offset 2 px) clears the text (captured focused by keyboard at 1280).

Phone and tablet captures of every intake state and the landing (33 with the three cases at 1280) are
pixel-identical to the captures taken at HEAD before piece 4.

Recorded after the re-check (Oct 28, 2026, orchestrator): `FieldRow` is shared with the case page's
"Show the full case card" panel, so that panel's labels now read in the world's register too (14 px,
sentence case, 400) instead of the old uppercase eyebrows. Accepted as the intended outcome of
Alvaro's label decision, not a regression: the finish review had removed that register from every
other part of the case page. The collapsed case page is pixel-identical; only the expanded panel changes.

## 13. Second opinion on the page (Oct 28, 2026)

The API now runs the verdict stage a second time on Muse Spark Open (Meta's open-weights model) with the
same findings and prompt, beside the letter, and stores `second_opinion` with whether it agrees with Muse
Spark 1.3's verdict (`api/main.py`, `policyqa/second_opinion.py`). It is a trust signal for the reader and
a Meta-tooling point for the judges; it never changes the verdict. The page shows it in the world's idiom
(a drawn mark beside words, ink, no new hue) without moving anything piece 3 holds still. Made by the
orchestrator (F1 to F7), then by the builder where marked.

- F1. Contract: `CaseRecord.second_opinion?: SecondOpinion | null` in `src/lib/case.ts`, the API's shape
  (status skipped, running, done or failed; reason, model, outcome, proposed_outcome, decisive_fact,
  relies_on_exception, agrees, the token counts, latency_ms, cost_usd, error). Nothing else in the
  contract changes.
- F2. One line directly under the counts line in the verdict section, at every width: a 16 px mark and
  17 px ink words, tabular numerals. Done and agrees: a tick, "Second opinion: Muse Spark Open agrees."
  Done and disagrees: an open ring, "Second opinion: Muse Spark Open says the denial holds" (or "the
  denial appears inconsistent", "the documents do not settle it"). Running: a ring, "... is deciding…".
  Failed: a ring, "... did not answer." Skipped, absent or null: not rendered. The name is "Muse Spark
  Open" for any model id containing "muse-spark-open", else the id as given.
- F3. Nothing moves when the second opinion settles: the line arrives with the counts at decided and
  changes its words in place (same element, no land on a text change); the tick steps in when agrees
  arrives; reduced motion stops it.
- F4. Receipt: a row "Second opinion (Muse Spark Open)" after the verdict's row with its seconds and
  cost when done; "Second opinion" with "did not answer" in the time column when failed; no row when
  skipped or absent. The total time leaves it out (it ran beside the letter); the total cost includes it.
- F5. Announced through a live region that already exists, never a new one.
- F6. Fixtures: `c_sample` agrees (running first, done one poll later), `c_consistent` disagrees (says not
  settled), `c_notsettled` is skipped; the other fixtures carry no `second_opinion` key.
- F7. Full-page captures of `c_dual`, `c_rejected`, `c_checkerror`, `c_fail` and `c_error` at 390 and
  1280 identical before and after; `c_sample` at 1280 identical except the added line and the receipt.

Decided by the builder, with the reason:

- The poll keeps going while `second_opinion.status` is "running" (`secondOpinionPending` in `pollCase`),
  but `isWorking` is unchanged: the case's chain is done at reviewed whatever the second opinion does, so
  the slip still folds into the band after its one-poll hold and nothing else waits for it. Absent, null,
  skipped, done and failed stop the poll as before.
- The slot is not reserved by an empty box: the line exists from the first poll that carries a running
  second opinion, which on the API is in practice the poll that brings the verdict (it is stored running
  right after the verdict, before the letter starts; a poll landing between those two writes would show
  the line one poll later), so it lands with the counts (the same `land` class) and only its words and
  mark change after. A case whose second opinion is skipped, absent or null keeps today's
  pixels, which F7 requires; an empty reserved row would have moved every one of them.
- The slip and the exhibits do not move because the stamp's column (stamp, counts, the new line) is
  still shorter than the reference block beside it: measured at 1280 by 800 on `c_sample`, counts at
  y 282.9, line at 311.5, slip at 371.2 and the first exhibit at 501.2 at decided (running), at done and
  at reviewed until the slip folds (then 395.2, as before), the same stamp (122.2), slip and exhibit
  values as before the change; the slip was at 371.2 while deciding too. At 1024 the slip at 494.8 and
  the exhibit at 656.8 from deciding through reviewed. (Numbers from the first build; re-measured after
  the fix pass below.) The mark is top-aligned, centred on the first line, for when the words wrap.
- The tick on the line uses the slip's `tick-step` (160 ms, two steps), added when the mark turns to a
  tick, so it runs once; under reduced motion its animation is none (measured).
- Announcement: `useSecondOpinionNews` in `RoutingSlip.tsx`. When the view saw the second opinion go from
  running to done or failed, its line is the news in the slip's polite atomic region until the stage line
  changes; if the stage line changed in the same poll both are said ("Drafting the appeal letter… Second
  opinion: Muse Spark Open agrees."). A case opened already settled announces nothing; the line is on the
  page. The phone's existing stage-line live region (display: none at desktop) gets the same news as an
  unseen span, so a phone reader hears it too; no pixel changes there.
- The receipt row is not counted in the model line ("Model: fixture" stays) or in the heading's step
  count; its label names the model. A failed row prints its cost without the model, so a zero reads
  "$0.0000", not "prices not set". (The note about the total time is in the fix pass below.)
- `c_notsettled`'s skip reason is the one the API gives a fixture verdict ("the primary verdict is the
  fixture (no model call)"): it is never shown, and it is the honest reason for a fixture.
- `c_error` and `c_fail` share the sample's fixture kind but carry no second opinion: only the ids
  starting `c_sample`, `c_consistent` and `c_notsettled` do. `c_sample`'s line arrives at decided as "is
  deciding…" and turns to "agrees." at drafting (one poll), latency 4.2 s, cost $0.0091; `c_consistent`'s
  says "the documents do not settle it." (3.9 s, $0.0087).
- A model id that is null (a failure before the provider was made) is named "the second model".

Verified: `npx tsc --noEmit` and `npm run lint` clean. Poll stop, against mocked GET responses on a live
id with every other API request aborted, at 1280: a reviewed record with no `second_opinion` key, with
null, with skipped and with failed each sent 2 GETs and stopped (the no-key record is today's behaviour;
React's development double mount sends one extra); running for three GETs then done sent 4 and stopped;
running throughout kept polling (10 GETs in about 15 s). The line was the same node from "is deciding…"
to "agrees.", and the slip's live region read "Second opinion: Muse Spark Open agrees." F7 (captures run
one at a time; run in parallel the baseline itself was not stable): nine of the ten captures of the five
cases are pixel-identical to the baseline. `c_fail` at 1280 renders its receipt in one of two raster
states 1 px apart: one capture of seven after the change matched the baseline exactly and six were the
other state, while its layout measured the same on every run (receipt heading at y 1588.81, a fractional
offset that snaps either way). `c_notsettled` at 1280 is identical too.
`c_sample` at 1280: the page is 41 px taller (the receipt row); rows above the counts are identical except
46 pixels inside the stamp's noise texture (the stamp's y is 122.2 in both); the added line; the rest
identical down to the receipt's table, whose columns rebalance for the longer label, the new row and the
total cost ($0.0000 to $0.0091); the page foot under the table identical.

Fix pass (Oct 28, 2026, orchestrator), built as follows:

1. Size. The line takes the counts' size, weight and leading at every width: 15 px / 20.6 px at 400 at
   desktop, 17 px / 23.4 px at 400 on the phone (measured equal to the counts at 390, 1024 and 1280), and
   sits 4 px under them, the counts' own row gap (was 8 px and 17 px everywhere), so the two read as one
   group. The mark is 2 px down the 21 px line at desktop, 4 px down the phone's 23 px line. Re-measured
   on `c_sample` at 1280 by 800: stamp 122.2, counts 282.9, line 307.5, slip 371.2 (371.2 while deciding
   too), first exhibit 501.2, the same at decided (running), at done and at reviewed until the slip folds
   (then 395.2); at 1024: stamp 170.5, slip 494.8, exhibit 656.8 through the same moments. `c_consistent`
   at 1280 gives the same stamp, slip and exhibit values.
2. Wording. At 15 px the longest wording, "Second opinion: Muse Spark Open says the documents do not settle
   it.", measures 467 px and sets on one line at 1024 (the line box is 498 px) and at 1280 (526 px), so
   the disagree form is not shortened. On the phone (17 px, 300 px for the words) it takes two lines,
   under the counts' three rows.
3. Receipt note. When the second opinion's row is shown, one line under the table, before the model
   line: "The second opinion ran beside the letter; its time is not in the total." It uses the receipt's
   existing note style, which measures 15 px in faded ink (#4e493d), not 14 px; matched to the notes
   already on the slip. Measured on all eight fixtures at 1280: the note is on `c_sample` and on
   `c_consistent` (the two with a second opinion row, F6); none of the other six. This replaces the
   builder bullet above that left the total unexplained.

Verified after the fix pass: `tsc --noEmit` and `npm run lint` clean. F7 recaptured one at a time: the
same nine of ten captures pixel-identical, `c_fail` at 1280 again in its other raster state, `c_notsettled`
at 1280 identical. `c_sample` at 1280 is identical above row 311 (the stamp's texture matched this time),
then the line, the rest identical down to the receipt; the page is 76 px taller (the row and the note).

Recorded after the fresh evaluation (Oct 28, 2026, orchestrator), not changed: on the phone the
stage line's atomic region re-reads its old line together with the second opinion's news when it
settles; at 390 the agree line wraps with "agrees." alone on its second line; a done second opinion
with a null outcome reads "did not answer" on the line while its receipt row keeps its seconds and
cost; the receipt note's "ran beside the letter" reads oddly on a case that drafted no letter; the
`c_fail` fixture's receipt sits 1 px higher on about half of its 1280 captures with or without this
change (a pre-existing flicker, not a layout change).

## 14. Critique fixes (Oct 28, 2026)

From the Impeccable critique of Oct 28 (27 of 40; `.impeccable/critique/2026-10-28T19-51-00Z__web-src-app-case-id-page-tsx.md`):
the four fixes that keep the page's structure and cost nothing in layout. A caregiver with a consistent or
not-settled verdict was shown "Appeal by" as the lead while the real next step sat far down the page; the
steelman, a stated differentiator, was hidden under a disclosure; the run's findings landed out of view;
and a screen reader met an h2 before the h1. Decided by the orchestrator (G1 to G5), then by the builder
where marked.

- G1. On the consistent and the not-settled verdicts the reference block's Lead line is the next step, at
  the Lead size, and the deadline follows it as a 17 px line with its day count (the reader may still
  appeal). The inconsistent verdict keeps "Appeal by" as the Lead. Nothing moves at decided.
- G2. The steelman shows as a one-line strip on the top sheet: "The payer would say" (14 px faded ink) and
  the steelman's first sentence (17 px ink), ending in an ellipsis rather than taking a second line; the
  "+ The payer's best argument" disclosure keeps the full text.
- G3. During the run the newest landed finding's question is in view under the slip, 17 px ink with its
  mark (tick supported, open ring not settled, strike unsupported), one element changing in place, its
  line held from the first poll, gone when the slip folds.
- G4. The h1 (the payer before the verdict, the stamp after) is the first heading in the DOM at every
  width, the h2 "Verdict" follows it, and "The rule" and "The gap" are h3 under it; the index tabs and the
  band carry no headings.
- G5. Under 1024 px G1 to G4 apply in the one-column layout, G3 in the same place (under the stage lines).
  Every other fixture is pixel-identical; where a fixture carries a steelman or a consistent or
  not-settled verdict, the only changes are these lines.

Decided by the builder, with the reason:

- G1 wording. The orchestrator's examples ("Ask the plan for the September authorization", "No appeal
  letter; see why the denial holds") measure 586 and 548 px at the Lead size against a 440 px reference
  block (340 px from 1024 to 1279), so each takes two lines. The reference block is the taller column, so
  the slip and the exhibits sit under it: every extra Lead line would move them 33.6 px at decided. The
  Lead lines are therefore short fixed actions in the page's own words that set on one line at 1024 and
  at 1280: "See why the denial holds" (consistent, 328 px) and "Find what would settle it" (not settled,
  317 px). The specific record is named under "What would change it" on the same sheet. A line derived
  from `what_would_change` is free text from the model and cannot be held to one line. "No appeal letter"
  is not used: at decided the letter stage has not run, and the page does not guess (section 11).
- G1 layout. The deadline Lead line is always laid out in its slot; when the next step leads, it stays as
  an unseen spacer (`visibility: hidden`, out of the accessibility tree) and the next step and the 17 px
  deadline line sit over it in the same grid cell, so the slot keeps its height (67.2 px at 1280, 100.8 at
  1024) and the rows, the slip and the exhibits do not move. The deadline line reads "Appeal by Dec 13,
  2026 · 46 days left". Neither line carries a mark: the open ring already means too many things (the
  critique counted seven). On the phone the next step is 20 px at 600 (the phone's Lead) above the same
  17 px deadline line, in place of the 20 px deadline line. Edge: a not-settled or consistent case with
  no stated deadline has a one-line spacer ("Deadline not stated"), so its slot grows by one line at
  decided; no fixture has that case.
- G2 placement. The strip sits inside the steelman's group, under the disclosure's heading and above the
  full text when it is opened: the heading then introduces the strip for a screen reader (above the
  heading it would be read as part of the previous section). The group follows the rule and the gap, and
  "What would change it" on a case with a letter, as before. One line from 1024 px within the group's
  70ch measure; on the phone the label sits over the sentence, since a shared 326 px line would leave the
  sentence about 20 characters. A struck steelman (`c_dual`) is struck in the strip too, with "Struck,
  could not verify" read before it. The sentence's line is 26 px, a whole pixel, so the page under the
  strip shifts by exactly 30 px (50 on the phone) and renders identically after it.
- G3. The line is a plain paragraph inside the slip's block, 12 px under the stages, 24 px tall even when
  empty; it is not a live region (the slip's region already says "Question 3 of 5…"). A screen reader
  hears "Latest finding:", the question, and the state in words, since the mark alone is never the
  signal. A run that stops before the verdict (`c_fail`) drops the line: no exhibits exist to move, and the
  slip's words say where it stopped. On the phone it sits under the two stage lines, gone when the chain is
  done or stopped before the verdict.
- G3 found a remount: the slip remounted at decided. `VerdictSection` padded its pending tree with nulls so
  the slip kept its index, and by the child positions in the code the padding fell out of step when the second opinion line was added (inferred from the code, not measured on the earlier commit).
  The slip is now a keyed child in both trees, so it is matched by key, not by position. Measured: the
  slip's list and the latest-finding line are the same nodes from the first poll to the fold at 1280, 1024
  and 390 on the three cases below.
- G4. The visible opening ("What the documents say" on the phone, "1 Verdict" from 1024 px, unseen at
  tabs sizes) is no longer a heading: it is a paragraph hidden from assistive technology and keeps the id
  the index tab links to and the scroll spy reads, so the tab lands where it did. A visually hidden h2 after
  the stamp carries the same name ("1. Verdict" at desktop, "What the documents say" on the phone) and
  labels the section. No pixel changes.

Measured on `c_sample`, `c_notsettled` and `c_consistent` (fixtures, every API call aborted), y in page px:

| Width | Moment | Stamp | Slip | Latest line | First exhibit |
|---|---|---|---|---|---|
| 1280 x 800 | first poll | 138.5 (deadline stamp) | 371.2 | 465.2 (empty) | none |
| 1280 x 800 | decided | 122.2 | 371.2 | 465.2 | 537.2 (was 501.2) |
| 1280 x 800 | reviewed, slip open | 122.2 | 371.2 | 465.2 | 537.2 |
| 1280 x 800 | reviewed, slip folded | 122.2 | none | none | 395.2 (as before) |
| 1024 x 800 | first poll | 138.5 (deadline stamp) | 494.8 | 620.8 (empty) | none |
| 1024 x 800 | decided to reviewed | 170.5 / 171.9 / 172.7 | 494.8 | 620.8 | 692.8 (was 656.8) |
| 1024 x 800 | slip folded | as at decided | none | none | 518.8 (as before) |

The reference block measured 233.2 px at 1280 and 304.8 at 1024, and its Lead slot 67.2 and 100.8, on all
three cases at every moment, as before the change. The exhibits sit 36 px lower while the slip is open
(the reserved line and its 12 px); the stamp, the slip and the folded page are where they were. On the
phone the line holds 32 px above the stamp during the run and folds with the chain, so the stamp moves
up 32 px at the end (the reader's place is kept by the existing anchor).

Verified: `tsc --noEmit` and `npm run lint` clean. Full-page captures of the eight fixtures at 390 and 1280,
finished, against captures taken before the change (one at a time): `c_fail` identical at both widths
(its 1280 capture needed a second take for the known 1 px receipt raster state); `c_sample`, `c_error`,
`c_rejected` and `c_checkerror` identical except the inserted strip (30 rows at 1280, 50 at 390);
`c_consistent`, `c_notsettled` and `c_dual` identical except the Lead block (rows 142 to 203 at 1280; the
next-step lines at 390, 11 px taller, plus 41 pixels of the stamp's noise texture where the stamp moved
11 px) and the strip. Accessibility tree on `c_sample`: before the verdict, level 1 "Sunshine Health" then
level 2 "Investigation record" (1280) or "Findings" (390); after it, level 1 the stamp, level 2 "1. Verdict"
(1280) or "What the documents say" (390), then level 3 "The rule", "The gap", "What would change it",
"The payer's best argument".

Fresh evaluation (Oct 28, 2026, about 6:40 pm, an Opus evaluator that had not seen the build; its own
baseline from a worktree of b32d9c9 on port 3001, pixel-identical to the builder's `before` set; patch id
dfecc7f47bca45069bde93bdb8ade319907e75ce): G1, G2, G4 and the remount claim PASS (the base remounted the
slip and its `ol` on all 12 runs, the change on none; every desktop number in the table above
reproduced; the second-opinion line is one element from "is deciding…" to "agrees."); G3 and G5 FAIL,
both under 1024 px. Accessibility: no regression (strip label 8.96:1, sentence 17.22:1, the struck state
read in words before the sentence). Findings and what was decided:

- D1 (G3, phone). At 390 by 844 the latest-finding line under the stage lines sits below the viewport
  during the run (c_dual at y 835 to 869; c_sample ends 3.7 px from the bottom edge), so "in view" does
  not hold on the phone. Alvaro, Oct 28: deferred to the weekend's phone pass (the critique's P1 redoes
  that layout); recorded here as a known gap until then.
- D2. `firstSentence` cut at an abbreviation followed by a capital: "Under 42 C.F.R. Part 409…" became
  "Under 42 C.F.R."; "U.S. Code", "Fla." and "Dr." the same. No fixture triggers it; real steelmans
  cite C.F.R. and Fla. Fixed Oct 28 (orchestrator): a stop that ends a dotted token, a single letter or
  a listed abbreviation does not end the sentence, and a closing quote or bracket after the stop belongs
  to the sentence (the quote case was already wrong at 405a414; the evaluator's control found it).
  Re-checked by the same evaluator on its thirteen strings: the four that failed and seven controls
  cut right; two accepted over-runs ("under Part B. The plan", "answered no. It") come back whole, held
  to one line by the strip's ellipsis, the cost of keeping "U.S." and "No. 5" intact. The reader-text
  fix passes (the tree reads "Latest finding: <question>, supported"); all sixteen finished captures
  pixel-identical to the evaluated set; tsc and lint clean.
- D3 (G5, cosmetic). At 390 on c_consistent, c_notsettled and c_dual the stamp's grain changes where
  the stamp moved 11 px: the `#ink-stamp` filter's noise depends on position. Accepted; "pixel-identical"
  in G5 reads as "except the stamp's grain where the stamp moves".
- D4 (disclosed). On the phone the reference block grows 17 px at decided where it grew 6 px before;
  the outcome-first reflow at the same moment hides it. Accepted.
- Screen-reader text of the latest line read "? , supported" (a join artifact between nodes). Fixed
  Oct 28: one string, "Latest finding: <question>, supported", with the visible question aria-hidden.
- Not verified by the evaluator: the open ring for a not-settled finding as the newest one (the polls
  land findings 2, 4, 6 and 8, never the fixture's only not-settled finding, number 3).
- Contract gaps it named, left open: "nothing moves at decided" cannot hold under 1024 px because the
  base already reflows outcome-first there (limit it to 1024 px and up); G3's "in view" conflicts with
  the phone placement under the stage lines; index tab 1 points at an aria-hidden paragraph (pointing it
  at the hidden h2 would remove the question, untested with a screen reader); the next-step Lead reads
  like an action but is not a link; no fixture covers a consistent or not-settled verdict with no stated
  deadline, an empty steelman, a failure after the verdict, a letter deadline different from the
  claimed one, widths from 391 to 1023 px, or a phone shorter than 844 px.

## 15. The sample as a recorded run (Oct 28, 2026)

The critique of Oct 28 (P1, issue 2) found that the showcase proof reads as fake: every highlight on
`c_sample` says "[synthetic fixture quote, not from the document]", the page images are drawn
"SYNTHETIC FIXTURE PAGE"s, the receipt says "Model: fixture" and "$0.0000", and that case is the
landing's only sample link. The fix is to replay a real run. On Oct 28 at 4:04 pm the demo letter dc-001
went through the restarted API with the second opinion on and is stored as `data/cases/c_f3b3d0.json`
(inconsistent, 6 findings all supported, 4 of 4 letter claims verified, the critic found one issue and
rejected its own revision, the second opinion agrees in 4.1 s, $0.12 in all). That record becomes
`c_sample`. Only the denial letter is synthetic (dc-001 was written for the demo and says so in its
first line); the policy pages, quotes, highlights, vision checks, costs, seconds and the second opinion
are what the API produced. Decided by the orchestrator with Alvaro (H1 to H12), then by the builder
where marked. Alvaro's two decisions, Oct 28, 5:40 pm: the replay runs at the recorded timing, and the
one disclosure lives in the band's tab.

- H1. Scope. The `c_sample` family only (`c_sample` and the `c_sample<n>` ids the fixture-mode intake
  issues). The other seven fixtures (`c_consistent`, `c_notsettled`, `c_dual`, `c_rejected`,
  `c_checkerror`, `c_fail`, `c_error`) keep their synthetic data and their pixels: full-page captures at
  390 and 1280, finished, identical before and after (the control). They are screenshot fixtures and
  nothing public links to them.
- H2. The export. A script `web/scripts/sample-case.mjs`, run from `web/` against the local API
  (`http://localhost:8000`), reads `../data/cases/c_f3b3d0.json` (gitignored; it lives on Alvaro's
  machine) and writes two committed outputs: `web/src/lib/sample-case.ts` (generated, "do not edit by
  hand" in its header, the source record named) and `web/public/sample/<doc_id>-p<page>.png`, the cited
  pages at 110 dpi from `GET /doc/{doc_id}/page/{page}.png` (six pages on Oct 28: fl-03 p5, fl-04 p5,
  p6, p7, fl-14 p5, fl-21 p71; about 260 KB each). The generated module holds: the `CaseRecord` as the
  API served it at `reviewed` with `case_id` rewritten to `c_sample` and nothing else changed; and, for
  every distinct (doc_id, page, quote) cited anywhere in the record (each finding's citations and
  struck list, the steelman, the rule, every letter sentence, the evidence checklist, the deadline and
  the filing), the highlight response from `GET .../highlight?quote=&dpi=110` (title, width_px,
  height_px, boxes_px, score, found, matched) and the vision result from `POST .../vision-check`
  (checked, model, text_in_highlight, agrees, latency_ms, cost_usd), with `image_url` rewritten to
  `/sample/<doc_id>-p<page>.png`. The script is idempotent and prints what it wrote. The API caches
  vision results in process, so a re-run after the first costs nothing; the first run is at most about
  20 vision checks at about $0.005 each.
- H3. The replay runs at the recorded timing. The page opens as today with the investigation running
  (the slip at its first mark), and each stage lands when it did on Oct 28: the plan after its span
  (5.2 s), the findings in the order of the trace's `question` spans at offsets reconstructed from the
  trace under the API's recorded concurrency so that the last finding lands at the investigation's
  `latency_ms` (17.9 s, within half a second; the builder reads the worker count from `policyqa` and
  records the reconstruction, or spreads the findings evenly after the plan if the trace cannot
  support it and says so); `investigated` then `deciding` at once; `decided` with the verdict
  `verdict.latency_ms` later (4.1 s); `drafting`, then `drafted` with the letter `letter.latency_ms`
  after the verdict (6.9 s); `reviewing`, then `reviewed` with the critique `critique.latency_ms`
  later (9.0 s); the second opinion `running` from `decided` and `done` `second_opinion.latency_ms`
  after the verdict (4.1 s, during drafting). About 40 s to `reviewed`. Each stage still outlasts one
  poll (1.5 s), so every slip mark is seen. The status names are the API's
  (`investigating`, `investigated`, `deciding`, `decided`, `drafting`, `drafted`, `reviewing`,
  `reviewed`).
- H4. Every number on the page is the record's: the receipt's rows carry the recorded seconds and
  costs per stage and the real model names ("muse-spark-1.3", "Muse Spark Open" for
  `meta-models/muse-spark-open-1026`), the counts are the record's, the trace is the record's. An
  enumerable check at `reviewed`, at 390 and 1280: the rendered text of `/case/c_sample` contains none
  of "fixture", "synthetic fixture", "SYNTHETIC", "$0.0000", "Model: fixture", "Vision check not run",
  "prices not set", "Sunshine Health", "[synthetic". The word "sample" is allowed only in the band's
  tab (H6), the letter's own text ("Sample Health Plan", "A. Sample", its first line) and the card.
- H5. Highlights and the vision check. `getHighlight` and `visionCheck` answer from the recording for
  the sample's quotes: a lookup by (doc_id, page, quote) in the generated table before anything else,
  in both intake modes; a quote not in the table behaves as today (synthetic prefix in fixture mode,
  the API in live mode). The highlight waits the fixture's 450 ms; the vision check waits the recorded
  `latency_ms` of that check. The policy exhibit on the top sheet shows the real page crop with the
  real boxes and the caption "Muse Spark vision check: matches the quote." with its tick; "See the
  page" opens the real page from `/sample/` with the recorded highlight and the recorded check. The
  exhibit effect stays keyed on `doc_id`, `page`, `quote` (section 11); the check runs once per open.
- H6. The disclosure, once. On the sample family the band's folder tab reads
  `c_sample · recorded run, sample letter` (the id as today, then the words in the tab's 14 px mono)
  with the title "A recorded run of October 28, 2026 on a denial letter written for this demonstration.
  The policy pages, quotes, checks, costs and the second opinion are the API's own." Under 640 px,
  where the tab is hidden, the band's plain marker reads `recorded run` with the same title. The other
  fixtures keep `· sample case` and `sample case` as today. No other line on any sheet says synthetic,
  sample or demo, and the landing's copy is not touched.
- H7. The card, summary and letter text. The sample family carries the record's `card`, `summary` and
  `raw_text` (Sample Health Plan, 16 hours a day, $11,520.00, letter of October 7, 2026, appeal by
  December 6, 2026). The fixture-mode intake (`fixtureIntake`) returns the record's card and summary
  too, so the case it opens (`c_sample<n>`) reads as the same case from the card on. The other seven
  fixtures keep `SAMPLE_CARD`, `SAMPLE_SUMMARY` and `SAMPLE_LETTER_TEXT` (Sunshine Health) unchanged:
  the builder splits the constants rather than editing them.
- H8. Dates stay live. `days_left` on the deadline stamp, the Lead line and the deadline section is
  computed from the record's date at render (the components already fall back to `daysUntil` when
  `days_left` is absent; the replay sends it absent or recomputed, never the recorded 39), so the count
  is right on the day a judge opens the page. The recorded `created_at` and the investigation's
  `started_at` and `finished_at` are shifted to the replay's own clock, as the fixture does today, so the
  receipt's elapsed times and the slip's timing agree.
- H9. Production. The fixtures ship in the production build (section 12, Alvaro's decision), so
  `npm run build` must pass with the generated module and the six PNGs, and `/case/c_sample` must open
  with every request to the API aborted (the captures below are taken that way). The generated module
  stays under about 200 KB; the PNGs are served from `public/sample/`.
- H10. Nothing moves on the replay that held still on the fixture: measured with the section 14
  script (stamp, slip, latest-finding line, first exhibit, register, Lead slot, strip) at 1280 by 800
  and 1024 by 800 every 100 ms from the first poll to the fold, and at 390. The positions may differ
  from section 14's table because the content differs (the stamp's column, the reference block and
  the strip hold other words), but after an element lands it does not move until the slip folds, the
  slip and its `ol` are one node from the first poll to the fold, and the second-opinion line is one
  node from "is deciding…" to "agrees." (sections 11, 13, 14). The builder reports the measured table
  for `c_sample` in this section.
- H11. The record's text is kept byte for byte: the policy quotes carry U+2022 bullets from the PDF
  text layer, and the struck or supported states, the critic's rejected revision ("The revision made
  no change to the letter.") and the second opinion's decisive fact are shown as the components show
  them for a live case. If a component renders a recorded field badly (a wrapped bullet, an empty
  "What would change it"), the builder reports it here and does not edit the data.
- H12. Verified before Alvaro's look: `npx tsc --noEmit`, `npm run lint` and `npm run build` clean;
  the export re-run prints "nothing changed"; the H4 text check at both widths; the H1 control (seven
  fixtures, fourteen captures, pixel-identical, one at a time); H10's table; full-page captures of
  `c_sample` at 390 and 1280 at `reviewed`, and the run frames at 1280 (the section 14 script with a
  shots folder). README's demo line ("synthetic sample letters") gains the words that the public
  sample is a recorded run of dc-001 with its date; DECISIONS gets the entry.

Decided by the builder, with the reason (Oct 28, 2026, evening):

- The export (`web/scripts/sample-case.mjs`) reads the stored file, not `GET /case/c_f3b3d0`, so it
  runs against an API that no longer holds the case. It walks every citation H2 lists plus the draft
  paragraphs and the critic round's before and after, and finds 15 distinct (doc_id, page, quote) on the
  six pages. The generated module is 95 KB. The page images carry no `dpi` parameter, so the exhibit's
  220 dpi request (`sharpSrc`) leaves them at 110 dpi as H2 says: the crop is softer than a live one.
- `pageImageSrc` treats `/sample/` like `/fixtures/` (served by the web app, never the API), so the
  production build in live mode loads the pages from `public/sample/`.
- The reconstruction (H3): `ANSWER_WORKERS = 3` in `policyqa/investigate.py`. The questions go to the
  pool in planned order once the route and plan spans are done (5.19 s); each lands at its worker's
  start plus its `question` span. Result: f2 at 10.44 s, f1 11.19, f3 12.59, f4 15.92, f5 16.67, f6
  17.89, which is the order of the trace's question spans; the last lands 7 ms before the recorded
  17.894 s. The replay computes this from the record when it loads (`recordedTimeline` in `case.ts`);
  if a question span were missing it would spread the findings evenly after the plan. As the API does,
  the findings list is in planned order, so f1 lands above f2 and the latest-finding line keeps f2's
  words until f3 lands.
- decided and drafted are each held 1.8 s (2.5 s since the fix round, below) inside the next step's recorded time,
  not added to it. A fixture poll comes every 1.75 s (the 250 ms read plus 1.5 s), so a shorter hold
  could be missed. The chain still lands at the recorded seconds: the verdict 4.1 s after the
  investigation, the letter 6.9 s after the verdict, the self-check 9.0 s after the letter, reviewed at
  37.9 s. `investigated` is not served (deciding at once, as H3 says).
- Counts and cost during the run follow the API's roll-up: `questions_planned` is 0 until the plan
  lands; the cost is 0 until the first finding, then the plan plus the landed findings. The trace grows
  with the run: each span appears once its step has landed.
- The constants are split: `RECORDED_CARD`, `RECORDED_SUMMARY` and `RECORDED_LETTER_TEXT` read the
  generated record; `SAMPLE_CARD`, `SAMPLE_SUMMARY` and `SAMPLE_LETTER_TEXT` are unchanged and still
  serve the seven fixtures. `isRecordedSample` (`/^c_sample\d*$/`) picks the family.
- The H4 check is `web/scripts/sample-text-check.mjs`. "sample" is allowed in the band, the case id,
  the register (the card's payer), the letter exhibit and the appeal letter. Its control: run on
  `c_rejected` it fails with 41 offending strings.

Measured (dev server, every API request aborted, one page at a time):

| Check | Result |
|---|---|
| Export, first run | 6 PNGs (219 to 260 KB), `sample-case.ts` 95 KB; 15 vision checks, 14 agree, 1 disagrees (below); recorded cost $0.1031, of which one check ($0.0048, the rule's fl-04 p5 quote) was already cached, so the run spent about $0.098 |
| Export, re-run | every file "unchanged", then "nothing changed", in 1.2 s |
| H1 control | 14 of 14 captures (seven fixtures at 390 and 1280) pixel-identical to the baseline taken before any source change |
| H4 text check | clean at 390 and 1280 on the dev server, and at 1280 on the production build in live mode (`next start`) |
| H9 | `npm run build` passes; on the production build `/case/c_sample` reaches reviewed with 0 API calls, the exhibit's page from `/sample/fl-04-p5.png`, the caption "Muse Spark vision check: matches the quote." |
| H5 viewer | "See the page" on `c_sample3` opens `/sample/fl-04-p5.png` with the recorded boxes and the recorded check text, 0 API calls |
| `tsc --noEmit`, `npm run lint` | clean |
| Receipt at reviewed | Investigation 18 s $0.0647, Verdict 4.1 s $0.0095, Second opinion 4.1 s $0.0076, Letter 6.9 s $0.0139, Self-check 9.0 s $0.0161, Total 38 s $0.1118; Model: muse-spark-1.3 |

H10 on `c_sample`, y in page px, seconds from page load:

| Width | Moment | Stamp | Slip | Latest line | First exhibit | Second opinion | Strip |
|---|---|---|---|---|---|---|---|
| 1280 x 800 | first poll (0.4 s) | 138.5 | 371.2 | 465.2 (empty) | none | none | none |
| 1280 x 800 | findings land (10.9 to 18.0 s) | 138.5 | 371.2 | 465.2 | none | none | none |
| 1280 x 800 | decided (23.3 s), settled by 23.9 s | 117.3, then 122.2 | 371.2 | 465.2 | 540.7, then 537.2 | 311, then 307.5 | 1165.3, then 1178 |
| 1280 x 800 | drafting to reviewed (25.1 to 39.2 s) | 122.2 | 371.2 | 465.2 | 537.2 | 307.5 ("agrees." at 26.9 s) | 1178 |
| 1280 x 800 | slip folded (40.8 s) | 122.2 | none | none | 395.2 | 307.5 | 1036 |
| 1024 x 800 | first poll | 138.5 | 461.2 | 587.2 (empty) | none | none | none |
| 1024 x 800 | decided, settled by 23.8 s | 169.2, then 170.5 | 461.2 | 587.2 | 660.7, then 659.2 | 339.5, then 337.9 | 1312.9, then 1322.1 |
| 1024 x 800 | drafting to reviewed | 170.5 | 461.2 | 587.2 | 659.2 | 337.9 | 1322.1 |
| 1024 x 800 | slip folded | 170.5 | none | none | 485.2 | 337.9 | 1148.1 |

The slip's `ol`, the latest-finding line and the second-opinion line kept one node each from their first
appearance to the fold at 1280, 1024 and 390. The register held 233.2 px (1280) and 271.2 (1024), its
Lead slot 67.2, at every sample. The settle at decided (the stamp 117.3 to 122.2 within 0.4 s, the strip
once more when the policy crop's image loads) is not new: the unchanged `c_consistent` settles the same
way at 1280 (117.3 to 122.2, 540.7 to 537.2), and `c_rejected`'s strip moves twice (crop, then caption).
At 390 the stage lines above the stamp change height with each status (stamp 858.1 and 886.1 in turn,
the latest line 744.3 and 772.3), as on the unchanged `c_rejected` (759.1 and 787.1): the phone layout's
known behaviour (D1), not the replay.

Reported, not changed (H11 and what the look showed):

- (Fixed in the fix round, below.) The band on the finished case at desktop: the tab with the payer, the date and "recorded run, sample
  letter" is 755 px wide (616 on `c_rejected`), so the status line beside it is 115 px wide and clamps
  to "Letter checked: / the first draft..." at 1280, 1440 and 1536 px alike (the column stops at
  1120 px). On the fixtures it fits on one line. A layout choice for Alvaro: drop the payer and the date
  from the sample's tab, or give the status line its room another way.
- (Fixed in the fix round, below.) During the first 10.4 s (before the first finding) the receipt reads "Investigation ... $0.0000
  (prices not set)", because the API's roll-up has cost 0 until a question completes and the model is
  real. It is below the fold at 1280 and 1024. A live case shows the same; the fix belongs in
  `formatCost` or the receipt (a running step's zero is not "prices not set"), not in the data.
- One recorded vision check disagrees: fl-04 p6, the 265-character quote "services for recipients
  under the age of 21 years exceeding the coverage described within this policy..." (finding f3 and one
  evidence item). Its "See the page" says "does not match the quote." That is the API's own result.
- The verdict's `what_would_change` is null; the section is left out, as the component does for an
  empty value. The U+2022 bullets in the fl-04 p5 quotes render inline in the exhibits and the letter
  ("• Are determined medically necessary • Do not duplicate another service ...").
- Not measured: the fixture-mode intake returning the record's card (the dev server runs in live mode,
  and a live intake is a POST this build may not make); `c_sample3` was opened directly instead.

Files: `web/scripts/sample-case.mjs`, `web/src/lib/sample-case.ts` (generated), `web/public/sample/`
(six PNGs), `web/src/lib/case.ts`, `web/src/components/intake/Band.tsx`,
`web/src/components/investigation/InvestigationView.tsx`, `web/scripts/sample-text-check.mjs`,
`README.md`, `DECISIONS.md`.

Fix round (Oct 28, 2026, evening), from a fresh evaluator's report and two decisions by Alvaro:

1. The sample's tab drops "opened <date>" (Alvaro's choice; the date came from the replay's clock). It
   reads `CASE c_sample · Sample Health Plan · recorded run, sample letter`; the title is unchanged.
   Measured on the finished case: the tab is 403 px at 1024 (the payer is hidden below 1280), 575 px at
   1280 and 1440; the band's status line "Letter checked: the first draft stands." is 223 px wide and
   one line (19 px) at all three, the same as `c_rejected` at 1280 (tab 616 px, status 223 px, one line).
2. The export is fail-closed. It fetches everything into memory; if any quote is not found or any
   vision check is not `checked` (or carries an error), it writes nothing, names each failure and exits 1.
   Otherwise it compares every would-be file with the one on disk and writes only those that differ,
   or says "nothing changed". Proved with a stub API (`node stub.mjs`, no model calls) in two modes:
   every vision check `checked:false, error:"provider timeout"` gave "REFUSED: 15 failure(s); nothing
   was written." and exit 1; one highlight not found gave "REFUSED: 1 failure(s)" and exit 1; the hash
   of the module and the six PNGs was the same before and after both. Re-run against the live API: exit
   0, all seven files "unchanged", "nothing changed", in 920 ms for 15 highlights, 15 vision checks and
   six pages. An uncached check took 2.3 to 13.5 s on the first run, so none of these 15 called the
   model. The API's own log was not readable from this session (it runs in a window I cannot see).
3. The intake page in fixture mode passes `sample="intake"` to the band, whose title now reads
   "Fixture mode: every submit opens the recorded run of the Sample Health Plan letter (October 28,
   2026)". The seven fixtures' case pages keep the old title. Not rendered: the dev server runs in
   live mode, where the intake band carries no mark; checked in the source and by tsc. The landing
   page (`app/page.tsx`) still passes `sample` as a boolean and keeps the old title in fixture mode,
   since H6 leaves the landing untouched; the orchestrator decides whether it changes too.
4. `formatCost(usd, model, reportedTokens)`: "(prices not set)" is added only when the cost is zero, the
   model is real, and the step's finished calls reported tokens (the plan or any finding for the
   investigation, the call itself for the verdict, letter and second opinion, the rounds for the
   self-check). The total gets the note only when some step reported tokens. The replay now counts the
   plan's cost when the plan lands (5.2 s), as it already showed the plan's tokens then; the API's own
   roll-up adds it at the first finding. Receipt per poll on the replay at 1280: $0.0000 from 0.3 to
   3.9 s, $0.0066 from 5.7 to 9.1 s, then $0.0146, $0.0236, $0.0349, $0.0543, $0.0647 as findings land,
   $0.1118 at reviewed; "prices not set" in 0 of the samples (49 samples, 5.6 to 9.1 s, in a run with the new rule but before the plan-cost change). The
   seven fixtures' finished pages are pixel-identical (item 6's control).
5. The recorded highlight and vision lookup answers only on the recorded sample family:
   `getHighlight` and `visionCheck` take the case id, which `PageViewerProvider` now carries in a
   context (`useViewerCaseId`) to the exhibit and the viewer. Proved on the live-mode dev server: case
   `c_f3b3d0` (its GET answered in the browser from the stored record, which cites the same 15 quotes)
   sent its highlight request to the API (2 requests, aborted and counted; the exhibit shows its error
   state), while `c_sample` reached reviewed with 0 API requests and its crop.
6. The holds for decided and drafted are 2.5 s. Re-measured at 1280 (seconds from page load, every
   API request aborted):

| Status first seen | 0.4 investigating | 19.8 deciding | 23.4 decided | 25.0 drafting | 30.4 drafted | 32.1 reviewing | 39.2 reviewed | 40.7 slip folded |
|---|---|---|---|---|---|---|---|---|

   Every status was seen. The latest-finding line changed at 10.9, 14.5, 18.0 and 19.8 s (f4 and f5
   landed between two polls, as the evaluator saw at 390); the stamp 138.5 then 122.2 (after a
   120.9 sample at decided), the slip 371.2, the latest line 465.2, the first exhibit 537.2 then 395.2
   at the fold, the second-opinion line 307.5 ("agrees." at 26.8 s), the strip 1178 then 1036: the same
   positions as the first table. The slip's `ol`, the latest line and the second-opinion line kept one
   node each to the fold.

Checks after the round: `tsc --noEmit`, `npm run lint` and `npm run build` clean; the H4 check
(`scripts/sample-text-check.mjs`, now also reading the page about 7 s into the run, after the plan
lands and before the first finding, where every forbidden string but "$0.0000" must be absent) clean at
390 and 1280. Its control: with the old cost line put back for one run (case.ts saved, mutated,
restored, compared byte for byte) it found "prices not set" twice at 7.0 s and exited 1. H1 control:
14 of 14 captures pixel-identical to the original baseline. `c_sample` captured at 390 and 1280 at
reviewed.

Fresh evaluation (Oct 28, 2026, 8:00 to 9:20 pm, an Opus evaluator that had not seen the build; its own
base worktree of 7bede24 on port 3001, a byte-checked copy of the head in fixture mode on 3002 and as a
production build on 3003, every API request aborted and counted): H1 to H11 PASS, H12 UNVERIFIED only
because re-running the export could spend credits. Evidence it produced: the generated record equal to
`data/cases/c_f3b3d0.json` across 1,067 leaves except `case_id`; the 15 distinct cited quotes set-equal
with the table; the six PNGs byte-identical to the API's render and all 15 highlights equal to the API's
answer; every stage landing in the first poll after its recorded time; 23 "See the page" opens from
`/sample/` with 0 API calls (the one recorded disagreement, fl-04 p6, shown honestly); the day count 16
with the clock moved to Nov 20; the receipt equal to the record ($0.1118, 38 s); no remounts, every
settle also present on the unchanged fixtures; 14 of 14 control captures identical. Four defects and two
contract gaps, all fixed in the fix round above by Alvaro's go (the tab wording his choice): the export
was fail-open (15 failed checks written, exit 0); the tab clamped the band's status line at 1280 and
1440; the fixture-mode intake title named Sunshine Health; "(prices not set)" showed for the first 9 s
of every case; the recorded lookup applied to any case citing one of the 15 quotes; the 1.8 s holds were
shorter than the measured poll gap. Re-check by the same evaluator: all six PASS (tab 575 px at 1280,
status line 223 px on one line; the export refuses with exit 1 and unchanged hashes on two stubs; 0 of
71 receipt samples with the note; a non-sample case id reaches the API, `c_sample` never; every status
seen on three runs, reviewed at 39.3 to 39.5 s; 14 of 14 control captures identical; the whole-DOM grep
clean at 7 s and at reviewed). Left as recorded: the replay lands the plan at 5.2 s where the real API
emits nothing until the first question completes; the landing's fixture-mode band title is untouched
(H6; production runs live).


## 16. The sample letters door (Oct 29, 2026)

From the Oct 26 scope brainstorm (DECISIONS.md: "Live judge-submitted letter on the deployed app, with a gallery of
ten synthetic letters, one a trap"). A judge on the deployed site has no letter in hand; today the only way in is to
type one or open the recorded sample. Decided by Alvaro (Oct 29, by prompt, from three shapes): a third door on the
intake desk, not a new page and not a list on the landing; the letters' expected outcomes stay hidden, so a judge's
run is blind; desktop only until the weekend's phone pass. Made by the orchestrator within section 12 and DESIGN.md
(J1 to J10), then by the builder where marked. Files: `web/scripts/sample-letters.mjs` (new), `web/src/lib/sample-letters.ts`
(generated, committed), `web/src/components/intake/EntryForm.tsx`, `IntakeFlow.tsx`, `web/src/app/page.tsx`. Nothing in
`api/`, `policyqa/` or `cases/` changes.

- J1. The data. `web/scripts/sample-letters.mjs` (run from `web/`, like `sample-case.mjs`) reads `../cases/cases.csv`
  and keeps the ten rows with `demo` = `yes` in file order, and reads each one's `../cases/letters/<id>.txt`. It
  writes `src/lib/sample-letters.ts`: an array of `{ id, payer, program, service, reason, text }` where `program` is
  the plain label (the same map as `policyqa.investigate.PROGRAM_LABELS`: "Florida Medicaid (MMA)", "Medicare Part B",
  and so on), `reason` is the first sentence of the card's stated denial reason, and `text` is the letter file as is.
  Nothing else from the CSV reaches the module: no intended outcome, no trap flag, no hinge, no notes, no difficulty.
  The script refuses to write when a letter file is missing or shorter than 200 characters, and says "nothing
  changed" when the module is already current. A test or a grep in the builder's report proves the generated file
  contains none of the words `intended`, `trap`, `hinge`, `inconsistent`, `not_settled`.
- J2. The door. At 1024 px and up, in the desk's 420 px column under the two file doors (E3), after its own short
  label in the first label's style ("Or start from a sample"), a third secondary button in the doors' exact style
  (bond, 1 px ink border, 48 px, full width, ink text at 600): "Try a sample letter", with the hint under it in the
  doors' hint style: "Ten letters written for this demo. Pick one and read it as your own." The door is a button with
  `aria-expanded` and `aria-controls` naming the list.
- J3. The list. Pressing the door opens, under it in the same column, the list: a 14 px faded-ink label "Sample
  letters", then ten rows in CSV order, each one a button, full width, bond with a 1 px pencil-edge border, 12 px
  inset, at least 44 px tall, square corners, left-aligned: line 1 the service (16 px ink, 600) and the payer after
  it (16 px ink, 400); line 2 the program label, a middle dot, and the reason's first sentence (14 px faded ink,
  clamped to two lines with an ellipsis). No outcome, no number, no "trap". Hover and focus as the world's other
  buttons (the ink focus ring). Pressing the door again, or Escape while the list has focus, closes it.
- J4. Choosing a letter. Pressing a row puts the letter's text in the paste box (the same `text` state the textarea
  edits, through `onTextChange`), so the character count line updates and "Read this letter" enables as for pasted
  text; the list closes; focus moves to the "Read this letter" button; a polite, visually hidden status announces
  "Sample letter loaded: <service>, <payer>." The reader can edit the text afterwards; nothing else changes about
  the entry state. The door's label stays "Try a sample letter" (pressing it again reopens the list).
- J5. The landing. Beside "See a sample case" (E9), a third text action in the same style, "Try a sample letter",
  linking to `/case/new#sample-letters`; on the intake, when the page opens with that hash, the entry form shows the
  list open (read once on mount; no `useSearchParams`, no Suspense boundary). Desktop only, like the sample link.
- J6. Under 1024 px nothing changes on either page (E12): no door, no list, the landing's new link hidden like the
  sample link. Captures of the landing and the intake entry at 390 and 768 are pixel-identical to captures taken
  before the change.
- J7. The other entry controls are untouched: the paste box, the photo and file doors, the character count, the
  scope line (E4). Processing, errors, reviewing, confirming and confirmed (E5 to E8) hide the list as they hide the
  doors; returning to the entry state (Cancel, Retry, "choose again") shows the door closed with the loaded text
  kept, as pasted text is kept today.
- J8. Fixture mode behaves the same (the fixture intake accepts any text); in live mode the loaded letter runs the
  real intake as a pasted letter would. The case page and `c_sample` are untouched: full-page captures of
  `/case/c_sample` at 1280 and 390 pixel-identical before and after.
- J9. Accessibility (AA, DESIGN.md): the door and every row at least 44 px tall and keyboard reachable in reading
  order; the list is a `ul` of buttons (not links) with the label as its accessible name; the status announcement
  is polite and atomic; contrast as the world's; the hint is the door's description.
- J10. Verification the builder owes before reporting: `npx tsc --noEmit`, `npm run lint` and `npm run build` clean;
  the generated module committed with the script and a `package.json` script entry if `sample-case` has one;
  Playwright full-page captures at 390, 768, 1024 and 1280 by 800 of the landing and of the intake entry state in
  fixture mode (door closed; list open; a letter loaded, with the count line visible), one page at a time; the
  before-and-after identity captures of J6 and J8; the live path not required (no credits). A fresh evaluator grades
  J1 to J10 with the captures before the orchestrator looks.

Decided by the builder, with the reason (filled in by the builder):

- The program labels are read from `policyqa/investigate.py` itself (the `PROGRAM_LABELS` block), not
  copied into the script, so the two maps cannot drift; a program with no label refuses the write.
- The letter text is stored with LF line endings (as git stores the files). The working copy on Windows
  has CRLF (autocrlf), so "as is" byte for byte would make the module differ by checkout and put `\r`
  into the textarea's state and its character count. The comparison for "nothing changed" also ignores
  CR, so a CRLF checkout of the committed module still reads as current.
- The script also refuses a letter over 6,000 characters (the intake's other limit) and refuses to write
  a module that would contain any of the five answer-key words (case-insensitive), so J1's grep is also
  enforced at generation. `SAMPLE_LETTERS_CASES` points it at a copy of the cases folder, to prove the
  refusal without touching `cases/`. No `package.json` entry: `sample-case` has none.
- The first sentence is the text up to the first `.`, `!` or `?` followed by a space or the end; it
  is right for all ten reasons as written.
- The list's open state lives in `IntakeFlow`, not `EntryForm`, because `EntryForm` remounts on every
  return to the entry state and a mount-time hash read there would reopen the list after Cancel (J7).
  It is "the reader's choice, or else the hash the page opened with": the hash is read through
  `useSyncExternalStore` with no subscription (the repo's pattern; a setState in a mount effect fails
  lint), so the server renders it closed and the client opens it after hydration; any press of the
  door, and every submit, set the choice and the hash is no longer consulted. The landing's link opens
  it on client navigation too (checked).
- The door reuses the two file doors' class strings (`WAY`, `WAY_TITLE`, `DOOR_HINT`, `LABEL`), so its
  style is theirs by construction (measured equal at 1280: 48 px, 1 px ink, bond, 18 px at 600). Its
  group sits 32 px under the file door's hint, more than the 20 px between the two file doors, so it
  reads as a second group under its own label.
- The list's label sits 24 px under the door's hint; the label is 14 px faded ink at 400 (DESIGN.md's
  label); rows are 8 px apart. A row's hover is the phone door's: ink border and the paper ground.
- The status line is a `role="status"` paragraph (polite, atomic, `sr-only`) inside the desktop-only
  group, present before any letter loads; its message node is keyed on the load count, so choosing the
  same letter again replaces the node and is read again (fix round).

Fix round after the evaluation (Oct 29, 2026):

- Line 1 is the service, a middle dot in faded ink with the spaces line 2 uses, then the payer; each row's `aria-label` is "<service>, <payer>. <program>. <reason>", which also covers the dot.
- The list (its label and the `ul`) is always rendered and closed with the `hidden` attribute, so the door's `aria-controls` resolves in both states.
- Escape closes the open list from anywhere in the door's group, the door included, and returns focus to the door.

Fresh evaluation (Oct 29, 2026, about 1:30 pm, an Opus evaluator that had not seen the build; its own fixture build on
another port, a worktree of ca7b9dd for the before captures, byte comparison): J1 to J10, accessibility and craft all
PASS. The generator's refusals proven on a copy (a missing letter, a 145-character letter, a forbidden word in a CSV
reason); the module's ten entries checked key by key against the CSV and PROGRAM_LABELS; the door measured equal to the
file door (387 by 48, 1 px ink, 18 px at 600); contrast 8.96:1 for faded ink on bond, 5.07:1 for the row border; the
landing and the intake at 390 and 768 and c_sample at 1280 and 390 byte-identical before and after, with the landing at
1280 as the control that differs. Four low defects, fixed by the builder in one round and re-checked, all PASS: a repeat
choice of the same letter was not announced (the status node is now keyed on the load count); the row's reader name had
a stray space before the hidden comma (an aria-label "service, payer. program. reason" now); aria-controls named an
element that did not exist while closed (the list always renders, closed with hidden); Escape closed the list only from
inside it (the door's group handles it now). One craft item from the orchestrator's look, added in the same round: a
visible middle dot between the service and the payer on line 1, as line 2 has. The re-check found the dot could sit
alone at a line's end when the payer wraps (4 of 10 rows at 1024); the orchestrator made the space before the dot
non-breaking, so the dot stays with the service and the payer wraps whole (tsc and lint clean; measured at 1024 and
1280). Alvaro's decision on the open list's look (the left column empty under "Read this letter" while the ten rows run
down the right column, about 1,050 px at 1280): keep it.

## 17. The phone world (Oct 29, 2026)

From the Impeccable critique of Oct 28 (P1, issue 1): "The full world stops at 1024 px: at 390 the stamp sits at
about y 730 under a recap and jargon lines, no exhibits, no policy page. Fix: stamp first, both exhibits stacked
under it, the case card collapsed to one line." PRODUCT.md puts the stressed person on a phone first, and the
judges will open the site on whatever they hold. Measured on Oct 29 at about 9:30 pm on the local build at
816b19e, 390 by 844, c_sample at reviewed: the band 57 px; the case card (payer, case id, the deadline ring line,
service, reason, program, "Show the full case card") to about 650 px; two status lines; the "What the documents
say" sheet from 768 px with the stamp's top at 826 px, so the first screen shows the card and no verdict; no
exhibits (the pair is `hidden` under 1024), no page crop, no vision check; the rule and the gap as text with
citation chips; the page 11,413 px tall (13.5 screens). During the run: the deadline stamp in the card,
"Investigating under Florida Medicaid (MMA)…", "Question 1 of 6…", "Keep this screen open", and the latest-finding
line at 905 px, below the fold (section 14, D1). The intake at 390: three stacked doors, no sample letters door;
the landing: the h1, the paragraph, the scope line, the primary button, no sample link. Shaped with Alvaro on
Oct 29 by prompt (four answers, every recommended reading taken). Made by the orchestrator within sections 9 to 16
and DESIGN.md (K1 to K13), then by the builder where marked. Files: `VerdictSection.tsx`, `ExhibitPair.tsx`,
`CaseHeader.tsx`, `RoutingSlip.tsx`, `InvestigationView.tsx`, `PageViewer.tsx`, `EntryForm.tsx`, `IntakeFlow.tsx`,
`web/src/app/page.tsx`, `DESIGN.md`. Nothing in `api/`, `policyqa/` or `cases/`.

- K1. The range. The phone world applies under 1024 px at every width (390 is the measured phone, 768 the
  tablet): one column, the content 358 px wide at 390, sheets at the column width. Nothing changes at 1024 px and
  up: full-page captures of every fixture, the intake and the landing at 1280 by 800 and 1024 by 800 are
  byte-identical before and after (the control: the same captures at 390 differ).
- K2. The first screen after the verdict. Under the band, the top sheet (bond, 1 px ink edge, 20 px inset) holds
  in this order: the stamp as the h1 (28 px, DESIGN.md's phone size, turned and inked as on the desktop) at the
  sheet's top; the Lead line (20 px at 600: "Appeal by Dec 6, 2026" with the day count under it at 400; on the
  consistent and not-settled verdicts the next step leads and the deadline follows at 17 px, as G1); the counts
  as marks, one per line (findings verified, letter sentences verified, struck, the second opinion); then the case
  card as one line: the payer at 600, a middle dot in faded ink, the service (15 px, wrapping to two lines when
  it must), with "Show the full case card" as a text action under it. Targets at 390 by 844 on c_sample: the
  stamp's top under 160 px from the page top, the card line's top under 640 px, the first exhibit's head visible
  at the fold.
- K3. The exhibits. Under the card line, the two exhibits stacked at the column width, each a bond sheet with
  its paper clip and corner marks: Exhibit 1 "The letter says" (the denial sentence at 19 px, the source line at
  14 px faded ink), then Exhibit 2 "The policy says" (the cited sentence as live text with the red highlight, the
  page crop under it at the column width with the highlight boxes drawn, the folio in mono, the vision check line
  with its mark). The crop keeps its aspect and scales to the column; its type will be small, and that is a crop:
  the live sentence above it carries the reading. Then the rule and the gap in one column as today, the steelman
  strip (G2), and "What would change it" where it applies.
- K4. See the page on the phone. Pressing "See the page" grows the page image under the policy exhibit, inside
  the exhibit sheet, at the column width: the page at its aspect in a box no taller than 70 vh, scrollable
  inside, the highlight boxes drawn and scrolled into view, the vision line under the box; a "Close" text action
  (44 px) and Escape close it and return focus to the button; `aria-expanded` on the button; one page open at a
  time. No Zoom button under 1024 px (the browser's own pinch zooms). When the page opens or closes the window
  does not scroll and nothing above the box moves, the toggle included; the content under the box moves by the
  box's height, which a page growing in place cannot avoid (wording settled by the orchestrator on Oct 30 after
  the evaluation; the first wording said "nothing else on the page moves").
- K5. During the run (from the first poll until decided). The top sheet holds, in this order: the case card line
  (K2's line) with the deadline stamp small at its right (the DESIGN.md deadline stamp scaled to about 120 px
  wide; the card line wraps in the space left); the seven stages as a compact list of marks in two columns (four
  and three, 15 px, the running stage's note under the list as today's "Drafting the appeal letter…"); the
  latest-finding line right under the stages (G3: 17 px ink with its mark, one element changing in place, its
  24 px line held from the first poll, gone when the slip folds). Target at 390 by 844: the latest-finding line's
  bottom under 520 px from the page top at every poll. The findings sheet follows below as today.
- K6. The one movement at decided. The slip folds, the stamp presses in at the sheet's top (the press motion),
  and the card line drops to its K2 place under the marks; the deadline stamp becomes the Lead line. This is the
  outcome-first reflow the phone already makes (section 14, D4); "nothing moves at decided" stays a rule of 1024
  px and up. The stamp's press is the only motion; the rest is a reflow in one frame.
- K7. The case card disclosure. "Show the full case card" opens, in place under the card line, the reference rows
  (Member, Plan, Letter dated, Service and code, Amount) and "The letter as read"; closed by default in every
  status; `aria-expanded`; "Hide the case card" closes it. The reason the letter gives is not repeated on the top
  sheet: Exhibit 1 carries it.
- K8. Heading order (G4) holds at every width: the h1 (the payer before the verdict, the stamp after) first in
  the DOM, the h2 "Verdict" after it, the exhibits' titles and "The rule" and "The gap" under it.
- K9. The intake door on the phone (J6 reversed). A fourth door "Try a sample letter" after "Paste text", in the
  three doors' exact style (stacked, full width, 1 px ink border, the hint under the title); pressing it opens the
  list of ten rows under it (J3's rows at the column width, two-line reasons clamped); choosing a row opens the
  paste state with the letter loaded as J4 does (the text in the box, the count line updated, "Read this letter"
  focused, the polite announcement). The landing shows "See a sample case" and "Try a sample letter" at every
  width, as two text actions under the primary button in E9's style. The desktop door and landing (J2 to J5)
  are unchanged.
- K10. Accessibility (AA, DESIGN.md): every target 44 px; the stamp's text selectable and read as the h1; the
  exhibits read letter then policy; the page viewer's Close reachable by keyboard; contrast as the world's; the
  focus ring the world's 3 px ink outline.
- K11. Untouched: every section after the exhibits (the letter pages, the checklist, where to file, the record,
  the self-check, the receipt) keeps today's phone layout; the index tabs stay hidden under 1280; the c_sample
  replay's timing; the API; every desktop capture (K1).
- K12. DESIGN.md. The builder rewrites "Where the world lands" (the phone and tablet get the world's structure,
  not tokens on the old one) and the Layout paragraph for under 1024 px, from what was built, measured.
- K13. Verification the builder owes before reporting: `npx tsc --noEmit`, `npm run lint` and `npm run build`
  clean; Playwright captures at 390 by 844 and 768 by 1024 (full page and viewport), one page at a time, of
  c_sample during the replay (at 1, 8, 20 and 32 s) and at reviewed, of c_consistent, c_notsettled, c_dual,
  c_rejected, c_checkerror, c_fail and c_error at reviewed, of the page viewer open on c_sample at 390, of the
  intake entry state (door closed; list open; a letter loaded) and the landing; the measured positions of K2 and
  K5 against their targets; the byte-identity set of K1 against captures from a worktree of the base. A fresh
  evaluator grades K1 to K13 with the captures before the orchestrator looks.

Decided by the builder, with the reason (Oct 29, 2026):

- The phone's case line is its own element (`CardLine` in `CaseHeader.tsx`), a keyed child of the verdict
  section like the slip: the section's first child before the verdict, after the counts once it exists, so
  React moves the node at decided instead of remounting it (measured: the same node, the disclosure still open,
  across decided on `c_sample` and `c_consistent`). The desktop reference block (`CaseHeader`) is display: none
  under 1024 px, and the case line is display: none from 1024 px. The header could not move itself: it floats
  at the top of the desktop sheet, before the verdict section, and K1 forbids changing that.
- The payer is the case line's h1 while the case runs (an inline h1 inside the line) and plain text once the
  stamp is the h1. Each width exposes one h1; the other is display: none.
- The phone's stage list is the routing slip itself, laid out in two columns under 1024 px and folding at decided
  there (at the end of the chain from 1024 px). The phone's old status block (the route line, "Question 1 of
  6…", the stage line, "Keep this screen open") is display: none under 1024 px; the slip's live region, which
  was desktop only, now announces the chain at every width, so the phone keeps one live region. The stage's
  words sit on their own 17 px line under the list (beside the stage from 1024 px), held at 24 px from the
  first poll.
- From decided until the chain is done, one more row under the counts: an open ring and the running stage's
  words ("Drafting the appeal letter…", "Appeal letter ready." linking to the letter with a 44 px target,
  "Checking the letter against itself…", or the words of a stage that stopped). K6 folds the slip at decided,
  but the letter is still being drafted then, and the phone's old stage line was its only sign and its link.
  The row goes when the desktop slip folds, so at reviewed the case line and everything under it move up one
  row (27 px on `c_sample`); a self-check that failed is then reported only in the self-check section (the
  desktop also has the band line).
- The exhibits are inside the top sheet at its inner width (316 px at 390), not on the manila at 358 px: K2 and
  K3 put them under the card line on the sheet, and the desktop clips them to the top sheet. Their side insets
  are 20 px under 1024 px (28 from 1024), leaving the quote 274 px.
- The crop is not a control on the phone (nothing shows that an image opens something); "See the page" is a
  text action under the vision line. While the page is open the same button reads "Close" with
  `aria-expanded="true"` (the pattern of "Show the full case card" and "Hide the case card"), so K4's Close and
  the button are one control; Escape closes and focus returns to it. The page takes the crop's place inside the
  exhibit, in flow, so the folio, the vision line, the button and everything under the exhibit move down by the
  page's height. "Nothing else moves" is built as: the window does not scroll and nothing above the page moves.
  Chrome's scroll anchoring scrolled the window 381 px on open (it kept the button on screen), so the open and
  the close run with `overflow-anchor: none` on the document and the window is put back before paint (measured:
  scrollY the same before, after open, after Close and after Escape, at 390 and at 768). At 390 the whole page
  fits its box (314 by 406 px, under 70 vh = 591), so it does not scroll inside; at 768 it does (564 by 730 px
  in a 717 px box, the highlight placed 15 px down). The box shows the 220 dpi raster the crop already loaded.
- The deadline stamp on the run's case line is the DESIGN.md stamp with CSS `zoom: 0.77` (156 to 120 px), so the
  frame, the type and the grain scale together; its 14 px small lines read about 11 px there, and its image
  label carries the whole deadline for a screen reader.
- The stamp sits 8 px under the sheet's inset at 390 and 20 px from 640 px: turned from its left edge, its right
  end rises about 15 px at 390 and 26 px at 768, and at 8 px it came within 3 px of the sheet's edge at 768.
- The visible opening ("What the documents say") is display: none under 1024 px in the folder, since the stamp
  opens the sheet (K2); the hidden h2 after the h1 reads "Verdict" there (K8), and as before from 1024 px.
- The counts are one per line under 1024 px (`flex-col`); the second opinion stays the line under them.
- The intake's fourth door uses the three doors' class strings (`WAY`, `WAY_TITLE`, `WAY_HINT`): their border is
  the pencil edge, ink on hover and while its list is open, as "Paste text" does; K9's "1 px ink border" was
  read as a description of those doors, and "exact style" won. It is named by its title and described by the
  desktop door's hint, like the photo and file doors. Its list shares the desktop list's open state (one shows
  at a width), so the landing's "Try a sample letter" opens it on the phone too; it has its own polite status
  line (the desktop one is display: none under 1024 px). Choosing a row also opens the paste box (`textOpen`); at
  desktop the box is always open, so nothing changes there. The doors' list label read "Three ways to add the
  letter"; it now reads "Ways to add the letter" (four on the phone, two at desktop).
- The landing's two text actions sit in a wrapper that is a wrapping row under the button under 1024 px and
  display: contents from 1024 px, so the desktop flex row is unchanged.
- "The letter as read" in the case line's disclosure is a labelled, focusable scrolling frame capped at 50 vh
  (the intake's letter-as-read frame, 15 px), under the five reference rows.
- The byte-identity set compares two production builds: the base worktree on port 3001 and this change built in
  `web/` and served with `next start` on port 3002 (a dev render against a production render would compare two
  different builds; the dev server on 3000 served the look). The six 1280 captures of the base taken twice were
  byte-identical to each other, so the set is deterministic.

Fix round after the fresh evaluation (Oct 30, 2026; the evaluator's record is
`web/phone-evaluation-2026-10-29.md`: 13 PASS, K4 and K6 FAIL, five low notes). It replaces the bullets above
where they differ:

- K4, as the orchestrator settles it: nothing above the page box moves and the window does not scroll; the
  content under the box moves down by the box's height, which a page growing in place cannot avoid. "See the
  page" now sits between the quote and the crop, so it stays where it was pressed and the page grows under it
  (it sat under the vision line and moved down 381 px at 390 and 669 at 768, off the window there). Measured:
  the button at viewport y 250.2 (390) and 339.9 (768) before the open, while open ("Close"), after Close and
  after Escape; scrollY unchanged; the page box 314 by 408 at 390 and 564 by 717 (scrolling, 15 px down) at 768.
  The window hold (scroll anchoring off for the change) stays.
- K6: the phone's top sheet now moves once, at decided. On the inconsistent verdict, while its letter is not
  done, the counts hold the two letter lines' places as unseen spacers (display: none from 1024 px), and the
  letter's counts fill them. The letter's row is laid out from decided to the end in one line of short words of
  its own (`phoneStatusLine`): "Verdict reached.", "Drafting the appeal letter…", "Checking the letter…" and "The
  letter could not be drafted." with the open ring; "Appeal letter ready." (the link, kept through reviewed,
  also when the self-check failed; the self-check section reports that) and "No appeal letter was drafted." with
  the tick. One line at 360 px and up, truncated as a guard; the full stage line stays the live region's.
  Measured, case line and Exhibit 1 top at decided, drafted and reviewed, equal to the pixel: `c_sample` 487 and
  628 at 390, 464.2 and 583.2 at 768, 487 and 628 at 360 by 740; `c_consistent` 415.3 and 556.3 (390), 386.4 and
  505.4 (768); `c_notsettled` and `c_dual` 364.5 and 505.5 (390), 359.1 and 478.1 (768); `c_checkerror` 436.3 and
  577.3 (390), 436.8 and 555.8 (768). K2's targets still hold at 390: stamp 95.7, case line 487 (under 640),
  Exhibit 1 628 with its head in the first screen; page 11,779 px.
- "Show the full case card" moved out of the column beside the run's stamp to its own line under the case line
  and the stamp, `whitespace-nowrap`, so it is one line at 360 (it wrapped in the 152 px column). The run's
  latest-finding bottom is now 439.8 at 390 and 360, 442.1 at 768, at every poll (target under 520).
- The letter's row takes the tick for finished states (above); a tick that replaces a ring steps in.
- The slip's note under the stages is `aria-hidden`: the live region after the slip says the same words, so a
  screen reader hears them once.
- DESIGN.md records the letter's row and the one reflow at decided (Layout), with the new numbers.
- The run's deadline stamp keeps its small lines at 12 px: they are set at 15.6 px inside the 0.77 zoom; the
  frame and the date still scale.
- Verified: `npx tsc --noEmit`, `npm run lint` and `npm run build` clean. K1 against a fresh base build of
  533ce76 (production on both sides, `animations: "disabled"`): 20 of 20 desktop captures (8 fixtures, the
  intake, the landing, 1280 and 1024 by 800) byte-identical; control at 390 (`c_sample`, intake, landing) 3 of 3
  differ.

## 18. The landing proof (Oct 30, 2026)

From the Impeccable critique of Oct 28 (P2, issue 5): "The landing persuades with nothing: one sheet of text,
375 px of empty manila, the sample link hidden under 1024. Fix: the sample's stamp and exhibit pair on the
landing as proof; the link at every width." The link is at every width since section 17 (K9). The judge's
red flag in the same critique: "no proof on the landing" in the three minutes they give the site. Measured on
Oct 30 on the deployed site (8d78c32) and the session 11 captures: at 1280 by 800 the top sheet runs from y 101
to 426 and 374 px of manila sit empty under it; at 390 by 844 the one column (no sheet) ends with the two sample
links at about 593 px, with about 250 px of manila under them; the landing makes no API call. E9 of section 12
(Alvaro, Oct 28: "no second sheet, no stamp, no feature list, no screenshots") is reopened by Alvaro on Oct 30 by
prompt, both recommended readings taken: a second sheet under the top sheet, the full pair, named once. Made by
the orchestrator within sections 9 to 17 and DESIGN.md (L1 to L11), then by the builder where marked. Files:
`web/src/app/page.tsx`, a new component for the proof sheet (the builder names it, under `web/src/components/`),
and only where a piece must be extracted or given a heading level, `VerdictSection.tsx`, `ExhibitPair.tsx`,
`CaseHeader.tsx`, `DESIGN.md`. Nothing in `api/`, `policyqa/` or `cases/`; `sample-case.ts` is read, never changed.

- L1. The second sheet. Under the top sheet at every width, the sample case as decided. At 1024 px and up a
  second bond sheet in the top sheet's exact style (`TOP_SHEET`: 1 px ink border, bond, the same insets), the
  top sheet's width, set under it by the folder's rhythm between sheets (the builder measures the case page's
  gap between its top sheet and the next sheet at 1280 and uses that number). Under 1024 px the landing has no
  sheet today; the proof is one bond sheet at the column width (358 px at 390, 608 at 768) with the phone case
  page's edge and inset (1 px ink, 20 px), 40 px under the two sample links. The top sheet above it does not
  change at any width (L9).
- L2. What the sheet holds, in this order, every piece from the recorded dc-001 run (`SAMPLE_RECORD`, the
  record `c_sample` replays) and rendered by the case page's own components or pieces extracted from them, so
  the words, the marks, the paper clips and the highlight are the case page's to the pixel: the head line (L3);
  the stamp "The denial appears inconsistent with the policy." in the `.stamp` style at DESIGN.md's sizes (38 px
  at 1280 and up, 32 at 1024, 34 at 640, 28 on the phone), turned and inked, real selectable text, already
  pressed (no press motion, no `stamp-in`); the Lead line under it as the case page's Lead gives it for this
  verdict ("Appeal by Dec 6, 2026" with the day count computed from today, the same text `c_sample` shows that
  day); the counts as marks, one per line as on the phone (section 17, K2), from the sample's investigation and
  letter as the case page computes them (the findings verified, the letter sentences verified, struck, then the
  second opinion line "Second opinion: Muse Spark Open agrees." with its tick); then the exhibit pair exactly as
  the case page renders it at reviewed (`ExhibitPair` with the sample's card and its rule citation, unsupported
  false): the two columns at 1024 px and up, stacked under 1024 px (K3). Nothing else from the case page: no case
  line, no reference block, no rule and gap, no steelman strip, no letter, no checklist, no receipt.
- L3. The head line. One line at the sheet's top, before the stamp, that names what this is: the words
  "The sample case, decided." at 600 in ink, then in faded ink on the same line (wrapping under it under
  1024 px, so at 768 as on the phone) "A sample letter, run for real on Oct 28, 2026." Draft wording; Alvaro's look settles it. This is the
  only naming on the sheet: Exhibit 1's source line already reads "Sample Health Plan, letter dated October 7,
  2026", and the band is the landing's band as today. No "synthetic", no "fixture" anywhere on the landing.
- L4. See the page. The policy exhibit keeps its "See the page" action and it works as on `c_sample`: the page
  opens in place (the desktop viewer at 1024 px and up, the phone's in-exhibit box under 1024 px, K4) with the
  recorded highlight and the recorded vision line, from `SAMPLE_PAGES`, with zero API calls at load and zero on
  open (section 15: the sample's pages and vision checks are recorded; the builder proves it with a network log).
  Close and Escape as on the case page. If the viewer cannot open on the landing without an API call, the
  action is left out of the landing's exhibit and the builder says why.
- L5. Links. No new link. The top sheet's "Start with your letter", "See a sample case" and "Try a sample
  letter" stay word for word where E9 and K9 put them. The proof sheet is proof, not a door: nothing on it
  navigates except the citation chips and "See the page" that the exhibit already carries, and those behave as
  on the case page.
- L6. Heading order and reading. The landing's h1 is the headline on the top sheet, as today. The stamp is an
  h2, never an h1 (the case page's `VerdictSection` renders its stamp as the page's h1; the landing needs the
  stamp with the same look at h2, by a heading-level prop or an extracted stamp piece; the case page's output
  does not change, L9). The head line is a paragraph, not a heading. Then the exhibits as the case page gives
  them (figures, their titles as paragraphs). The outline at every width: h1, h2. The marks read as the case
  page's ("6 of 6 findings verified", with the tick's reader word). Every target 44 px; contrast as the
  world's; the focus ring the world's 3 px ink outline.
- L7. Motion. None on the landing: the sheet is there at load, the stamp already pressed, nothing lands.
- L8. Positions, measured at the four widths on a production build. At 1280 by 800: the proof sheet's top
  edge inside the first viewport (under 800 px from the page top; expected about 458) and the stamp wholly
  visible in it (its bottom under 800). At 1024 by 800 the same two targets. At 390 by 844: the sheet's top
  edge under 700 and the stamp's top under 760, so the first screen ends on the proof's head and the stamp's
  top. The page height at each width recorded in DESIGN.md (L10).
- L9. Untouched, the control set. Every case fixture page (`c_sample` at reviewed, `c_consistent`,
  `c_notsettled`, `c_dual`, `c_rejected`, `c_checkerror`, `c_fail`, `c_error`) and the intake (the entry state,
  the sample list open, a letter loaded) byte-identical before and after at 1280 by 800, 1024 by 800, 768 by
  1024 and 390 by 844: two production builds, the base a worktree of `e5b91b8`, captured full page with
  `animations: "disabled"`, one page at a time (section 17's method). The control that proves the set can
  fail: the landing differs at all four widths. The landing's top sheet is unchanged: every element rect inside
  `[data-top-sheet="landing"]` equal before and after at the four widths. `c_sample`'s replay and its timing are
  untouched. The landing still makes no network request at load beyond its own assets.
- L10. DESIGN.md. The builder rewrites the landing's part of "The folder frame at desktop, one column under
  it" from what was built, measured: the second sheet, its gap, the page heights at the four widths.
- L11. Verification the builder owes before reporting: `npx tsc --noEmit`, `npm run lint` and `npm run build`
  clean; Playwright captures of the landing at 1280 by 800, 1024 by 800, 768 by 1024 and 390 by 844, full page
  and viewport, and of "See the page" open at 1280 and 390; the L8 numbers; the L9 byte-identity set with its
  control; a network log of the landing at load and after "See the page"; the aria heading outline at 1280 and
  390 (L6). A fresh evaluator grades L1 to L11 with the captures before the orchestrator looks.

Decided by Alvaro (Oct 30, by prompt, both recommended readings): the proof as a second sheet under the top
sheet, filling the desktop's empty manila and stacked under the links on the phone, rather than inside the top
sheet's empty right third or a stamp alone; the full pair with the crop and the vision line, named once by one
head line, with no second link to the sample case. His look at the build (Oct 30, afternoon: the builder's captures at 1280
and 390 and the viewer open at 1280): passes as built; the head line's wording kept as built (L3 settled).

After the fresh evaluation (Oct 30, 2:25 pm; the record is `web/landing-evaluation-2026-10-30.md`: 14 PASS, 0 FAIL,
five low notes), settled by the orchestrator: the desktop viewer opened from the landing shows "Loading page" and
"Checking the highlight with vision…" for about 2.9 s before the recorded vision line, with no request, exactly as
`c_sample` does (section 15's recorded holds); accepted as the sample's behaviour. Without JavaScript the Lead stays
hidden and leaves a 67 px gap at desktop (47.5 on the phone); accepted, the case page itself needs JavaScript. The
empty bond to the right of the stamp, the Lead and the counts at desktop (about 480 px, y 539 to 921 at 1280) is
the case page's own top-sheet shape and Alvaro's look passed it. Two stale lines fixed in DESIGN.md (the stamp as
the case page's h1, pressed on arrival there and already pressed on the landing) and L3's wrap note corrected to
under 1024 px.

Decided by the builder, with the reason (Oct 30, 2026; the build measured on a production build against a
worktree of e5b91b8; scripts and captures under `C:\Users\pau\AppData\Local\Temp\claude\landing-build\`):

- The sheet is `web/src/components/landing/ProofSheet.tsx`, reading `SAMPLE_RECORD` and `SAMPLE_PAGES` and
  rendering the head line, the stamp, the Lead, the counts, the second opinion and `ExhibitPair`, wrapped in
  the case page's `PageViewerProvider` with `caseId="c_sample"` and its `PageViewerFrame`, so "See the page"
  answers from the recording at every width (the side viewer from 1024 px, the in-exhibit box under it, K4).
- Three pieces extracted from `VerdictSection.tsx` and exported, the case page calling them with its old class
  strings: `VerdictStamp` (heading level 1 or 2; `pressed` adds the press motion), `ProofCounts`,
  `SecondOpinionMark`.
- `ExhibitPair` takes an optional `settled` prop: the policy exhibit starts finished (the crop drawn, the
  vision check done, no request), the values mapped from `SAMPLE_PAGES` as `getHighlight` and `visionCheck`
  map them. The case page never passes it; without a recorded check the exhibit falls back to asking.
  Reason: the normal path shows "Loading page" for 450 ms and then "Checking…", and the arriving crop grows
  the sheet, which L7 forbids on the landing.
- The desktop gap under the top sheet is 80 px, the case page's measured gap between its top sheet and the
  next block at 1280 (101 to 1116, then 1196); 96 px is the gap between later sheets. The sheet's top is at
  506 at 1280 and 1024 (the brief expected about 458 from a 32 px guess), the stamp's bottom 105 px above the
  1024 fold.
- Under 1024 px the sheet starts 40 px under the sample links: 656 at 390 (links end at 616), 531 at 768.
- The stamp keeps the case page's maximum widths from 1024 px, so it breaks into the same two lines (526 px
  wide at 1280); its margin under the head line is 28 px on the phone and 36 px from 640 (the turned right
  end rises 15 to 26 px; measured clearance 13.7 px at 390, 10.4 at 768, 12.2 at 1280).
- The Lead is `PhoneLead` (20 px) under 1024 px and `DeadlineLine` at the lead size (30 px) from 1024, the
  case page's sizes at each width, with the same `daysUntil` count. Today is read on the client: the landing
  is prerendered, so before hydration the Lead is laid out with the recorded day and kept invisible, then
  shown with today's count in place (no reflow, no hydration mismatch).
- The head line's faded part is 15 px under 1024 px (at 17 px it wrapped and put the stamp's top at 760.8,
  0.8 px past L8's target); the date in it comes from the record's `created_at`.
- The counts are one per line at every width at the case page's sizes (17 px under 1024, 15 px from 1024).
- The sheet is an unnamed `<section>`, so no extra landmark is announced.
- Measured: L2 equal to `c_sample` at reviewed on the same build (the stamp 526 by 113 at 1280 and 316 by 113
  at 390, the Lead "Appeal by Dec 6, 2026 / 37 days left", the counts, the second opinion line, the pair's box
  1006 by 366.9 and 316 by 841.2, the pair's HTML equal once SSR markers are stripped); L8 at 1280: sheet 506,
  stamp 574.5 to 711.1, page 1,401; at 1024: 506, 575.8 to 694.6, 1,379; at 768: 531, 606.4 to 733.8, 1,692;
  at 390: 656, 734.7 to 862.2, 2,045; L9 44 of 44 byte-identical (8 fixtures and the intake's three states at
  four widths) with the landing differing at 4 of 4 and the top sheet's 9 element rects equal; the landing
  loads with 19 GET requests to its own origin and "See the page" adds none; the outline h1 then h2 only;
  zero animations in the sheet at load; tsc, lint and build clean.
- One target missed, settled by the orchestrator: the desktop crop button (the policy exhibit's crop as a
  control from 1024 px) is 481 by 41.5 px at 1280 and 417 by 36 at 1024, the same as on the case page, where it
  has been since section 11. It is the base's control, as section 17's evaluator treated the citation chips
  and checkboxes; a fix belongs to both pages at once (bug bash, after the video), not to the landing alone,
  since the landing may neither change the case page (L9) nor differ from it (L2).

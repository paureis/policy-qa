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

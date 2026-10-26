# Design critique: Recourse case page (and intake), Oct 26, 2026

Reviewer stance: product designer, design-critique framework (first impression, usability, hierarchy, consistency, accessibility), then a second pass against `PRODUCT.md`, the three briefs in `web/`, and `web/src/app/globals.css`. Stage: functional build, pre-polish, with a hackathon demo due Nov 4. No repo files were edited.

Inputs read (all present, none missing):

- Intake: `shots/01-entry-1280.png`, `04-reviewing-flagged-1280.png`, `06-confirmed-390.png` (career-sprint scratchpad)
- Case with findings, live: `e2e2/live-investigated-390.png`
- Finished case: `shots4/c_sample1-drafted-1280.png` (1280 x 7475), `c_sample1-letter-1280.png`, `c_dual1-1280.png` (1280 x 5248), `c_consistent1-1280.png` (1280 x 5142)
- Live chain, phone: `e2e3/chain-drafted-390.png` (390 x 8529)

Measured positions on `c_sample1-drafted-1280.png` (viewport assumed 1280 x 800):

| Element | Top (px) | Share of page | Viewports down |
|---|---|---|---|
| Postmark and case card | 100 | 1% | 0 |
| Verdict headline | about 2,990 | 40% | 3.7 |
| Appeal letter heading | about 4,030 | 54% | 5.0 |
| Deadline section (second postmark) | about 6,200 | 83% | 7.7 |
| Trust panel | about 6,890 | 92% | 8.6 |

Content column: x = 336 to 944 (608 px) on a 1280 canvas. 52% of the width is empty on every screen except intake reviewing and the dual findings.

---

## Overall impression

The world is right and the restraint is real: bond white, one blue band, ink, hairlines, a single postmark, no gradients, no purple, no emoji, no shadows. The problem is not taste, it is structure. The finished case is a log printed in the order the agent worked (card, findings, verdict, letter, checklist, deadline, trust), so the answer sits four screens down, the deliverable five, and the proof eight and a half. Every section wears the same 4 px ink rule, the same uppercase overline, the same 22 px heading, and the same boxed chips, so nothing tells the eye which part is the outcome. That is what reads as "bland" and "one straight line": a uniform rhythm, not a missing color.

---

## 1. Hierarchy (finished case, 1280)

What the eye lands on, in order, in the first viewport:

1. The blue band (full-bleed, the only saturated area).
2. The postmark (the only graphic, top right).
3. "Sunshine Health" and the case card rows.
4. "5 questions investigated. Appeal letter ready." (bold 20 px, reads as a status, not a destination; no link to the letter).

What it should be, for both audiences:

1. The verdict headline ("The denial appears inconsistent with the policy.") with the day count beside it.
2. The appeal letter (the deliverable) and how to send it.
3. The proof: "3 of 4 findings verified", "3 of 4 letter sentences verified; 1 struck", then the findings as the reasoning behind it.

The verdict is already the biggest type on the page (38 px, stamp blue) and is correct in isolation. It loses because it is placed after 2,800 px of findings that are all set at a heading weight close to it. A judge scrolling a demo will see five near-identical finding blocks before the answer. A stressed caregiver on a phone (verdict at about 45% of 8,529 px) has it worse. `PRODUCT.md` principle 3 says the deadline and where to file are "never buried"; today the filing path is at 83%.

Verdict: the order is the agent's order, not the reader's. While the case runs, chronological is right (it is the show). Once `drafted`, the page should read outcome first.

## 2. Information architecture

The page mixes three kinds of content that want different homes:

| Kind | Content | Home it wants |
|---|---|---|
| Persistent facts (stay in view) | Payer, service, the letter's reason, program, deadline with day count, verdict in one line, verification coverage | A rail or a sticky summary strip |
| Reading flow (read top to bottom once) | Verdict with the rule, the gap, what would change it, steelman; the appeal letter; the evidence checklist; where and how to file | The main column, in that order |
| Receipt (consulted, not read) | Findings in full with struck citations, per-finding cost and time, totals, model, trace | An appendix section and a receipt block |

Today all three are one column. The case card's ten rows and the trust panel's five rows use the same label/value grid (`sm:grid-cols-[200px_1fr]`), so facts, outcome and receipt look like the same kind of thing.

Desktop already has a precedent that the case page abandons: intake reviewing at 1280 puts the letter (400 px) beside the card, and the investigation brief reserves a sticky right-hand page viewer at 1024 px and up. So desktop is half-designed: two of the four screens get a layout, the most important one does not. Any direction below must leave room for that page viewer.

Small IA bug: the band is 1120 px wide (`Band.tsx`) and the main column is 640 px, so the RECOURSE wordmark sits at x = 96 and the content at x = 336. On a single case the header and page do not share an edge.

## 3. The case-file metaphor

The brief's world ("The Notice, Answered": the notice register, bond, a blue band, a postmark) is carried well at intake and then thins out:

- Intake reviewing: strong. Gold highlighter rows with "Check", the letter beside the card, the postmark landing. This is the best screen.
- Case page: the postmark appears twice (case header and deadline section) with different ring text ("CASE OPENED" in one, "RECOURSE" in the other). The second stamp dilutes the "one expressive element" rule.
- The appeal letter is the one place the metaphor should peak (a letter on bond, To and Re, a signature block) and it is a hairline box on a white page. White on white: the sheet does not read as a sheet.
- Nothing else on the page says "case file": no case number treatment, no register lines, no sense of a dossier with a cover, an outcome, and an appendix.

The world was defined as a document world, and documents have structure (a cover, a heading block, a body, an enclosure list, a receipt). The case page uses the palette of that world but not its structure.

## 4. Density and rhythm

Walls of same-weight sections:

- Findings: five blocks, each overline (14 px caps) + question (20 px bold) + answer (17 px) + one to two full-width chip boxes + optional "1 citation was struck" quote + a muted cost line. Identical rhythm five times, about 2,300 px.
- Section breaks: Verdict, Action, Evidence checklist, Deadline and filing path, Trust each start with the same 4 px ink rule, overline, and 22 px heading. Five equal "chapters" where one is the answer and one is a receipt.
- Repeated muted line "0.8 seconds, $0.0000 · Passages shown to the model: 5" under every finding: five times the same noise, in fixture mode the same numbers.
- Repeated full document titles: "Florida Medicaid Private Duty Nursing and Family Home Health Aide Services Coverage Policy (Rule 59G-4.261)" appears about ten times at 16 px semibold. The deadline section cites the same "page 41" twice.
- Route line restates itself: "Investigating under Florida Medicaid (MMA). The letter is about Florida Medicaid (MMA), so the Florida Medicaid rules decide this case."

Whitespace is generous but evenly distributed, so it does not group anything. Vary it: tight inside a finding, wide between outcome and appendix.

## 5. Citation chips: evidence or buttons?

They read as buttons, and worse, as form fields. A full-width rectangle with a 1 px ink border, `rounded-sm`, a leading "+", and bold text is the same visual vocabulary as the intake inputs and the "Show the trace" and "Download as text" buttons. Three consequences:

- Evidence looks like UI chrome, so the "verified citation" (the product's core claim) has no visual authority.
- The expanded quote (federal-blue left rule, caption in muted gray) is the actual evidence and it looks right; the chip that opens it does not.
- In the letter, inline chips are truncated ("SMMC Model Health Plan Contract, E... , page 41", with a stray space before the comma) and sit mid-sentence at 14 px in a box, which breaks the letter's reading line.

Make the chip look like a reference, not a control: short document name plus a page folio ("Rule 59G-4.261 · p. 5"), set like a legal cite (no box, a hairline underline or a paper-tint background, tabular page number), with the 44 px hit area kept by padding, and a verified mark that is a word, not a color. Dedupe identical (document, page) pairs within a section.

## 6. Trust panel: proof or footer?

Footer. It sits at 92% of the page, uses the same label/value rows as the case card, and leads with a 17 px bold line. "Cost of this case $0.0000" and "Model fixture" (monospace) get the same weight as "3 of 4 findings verified", which is the number that makes Recourse different from a retrieval demo (`PRODUCT.md` positioning).

Make it a receipt: paper ground, ruled lines, tabular numerals, the two verification lines set large ("3 of 4" at the verdict's scale, never a percentage), cost and time as the smaller itemized lines with the total at the foot, "Show the trace" as the receipt's back. And surface the two verification counts again next to the verdict, so the proof is read with the claim.

## 7. Motion within "nothing fades"

Already defined in `globals.css`: `stamp-in` (verdict, 150 ms, scale 1.04 from a -2 deg tilt), `land` (6 px up, 120 ms), `tick-step`, `step-in`, highlight boxes drawing at 150 ms; all disabled under reduced motion. Good, and correctly transform-only.

Opportunities, all transform or stepped, no opacity:

- The strike: when the verifier rejects a finding, draw the strikethrough left to right (a `scaleX` line over the text, 150 ms) instead of appearing pre-struck. It shows the verifier acting; it is the best single moment for the demo video.
- The postmark lands once, at the moment the case opens, then never moves again; on the finished page it should not re-animate on each load from cache.
- Stage index ticks (if a rail or stage header is adopted): each stage steps from open ring to filled, `steps(2)`.
- Letter sentences land one by one as they are drafted (6 px up), each chip appearing with its verified mark after.
- Avoid: counters spinning up to "3 of 4" (reads as a dashboard trick), skeleton shimmer (a fade by another name), scroll-linked parallax.

## 8. Typography

Public Sans only, plus the system mono for the case id and the model name. The family is right for a federal-notice world.

The scale is compressed. Sizes in use: 13, 14, 15, 16, 17, 18, 20, 22, 32/38 px. Eight steps between 13 and 22, then a jump to 38. The 20 px bold finding question and the 22 px section heading are too close, so a finding looks like a chapter. Suggested scale at desktop: 14 (overline, captions), 17 (body), 20 (h3), 28 (h2), 44 to 48 (verdict). Use weight 700 only for the verdict and h2, 600 for h3.

Other notes:

- Uppercase tracked overlines on every block ("COVERAGE", "LIMITS", "VERDICT", "ACTION", "TRUST", "EVIDENCE CHECKLIST", "DEADLINE AND FILING PATH") flatten everything to the same register. Keep them on the five or six top-level sections; drop them on findings (put the topic in the question's lead or a small inline tag).
- Measure: 608 px at 17 px is about 70 characters, fine. The letter body at about 550 px with a line height near 1.9 looks airy and un-letter-like; a letter at 1.55 to 1.6 reads as a letter.
- Desktop body drops to 17 px from 18 px on the phone. For an older, low-vision audience (`PRODUCT.md`, Accessibility) keep 18 px at desktop in the letter at least.
- Numbers: switch on `font-variant-numeric: tabular-nums` for the day count, the trust rows, and page numbers.

## 9. Color

One blue band, stamp blue for the inconsistent verdict, federal blue for the primary button and the quote rule, gold only on fields to check. The discipline holds. Contrast tokens are sound (`--muted` #565c65 on white is about 6.9:1; `--stamp` #1a4480 about 10:1; `--edge` chosen for 1.4.11).

Under-used: paper versus bond. `--paper` (#f7f8f9) appears only behind the intake letter panel and an open chip. The page is white end to end, so there is no figure and ground. Invert it on the case page: paper as the desk, bond white for the documents that sit on it (the case card, the letter, the receipt). That one move gives the page objects without adding a color, a shadow or a rounded card.

Also: the three verdict colors (stamp blue, ink, muted ink) are right; the muted "not settled" headline in `c_dual1` is gray at 38 px and can read as disabled. Keep it ink with a different mark (an open ring rather than a filled bar) so abstention reads as an outcome, as the brief requires.

## 10. Accessibility regressions to avoid in any redesign

- DOM order must match visual order. If the verdict moves above the findings visually, move it in the DOM too; do not use `order` or grid placement to reorder.
- Sticky rails: unstick under a short viewport (`@media (max-height: 700px)`) and at 200% zoom; a sticky column taller than the viewport traps content. WCAG 1.4.10 reflow at 320 CSS px must hold with no horizontal scroll.
- Margin notes (direction B) must sit in the DOM immediately after their sentence and stay buttons with `aria-expanded`; keyboard order must not jump between columns.
- Keep "Could not verify" and the abstention sentence as text. Strikethrough alone is not announced by most screen readers.
- Keep 44 px targets on inline chips (today done with a `::before` hit area; keep it if the box goes away).
- Focus ring is federal blue; on the federal band it is invisible. The wordmark overrides to white; check every band control ("New case", "Start over") does too.
- The page viewer is a non-modal dialog; in a three-column layout make sure Escape and focus return still work when it overlays the rail or the margin.
- Do not introduce color-only verdict states, a dark mode that flips the bond, or gold as text (gold #ffbe2e on white fails contrast).

## 11. AI slop check

Absent (good): gradients, purple, emoji, glassmorphism, drop shadows, big rounded cards, illustration, hero blobs, lorem-like marketing copy, confidence percentages, sparkle icons.

Present or at risk:

- Intake entry at 1280: three identical bordered option cards stacked in a 608 px column over an empty page. This is the most template-looking screen in the product. Three equal choices are right per the brief, but they need a real composition at desktop (three across, or a paste box as the main surface with photo and file as secondary).
- Side-stripe accents used four ways: the 6 px verdict bar, the 4 px federal quote rule, the gold field bar, the struck-quote gray bar. A left border on everything is a recognized generated-UI tell. Keep it on quotes (where it is a typographic convention) and drop it from the verdict.
- Uppercase overline on every block (see Typography). Eyebrow-everywhere is a template pattern.
- Uniform outlined boxes for chips, tags ("COULD NOT VERIFY"), the "SAMPLE CASE" tag, and buttons. Four meanings, one shape.
- Copy with a performed tone: "That is recorded, not guessed." and "Before deciding, the agent argued the payer's side as strongly as the documents allow." are fine once; repeated per finding they start to sound like a model narrating itself. "Passages shown to the model: 5" is engineering jargon on a patient-facing page; move it to the trace.
- Screenshot hygiene: the Next.js dev indicator ("N" bubble) overlaps content in four captures, and "Copied." is visible in the 1280 letter capture. A judge will notice both in a video. Disable `devIndicators` for capture builds and reset state before screenshots.

## 12. What works (keep)

- The three verdict headlines, verbatim, with color only as reinforcement.
- Struck findings stay visible with the verifier's reason; abstention has its own sentence and is not styled as an error.
- The postmark: a real idea, legible, on-world, and the day count is the most useful number on the page.
- Gold "Check" rows at intake with a gated Confirm and a count ("4 details still to check"): clear and honest.
- Intake reviewing's two-column desktop layout. It is the template the case page should follow.
- Copy is plain and short across the product; "What would change it" is excellent.

---

## Usability findings (severity)

| Finding | Severity | Recommendation |
|---|---|---|
| Verdict at 40% and letter at 54% of the finished page; filing at 83% | Critical | Outcome first once `drafted`; findings become an appendix |
| Citation chips look like buttons and inputs | Moderate | Reference styling, short names, dedupe |
| Trust panel reads as a footer | Moderate | Receipt treatment; verification counts beside the verdict |
| Two postmarks with different ring text | Moderate | One stamp; deadline section refers to it |
| "COULD NOT VERIFY" tag shares the outlined-box shape with buttons and the SAMPLE CASE tag | Moderate | Filled ink tag or plain bold text, not an outline |
| Status "Appeal letter ready." is not a link | Minor | Make it jump to the letter |
| Band and content edges misaligned at 1280 | Minor | Match the band width to the layout |
| Dev indicator and leftover "Copied." in captures | Minor | Capture hygiene |

---

## Three layout directions for the finished case at desktop

### A. The case file (left rail)

1. Name: Case File.
2. Idea: the case is a folder; the rail is its cover sheet and stays in view, the main column is the file's contents in reading order.
3. Grid at 1280: 32 px margin, rail 300 px (sticky, top 24 px, unsticks under 720 px height), 48 px gap, main 640 px, remaining right gutter free for the page viewer as an overlay sheet.
4. Rail, top to bottom: payer and case number, service and the letter's reason, the postmark (the only one), the verdict in one line once reached, "3 of 4 findings verified", then the seven-step index (Intake, Routing, Investigation, Steelman, Verdict, Action, Trust) as anchor links with stepped ticks.
5. Main: verdict with the rule, gap, change, steelman; then the appeal letter; then evidence checklist; then where and how to file.
6. Findings: an appendix section, "The investigation", after Action, compact by default (question and one-line answer, expand for citations).
7. Trust: a receipt block at the foot of the main column; the rail carries its headline count.
8. Page viewer: slides over the right gutter and part of the main column as a sheet, rail stays visible.
9. Phone: rail becomes the existing top case header plus a slim sticky footer bar ("48 days left · Read the letter"); the index becomes a jump menu.
10. Risk: duplication between rail and body, a tall rail at 800 px height, and the rail competes with the page viewer for the eye at 1280.

### B. The letter beside its evidence (reading view)

1. Name: Annotated Letter.
2. Idea: "the quoted rule is the product", so every letter sentence sits beside the quote that proves it, like a brief with margin citations.
3. Grid at 1280: paper ground; a 1,120 px frame with main 620 px (the letter on a bond sheet) and a 420 px margin column; each letter paragraph is its own grid row, so notes align to their paragraph without measuring JS. Nothing sticky except the margin's open page image.
4. Verdict: full width above the sheet as the notice's heading block, headline at 44 to 48 px, with the two verification counts and the day count on one line under it.
5. Letter: the bond sheet with To, Re, body, signature lines; struck sentences stay in place, struck, with "Could not verify".
6. Findings: below the letter, "How the case was investigated", two columns at desktop (findings left, struck citations and reasons right).
7. Stamp: once, at the top right corner of the letter sheet, as if postmarked on the envelope; the deadline line sits under it.
8. Trust: a receipt strip directly under the verdict heading ("3 of 4 letter sentences verified · 1 struck · 8.9 s · $0.0000") and the full receipt at the foot.
9. Phone: margin notes collapse to the current inline chips under each sentence; layout is the current column with the verdict summary moved up.
10. Risk: the consistent and not-settled cases have no letter, so they need a sibling layout (explanation beside the rule quotes); the margin column and the page viewer must share one space.

### C. The board of stages

1. Name: Stage Board.
2. Idea: show the case working itself; the seven stages are columns that fill left to right, so the agent's reasoning is visible as a structure, not a scroll.
3. Grid at 1280: a stage header row across the full 1,200 px (seven labeled steps with stepped ticks), then three working columns at 1fr / 1.2fr / 1.4fr: Investigation, Verdict (with Steelman), Action. Header is sticky.
4. Investigation column: findings as compact index entries (topic, one-line answer, a word mark: verified, struck, not settled); opening one expands it in place.
5. Verdict column: the headline at the top, the rule, gap, change, steelman, each quote one tap away.
6. Action column: the letter as a bond sheet preview with Copy and Download, then checklist, then filing; the stamp lands at the head of this column.
7. Trust: a ledger row across the foot of all three columns with the totals, like a column sum.
8. Page viewer: replaces the Investigation column while open, so the reader sees the page beside the verdict.
9. Phone: the board becomes a stepped list with the current or final stage open and the others as one-line summaries.
10. Risk: kanban reads as project-management software (off-world and close to template); the letter, the actual deliverable, is squeezed into a third of the width; reading order for screen readers is ambiguous.

---

## Recommendation

Build B, the annotated letter, for the finished case: it turns the product's one claim (every sentence carries a verified citation) into the layout itself, it is the screen a design-literate judge will remember, and it reuses the intake reviewing pattern of a document beside its source. Take from A only the outcome summary (verdict, day count, verification counts) as a full-width heading block at the top, and from C only the stage header during the live run, where chronological order is the show. Leave the phone as the single column with the outcome moved up, since phone first is binding and the column already works there.

## Five smallest changes for tonight (no redesign)

1. Outcome first once the case is `decided` or `drafted`: render Verdict and Action before Findings in `InvestigationView.tsx` (DOM order, not CSS order), and title the findings block "How the case was investigated". Make "Appeal letter ready." a link to the letter.
2. One postmark: drop the stamp from the deadline section (keep the date and day count as text with its citation) and make the ring text identical everywhere.
3. Chips as references: remove the full-width border box, show a short document name plus "p. 5" with tabular numerals and a paper-tint background, keep the 44 px hit area, and dedupe identical (document, page) pairs in a section.
4. Trust as a receipt: paper background, "3 of 4 findings verified" and "3 of 4 letter sentences verified; 1 struck" set at 28 px, cost and time as smaller itemized lines; delete the per-finding "0.8 seconds, $0.0000 · Passages shown to the model: 5" lines (they are in the trace).
5. Stop the box sameness: "Could not verify" as a filled ink tag (white text on ink) so it no longer looks like a button; drop overlines from individual findings; and align the band to the content width so the wordmark and the page share an edge. Plus capture hygiene: `devIndicators: false` and a clean state before screenshots.

---
name: Recourse
description: A coverage denial becomes a case, and the page is the open folder with the documents clipped inside it.
colors:
  stamp-red: "#b3261e"
  fill-in-gold: "#ffbe2e"
  fill-in-wash: "#fff5d6"
  folder-manila: "#e6d3a3"
  folder-kraft: "#d3bb82"
  tab-kraft-pale: "#efe4c6"
  tab-kraft-deep: "#c9ad74"
  bond: "#ffffff"
  ink: "#1b1b1b"
  faded-ink: "#4e493d"
  pencil-edge: "#766e58"
  hairline: "#cebd93"
  reference-paper: "#f8f2e3"
typography:
  stamp:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "38px"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "0.01em"
    fontVariation: "\"wdth\" 62"
  lead:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.25
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.25
  exhibit-title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
  body-phone:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.5
  letter:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, Liberation Mono, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
  wordmark:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontVariation: "\"wdth\" 88"
rounded:
  none: "0px"
spacing:
  tab-gap: "4px"
  page-gap: "24px"
  exhibit-inset: "28px"
  sheet-inset: "40px"
  column-gap: "40px"
  margin-gutter: "48px"
  letter-margin: "72px"
  section-gap: "80px"
  sheet-gap: "96px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bond}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "48px"
  button-secondary:
    backgroundColor: "{colors.bond}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "48px"
  sheet:
    backgroundColor: "{colors.bond}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "32px 40px 40px"
  exhibit:
    backgroundColor: "{colors.bond}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "24px 28px 20px"
  verdict-stamp:
    textColor: "{colors.stamp-red}"
    typography: "{typography.stamp}"
    rounded: "{rounded.none}"
  index-tab:
    backgroundColor: "{colors.tab-kraft-pale}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    width: "46px"
  index-tab-hover:
    backgroundColor: "{colors.folder-kraft}"
  index-tab-current:
    backgroundColor: "{colors.tab-kraft-deep}"
    textColor: "{colors.ink}"
    width: "54px"
  band:
    backgroundColor: "{colors.folder-kraft}"
    textColor: "{colors.ink}"
    height: "64px"
  folder-tab:
    backgroundColor: "{colors.folder-manila}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    padding: "0 24px"
    height: "42px"
  fill-in-field:
    backgroundColor: "{colors.fill-in-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
---

# Design System: Recourse

## Overview

**Creative North Star: "The Case File"**

A denial becomes a case, and the page is the open folder with the documents clipped inside it. Manila is the folder itself, the ground of every page. Kraft tones of the same hue are the folder's back edge (the band at the top) and its index tabs. Every document the reader handles is a bond white sheet with a 1 px ink edge and square corners: the top sheet with the verdict, the two exhibits, the pages of the appeal letter, the section sheets, the receipt. Ink carries all text. One red is the rubber stamp and the highlight, nothing else. The world refuses the category's two arrangements: the white portal with rounded cards and a blue button, and the government-notice replica the product wore before Oct 27, 2026.

Depth is paper on paper: a sheet sits on the folder because it is whiter and edged, never because it casts a shadow. State is a drawn mark, never a hue: a tick for verified, a strike for struck, an open ring for not settled. The words beside the mark carry the meaning. The stamp is the one moment of texture: condensed caps, turned -2.6 degrees, inked unevenly by an SVG noise filter, still real selectable text. The density is a working file, not a brochure: reference rows in tabular numerals, folios in mono, exhibits titled and captioned like plates.

The contract's seed reference line, as the FORM line gives it: "The Case File, candidate 6 of 7 on the grounded list; assigned by the roll. seed:de806ea490aaaeca."

Where the world lands, as built on Oct 29, 2026 (case-page brief section 17, the phone world):

- **Full world:** the finished case page at 1280 by 760 px and up (the `tabs` size). The top sheet, the exhibit pair with paper clips, the US Letter pages, each later section on its own bond sheet with its title as the sheet's head, the receipt as a dashed-top slip, and the six index tabs down the folder's right edge.
- **Most of the world:** the case page from 1024 to 1279 px, or shorter than 760 px. Sheets, exhibits, and letter pages stand; the index tabs are hidden and each section opens with its number and a 4 px ink rule instead.
- **The world's structure in one column:** the case page on the phone and the tablet (under 1024 px, measured at 390 and 768). The folder's top sheet is there from the first poll, a bond sheet at the column width with its 1 px ink edge: the case as one line and the routing slip while the case runs, then, from the one reflow at decided, the stamp as the h1, the Lead line, the counts as marks, the letter's row, the case line, and the two exhibits stacked with their paper clips and corner marks, the policy page crop under the cited sentence. The rule, the gap and the payer's side close the sheet. The sections after it (the letter, what to send and where to file, the record, the self-check, the receipt) keep round 3's one column: each a bond sheet with a 1 px ink edge and a 16 px inset (24 px from 640), no index tabs.
- **The folder frame at desktop, one column under it:** the landing page and the intake (`/`, `/case/new`). From 1024 px the band, the manila ground and one bond top sheet (section 12; on the intake the paste box with the file door and the sample door beside it, and no photo door, since a desktop has no phone camera to offer); under 1024 px one column on the manila under the band, the intake's four doors as bond panels with a pencil-edge border ("Try a sample letter" the fourth, its ten letters opening under it), the landing's two sample text actions under its button. The landing has a second sheet under its top sheet at every width, the proof (section 18): the public sample as its recorded run ends, drawn by the case page's own pieces from the same record. In order: the head line ("The sample case, decided." at 600, then the run's date in faded ink), the verdict stamp as an h2 already pressed (the case page's sizes and line breaks, no press motion), the Lead line ("Appeal by Dec 6, 2026" and the day count from today: 30 px from 1024, 20 px under it), the counts and the second opinion one per line, then the exhibit pair as the case page draws it at its end, side by side from 1024 and stacked under it. From 1024 px the sheet is the top sheet's style and width (1,088 px at 1280, 960 at 1024, 1 px ink edge, 32 / 40 / 40 insets), 80 px under it, the case page's gap under its own top sheet (measured on `c_sample` at 1280). Under 1024 px it is a bond sheet at the column width (358 px at 390, 608 at 768) with a 1 px ink edge and a 20 px inset, 40 px under the sample text actions. Measured on a production build: the sheet's top at y 506 at 1280 and 1024, 531 at 768, 656 at 390; the stamp from 575 to 711 at 1280 (38 px), 576 to 695 at 1024 (32 px), 606 to 734 at 768 (34 px), 735 to 862 at 390 (28 px), so the stamp is whole in the first 800 px at desktop and its top is in the phone's first screen. Page heights: 1,403 px at 1280 by 800, 1,387 at 1024 by 800 (the 44 px crop control, section 19), 1,692 at 768 by 1024, 2,045 at 390 by 844.

**Key Characteristics:**
- Manila ground, bond sheets with a 1 px ink edge, ink text, one red.
- Square everything: sheets, tabs, fields, buttons.
- No shadows; depth is tone and edge.
- One stamp per sheet, condensed, turned, unevenly inked.
- State as drawn marks in ink, always with words.
- One grotesque (Archivo) at two weights, 400 and 600; mono only for ids, folios, and the folder tab.

## Colors

A warm paper palette of one hue family (manila and kraft) with white sheets, near-black ink, one rubber-stamp red, and gold reserved for the reader's own pen.

### Primary
- **Stamp Red** (stamp-red): the rubber stamp's ink (the verdict, or the deadline before a verdict exists) and the quote highlight on the policy page (red at 15 to 20 percent alpha with a 2 px red underline at 60 to 70 percent). Also the text-selection tint (22 percent). Measured 6.54:1 on bond and 4.42:1 on manila, so red text on manila is allowed only at stamp size (28 px, weight 850, and up).

### Secondary
- **Fill-in Gold** (fill-in-gold): the 2 px underline of a field the reader fills in by hand on the letter, and the bar and label of a case-card field the reader must check. It marks the reader's own action.
- **Fill-in Wash** (fill-in-wash): the ground of those same fields. Ink on it measures 15.82:1. In print both drop to ink and transparent.

### Neutral
- **Folder Manila** (folder-manila): the page ground everywhere, the folder tab in the band. Ink 11.66:1, faded ink 6.06:1.
- **Folder Kraft** (folder-kraft): the band across the top of every page (the folder's back edge) and an index tab's hover. Ink 9.19:1, faded ink 4.78:1.
- **Tab Kraft Pale** (tab-kraft-pale): an index tab not in view. Ink 13.60:1.
- **Tab Kraft Deep** (tab-kraft-deep): the index tab of the section in view. Ink 7.97:1.
- **Bond** (bond): every sheet, exhibit, letter page, open panel, and the receipt. Ink 17.22:1.
- **Ink** (ink): all text, every 1 px sheet edge, the 4 px section rules, the marks, the focus ring, the primary button's ground.
- **Faded Ink** (faded-ink): secondary text: labels, captions, source lines, receipt column heads. 8.96:1 on bond, 6.06:1 on manila. Body-safe.
- **Pencil Edge** (pencil-edge): borders of controls that must meet 3:1 (citation chips at rest). 5.07:1 on bond, 3.43:1 on manila. Never text.
- **Hairline** (hairline): rules between rows, under sheet heads, around the page crop. 1.85:1 on bond, 1.25:1 on manila. Never text, never a control boundary.
- **Reference Paper** (reference-paper): a pale tint for an open reference (a chip's pressed state, the letter source panel on intake). Ink 15.42:1.

### Named Rules
**The One Red Rule.** Red is the stamp and the highlight. It never colors a link, a button, an error, a state, or a heading.

**The Reader's Pen Rule.** Gold appears only where the reader writes or checks something. It is the single sanctioned second color, and it marks an action, never a status.

**The Same-Hue Rule.** Every tint is mixed from the world's colors (ink into manila, manila into bond). No new hue enters for a state; a new state gets a mark.

## Typography

**Display Font:** Archivo (variable in weight and width, via next/font; system-ui fallback)
**Body Font:** Archivo
**Label/Mono Font:** the system mono stack (ui-monospace, Cascadia Mono, Consolas, Liberation Mono)

**Character:** One working grotesque at full scale for everything a clerk would type, condensed to 62 percent width and weight 850 only where a rubber stamp is pressed. Mono is the file's own numbering: the case id, the folios, the folder tab.

### Hierarchy
Values measured at 1280 by 800 unless noted.
- **Stamp** (850, 38 px at 1280 and up, 32 px at 1024, 34 px at 640, 28 px on the phone; line height 1; width 62 percent; uppercase; 0.01em): the verdict headline, the case page's h1 (an h2 on the landing's proof sheet, section 18). The deadline stamp before a verdict uses the same face at 25 to 28 px for the date.
- **Lead** (600, 30 px, 1.12, -0.015em): the deadline on the top sheet ("Appeal by Dec 6, 2026"), the day count under it at 400. 20 px on the phone.
- **Headline** (600, 28 px, 1.25): a section opening (number and title on one baseline). 22 px on the phone.
- **Title** (600, 20 px, 1.25): a section sheet's head at tabs sizes, the verdict's h3s, the receipt's counts, the appendix openings. The exhibit titles are 21 px with -0.01em.
- **Body** (400, 17 px at 1024 and up, 18 px under it, 1.5; reading paragraphs 1.625 at a 70ch cap): all running text. The quoted denial reason in an exhibit is 19 px at 1.45.
- **Letter** (400, 18 px, 1.6): the appeal letter's paragraphs on the US Letter page; the date line, address, and Re line at 17 px.
- **Label** (400, 14 px, faded ink): reference-row labels, source lines and captions (14 to 15 px), receipt column heads (at 600).
- **Mono** (400, 14 px): the folder tab, exhibit folios, the case id.
- **Wordmark** (600, 21 px, width 88 percent, -0.01em): "Recourse" in the band.

### Named Rules
**The Two Weights Rule.** The page uses 400 and 600. The stamp alone is 850. The theme maps "bold" to 600, so nothing renders at 700.

**The Condensed Means Stamped Rule.** The 62 percent width belongs to the stamp. The wordmark's 88 percent is the only other narrowed setting.

**The Tabular Rule.** Every count, date, amount, and folio sets tabular numerals.

## Layout

The case page is a folder frame 1,120 px wide (1,088 px of content inside 32 px of padding), centered on the manila ground under the kraft band (64 px tall at 1024 and up, 56 px under it). The band's left holds the wordmark and, on a case, the manila folder tab joined to the ground below (42 px tall, open at the bottom); its right holds the status line and the page's links.

At 1280 by 800 the top sheet starts 101 px from the top of the window and runs past the fold: the stamp at its top left, the reference block (440 px wide; 340 px from 1024 to 1279) floated to its top right, the two exhibits side by side under them (483 px each, 40 px apart), then the rule and the gap in the same two columns. The appeal letter is two US Letter pages, 620 by 802 px (8.5 by 11 inches at 1280), 24 px apart, with 72 px inner margins, and its margin notes in a 420 px column across a 48 px gutter (the 620 : 420 ratio holds down to 1024). From 1280 px, where the index tabs stand at the folder's right edge, the margin column is 16 px narrower (404 px), so it ends 16 px short of the tabs; its left edge and the letter do not move. Section sheets span the full 1,088 px with 32 px top, 40 px side, and 40 px bottom insets. Measured spacing between documents: 80 px from the top sheet to the letter's opening, 96 px from the letter to the next sheet and between sheets, 64 px above the receipt's opening. The receipt is a 560 px slip.

The index tabs are fixed to the folder's right edge (50 percent plus 544 px, 88 px from the top), stacked with 4 px gaps, written vertically. They appear only at 1280 px wide and 760 px tall and up; under that, the section openings carry the numbers.

Under 1024 px the case page is one column: 358 px of content at 390 (16 px side gutters), 608 px at 768 (a 640 px frame), body at 18 px, under a 56 px band. The top sheet starts 24 px under the band (y 81 at 390) and spans the column with a 20 px inset, so its contents are 316 px wide at 390 and 566 at 768. Measured on `c_sample` at its end, 390 by 844: the stamp's turned top at y 96 (28 px, three lines, 8 px under the inset), the Lead line at 243 (20 px; the next step and a 17 px deadline line on the consistent and not-settled verdicts), the counts one per line from 311 (17 px), the letter's row at 444, the case line at 487 under a hairline (15 px, "Show the full case card" a 44 px text action under it), Exhibit 1 at 628, so its head is in the first screen. The letter's row is one 17 px line under the counts, from decided to the end, in short words of its own: an open ring while a stage runs ("Verdict reached.", "Drafting the appeal letter…", "Checking the letter…") or when one stopped, a tick for a finished state ("Appeal letter ready.", a link to the letter that stays through reviewed, or "No appeal letter was drafted."). The exhibits stack 48 px apart with 20 px side insets (28 from 1024); the crop and the opened page run edge to edge inside the exhibit's frame (314 px at 390), with "See the page" between the quote and the crop. At 768 by 1024: the stamp at 34 px on two lines, its turned top at 96 (20 px under the inset, since the wider stamp rises more), the case line at 464, Exhibit 1 at 583. While the case runs the sheet holds the case line at y 102 with the deadline stamp at 120 px wide at its right (its small lines kept at 12 px), "Show the full case card" under both, the seven stages as marks in two columns (four and three, 15 px), the running stage's words (17 px) and the latest finding (17 px) under them, the latest finding's bottom at 440 at 390 and 442 at 768 at every poll.

At decided the phone's top sheet moves once and then holds still: the slip folds, the stamp presses in at the sheet's top (the one motion), the case line drops under the counts and the letter's row, and the deadline stamp becomes the Lead line. From then on the sheet's height does not change: on the inconsistent verdict the counts hold the two letter lines' places (unseen) until the letter's counts fill them, and the letter's row keeps its one line to the end, so the case line and Exhibit 1 sit at the same y at decided, drafted and reviewed (487 and 628 at 390, 464 and 583 at 768). The page is 11,779 px tall at 390 (14 screens). The sections after the top sheet sit 40 px apart.

Breakpoints: 640 px (sm), 1024 px (lg, the desktop structure), 1280 px (xl), and the custom `tabs` condition (1280 wide and 760 tall). The page image panel is sticky only at 1024 wide and over 700 tall.

**The Space Above Rule.** The gap above a section is always larger than the gap under its opening (96 px over, 16 px under at 1024 and up).

## Elevation & Depth

The system is flat. Nothing on screen has a box-shadow. A sheet reads as lying on the folder because it is bond on manila with a 1 px ink edge; the current index tab reads as forward because it is the deeper kraft and juts 8 px further out. Open panels (the expanded quote, the full case card, the page image in the margin) are bond with a 1 px ink edge over whatever is beneath them.

**The Edge Not Shadow Rule.** Depth is a 1 px ink edge and a lighter sheet. No shadows, no gradients, no blur.

## Shapes

Every corner is square: sheets, exhibits, letter pages, tabs, fields, buttons, chips. The theme sets the small radius to 0, so the leftover small-radius classes render square. Lines are the shape language: 1 px ink edges around documents, 4 px ink rules over sections on the phone and from 1024 to 1279, 1 px hairlines between rows, a 2 px ink left rule on an expanded quote, a dashed top edge on the receipt slip. Two drawn forms recur: the paper clip (a 20 by 52 px ink wire at 72 percent opacity, overlapping a clipped sheet's top edge by about 22 px) and the stamp's double frame.

**The Square Sheet Rule.** No radius anywhere. A rounded corner is the other world's card.

## Components

### Buttons
Plain, typeset, and square.
- **Shape:** square corners (0 px).
- **Primary:** ink ground, bond text, 18 px at 600, 48 px tall, 20 px side padding; full width on the phone, auto from 640 px ("Copy the letter", "Start with your letter").
- **Secondary:** bond ground, ink text, 1 px ink border, same size ("Download as text").
- **Text actions:** ink, 600, underlined with a 4 px offset, at least 44 px tall ("Show the full case card", "New case").
- **Focus:** a 3 px ink outline 2 px off the control, the same everywhere.

### Chips (citations)
- **Style:** a reference line in ink with a 1 px pencil-edge border on reference paper at rest on the phone; at desktop the border and ground are transparent until pressed.
- **State:** open goes to an ink border on a hairline ground. At least 44 px tall.

### Cards / Containers (sheets)
- **Corner Style:** square.
- **Background:** bond on manila.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1 px ink; the receipt slip's top border is dashed.
- **Internal Padding:** 32 px top, 40 px sides and bottom for the top sheet and section sheets; 24, 28, and 20 px for an exhibit; 72 px on a letter page.

### Inputs / Fields
- **Style:** square, hairline rule beneath, ink caret.
- **Fill-in field (letter):** fill-in wash ground, 2 px gold underline, "Fill in" in 14 px 600 ink; prints as an ink underline on white.
- **Check field (case card):** fill-in wash ground with a 6 px gold bar at the left and a gold "Check" label; the word carries the meaning.

### Navigation
- **Band:** kraft, 64 px, wordmark left, the manila folder tab beside it in 14 px mono, links right at 15 px.
- **Index tabs:** kraft-pale tabs 46 px wide, 1 px ink edges on three sides (30 percent), 14 px label written vertically with the number in tabular figures, at least 44 px tall (measured 70 to 138 px by label length). The current tab is kraft-deep, 54 px wide, 600, and carries aria-current. Hover goes to kraft. Hidden under the `tabs` size and in print.

### Verdict Stamp (signature)
The verdict headline as a rubber stamp: Archivo condensed caps at 850 in stamp red, a 4 px red frame with a second 1.5 px frame inset 10 px inside it (Chromium paints the inner frame at 1 px at 1x density), padding 0.42em 0.6em 0.34em, turned -2.6 degrees from its left edge (measured -2.60), inked unevenly by the `#ink-stamp` SVG filter (fine noise holes, slow patch fade, 2 px edge displacement). Measured at 1280: 38 px type, two lines, 526 px wide unrotated, 113 px tall. On the case page it is pressed once on arrival (150 ms, from 1.06 scale and -4 degrees) unless reduced motion is set; on the landing's proof sheet it is already pressed, with no motion. In forced-colors mode the filter is off. It stays real text: selectable, read aloud, printed.

### Deadline Stamp
Before a verdict exists, the deadline is the sheet's one stamp: 156 px wide, a 3 px red frame and a 1 px frame inset 6 px (dashed until confirmed, solid once landed), turned -1.4 degrees, then -2.6 when landed. The date is red at 850 condensed; the small lines ("Appeal by", the day count, "Case opened") are ink at 14 px, 600. Once the verdict lands, the deadline becomes the Lead line with a drawn calendar mark. On the phone's top sheet during the run it is the same stamp scaled to 120 px wide (zoom 0.77), its small lines kept at 12 px, at the right of the case line.

### Exhibit Pair (signature)
Two bond sheets side by side at 1024 and up, stacked letter then policy on the phone's top sheet under it (20 px side insets, 48 px apart), each held by a paper clip: "The letter says" (the denial reason quoted at 19 px, its source line in 14 px faded ink at the foot) and "The policy says" (the cited sentence as live text with the red highlight, a crop of the real policy page under it with the highlight boxes drawn left to right over 150 ms, the folio in mono, and the vision check caption with its mark). On the phone the crop is not a control: "See the page", a text action between the quote and the crop, grows the whole page in the crop's place (a box no taller than 70 vh that scrolls inside, the first highlight in its top third, no Zoom) and reads "Close" while it is open, where it was pressed; the window and everything above the page stay still, and what is under the page moves down by its height.

### Marks
16 by 16 px drawn SVGs in ink at one stroke weight (2 to 2.2 px, square caps): tick, strike (a heavy bar with two half-opacity guide lines), open ring, calendar leaf. Always beside words. The tick, the strike and the ring are state (verified, struck, not settled or not reached). The calendar leaf is not a state: it is the deadline's mark wherever the deadline is the Lead line (the phone's Lead, the desktop reference block's Lead, the landing's proof sheet), a square-cornered leaf with a header rule and two binding rings over its top edge, read as "Deadline" before the date. It has two sizes, each redrawn on its own pixel grid so the stroke stays 2 px: 16 by 16 px on the phone's Lead (and in this list), 20 by 20 px beside the 30 px Lead type from 1024 px (the reference block's Lead and the landing's proof sheet), the slot the ring had there. A deadline the letter does not state keeps the ring, and the next step that leads on the consistent and not-settled verdicts carries no mark. The paper clip shares the same ink and drawing hand.

### Motion
Transform only, never an opacity fade on text: the stamp press (150 ms, cubic-bezier(0.2, 0.8, 0.2, 1)), sections land 6 px up (120 ms ease-out), checklist ticks step (160 ms, two steps), the page panel steps in 8 px (120 ms, two steps). All of it stops under reduced motion.

## Do's and Don'ts

### Do:
- **Do** set every document on bond with a 1 px ink edge on the manila ground, square-cornered.
- **Do** keep one stamp per sheet: the verdict once it exists, the deadline before it.
- **Do** show state with a tick, a strike, or an open ring, always next to words.
- **Do** keep red to the stamp and the highlight, and gold to fields the reader fills in or checks.
- **Do** keep text at 400 or 600, with tabular numerals for every count, date, amount, and folio.
- **Do** use mono only for the case id, folios, and the folder tab.
- **Do** give every control at least 44 by 44 px and the 3 px ink focus ring.
- **Do** print the appeal letter alone, on US Letter, with the folio in the page margin.

### Don't:
- **Don't** add a shadow, a gradient, or a blur; the 1 px edge is the only depth.
- **Don't** round a corner.
- **Don't** introduce a second accent or a status color; a new state gets a mark and a word.
- **Don't** set body text in red, or any red text smaller than the stamp on manila (4.42:1).
- **Don't** add illustration beyond the world's drawn instruments (the marks, the paper clip, the calendar leaf, the stamp frame).
- **Don't** use the condensed width or weight 850 outside a stamp.
- **Don't** set hairline or pencil edge as text.
- **Don't** add a dark theme; the world is paper.

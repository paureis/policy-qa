"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { NOT_SETTLED_LABEL, type Letter, type Verdict } from "@/lib/case";
import { groupCitations, pageFolio, shortDocName } from "@/components/investigation/CitationChip";
import { Mark } from "@/components/investigation/Marks";
import { usePageViewer } from "@/components/investigation/PageViewer";
import { OPENING_H2, SHEET_HEAD, SectionTitle } from "@/components/investigation/SectionTitle";
import { FootnoteRef, MarginNote, noteRegionId, useOverlayPlacement, type NoteGroup } from "./Sidenotes";

/* Space between the margin head (not settled) and the first note. */
const HEAD_GAP = 20;

/*
  Section 2 of a finished case without a letter (consistent, not settled):
  why the denial holds, or why no letter was drafted, then what would have
  made it covered, or what would change it.

  On the phone (and under 1024 px): the plain section as it always was,
  the heading, the explanation, and for a denial that holds what would
  have made it covered (for not settled, what would change it stays in the
  verdict above).

  sheet: the finished case at 1024 px and up (classes only). The section
  becomes a document in the folder: a bond sheet 620 px wide with a 1 px
  ink edge and 72 px inner margins, the letter page's width and margins,
  set in the letter's 620 : 420 : 48 grid. The head is the sheet's head
  (number and a 4 px rule under 1280 px, a 20 px head with a hairline at
  tabs sizes), the explanation at the letter's type (18 px, 1.6), then
  what would change it. desk (the same width as the script sees it): the
  rule's citations as sidenotes in the 420 px margin, anchored to the
  explanation paragraph, with the letter's mechanics and look (Sidenotes.tsx):
  a footnote number per note at the paragraph's end opens the expanded
  quote, "page N" opens the page over the margin, one open at a time,
  Escape closes and returns focus. Not settled carries an open ring and
  "The documents do not settle this" at the head of the margin: the open
  question is a mark and words in ink, never a gray or dimmed state.
*/
export function ExplanationSheet({
  letter,
  verdict,
  sheet = false,
  desk = false,
  n = null,
}: {
  letter: Letter;
  verdict: Verdict | null;
  sheet?: boolean;
  desk?: boolean;
  n?: number | null;
}) {
  const settledAgainst = verdict?.outcome === "consistent";
  const notSettled = verdict?.outcome === "not_settled";
  const title = settledAgainst ? "Why the denial holds" : "Why no letter was drafted";
  const change = verdict?.what_would_change?.trim() ? verdict.what_would_change : null;
  const noteBase = useId();
  const unsupported = verdict?.rule?.unsupported === true;
  const ruleCitations = verdict?.rule?.citations ?? [];
  /* The rule's citations, one note per (document, page) pair, as the letter merges them; a struck rule's notes say "Could not verify". */
  const groups: NoteGroup[] =
    sheet && desk ? groupCitations(ruleCitations).map((citations, i) => ({ n: i + 1, citations, struck: unsupported })) : [];

  const [openNote, setOpenNote] = useState<number | null>(null);
  const viewer = usePageViewer();
  const viewerOpenKey = viewer?.state.open?.placement === "margin" ? viewer.state.open.key : null;
  const closeIf = viewer?.actions.closeIf;
  const frameRef = useRef<HTMLDivElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const paraRef = useRef<HTMLParagraphElement>(null);
  const marginRef = useRef<HTMLDivElement>(null);
  const notesBottom = useRef(0);
  const overlayBottom = useRef(0);
  const hasNotes = groups.length > 0;
  const explanation = letter.explanation?.trim() || "The service gave no explanation.";
  const cut = explanation.lastIndexOf(" ") + 1;
  const lead = explanation.slice(0, cut);
  const lastWord = explanation.slice(cut);

  /*
    The sheet stands at least as tall as its margin notes: when the notes run past the text, the
    sheet stretches (white space at the foot of a memo), so both columns end on one foot and the
    gap to the next section is measured from it. An open overlay that runs further grows the frame
    below the sheet instead, as on the letter.
  */
  const fitFrame = useCallback(() => {
    const frame = frameRef.current;
    const page = sheetRef.current;
    if (!frame || !page) return;
    page.style.minHeight = "";
    const natural = page.offsetHeight;
    page.style.minHeight = notesBottom.current > natural ? `${notesBottom.current}px` : "";
    frame.style.minHeight = overlayBottom.current > page.offsetHeight ? `${overlayBottom.current}px` : "";
  }, []);

  const toggleNote = useCallback(
    (k: number) => {
      if (viewerOpenKey && closeIf) closeIf(viewerOpenKey);
      setOpenNote((o) => (o === k ? null : k));
    },
    [viewerOpenKey, closeIf],
  );
  const closeQuote = useCallback(() => setOpenNote(null), []);

  /* Escape closes the expanded quote and returns focus to its footnote number. */
  useEffect(() => {
    if (openNote === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      const k = openNote;
      setOpenNote(null);
      frameRef.current?.querySelector<HTMLElement>(`[data-footnote="${k}"]`)?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openNote]);

  /* The margin starts at the explanation paragraph's first line; the frame grows if the notes run past the sheet. */
  useLayoutEffect(() => {
    const para = paraRef.current;
    const margin = marginRef.current;
    if (!hasNotes || !para || !margin) {
      notesBottom.current = 0;
      fitFrame();
      return;
    }
    let raf = 0;
    const layout = () => {
      margin.style.top = `${para.offsetTop}px`;
      /* Measured on sub-pixel boxes and rounded up, so the sheet's foot is never a pixel above the notes'. */
      const frameTop = frameRef.current?.getBoundingClientRect().top ?? 0;
      notesBottom.current = Math.ceil(margin.getBoundingClientRect().bottom - frameTop);
      fitFrame();
    };
    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(layout);
    };
    layout();
    const ro = new ResizeObserver(schedule);
    if (sheetRef.current) ro.observe(sheetRef.current);
    ro.observe(margin);
    void document.fonts?.ready.then(schedule);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [hasNotes, fitFrame]);

  useOverlayPlacement(frameRef, overlayBottom, fitFrame, openNote, viewerOpenKey);

  const h3 = `text-[18px] font-bold ${sheet ? "lg:text-[20px] lg:font-semibold" : ""}`;
  const body = `mt-2 text-[18px] leading-relaxed ${sheet ? "lg:leading-[1.6]" : "lg:text-[17px]"}`;

  return (
    <div ref={frameRef} className={sheet ? "lg:relative" : ""} data-explanation-frame={sheet ? "true" : undefined}>
      <div
        ref={sheetRef}
        className={sheet ? "lg:w-[calc((100%-48px)*620/1040)] lg:border lg:border-ink lg:bg-bond lg:p-[72px]" : ""}
        data-explanation-sheet={sheet ? "true" : undefined}
      >
        <h2
          id="action-heading"
          className={`mt-1 text-[22px] leading-tight font-bold ${
            sheet ? `${OPENING_H2} ${SHEET_HEAD} lg:border-t-4 lg:border-ink lg:pt-4 tabs:border-t-0 tabs:pt-0` : ""
          }`}
        >
          <SectionTitle title={title} short={title} n={sheet ? n : null} />
        </h2>
        <p
          ref={paraRef}
          className={`mt-3 text-[18px] leading-relaxed ${sheet ? "lg:mt-6 lg:leading-[1.6]" : "lg:text-[17px]"}`}
          data-explanation="true"
        >
          {hasNotes ? (
            <>
              {lead}
              {/* The last word and the footnote numbers never part across a line break. */}
              <span className="whitespace-nowrap">
                {lastWord}
                {groups.map((g) => (
                  <FootnoteRef
                    key={g.n}
                    n={g.n}
                    label={`${shortDocName(g.citations[0])}, ${pageFolio(g.citations[0])}`}
                    open={openNote === g.n}
                    controls={noteRegionId(noteBase, g.n)}
                    onToggle={() => toggleNote(g.n)}
                  />
                ))}
              </span>
            </>
          ) : (
            explanation
          )}
        </p>
        {/*
          The margin, in the DOM right after the paragraph it belongs to. Absolute in the frame (the
          sheet is not positioned), so it sits in the 420 px column across the 48 px gutter; from 1280 px,
          where the index tabs stand, 16 px narrower so it ends short of them, as the letter's (section 19, M3).
        */}
        {hasNotes ? (
          <div
            ref={marginRef}
            className="absolute top-0 left-[calc((100%-48px)*620/1040+48px)] w-[calc((100%-48px)*420/1040)] xl:w-[calc((100%-48px)*420/1040-16px)]"
            data-margin-anchor="explanation"
            data-explanation-margin="true"
          >
            {notSettled ? (
              <p className="flex items-center gap-2 text-[17px] leading-snug font-semibold text-ink" data-margin-open-question="true">
                <Mark kind="ring" />
                {NOT_SETTLED_LABEL}
              </p>
            ) : null}
            <ul aria-label="The rule" className="space-y-5" style={notSettled ? { marginTop: HEAD_GAP } : undefined} data-margin="explanation">
              {groups.map((g) => (
                <MarginNote
                  key={g.n}
                  group={g}
                  noteBase={noteBase}
                  open={openNote === g.n}
                  onClose={() => toggleNote(g.n)}
                  onOpenPage={closeQuote}
                />
              ))}
            </ul>
          </div>
        ) : null}
        {/*
          What would change the outcome. For a denial that holds, "What would have made it covered",
          as on the phone. For not settled, "What would change it" moves here from the verdict at
          1024 px and up (on the phone it stays in the verdict, so it is display: none there).
        */}
        {change && (settledAgainst || (sheet && notSettled)) ? (
          <div
            className={`mt-5 border-t border-hairline pt-4 ${sheet ? "lg:mt-8" : ""} ${settledAgainst ? "" : "hidden lg:block"}`}
            data-what-would-change="sheet"
          >
            <h3 className={h3}>{settledAgainst ? "What would have made it covered" : "What would change it"}</h3>
            <p className={body}>{change}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

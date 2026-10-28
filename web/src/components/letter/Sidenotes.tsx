"use client";

import { useEffect, useLayoutEffect, type MutableRefObject, type RefObject } from "react";
import { pageFolio, shortDocName, type ChipCitation } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { Mark } from "@/components/investigation/Marks";
import { MarginPageViewer, usePageViewer, viewerPanelId } from "@/components/investigation/PageViewer";

/*
  The sidenote mechanics shared by the appeal letter's sheet and the
  explanation sheet of a finished case without a letter: a footnote number in
  the text, a margin note beside it (short title, folio, the full quote, its
  verification state as words), the expanded quote and the cited page opening
  as overlays over the margin below the note. One thing open at a time;
  Escape closes it and returns focus. Moved here unchanged from
  AppealLetter.tsx on Oct 27, 2026 (piece 2), so both sheets share one look.
*/

/* One margin note: the verified quotes of one (document, page) pair, or one struck citation. */
export interface NoteGroup {
  n: number;
  citations: ChipCitation[];
  struck: boolean;
}

/* A block in the margin column, beside the sheet: absolute, its top set by the layout above. */
export const MARGIN_BLOCK = "absolute top-0 left-[calc(100%+48px)] w-[calc(100%*420/620)]";

export function noteRegionId(base: string, n: number): string {
  return `${base}-note-${n}`;
}

/*
  An open overlay (the expanded quote or the page) hangs below its note.
  When it would run past the last page, it opens upward from the note
  instead; when there is no room above either, the frame grows to hold it,
  so it never paints over the next section. Re-measured as the page image
  loads. container: the element the notes are positioned in, whose height is
  the sheet's bottom.
*/
export function useOverlayPlacement(
  containerRef: RefObject<HTMLElement | null>,
  overlayBottomRef: MutableRefObject<number>,
  fitFrame: () => void,
  openNote: number | null,
  viewerOpenKey: string | null,
): void {
  useLayoutEffect(() => {
    const article = containerRef.current;
    if (!article) return;
    const overlay = article.querySelector<HTMLElement>('[data-note-region], [data-page-viewer="margin"]');
    if (!overlay) {
      overlayBottomRef.current = 0;
      fitFrame();
      return;
    }
    const place = () => {
      const note = overlay.parentElement;
      if (!note) return;
      overlay.style.top = "";
      overlay.style.bottom = "";
      overlay.style.marginTop = "";
      overlay.style.marginBottom = "";
      const base = article.getBoundingClientRect().top;
      const noteBox = note.getBoundingClientRect();
      const h = overlay.offsetHeight;
      const below = noteBox.bottom - base + 8 + h;
      const sheetBottom = article.offsetHeight;
      const above = noteBox.top - base - 8 - h;
      if (below > sheetBottom && above >= 0) {
        overlay.style.top = "auto";
        overlay.style.bottom = "100%";
        overlay.style.marginTop = "0px";
        overlay.style.marginBottom = "8px";
        overlayBottomRef.current = 0;
      } else {
        overlayBottomRef.current = below;
      }
      fitFrame();
    };
    place();
    const ro = new ResizeObserver(place);
    ro.observe(overlay);
    return () => {
      ro.disconnect();
      overlayBottomRef.current = 0;
      fitFrame();
    };
  }, [containerRef, overlayBottomRef, openNote, viewerOpenKey, fitFrame]);
}

/*
  A footnote number after a claim sentence: 14 px, tabular, ink, raised like
  a superscript and underlined so it reads as a link. Its hit area is its own
  box, a few pixels around the digits, so it never covers the words beside
  it or the lines above and below (an inline target in running text, the
  exception WCAG 2.5.8 makes; the note's own controls carry the 44 px
  targets). Its name says what it points to.
*/
export function FootnoteRef({
  n,
  label,
  open,
  controls,
  onToggle,
}: {
  n: number;
  label: string;
  open: boolean;
  controls: string;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={`citation ${n}: ${label}`}
      aria-expanded={open}
      aria-controls={open ? controls : undefined}
      onClick={onToggle}
      className={`relative -top-[0.45em] ml-0.5 inline-block px-[3px] align-baseline text-[14px] leading-4 font-semibold text-ink tabular-nums underline underline-offset-2 print:hidden ${
        open ? "bg-hairline decoration-2" : "decoration-1 hover:decoration-2"
      }`}
      data-footnote={n}
    >
      {n}
    </button>
  );
}

/* Reference-style links in a note: underlined, a 44 px tall target. */
const NOTE_LINK =
  "-my-2.5 inline-flex min-h-11 items-center px-1 text-[15px] font-semibold text-ink underline decoration-1 underline-offset-4 tabular-nums";

/*
  A margin note, set as a sidenote: its number, the short document name and
  the folio, the full quote, then its verification state as words: "Found on
  page 5" with a tick mark, "page 5" being the link that opens
  the cited page over the margin (the page image with the red highlight and the
  vision line); a struck citation carries "Could not verify" instead. The
  footnote number in the letter opens the expanded quote (the full title and
  the quote) over the margin below the note. Overlays are absolute, so the
  notes below and the letter never move.
*/
export function MarginNote({
  group,
  noteBase,
  open,
  onClose,
  onOpenPage,
}: {
  group: NoteGroup;
  noteBase: string;
  open: boolean;
  onClose: () => void;
  onOpenPage: () => void;
}) {
  const viewer = usePageViewer();
  const closeIf = viewer?.actions.closeIf;
  const { n, citations, struck } = group;
  const first = citations[0];
  const title = first.title?.trim() || first.doc_id;
  const region = noteRegionId(noteBase, n);
  const viewKey = `${region}-view`;
  useEffect(() => {
    if (!closeIf) return;
    return () => closeIf(viewKey);
  }, [closeIf, viewKey]);
  const pageOpen = viewer?.state.open?.key === viewKey;
  return (
    <li className={`relative pl-8 ${open || pageOpen ? "z-30" : ""}`} data-note={n} data-note-open={open ? "quote" : pageOpen ? "page" : "false"} data-note-struck={struck ? "true" : undefined}>
      <p className="text-[15px] leading-6 font-semibold tabular-nums" data-note-head="true">
        <span className="absolute left-0" data-note-number={n}>
          {n}
          <span className="sr-only">. </span>
        </span>
        {shortDocName(first)}, {pageFolio(first)}
      </p>
      {citations.map((c, k) => (
        <blockquote key={k} className="mt-1 text-[16px] leading-[1.5] text-ink" data-note-quote="full">
          {struck ? <s className="decoration-ink decoration-2">“{c.quote}”</s> : <>“{c.quote}”</>}
        </blockquote>
      ))}
      {struck ? (
        <p className="mt-2">
          <CouldNotVerifyTag inline />
        </p>
      ) : (
        <p className="mt-1.5 flex flex-wrap items-center gap-x-1.5 text-[15px] leading-6 text-ink tabular-nums" data-note-found="true">
          <Mark kind="tick" className="h-4 w-4" />
          <span>Found on</span>
          {viewer ? (
            <button
              type="button"
              aria-expanded={pageOpen}
              aria-controls={pageOpen ? viewerPanelId(viewKey) : undefined}
              aria-label={`page ${first.page} of ${title}`}
              onClick={(e) => {
                onOpenPage();
                viewer.actions.toggle(viewKey, first, { placement: "margin", returnTo: e.currentTarget });
              }}
              className={`${NOTE_LINK} -ml-1 ${pageOpen ? "bg-hairline" : ""}`}
              data-note-page="true"
            >
              page {first.page}
            </button>
          ) : (
            <span>page {first.page}</span>
          )}
        </p>
      )}
      {open ? (
        <div
          id={region}
          role="group"
          aria-label={`Citation ${n}`}
          className="step-in absolute inset-x-0 top-full z-20 mt-2 border border-ink bg-bond px-4 pt-3 pb-4"
          data-note-region="true"
        >
          {citations.map((c, k) => (
            <blockquote key={k} className={`${k > 0 ? "mt-3" : ""} border-l-2 border-ink pl-4 text-[17px] leading-relaxed text-ink`}>
              “{c.quote}”
            </blockquote>
          ))}
          <p className="mt-3 text-[15px] leading-snug text-muted" data-note-title="true">
            {title}, {pageFolio(first)}.{struck ? "" : " This quote was found on the cited page."}
          </p>
          <button type="button" onClick={onClose} className="mt-2 inline-flex min-h-11 items-center border border-ink bg-bond px-3 text-[16px] font-semibold text-ink">
            Close
          </button>
        </div>
      ) : null}
      <MarginPageViewer viewerKey={viewKey} />
    </li>
  );
}

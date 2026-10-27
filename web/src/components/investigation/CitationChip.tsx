"use client";

import { useEffect, useId, useState } from "react";
import { printedPage } from "@/lib/printed-folios";
import { Disclosure } from "./Marks";
import { InlinePageViewer, usePageViewer, viewerPanelId } from "./PageViewer";

/*
  A page reference that cannot be misread: "page 5" when the page prints its
  own index or no folio, "PDF page 5 (printed page 3)" when the number printed
  on the page differs (front matter before page 1), so the reader who opens
  the PDF and the reader who holds the paper find the same page.
*/
export function pageFolio(c: { doc_id: string; page: number }): string {
  const printed = printedPage(c.doc_id, c.page);
  return printed === null ? `page ${c.page}` : `PDF page ${c.page} (printed page ${printed})`;
}

/* What a chip needs: a finding's Citation and the verdict's CitationRef both fit. */
export interface ChipCitation {
  doc_id: string;
  title: string | null;
  page: number;
  quote: string;
}

/*
  The short name a chip shows, set like a legal cite: the rule number, the
  manual and chapter, the contract exhibit, the MLN number. The full title
  stays in the quote's caption and in the chip's tooltip.
*/
export function shortDocName(c: { title: string | null; doc_id: string }): string {
  const t = c.title?.trim();
  if (!t) return c.doc_id;
  let m = t.match(/\((Pub \d+-\d+)\),\s*Chapter (\d+)/i);
  if (m) return `${m[1]}, ch. ${m[2]}`;
  m = t.match(/\((Rule [^()]+)\)\s*$/);
  if (m) return m[1];
  m = t.match(/^SMMC Model Health Plan Contract,\s*([^:]+)/);
  if (m) return `SMMC Contract, ${m[1].trim()}`;
  m = t.match(/\(((?:MLN|CMS Product No\.)[^()]*\d[^()]*)\)\s*$/);
  if (m) return m[1].replace("CMS Product No.", "CMS No.");
  m = t.match(/^(.*\bManual),\s*Chapter (\d+)/);
  if (m) return `${m[1]}, ch. ${m[2]}`;
  const colon = t.indexOf(":");
  if (colon > 0 && colon <= 32) return t.slice(0, colon);
  return t;
}

/*
  Identical (document, page) pairs collapse into one chip; its distinct
  quotes all open under it. Order is first appearance.
*/
export function groupCitations(citations: ChipCitation[]): ChipCitation[][] {
  const groups = new Map<string, ChipCitation[]>();
  for (const c of citations) {
    const key = `${c.doc_id}|${c.page}`;
    const group = groups.get(key);
    if (!group) groups.set(key, [c]);
    else if (!group.some((x) => x.quote === c.quote)) group.push(c);
  }
  return [...groups.values()];
}

/* The chip's face: a short name and a page folio, read as a reference, not a control. */
function ChipFace({ citation, open, quotes = 1 }: { citation: ChipCitation; open: boolean; quotes?: number }) {
  return (
    <>
      <span aria-hidden="true" className="mr-1.5 inline-flex shrink-0 self-center text-muted">
        <Disclosure open={open} className="h-3 w-3" />
      </span>
      {/* Under 360 px the name wraps instead of pushing the page sideways (320 px reflow). */}
      <span className="min-w-0 truncate font-semibold max-[359px]:whitespace-normal lg:underline lg:decoration-edge lg:decoration-1 lg:underline-offset-4">
        {shortDocName(citation)}
      </span>
      <span aria-hidden="true" className="mx-1.5 shrink-0 text-muted">
        ·
      </span>
      <span className="shrink-0 whitespace-nowrap tabular-nums">
        <span aria-hidden="true">p.&nbsp;</span>
        <span className="sr-only">page </span>
        {citation.page}
      </span>
      {quotes > 1 ? <span className="ml-1.5 shrink-0 whitespace-nowrap text-muted">({quotes} quotes)</span> : null}
    </>
  );
}

/*
  At 1024 px and up the face drops the tint and the rule for an underlined
  cite (the name), so a 44 px tall target does not read as a button.
*/
const FACE = (open: boolean) =>
  `relative inline-flex max-w-full items-baseline border-b text-left text-ink tabular-nums before:absolute before:inset-x-0 before:content-[''] ${
    open ? "border-ink bg-hairline" : "border-edge bg-paper lg:border-transparent lg:bg-transparent"
  }`;

/*
  A verified citation: a short document name and page on a paper-tint
  reference, the quoted excerpt inline underneath when tapped. Never a bare
  footnote number. The visible face is short; a transparent extension makes
  the hit area 46px tall. aria-controls is set only while the excerpt is in
  the DOM.
*/
export function CitationChip({ citations }: { citations: ChipCitation[] }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const first = citations[0];
  const ids = citations.map((_, k) => `${id}-${k}`);
  return (
    <li className={`max-w-full min-w-0 list-none ${open ? "basis-full" : ""}`}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? ids.join(" ") : undefined}
        onClick={() => setOpen((o) => !o)}
        title={first.title?.trim() || undefined}
        className={`${FACE(open)} px-2 py-0.5 text-[16px] leading-6 before:-inset-y-[9px] lg:min-h-11 lg:items-center lg:before:hidden`}
        data-chip="reference"
      >
        <ChipFace citation={first} open={open} quotes={citations.length} />
      </button>
      {open ? citations.map((c, k) => <QuoteFigure key={ids[k]} id={ids[k]} citation={c} />) : null}
    </li>
  );
}

/*
  A chip inside a line of the letter. It keeps the line's rhythm: a 24px face
  inside a taller line, no box; a transparent extension makes the hit area
  44px tall.
*/
export function InlineReferenceChip({
  citation,
  open,
  controls,
  onToggle,
}: {
  citation: ChipCitation;
  open: boolean;
  controls: string;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={open ? controls : undefined}
      onClick={onToggle}
      title={citation.title?.trim() || undefined}
      className={`${FACE(open)} px-1.5 align-baseline text-[15px] leading-6 before:-inset-y-[10px] lg:-my-[10px] lg:border-transparent lg:bg-clip-content lg:py-[10px] lg:before:hidden`}
      data-chip="letter"
    >
      <ChipFace citation={citation} open={open} />
    </button>
  );
}

/*
  The quoted excerpt with its title and page as the caption, and "See the
  page" when a page viewer provider is present: the cited page as an image
  with the quote highlighted (below the quote on the phone, beside the case
  at desktop width). Collapsing the quote closes its viewer.
*/
export function QuoteFigure({ id, citation }: { id: string; citation: ChipCitation }) {
  const title = citation.title?.trim() || citation.doc_id;
  const viewer = usePageViewer();
  const closeIf = viewer?.actions.closeIf;
  useEffect(() => {
    if (!closeIf) return;
    return () => closeIf(id);
  }, [closeIf, id]);
  const pageOpen = viewer?.state.open?.key === id;
  return (
    <>
      <figure id={id} className="mt-2 mb-2 border-l-2 border-ink pl-4">
        <blockquote className="text-[18px] leading-relaxed lg:text-[17px]">“{citation.quote}”</blockquote>
        <figcaption className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-[15px] text-muted">
          <span>
            {title}, page {citation.page}. This quote was found on the cited page.
          </span>
          {viewer ? (
            <button
              type="button"
              aria-expanded={pageOpen}
              aria-controls={pageOpen ? viewerPanelId(id) : undefined}
              onClick={() => viewer.actions.toggle(id, citation)}
              className={`inline-flex min-h-11 items-center border border-ink px-3 text-[16px] font-semibold text-ink ${
                pageOpen ? "bg-paper" : "bg-bond"
              }`}
              data-see-page="true"
            >
              See the page
            </button>
          ) : null}
        </figcaption>
      </figure>
      <InlinePageViewer viewerKey={id} />
    </>
  );
}

/* A list of chips, one per (document, page), or nothing when there are none. */
export function CitationChips({ citations, label = "Verified citations" }: { citations: ChipCitation[]; label?: string }) {
  if (!citations || citations.length === 0) return null;
  const groups = groupCitations(citations);
  return (
    <ul className="mt-4 flex flex-wrap items-start gap-x-3 gap-y-[18px]" aria-label={label}>
      {groups.map((g) => (
        <CitationChip key={`${g[0].doc_id}-${g[0].page}`} citations={g} />
      ))}
    </ul>
  );
}

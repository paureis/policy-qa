"use client";

import { useId, useState } from "react";

/* What a chip needs: a finding's Citation and the verdict's CitationRef both fit. */
export interface ChipCitation {
  doc_id: string;
  title: string | null;
  page: number;
  quote: string;
}

/*
  A verified citation: the document title and page on a button, the quoted
  excerpt inline underneath when tapped. Never a bare footnote number.
  aria-controls is set only while the excerpt is in the DOM.
*/
export function CitationChip({ citation }: { citation: ChipCitation }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const title = citation.title?.trim() || citation.doc_id;
  return (
    <li className="list-none">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex min-h-11 w-full items-start gap-2 rounded-sm border px-3 py-2 text-left text-[16px] leading-snug sm:w-auto ${
          open ? "border-ink bg-paper text-ink" : "border-ink bg-bond text-ink"
        }`}
      >
        <span aria-hidden="true" className="mt-[2px] shrink-0 font-bold">
          {open ? "–" : "+"}
        </span>
        <span>
          <span className="font-semibold">{title}</span>
          <span className="text-muted">, page {citation.page}</span>
        </span>
      </button>
      {open ? <QuoteFigure id={id} citation={citation} /> : null}
    </li>
  );
}

/* The quoted excerpt with its title and page as the caption. */
export function QuoteFigure({ id, citation }: { id: string; citation: ChipCitation }) {
  const title = citation.title?.trim() || citation.doc_id;
  return (
    <figure id={id} className="mt-2 mb-2 border-l-4 border-federal pl-4">
      <blockquote className="text-[18px] leading-relaxed lg:text-[17px]">“{citation.quote}”</blockquote>
      <figcaption className="mt-2 text-[15px] text-muted">
        {title}, page {citation.page}. This quote was found on the cited page.
      </figcaption>
    </figure>
  );
}

/* A list of chips, or nothing when there are none. */
export function CitationChips({ citations, label = "Verified citations" }: { citations: ChipCitation[]; label?: string }) {
  if (!citations || citations.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-col gap-2" aria-label={label}>
      {citations.map((c, i) => (
        <CitationChip key={`${c.doc_id}-${c.page}-${i}`} citation={c} />
      ))}
    </ul>
  );
}

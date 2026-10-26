"use client";

import { useId, useState } from "react";
import type { Citation } from "@/lib/case";

/*
  A verified citation: the document title and page on a button, the quoted
  excerpt inline underneath when tapped. Never a bare footnote number.
  aria-controls is set only while the excerpt is in the DOM.
*/
export function CitationChip({ citation }: { citation: Citation }) {
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
      {open ? (
        <figure id={id} className="mt-2 mb-2 border-l-4 border-federal pl-4">
          <blockquote className="text-[18px] leading-relaxed lg:text-[17px]">“{citation.quote}”</blockquote>
          <figcaption className="mt-2 text-[15px] text-muted">
            {title}, page {citation.page}. This quote was found on the cited page.
          </figcaption>
        </figure>
      ) : null}
    </li>
  );
}

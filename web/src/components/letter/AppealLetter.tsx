"use client";

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import {
  API_URL,
  INTAKE_MODE,
  letterPlainText,
  sentenceStruck,
  type CitationRef,
  type Letter,
  type LetterSentence,
  type Paragraph,
} from "@/lib/case";
import { InlineReferenceChip, QuoteFigure, groupCitations, shortDocName, type ChipCitation } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { MarginPageViewer, usePageViewer, viewerPanelId } from "@/components/investigation/PageViewer";

const ACTION =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm px-5 text-[18px] font-semibold sm:w-auto";

/* "Copied." stays for two seconds, then the status line clears. */
const COPIED_MS = 2000;

/*
  The appeal letter. On the phone and tablet: set on bond in a hairline frame,
  To, Re, then the paragraphs, every claim sentence with a small citation chip
  (title, page; the quote on toggle). At desktop width (desk): the Annotated
  Letter, a bond sheet with a 1 px ink edge on the darker desk, set like a
  printed letter (inside address, Re line, wide margins, a closing block),
  each claim sentence carrying a footnote number and each paragraph's notes
  in a margin column beside it (one grid row per paragraph, so notes align
  with no measuring script), the one postmark at the sheet's top right, Copy
  and Download in the margin. The sheet ends at the signature block; the
  checklist and the filing path are the page's next section. A sentence the
  verifier struck, or a claim it could not verify, is shown struck with
  "Could not verify", never hidden, and is left out of what is copied or
  downloaded.
*/
export function AppealLetter({
  letter,
  caseId,
  desk = false,
  stamp = null,
}: {
  letter: Letter;
  caseId: string;
  desk?: boolean;
  /* The postmark, set at the sheet's top right corner (desk only). */
  stamp?: ReactNode;
}) {
  const [copy, setCopy] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const paragraphs = letter.paragraphs ?? [];
  /* Desk only: the one margin note shown in full (quote and full title), by its footnote number. */
  const [openNote, setOpenNote] = useState<number | null>(null);
  const toggleNote = useCallback((n: number) => setOpenNote((o) => (o === n ? null : n)), []);
  const noteBase = useId();

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const onCopy = async () => {
    if (timer.current) clearTimeout(timer.current);
    setCopy("idle");
    const ok = await writeClipboard(letterPlainText(letter));
    setCopy(ok ? "copied" : "failed");
    if (ok) timer.current = setTimeout(() => setCopy("idle"), COPIED_MS);
  };

  const onDownload = () => {
    const blob = new Blob([letterPlainText(letter)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `appeal-letter-${caseId}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const actions = (
    <>
      <div className={desk ? "flex flex-wrap gap-3" : "mt-4 flex flex-col gap-3 sm:flex-row"}>
        <button type="button" onClick={onCopy} className={`${ACTION} bg-federal text-white`} data-copy="true">
          Copy the letter
        </button>
        {INTAKE_MODE === "live" ? (
          <a
            href={`${API_URL}/case/${encodeURIComponent(caseId)}/letter.txt`}
            download={`appeal-letter-${caseId}.txt`}
            className={`${ACTION} border border-ink bg-bond text-ink`}
            data-download="live"
          >
            Download as text
          </a>
        ) : (
          <button type="button" onClick={onDownload} className={`${ACTION} border border-ink bg-bond text-ink`} data-download="fixture">
            Download as text
          </button>
        )}
      </div>
      <p role="status" aria-live="polite" className="mt-2 min-h-7 text-[16px] font-semibold" data-copy-status={copy}>
        {copy === "copied" ? "Copied." : copy === "failed" ? "Could not copy. Select the letter text and copy it by hand." : ""}
      </p>
      <p className="mt-1 text-[16px] text-muted">
        Struck sentences are left out of the copy and the download. Each verified claim keeps a short citation in brackets.
      </p>
    </>
  );

  if (!desk) {
    return (
      <div className="mt-4">
        <LetterFrame to={letter.to} re={letter.re} paragraphs={paragraphs} label="Appeal letter" kind="final" />
        {actions}
      </div>
    );
  }

  /*
    Footnote numbers run through the letter, one per margin note: a paragraph's
    cited (document, page) pairs are merged into one note, so two sentences
    citing the same page carry the same number.
  */
  const noteGroups: ChipCitation[][][] = [];
  let numbered = 0;
  const firstNumber: number[] = [];
  for (const p of paragraphs) {
    const cited = (p.sentences ?? []).filter((s) => !sentenceStruck(s) && s.claim && s.citation).map((s) => s.citation as CitationRef);
    const groups = groupCitations(cited);
    firstNumber.push(numbered + 1);
    numbered += groups.length;
    noteGroups.push(groups);
  }

  return (
    <div className="mt-8 @container/letter" data-sheet="annotated">
      <div className="grid grid-cols-1 @min-[880px]/letter:desk-cols">
        <article aria-label="Appeal letter" className="col-span-full grid grid-cols-subgrid" data-letter="true">
          <div className={`${SHEET} relative border-t pt-16 pb-10`} data-sheet-head="true">
            {stamp ? (
              <div className="absolute top-6 right-6" data-sheet-stamp="true">
                {stamp}
              </div>
            ) : null}
            {/* Set like a letter: the addressee as the inside address, then the Re line; no rules. */}
            <dl className={`text-[17px] leading-snug ${stamp ? "pr-[150px]" : ""}`}>
              <div>
                <dt className="sr-only">To:</dt>
                <dd className="font-semibold" data-letter-to="true">
                  {letter.to}
                </dd>
              </div>
              <div className="mt-7 flex gap-2">
                <dt className="shrink-0 font-bold">Re:</dt>
                <dd>{letter.re}</dd>
              </div>
            </dl>
          </div>
          {paragraphs.map((p, i) => (
            <SheetParagraph
              key={i}
              sentences={p.sentences ?? []}
              index={i}
              groups={noteGroups[i]}
              first={firstNumber[i]}
              noteBase={noteBase}
              openNote={openNote}
              onToggleNote={toggleNote}
            />
          ))}
        </article>

        <div className="col-span-full grid grid-cols-subgrid" data-signoff="true">
          {/* Blank lines to fill in by hand on the printed letter, set as a letter's closing block; the instruction above says what goes there. */}
          <div className={`${SHEET} border-b pt-6 pb-16`} aria-hidden="true" data-signature="true">
            <div className="max-w-[300px] space-y-4">
              {SIGNATURE_LINES.map((label) => (
                <div key={label}>
                  <div className={`${label === "Signature" ? "h-12" : "h-8"} border-b border-ink`} />
                  <p className="mt-1 text-[14px] text-muted">{label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="pt-6 pb-4 @min-[880px]/letter:col-start-2 @min-[880px]/letter:self-start @min-[880px]/letter:pb-0" data-letter-actions="true">
            {actions}
          </div>
        </div>
      </div>
    </div>
  );
}

/* A letter's closing order: the signature, the printed name, the member ID, the date. */
const SIGNATURE_LINES = ["Signature", "Name", "Member ID", "Date"] as const;

/*
  A cell of the bond sheet: column one of the letter grid. The sheet's 1 px
  ink edge (no shadow, no radius) runs down its sides; the head cell closes it
  at the top and the signature cell at the bottom. Inner margins like a
  printed letter: 48 px at 1024, 72 px from 1280.
*/
const SHEET = "border-x border-ink bg-bond px-12 xl:px-[72px] @min-[880px]/letter:col-start-1";

/*
  One paragraph of the sheet and, right after it in the DOM, its margin notes:
  the same grid row, so each note's top sits on the paragraph's first line.
  Each claim sentence ends in its footnote number; the number opens the note
  with the same number. Below the container's two-column width the notes
  stack under the paragraph on the sheet itself.
*/
function SheetParagraph({
  sentences,
  index,
  groups,
  first,
  noteBase,
  openNote,
  onToggleNote,
}: {
  sentences: LetterSentence[];
  index: number;
  groups: ChipCitation[][];
  /* The footnote number of this paragraph's first note. */
  first: number;
  noteBase: string;
  openNote: number | null;
  onToggleNote: (n: number) => void;
}) {
  const numberOf = (c: CitationRef): number | null => {
    const g = groups.findIndex((x) => x[0].doc_id === c.doc_id && x[0].page === c.page);
    return g < 0 ? null : first + g;
  };
  return (
    <>
      <div className={`${SHEET} pb-7`} data-paragraph={index}>
        <p className="text-[18px] leading-[1.6]">
          {sentences.map((s, i) => {
            const struck = sentenceStruck(s);
            const n = !struck && s.claim && s.citation ? numberOf(s.citation) : null;
            return (
              <span key={i} data-sentence={struck ? "struck" : s.claim ? "claim" : "plain"}>
                {i > 0 ? " " : ""}
                {struck ? (
                  <>
                    <s className="decoration-ink decoration-2">{s.text}</s> <CouldNotVerifyTag inline />
                  </>
                ) : (
                  s.text
                )}
                {n !== null ? (
                  <FootnoteRef n={n} open={openNote === n} controls={noteRegionId(noteBase, n)} onToggle={() => onToggleNote(n)} />
                ) : null}
              </span>
            );
          })}
        </p>
      </div>
      {groups.length > 0 ? (
        <ul
          aria-label={`Citations for paragraph ${index + 1}`}
          className="border-x border-ink bg-bond px-12 pb-6 @min-[880px]/letter:col-start-2 @min-[880px]/letter:self-start @min-[880px]/letter:border-0 @min-[880px]/letter:bg-transparent @min-[880px]/letter:px-0 @min-[880px]/letter:pt-1 @min-[880px]/letter:pb-7"
          data-margin={index}
        >
          {groups.map((g, gi) => (
            <MarginNote
              key={`${g[0].doc_id}-${g[0].page}`}
              n={first + gi}
              citations={g}
              noteBase={noteBase}
              open={openNote === first + gi}
              onToggle={() => onToggleNote(first + gi)}
            />
          ))}
        </ul>
      ) : null}
    </>
  );
}

function noteRegionId(base: string, n: number): string {
  return `${base}-note-${n}`;
}

/*
  A footnote number after a claim sentence: small, tabular, ink, raised like a
  superscript. Its target is 44 px square by padding, with negative margins so
  the line keeps its rhythm. It opens the margin note with the same number
  (the full quote and the document's full title).
*/
function FootnoteRef({ n, open, controls, onToggle }: { n: number; open: boolean; controls: string; onToggle: () => void }) {
  return (
    <button
      type="button"
      aria-label={`citation ${n}`}
      aria-expanded={open}
      aria-controls={controls}
      onClick={onToggle}
      className={`relative -top-[0.55em] -mx-4 -my-3.5 inline-flex min-w-11 justify-center rounded-sm py-3.5 align-baseline text-[13px] leading-4 font-semibold text-ink tabular-nums hover:underline ${
        open ? "underline decoration-2 underline-offset-2" : ""
      }`}
      data-footnote={n}
    >
      {n}
    </button>
  );
}

/* Reference-style links in a note: small, underlined, a 44 px tall target. */
const NOTE_LINK =
  "-ml-1 inline-flex min-h-11 items-center rounded-sm px-1 text-[15px] font-semibold text-ink underline decoration-1 underline-offset-4";

/*
  A margin note, set as a footnote: its number, the short document name and
  page folio, the quote clipped to two lines; "more" shows the whole quote
  and the document's full title. One small link per note, "page 5", opens the
  cited page in place (the page image with the gold box and the vision line);
  its name carries the full title. One page is open at a time; Escape closes
  it and returns focus to the link.
*/
function MarginNote({
  n,
  citations,
  noteBase,
  open,
  onToggle,
}: {
  n: number;
  citations: ChipCitation[];
  noteBase: string;
  open: boolean;
  onToggle: () => void;
}) {
  const viewer = usePageViewer();
  const closeIf = viewer?.actions.closeIf;
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
    <li className="relative mt-6 pl-8 first:mt-0" data-note={n} data-note-open={open ? "true" : "false"}>
      <p className="text-[15px] leading-6 tabular-nums">
        <span className="absolute left-0 font-semibold" data-note-number={n}>
          {n}
          <span className="sr-only">. </span>
        </span>
        <span className="font-semibold">{shortDocName(first)}</span>
        <span aria-hidden="true" className="mx-1.5 text-muted">
          ·
        </span>
        <span className="whitespace-nowrap">
          <span aria-hidden="true">p.&nbsp;</span>
          <span className="sr-only">page </span>
          {first.page}
        </span>
      </p>
      <div id={region} data-note-region="true">
        {open ? (
          <p className="mt-0.5 text-[15px] leading-6 text-muted" data-note-title="true">
            {title}, page {first.page}
          </p>
        ) : null}
        {citations.map((c, k) => (
          <blockquote
            key={k}
            className={`mt-1 text-[15px] leading-[1.55] text-ink ${open ? "" : "line-clamp-2"}`}
            data-note-quote={open ? "full" : "clipped"}
          >
            “{c.quote}”
          </blockquote>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-x-5">
        {viewer ? (
          <button
            type="button"
            aria-expanded={pageOpen}
            aria-controls={pageOpen ? viewerPanelId(viewKey) : undefined}
            aria-label={`page ${first.page} of ${title}`}
            onClick={(e) => viewer.actions.toggle(viewKey, first, { placement: "margin", returnTo: e.currentTarget })}
            className={`${NOTE_LINK} tabular-nums ${pageOpen ? "bg-hairline" : ""}`}
            data-note-page="true"
          >
            page {first.page}
          </button>
        ) : null}
        <button type="button" aria-expanded={open} aria-controls={region} onClick={onToggle} className={NOTE_LINK} data-note-more="true">
          {open ? "less" : "more"}
          <span className="sr-only">, citation {n}</span>
        </button>
      </div>
      <MarginPageViewer viewerKey={viewKey} />
    </li>
  );
}

/*
  The letter block: bond in a hairline frame, To and Re, then the paragraphs.
  The final letter on the phone and the read-only first draft share it, so
  they read alike.
*/
export function LetterFrame({
  to,
  re,
  paragraphs,
  label,
  kind,
  id,
}: {
  to: string;
  re: string;
  paragraphs: Paragraph[];
  label: string;
  kind: "final" | "draft";
  id?: string;
}) {
  return (
    <article
      id={id}
      aria-label={label}
      className="border border-hairline bg-bond px-4 py-5 shadow-[0_1px_0_var(--hairline)] sm:px-7 sm:py-7"
      data-letter={kind === "final" ? "true" : undefined}
      data-draft={kind === "draft" ? "true" : undefined}
    >
      <dl className="space-y-1 border-b border-hairline pb-4 text-[17px] leading-snug">
        <div className="flex gap-2">
          <dt className="shrink-0 font-bold">To:</dt>
          <dd>{to}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="shrink-0 font-bold">Re:</dt>
          <dd>{re}</dd>
        </div>
      </dl>
      <div className="mt-4 space-y-5">
        {paragraphs.map((p, i) => (
          <LetterParagraph key={i} sentences={p.sentences ?? []} index={i} />
        ))}
      </div>
    </article>
  );
}

function LetterParagraph({ sentences, index }: { sentences: LetterSentence[]; index: number }) {
  const [open, setOpen] = useState<Set<number>>(() => new Set());
  const base = useId();
  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div data-paragraph={index}>
      <p className="text-[18px] leading-[1.9] lg:text-[17px]">
        {sentences.map((s, i) => {
          const struck = sentenceStruck(s);
          const chip = !struck && s.claim && s.citation ? s.citation : null;
          return (
            <span key={i} data-sentence={struck ? "struck" : s.claim ? "claim" : "plain"}>
              {i > 0 ? " " : ""}
              {struck ? (
                <>
                  <s className="decoration-ink decoration-2">{s.text}</s> <CouldNotVerifyTag inline />
                </>
              ) : (
                s.text
              )}
              {chip ? (
                <>
                  {" "}
                  <InlineChip citation={chip} open={open.has(i)} controls={`${base}-q${i}`} onToggle={() => toggle(i)} />
                </>
              ) : null}
            </span>
          );
        })}
      </p>
      {sentences.map((s, i) =>
        open.has(i) && s.citation && !sentenceStruck(s) ? <QuoteFigure key={i} id={`${base}-q${i}`} citation={s.citation} /> : null,
      )}
    </div>
  );
}

/*
  A small reference inside a line of text: a short document name and page on
  a paper tint, no box, so the line keeps its rhythm; a transparent extension
  makes the hit area 44px tall.
*/
export function InlineChip(props: { citation: CitationRef; open: boolean; controls: string; onToggle: () => void }) {
  return <InlineReferenceChip {...props} />;
}

async function writeClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall back below */
  }
  try {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  } catch {
    return false;
  }
}

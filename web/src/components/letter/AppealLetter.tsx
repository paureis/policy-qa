"use client";

import { Fragment, useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import {
  API_URL,
  INTAKE_MODE,
  citationLabel,
  isFixtureCase,
  letterPlainText,
  sentenceStruck,
  type CitationRef,
  type Letter,
  type LetterSentence,
  type Paragraph,
} from "@/lib/case";
import { InlineReferenceChip, QuoteFigure, groupCitations, pageFolio, shortDocName } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { usePageViewer } from "@/components/investigation/PageViewer";
import { FootnoteRef, MARGIN_BLOCK, MarginNote, noteRegionId, useOverlayPlacement, type NoteGroup } from "./Sidenotes";

const ACTION =
  "inline-flex min-h-12 w-full items-center justify-center px-5 text-[18px] font-semibold sm:w-auto";

/* "Copied." stays for two seconds, then the status line clears. */
const COPIED_MS = 2000;

/*
  The sheet at desktop is US Letter: 620 px wide at 1,280 (8.5 in), so a page
  is 802 px tall (11 in), and it scales in proportion at 1,024. Inner margins
  72 px on every side (1 in), a 24 px strip of desk between pages, the folio
  in the bottom margin.
*/
const PAGE_RATIO = 802 / 620;
const PAGE_GAP = 24;
const MARGIN = 72;
/* Space between two margin notes, and between a note and the next paragraph's notes. */
const NOTE_GAP = 20;

/*
  The appeal letter. On the phone and tablet: set on bond in a hairline frame,
  To, Re, then the paragraphs, every claim sentence with a small citation chip
  (title, page; the quote on toggle). At desktop width (desk): the Annotated
  Letter, a real document: US Letter pages of bond with a 1 px ink edge on the
  darker desk, each with its folio ("Page 1 of 2"); a date line, the inside
  address and the Re line; the paragraphs at 18 px; the closing block with the
  fields to fill in by hand in gold wash ("Fill in", gold being reserved for
  what the person must check or complete). A paragraph never splits across a
  page; it moves to the next one.

  Beside the sheet, the margin: next to the sheet head the deadline, Copy the
  letter and Download as text; next to each paragraph its notes, set as
  sidenotes. A note starts at its paragraph's first line, clears the note
  above it, and stacks downward past its paragraph when the notes are taller
  than the paragraph; the paragraphs never stretch and no blank sheet opens.
  Each note is in the DOM right after its paragraph. A claim sentence ends in
  its footnote number; the number opens the expanded quote over the margin
  below the note, and "page N" opens the page image there; one thing open at
  a time, Escape closes it and returns focus. A sentence the verifier struck,
  or a claim it could not verify, is shown struck with "Could not verify",
  never hidden, and is left out of what is copied, downloaded, or printed.

  Printing the page prints the sheet alone (globals.css, data-print-sheet).
*/
export function AppealLetter({
  letter,
  caseId,
  desk = false,
  today = null,
  deadlineLine = null,
}: {
  letter: Letter;
  caseId: string;
  desk?: boolean;
  /* The date line at the sheet's head (desk only). */
  today?: Date | null;
  /* "Appeal by Dec 6, 2026, 41 days left", in the margin beside the sheet head (desk only). */
  deadlineLine?: string | null;
}) {
  const [copy, setCopy] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const paragraphs = letter.paragraphs ?? [];

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

  const liveDownload = INTAKE_MODE === "live" && !isFixtureCase(caseId);
  const actions = (
    <>
      <div className={desk ? "flex flex-wrap gap-3" : "mt-4 flex flex-col gap-3 sm:flex-row"}>
        <button type="button" onClick={onCopy} className={`${ACTION} bg-ink text-bond`} data-copy="true">
          Copy the letter
        </button>
        {liveDownload ? (
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
      <p className={`mt-1 text-[16px] text-muted ${desk ? "lg:text-[15px]" : ""}`}>
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

  return <Sheet letter={letter} paragraphs={paragraphs} actions={actions} today={today} deadlineLine={deadlineLine} />;
}

/*
  Footnote numbers run through the letter, one per margin note: a paragraph's
  verified (document, page) pairs merge into one note, so two sentences citing
  the same page carry the same number. A struck sentence that still names a
  citation gets its own note, marked "Could not verify".
*/
function numberNotes(paragraphs: Paragraph[]): NoteGroup[][] {
  let next = 1;
  return paragraphs.map((p) => {
    const sentences = p.sentences ?? [];
    const verified = groupCitations(sentences.filter((s) => !sentenceStruck(s) && s.claim && s.citation).map((s) => s.citation as CitationRef));
    const groups: NoteGroup[] = verified.map((citations) => ({ n: next++, citations, struck: false }));
    for (const s of sentences) {
      if (sentenceStruck(s) && s.citation) groups.push({ n: next++, citations: [s.citation], struck: true });
    }
    return groups;
  });
}

function noteFor(groups: NoteGroup[], s: LetterSentence): NoteGroup | null {
  if (!s.citation) return null;
  const struck = sentenceStruck(s);
  if (struck) return groups.find((g) => g.struck && g.citations[0] === s.citation) ?? null;
  if (!s.claim) return null;
  const c = s.citation;
  return groups.find((g) => !g.struck && g.citations[0].doc_id === c.doc_id && g.citations[0].page === c.page) ?? null;
}

function Sheet({
  letter,
  paragraphs,
  actions,
  today,
  deadlineLine,
}: {
  letter: Letter;
  paragraphs: Paragraph[];
  actions: ReactNode;
  today: Date | null;
  deadlineLine: string | null;
}) {
  const noteBase = useId();
  const groups = numberNotes(paragraphs);
  /* The one expanded quote, by footnote number. Pages open through the viewer provider; one of the two at a time. */
  const [openNote, setOpenNote] = useState<number | null>(null);
  const viewer = usePageViewer();
  const viewerOpenKey = viewer?.state.open?.placement === "margin" ? viewer.state.open.key : null;
  const closeIf = viewer?.actions.closeIf;
  const frameRef = useRef<HTMLDivElement>(null);
  const articleRef = useRef<HTMLElement>(null);
  const [pages, setPages] = useState<{ n: number; height: number }>({ n: 1, height: 802 });
  /* The lowest point of the margin notes and of an open overlay, in the article's coordinates; the frame grows to the larger. */
  const notesBottom = useRef(0);
  const overlayBottom = useRef(0);
  const fitFrame = useCallback(() => {
    const article = articleRef.current;
    const frame = frameRef.current;
    if (!article || !frame) return;
    const need = Math.max(notesBottom.current, overlayBottom.current);
    frame.style.minHeight = need > article.offsetHeight ? `${need}px` : "";
  }, []);

  const toggleNote = useCallback(
    (n: number) => {
      if (viewerOpenKey && closeIf) closeIf(viewerOpenKey);
      setOpenNote((o) => (o === n ? null : n));
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
      const n = openNote;
      setOpenNote(null);
      frameRef.current?.querySelector<HTMLElement>(`[data-footnote="${n}"]`)?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openNote]);

  /*
    Pagination and the sidenotes, measured once per layout change: every
    paragraph that would cross a page's bottom margin moves to the next page
    (a spacer before it takes up the rest of the page and the desk strip),
    then each margin block is placed at its anchor's top or under the block
    above it, whichever is lower. Only spacer heights and note offsets are
    written, so nothing re-renders but the page count.
  */
  useLayoutEffect(() => {
    const article = articleRef.current;
    const frame = frameRef.current;
    if (!article || !frame) return;
    let raf = 0;
    const layout = () => {
      const width = article.offsetWidth;
      if (width === 0) return;
      const pageH = Math.round(width * PAGE_RATIO);
      const pitch = pageH + PAGE_GAP;
      const spacers = Array.from(article.querySelectorAll<HTMLElement>("[data-page-spacer]"));
      for (const s of spacers) s.style.height = "0px";
      article.style.minHeight = "";
      let bottom = MARGIN;
      for (const s of spacers) {
        const block = s.nextElementSibling as HTMLElement | null;
        if (!block) continue;
        const top = block.offsetTop;
        const h = block.offsetHeight;
        const k = Math.floor(top / pitch);
        const limit = k * pitch + pageH - MARGIN;
        if ((top + h > limit && h <= pageH - 2 * MARGIN) || top > limit) {
          s.style.height = `${(k + 1) * pitch + MARGIN - top}px`;
        }
        bottom = block.offsetTop + h;
      }
      const n = Math.max(1, Math.floor((bottom + MARGIN - 1) / pitch) + 1);
      article.style.minHeight = `${n * pageH + (n - 1) * PAGE_GAP}px`;

      let prev = -Infinity;
      for (const m of Array.from(article.querySelectorAll<HTMLElement>("[data-margin-anchor]"))) {
        const anchor = article.querySelector<HTMLElement>(`[data-block="${m.dataset.marginAnchor}"]`);
        if (!anchor) continue;
        const top = Math.max(anchor.offsetTop, prev + NOTE_GAP);
        m.style.top = `${top}px`;
        prev = top + m.offsetHeight;
      }
      notesBottom.current = prev;
      fitFrame();
      setPages((p) => (p.n === n && p.height === pageH ? p : { n, height: pageH }));
    };
    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(layout);
    };
    layout();
    const ro = new ResizeObserver(schedule);
    ro.observe(article);
    for (const el of Array.from(article.querySelectorAll<HTMLElement>("[data-block], [data-margin-anchor]"))) ro.observe(el);
    void document.fonts?.ready.then(schedule);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [paragraphs, fitFrame]);

  /* An open overlay hangs below its note, or opens upward when it would run past the last page (Sidenotes.tsx). */
  useOverlayPlacement(articleRef, overlayBottom, fitFrame, openNote, viewerOpenKey);

  const dateLine = today ? today.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : null;

  return (
    <div className="mt-8" data-sheet="annotated">
      <div ref={frameRef} className="relative" data-letter-frame="true">
        <article
          ref={articleRef}
          aria-label="Appeal letter"
          /* z-10: the letter, with its margin overlays, stacks above the sections after it. */
          className="relative isolate z-10 w-[calc((100%-48px)*620/1040)] px-[72px] pt-[72px]"
          data-letter="true"
          data-print-sheet="true"
          data-pages={pages.n}
        >
          {/* The pages, behind the text: bond with a 1 px ink edge, the desk between them, the folio in the bottom margin. */}
          <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 -z-10" data-print-hide="true" data-sheet-pages="true">
            {Array.from({ length: pages.n }, (_, k) => (
              <div
                key={k}
                className="absolute inset-x-0 border border-ink bg-bond"
                style={{ top: k * (pages.height + PAGE_GAP), height: pages.height }}
                data-sheet-page={k + 1}
              >
                <p className="absolute right-[72px] bottom-8 text-[14px] text-muted tabular-nums">
                  Page {k + 1} of {pages.n}
                </p>
              </div>
            ))}
          </div>

          <div data-page-spacer="true" />
          <div className="mb-7" data-block="head" data-sheet-head="true">
            {dateLine ? (
              <p className="text-[17px] tabular-nums" data-letter-date="true">
                {dateLine}
              </p>
            ) : null}
            {/* Set like a letter: the addressee as the inside address, then the Re line; no rules. */}
            <dl className={`text-[17px] leading-snug ${dateLine ? "mt-7" : ""}`}>
              <div>
                <dt className="sr-only">To:</dt>
                <dd className="font-semibold" data-letter-to="true">
                  {letter.to}
                </dd>
              </div>
              <div className="mt-6 flex gap-2">
                <dt className="shrink-0 font-semibold">Re:</dt>
                <dd>{letter.re}</dd>
              </div>
            </dl>
          </div>
          <div className={MARGIN_BLOCK} data-margin-anchor="head" data-print-hide="true" data-letter-actions="true">
            {deadlineLine ? (
              <p className="mb-4 text-[17px] leading-snug font-semibold tabular-nums" data-letter-deadline="true">
                {deadlineLine}
              </p>
            ) : null}
            {actions}
          </div>

          {paragraphs.map((p, i) => (
            <Fragment key={i}>
              <div data-page-spacer="true" />
              <SheetParagraph
                sentences={p.sentences ?? []}
                index={i}
                groups={groups[i]}
                noteBase={noteBase}
                openNote={openNote}
                onToggleNote={toggleNote}
                onOpenPage={closeQuote}
              />
            </Fragment>
          ))}

          <div data-page-spacer="true" />
          <SignOff askName={!paragraphs.some((p) => (p.sentences ?? []).some((s) => /\[[^\]\n]*name[^\]\n]*\]/i.test(s.text)))} />
        </article>
      </div>
    </div>
  );
}

/*
  The closing block: the fields a letter is signed with, each a gold-wash
  field marked "Fill in", so they cannot be mistaken for text the service
  wrote. In print they are plain ruled lines. The name is asked once: when
  the sign-off already carries a name placeholder ("[Your name]"), the block
  drops its Name field.
*/
function SignOff({ askName }: { askName: boolean }) {
  const SIGNATURE_FIELDS = askName ? ["Signature", "Name", "Member ID", "Date"] : ["Signature", "Member ID", "Date"];
  return (
    <div className="pt-3" data-block="signoff" data-signature="true">
      <ul className="grid grid-cols-2 items-end gap-x-8 gap-y-5">
        {SIGNATURE_FIELDS.map((label) => (
          <li key={label} className={!askName && label === "Signature" ? "col-span-2 max-w-[calc(50%-16px)]" : ""}>
            <p className="text-[14px] leading-5 text-muted">{label}</p>
            <span
              className={`mt-1 flex ${label === "Signature" ? "h-12" : "h-9"} items-end border-b-2 border-gold bg-gold-wash px-2 pb-1 text-[14px] leading-5 font-semibold text-ink print:border-ink print:bg-transparent`}
              data-fill-in={label}
            >
              <span className="print:invisible">Fill in</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/*
  A bracketed placeholder the letter leaves for the person ("[Your name]")
  becomes a gold-wash field marked "Fill in"; in print it is the bracket text
  again, so nothing prints as a label.
*/
const PLACEHOLDER = /\[([^\]\n]{1,40})\]/g;

function withFields(text: string): ReactNode {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(PLACEHOLDER)) {
    const at = m.index ?? 0;
    if (at > last) parts.push(text.slice(last, at));
    parts.push(
      <span key={at} className="box-decoration-clone border-b-2 border-gold bg-gold-wash px-1 print:border-0 print:bg-transparent print:px-0" data-fill-in={m[1]}>
        <span className="mr-1.5 text-[14px] font-semibold print:hidden">Fill in</span>
        <span className="sr-only">: </span>
        <span className="print:hidden">{m[1]}</span>
        <span className="hidden print:inline">[{m[1]}]</span>
      </span>,
    );
    last = at + m[0].length;
  }
  if (parts.length === 0) return text;
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

/*
  One paragraph of the sheet and, right after it in the DOM, its margin notes
  (absolute, placed by the sheet's layout). Each claim sentence ends in its
  footnote number, which opens the note's expanded quote.
*/
function SheetParagraph({
  sentences,
  index,
  groups,
  noteBase,
  openNote,
  onToggleNote,
  onOpenPage,
}: {
  sentences: LetterSentence[];
  index: number;
  groups: NoteGroup[];
  noteBase: string;
  openNote: number | null;
  onToggleNote: (n: number) => void;
  onOpenPage: () => void;
}) {
  return (
    <>
      <div className="mb-5" data-block={`p${index}`} data-paragraph={index}>
        <p className="text-[18px] leading-[1.6]">
          {sentences.map((s, i) => {
            const struck = sentenceStruck(s);
            const note = noteFor(groups, s);
            return (
              <span key={i} data-sentence={struck ? "struck" : s.claim ? "claim" : "plain"}>
                {i > 0 ? " " : ""}
                {struck ? (
                  <>
                    <s className="decoration-ink decoration-2">{s.text}</s> <CouldNotVerifyTag inline />
                  </>
                ) : (
                  withFields(s.text)
                )}
                {note ? (
                  <FootnoteRef
                    n={note.n}
                    label={`${shortDocName(note.citations[0])}, ${pageFolio(note.citations[0])}`}
                    open={openNote === note.n}
                    controls={noteRegionId(noteBase, note.n)}
                    onToggle={() => onToggleNote(note.n)}
                  />
                ) : null}
                {!struck && s.claim && s.verified && s.citation ? (
                  <span className="hidden print:inline">
                    {" "}
                    [cite: {citationLabel(s.citation)}, p. {s.citation.page}]
                  </span>
                ) : null}
              </span>
            );
          })}
        </p>
      </div>
      {groups.length > 0 ? (
        <ul aria-label={`Citations for paragraph ${index + 1}`} className={`${MARGIN_BLOCK} space-y-5`} data-margin-anchor={`p${index}`} data-margin={index} data-print-hide="true">
          {groups.map((g) => (
            <MarginNote
              key={g.n}
              group={g}
              noteBase={noteBase}
              open={openNote === g.n}
              onClose={() => onToggleNote(g.n)}
              onOpenPage={onOpenPage}
            />
          ))}
        </ul>
      ) : null}
    </>
  );
}

/*
  The letter block: a bond sheet with a 1 px ink edge, To and Re, then the paragraphs.
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
      className="border border-ink bg-bond px-4 py-5 sm:px-7 sm:py-7"
      data-letter={kind === "final" ? "true" : undefined}
      data-draft={kind === "draft" ? "true" : undefined}
      /* Printing from a narrow window (or the browser's print layout, narrower than 1,024 px) prints this letter alone too. */
      data-print-sheet={kind === "final" ? "true" : undefined}
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
                  <span className="print:hidden">
                    <InlineChip citation={chip} open={open.has(i)} controls={`${base}-q${i}`} onToggle={() => toggle(i)} />
                  </span>
                  <span className="hidden print:inline">
                    [cite: {citationLabel(chip)}, p. {chip.page}]
                  </span>
                </>
              ) : null}
            </span>
          );
        })}
      </p>
      {sentences.map((s, i) =>
        open.has(i) && s.citation && !sentenceStruck(s) ? (
          <div key={i} className="print:hidden">
            <QuoteFigure id={`${base}-q${i}`} citation={s.citation} />
          </div>
        ) : null,
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

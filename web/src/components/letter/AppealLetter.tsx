"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
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
  Letter, a bond sheet on the paper desk with each paragraph's cited quotes in
  a margin column beside it (one grid row per paragraph, so notes align with
  no measuring script), the one postmark at the sheet's top right, signature
  lines, Copy and Download in the margin, and the footer register (the
  evidence checklist and the filing path). A sentence the verifier struck, or
  a claim it could not verify, is shown struck with "Could not verify", never
  hidden, and is left out of what is copied or downloaded.
*/
export function AppealLetter({
  letter,
  caseId,
  desk = false,
  stamp = null,
  register = null,
}: {
  letter: Letter;
  caseId: string;
  desk?: boolean;
  /* The postmark, set at the sheet's top right corner (desk only). */
  stamp?: ReactNode;
  /* The sheet's footer register: checklist and filing path (desk only). */
  register?: ReactNode;
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

  return (
    <div className="mt-6 @container/letter" data-sheet="annotated">
      <div className="grid grid-cols-1 @min-[880px]/letter:desk-cols">
        <article aria-label="Appeal letter" className="col-span-full grid grid-cols-subgrid" data-letter="true">
          <div className={`${SHEET} relative border-t pt-9 pb-7`} data-sheet-head="true">
            {stamp ? (
              <div className="absolute top-5 right-5" data-sheet-stamp="true">
                {stamp}
              </div>
            ) : null}
            <dl className={`space-y-1 border-b border-hairline pb-5 text-[17px] leading-snug ${stamp ? "pr-[150px]" : ""}`}>
              <div className="flex gap-2">
                <dt className="shrink-0 font-bold">To:</dt>
                <dd>{letter.to}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="shrink-0 font-bold">Re:</dt>
                <dd>{letter.re}</dd>
              </div>
            </dl>
          </div>
          {paragraphs.map((p, i) => (
            <SheetParagraph key={i} sentences={p.sentences ?? []} index={i} />
          ))}
        </article>

        <div className="col-span-full grid grid-cols-subgrid" data-signoff="true">
          {/* Blank lines to fill in by hand on the printed letter; the instruction above says what goes there. */}
          <div className={`${SHEET} pb-9`} aria-hidden="true" data-signature="true">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5 border-t border-hairline pt-6">
              {SIGNATURE_LINES.map((label) => (
                <div key={label}>
                  <div className="h-9 border-b border-ink" />
                  <p className="mt-1 text-[14px] text-muted">{label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="pt-6 pb-4 @min-[880px]/letter:col-start-2 @min-[880px]/letter:pt-0" data-letter-actions="true">
            {actions}
          </div>
        </div>

        {register ? (
          <div className="col-span-full grid grid-cols-subgrid" data-register="true">
            <div className={`${SHEET} border-t-[3px] border-b border-double border-t-edge pt-8 pb-10`}>{register}</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

const SIGNATURE_LINES = ["Signature", "Date", "Name", "Member ID"] as const;

/* A cell of the bond sheet: column one of the letter grid, hairline sides, the letter's margins inside. */
const SHEET = "border-x border-hairline bg-bond px-8 xl:px-14 @min-[880px]/letter:col-start-1";

/*
  One paragraph of the sheet and, right after it in the DOM, its margin notes:
  the same grid row, so each note's top sits on the paragraph's first line.
  Below the container's two-column width the notes stack under the paragraph
  on the sheet itself.
*/
function SheetParagraph({ sentences, index }: { sentences: LetterSentence[]; index: number }) {
  const base = useId();
  const cited = sentences.filter((s) => !sentenceStruck(s) && s.claim && s.citation).map((s) => s.citation as CitationRef);
  const groups = groupCitations(cited);
  return (
    <>
      <div className={`${SHEET} pb-7`} data-paragraph={index}>
        <p className="text-[18px] leading-[1.6]">
          {sentences.map((s, i) => {
            const struck = sentenceStruck(s);
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
              </span>
            );
          })}
        </p>
      </div>
      {groups.length > 0 ? (
        <ul
          aria-label={`Citations for paragraph ${index + 1}`}
          className="border-x border-hairline bg-bond px-8 pb-6 @min-[880px]/letter:col-start-2 @min-[880px]/letter:self-start @min-[880px]/letter:border-0 @min-[880px]/letter:bg-transparent @min-[880px]/letter:px-0 @min-[880px]/letter:pb-7"
          data-margin={index}
        >
          {groups.map((g, gi) => (
            <MarginNote key={`${g[0].doc_id}-${g[0].page}`} citations={g} baseKey={`${base}-n${gi}`} />
          ))}
        </ul>
      ) : null}
    </>
  );
}

/*
  A margin note: the short document name and page folio, the quote, and "See
  the page", which expands the note in place to the page image with the gold
  box and the vision line. One note is expanded at a time; Escape collapses it
  and returns focus to this button.
*/
function MarginNote({ citations, baseKey }: { citations: ChipCitation[]; baseKey: string }) {
  const viewer = usePageViewer();
  const closeIf = viewer?.actions.closeIf;
  const first = citations[0];
  const keys = citations.map((_, k) => `${baseKey}-${k}`);
  const joined = keys.join(" ");
  useEffect(() => {
    if (!closeIf) return;
    return () => joined.split(" ").forEach((k) => closeIf(k));
  }, [closeIf, joined]);
  return (
    <li className="mt-5 border-t border-hairline pt-4 first:mt-0 first:border-t-0 first:pt-0" data-note="true">
      <p className="text-[15px] leading-6 tabular-nums" title={first.title?.trim() || undefined}>
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
      {citations.map((c, k) => {
        const key = keys[k];
        const open = viewer?.state.open?.key === key;
        return (
          <div key={key}>
            <blockquote className="mt-1 text-[15px] leading-[1.55] text-ink">“{c.quote}”</blockquote>
            {viewer ? (
              <button
                type="button"
                aria-expanded={open}
                aria-controls={open ? viewerPanelId(key) : undefined}
                onClick={(e) => viewer.actions.toggle(key, c, { placement: "margin", returnTo: e.currentTarget })}
                className={`mt-1 -ml-2 inline-flex min-h-11 items-center rounded-sm px-2 text-[15px] font-semibold text-ink underline decoration-1 underline-offset-4 ${
                  open ? "bg-hairline" : ""
                }`}
                data-note-page="true"
              >
                See the page
              </button>
            ) : null}
            <MarginPageViewer viewerKey={key} />
          </div>
        );
      })}
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

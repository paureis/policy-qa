"use client";

import { useId, useState } from "react";
import {
  API_URL,
  COULD_NOT_VERIFY_LABEL,
  INTAKE_MODE,
  citationLabel,
  letterPlainText,
  sentenceStruck,
  type CitationRef,
  type Letter,
  type LetterSentence,
} from "@/lib/case";
import { QuoteFigure } from "@/components/investigation/CitationChip";

const ACTION =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm px-5 text-[18px] font-semibold sm:w-auto";

/*
  The appeal letter, set on bond in a hairline frame: To, Re, then the
  paragraphs. Every claim sentence carries a small citation chip (title,
  page; the quote on toggle). A sentence the verifier struck, or a claim it
  could not verify, is shown struck with "Could not verify", never hidden,
  and is left out of what is copied or downloaded.
*/
export function AppealLetter({ letter, caseId }: { letter: Letter; caseId: string }) {
  const [copy, setCopy] = useState<"idle" | "copied" | "failed">("idle");
  const paragraphs = letter.paragraphs ?? [];

  const onCopy = async () => {
    setCopy("idle");
    const ok = await writeClipboard(letterPlainText(letter));
    setCopy(ok ? "copied" : "failed");
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

  return (
    <div className="mt-4">
      <article
        aria-label="Appeal letter"
        className="border border-hairline bg-bond px-4 py-5 shadow-[0_1px_0_var(--hairline)] sm:px-7 sm:py-7"
        data-letter="true"
      >
        <dl className="space-y-1 border-b border-hairline pb-4 text-[17px] leading-snug">
          <div className="flex gap-2">
            <dt className="shrink-0 font-bold">To:</dt>
            <dd>{letter.to}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="shrink-0 font-bold">Re:</dt>
            <dd>{letter.re}</dd>
          </div>
        </dl>
        <div className="mt-4 space-y-5">
          {paragraphs.map((p, i) => (
            <LetterParagraph key={i} sentences={p.sentences ?? []} index={i} />
          ))}
        </div>
      </article>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
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
    </div>
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
                  <s className="decoration-ink decoration-2">{s.text}</s>{" "}
                  <span className="inline-block border border-ink px-1.5 align-baseline text-[13px] leading-5 font-bold tracking-wide text-ink uppercase">
                    {COULD_NOT_VERIFY_LABEL}
                  </span>
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
  A small chip inside a line of text. The visible pill is short so the line
  keeps its rhythm; a transparent extension makes the hit area 44px tall.
*/
function InlineChip({
  citation,
  open,
  controls,
  onToggle,
}: {
  citation: CitationRef;
  open: boolean;
  controls: string;
  onToggle: () => void;
}) {
  const title = citationLabel(citation);
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={open ? controls : undefined}
      onClick={onToggle}
      className={`relative inline-flex max-w-full items-baseline rounded-sm border border-ink px-1.5 align-baseline text-[14px] leading-6 text-ink before:absolute before:inset-x-0 before:-inset-y-[10px] before:content-[''] ${
        open ? "bg-paper" : "bg-bond"
      }`}
      data-chip="letter"
    >
      <span aria-hidden="true" className="mr-1 font-bold">
        {open ? "–" : "+"}
      </span>
      <span className="max-w-[17ch] truncate font-semibold sm:max-w-[30ch]">{title}</span>
      <span className="shrink-0 text-muted">, page {citation.page}</span>
    </button>
  );
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

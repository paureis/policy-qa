"use client";

import { useId, useState } from "react";
import {
  COULD_NOT_INVESTIGATE_LABEL,
  NOT_SETTLED_LABEL,
  findingError,
  findingStatus,
  unsupportedExplanation,
  type Finding,
} from "@/lib/case";
import { CitationChips } from "./CitationChip";
import { CouldNotVerifyTag } from "./CouldNotVerifyTag";
import { StruckList } from "./StruckList";

/* The answer's first sentence and the rest, split at the first sentence end followed by a capital. */
function splitAnswer(answer: string): { first: string; rest: string } {
  const text = answer.trim();
  const m = text.match(/^([\s\S]+?[.!?])\s+(?=[A-Z“"(])/);
  if (!m) return { first: text, rest: "" };
  return { first: m[1], rest: text.slice(m[0].length) };
}

/*
  One finding: the question as the heading (no overline: overlines belong to
  the page's top-level sections), the answer in body text, the verified
  citations as reference chips, one per document and page, and any struck
  citations under them. An unsupported finding is struck out on screen, never
  hidden, with the words "Could not verify". A finding the documents do not
  settle says so in the same register as an answer. A failed model call says
  the question could not be investigated, which is not an abstention. Cost,
  time, and passages per question live in the trace, not here.

  record: the finished case with a letter, at 1024px and up, the compact
  investigation record: the question and the answer's first sentence; the
  question (with its + mark) opens the rest of the answer and its citations.
  Struck citations and their reasons stay visible, in a second column, and
  only a finding that has them takes two columns. On the phone everything
  shows as before: the collapsed parts are display: none at desktop only, so
  nothing remounts and the phone is unchanged.
*/
export function FindingCard({ finding, level = 3, record = false }: { finding: Finding; level?: 3 | 4; record?: boolean }) {
  const [open, setOpen] = useState(false);
  const restId = useId();
  const headingId = `finding-${finding.id}-q`;
  const status = findingStatus(finding);
  const Heading = level === 4 ? "h4" : "h3";
  const { first, rest } = splitAnswer(finding.answer);
  const struckSide = record && status !== "error" && finding.struck.length > 0;
  const expandable =
    record &&
    (rest !== "" || status === "not_settled" || status === "unsupported" || (status === "supported" && finding.citations.length > 0));
  /* Hidden at desktop while the record row is collapsed. */
  const more = expandable && !open ? "lg:hidden" : "";

  return (
    <article
      aria-labelledby={headingId}
      className={`land border-t border-hairline pt-4 pb-5 ${record ? "lg:border-edge lg:pt-3 lg:pb-4" : ""} ${
        struckSide ? "lg:grid lg:desk-cols lg:grid-rows-[auto_1fr] lg:items-start lg:*:col-start-1" : record ? "lg:max-w-[calc((100%-48px)*620/1040)]" : ""
      }`}
      data-finding={finding.id}
      data-status={status}
      data-topic={finding.topic}
      data-record-open={expandable ? (open ? "true" : "false") : undefined}
    >
      <Heading id={headingId} className={`text-[20px] leading-snug font-bold ${record ? "lg:font-semibold" : ""}`}>
        {expandable ? (
          <>
            <span className="lg:hidden">{finding.question}</span>
            <button
              type="button"
              aria-expanded={open}
              aria-controls={open ? restId : undefined}
              onClick={() => setOpen((o) => !o)}
              className="-ml-1 hidden min-h-11 w-full items-baseline gap-3 rounded-sm px-1 py-1.5 text-left lg:flex"
              data-record-toggle="true"
            >
              <span aria-hidden="true" className="w-4 shrink-0 text-[20px] font-semibold">
                {open ? "–" : "+"}
              </span>
              <span>{finding.question}</span>
            </button>
          </>
        ) : (
          finding.question
        )}
      </Heading>

      <div id={restId} className={expandable ? "lg:pl-7" : ""}>
        {status === "error" ? <ErrorBody message={findingError(finding)} /> : null}

        {status === "not_settled" ? (
          <div className={`mt-3 ${record ? "lg:mt-1" : ""}`}>
            <p className="text-[18px] leading-relaxed font-semibold lg:text-[17px]">{NOT_SETTLED_LABEL}.</p>
            <p className={`mt-1 text-[16px] text-muted ${more}`}>
              The documents in the corpus do not answer this question, so no answer is given. That is recorded, not guessed.
            </p>
          </div>
        ) : null}

        {status === "unsupported" ? (
          <div className={`mt-3 ${record ? "lg:mt-1" : ""}`}>
            <p className="text-[18px] leading-relaxed lg:text-[17px]">
              <s className="decoration-ink decoration-2">
                <Answer text={finding.answer} first={first} rest={rest} record={record} open={open} />
              </s>
            </p>
            <CouldNotVerifyTag />
            <p className={`mt-2 text-[16px] text-muted ${more}`}>{unsupportedExplanation(finding.struck)}</p>
          </div>
        ) : null}

        {status === "supported" ? (
          <div className={`mt-3 ${record ? "lg:mt-1" : ""}`}>
            <p className="text-[18px] leading-relaxed lg:text-[17px]">
              <Answer text={finding.answer} first={first} rest={rest} record={record} open={open} />
            </p>
            <div className={more}>
              <CitationChips citations={finding.citations} />
            </div>
          </div>
        ) : null}
      </div>

      {status !== "error" ? <StruckList struck={finding.struck} className={struckSide ? "lg:col-start-2! lg:row-span-2 lg:row-start-1 lg:mt-1" : ""} /> : null}
    </article>
  );
}

/*
  The answer as one text node on the phone (so its glyphs set exactly as
  before), and at desktop in the record its first sentence, with the rest
  once the row is open.
*/
function Answer({ text, first, rest, record, open }: { text: string; first: string; rest: string; record: boolean; open: boolean }) {
  if (!record) return <>{text}</>;
  return (
    <>
      <span className="lg:hidden">{text}</span>
      <span className="hidden lg:inline">{open && rest ? `${first} ${rest}` : first}</span>
    </>
  );
}

function ErrorBody({ message }: { message: string }) {
  return (
    <div className="mt-3">
      <p className="text-[18px] leading-relaxed font-semibold text-ink lg:text-[17px]">{COULD_NOT_INVESTIGATE_LABEL}.</p>
      <p className="mt-1 font-mono text-[15px] break-words text-muted">{message || "The service gave no reason."}</p>
    </div>
  );
}

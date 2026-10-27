"use client";

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

/*
  One finding: the question as the heading (no overline: overlines belong to
  the page's top-level sections), the answer in body text, the verified
  citations as reference chips, one per document and page, and any struck
  citations under them. An unsupported finding is struck out on screen, never
  hidden, with the words "Could not verify". A finding the documents do not
  settle says so in the same register as an answer. A failed model call says
  the question could not be investigated, which is not an abstention. Cost,
  time, and passages per question live in the trace, not here.

  record: the finished case with a letter, at 1024px and up. The finding is
  one row of the investigation record: the question, the answer, and its
  citations on the left; the struck citations and their reasons on the right.
  Grid placement only, the same elements, so nothing remounts.
*/
export function FindingCard({ finding, level = 3, record = false }: { finding: Finding; level?: 3 | 4; record?: boolean }) {
  const headingId = `finding-${finding.id}-q`;
  const status = findingStatus(finding);
  const Heading = level === 4 ? "h4" : "h3";
  return (
    <article
      aria-labelledby={headingId}
      className={`land border-t border-hairline pt-4 pb-5 ${record ? "lg:grid lg:desk-cols lg:grid-rows-[auto_1fr] lg:items-start lg:*:col-start-1" : ""}`}
      data-finding={finding.id}
      data-status={status}
      data-topic={finding.topic}
    >
      <Heading id={headingId} className={`text-[20px] leading-snug font-bold ${record ? "lg:font-semibold" : ""}`}>
        {finding.question}
      </Heading>

      {status === "error" ? <ErrorBody message={findingError(finding)} /> : null}

      {status === "not_settled" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed font-semibold lg:text-[17px]">{NOT_SETTLED_LABEL}.</p>
          <p className="mt-1 text-[16px] text-muted">
            The documents in the corpus do not answer this question, so no answer is given. That is recorded, not guessed.
          </p>
        </div>
      ) : null}

      {status === "unsupported" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed lg:text-[17px]">
            <s className="decoration-ink decoration-2">{finding.answer}</s>
          </p>
          <CouldNotVerifyTag />
          <p className="mt-2 text-[16px] text-muted">{unsupportedExplanation(finding.struck)}</p>
        </div>
      ) : null}

      {status === "supported" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed lg:text-[17px]">{finding.answer}</p>
          <CitationChips citations={finding.citations} />
        </div>
      ) : null}

      {status !== "error" ? <StruckList struck={finding.struck} className={record ? "lg:col-start-2! lg:row-span-2 lg:row-start-1 lg:mt-1" : ""} /> : null}
    </article>
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

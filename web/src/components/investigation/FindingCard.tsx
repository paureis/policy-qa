"use client";

import {
  COULD_NOT_INVESTIGATE_LABEL,
  COULD_NOT_VERIFY_LABEL,
  NOT_SETTLED_LABEL,
  TOPIC_LABELS,
  findingError,
  findingStatus,
  formatCost,
  formatSeconds,
  unsupportedExplanation,
  type Finding,
} from "@/lib/case";
import { CitationChip } from "./CitationChip";
import { StruckList } from "./StruckList";

/*
  One finding: the topic as an overline, the question as the heading, the
  answer in body text, the verified citations as chips, and any struck
  citations under them. An unsupported finding is struck out on screen,
  never hidden, with the words "Could not verify". A finding the documents
  do not settle says so in the same register as an answer. A failed model
  call says the question could not be investigated, which is not an
  abstention.
*/
export function FindingCard({ finding, showJurisdiction = false }: { finding: Finding; showJurisdiction?: boolean }) {
  const headingId = `finding-${finding.id}-q`;
  const status = findingStatus(finding);
  const passages = finding.passages;
  return (
    <article aria-labelledby={headingId} className="land border-t border-hairline pt-4 pb-5" data-finding={finding.id} data-status={status}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">
        {TOPIC_LABELS[finding.topic]}
        {showJurisdiction ? ` · ${finding.jurisdiction}` : ""}
      </p>
      <h3 id={headingId} className="mt-1 text-[20px] leading-snug font-bold">
        {finding.question}
      </h3>

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
          <p className="mt-2 inline-block border border-ink px-2 py-0.5 text-[14px] font-bold tracking-wide text-ink uppercase">
            {COULD_NOT_VERIFY_LABEL}
          </p>
          <p className="mt-2 text-[16px] text-muted">{unsupportedExplanation(finding.struck)}</p>
        </div>
      ) : null}

      {status === "supported" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed lg:text-[17px]">{finding.answer}</p>
          <ul className="mt-3 flex flex-col gap-2" aria-label="Verified citations">
            {finding.citations.map((c, i) => (
              <CitationChip key={`${c.doc_id}-${c.page}-${i}`} citation={c} />
            ))}
          </ul>
        </div>
      ) : null}

      {status !== "error" ? <StruckList struck={finding.struck} /> : null}

      <p className="mt-3 text-[14px] text-muted">
        {formatSeconds(finding.latency_ms)}, {formatCost(finding.cost_usd, finding.model)}
        {passages ? ` · Passages shown to the model: ${passages.length}` : ""}
      </p>
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

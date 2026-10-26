"use client";

import {
  COULD_NOT_VERIFY_LABEL,
  NOT_SETTLED_LABEL,
  TOPIC_LABELS,
  formatCost,
  formatSeconds,
  type Finding,
} from "@/lib/case";
import { CitationChip } from "./CitationChip";

/*
  One finding: the topic as an overline, the question as the heading, the
  answer in body text, the verified citations as chips. An unsupported
  finding is struck out on screen, never hidden, with the words "Could not
  verify" and the struck quotes with the verifier's reason. A finding the
  documents do not settle says so in the same register as an answer.
*/
export function FindingCard({ finding, showJurisdiction = false }: { finding: Finding; showJurisdiction?: boolean }) {
  const headingId = `finding-${finding.id}-q`;
  return (
    <article
      aria-labelledby={headingId}
      className="border-t border-hairline pt-4 pb-5"
      data-finding={finding.id}
      data-status={finding.status}
    >
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">
        {TOPIC_LABELS[finding.topic]}
        {showJurisdiction ? ` · ${finding.jurisdiction}` : ""}
      </p>
      <h3 id={headingId} className="mt-1 text-[20px] leading-snug font-bold">
        {finding.question}
      </h3>

      {finding.status === "not_settled" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed font-semibold lg:text-[17px]">{NOT_SETTLED_LABEL}.</p>
          <p className="mt-1 text-[16px] text-muted">
            The documents in the corpus do not answer this question, so no answer is given. That is recorded, not guessed.
          </p>
        </div>
      ) : null}

      {finding.status === "unsupported" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed lg:text-[17px]">
            <s className="decoration-ink decoration-2">{finding.answer}</s>
          </p>
          <p className="mt-2 inline-block border border-ink px-2 py-0.5 text-[14px] font-bold tracking-wide text-ink uppercase">
            {COULD_NOT_VERIFY_LABEL}
          </p>
          <p className="mt-2 text-[16px] text-muted">
            The model answered, but the verifier could not find its quote on the cited page, so the answer is struck out and
            not used.
          </p>
          <ul className="mt-3 space-y-3" aria-label="Quotes the verifier struck">
            {finding.struck.map((s, i) => (
              <li key={`${s.doc_id}-${s.page}-${i}`} className="border-l-4 border-hairline pl-4">
                <p className="text-[16px] leading-relaxed">
                  <s className="decoration-ink decoration-2">“{s.quote}”</s>
                </p>
                <p className="mt-1 text-[15px] text-muted">
                  Claimed from {s.title}, page {s.page}.
                </p>
                <p className="mt-1 text-[15px] font-semibold text-ink">Reason: {s.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {finding.status === "supported" ? (
        <div className="mt-3">
          <p className="text-[18px] leading-relaxed lg:text-[17px]">{finding.answer}</p>
          <ul className="mt-3 flex flex-col gap-2" aria-label="Verified citations">
            {finding.citations.map((c, i) => (
              <CitationChip key={`${c.doc_id}-${c.page}-${i}`} citation={c} />
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-3 text-[14px] text-muted">
        {formatSeconds(finding.latency_ms)}, {formatCost(finding.cost_usd)}
      </p>
    </article>
  );
}

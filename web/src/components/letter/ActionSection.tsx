"use client";

import type { Critique, Letter, Verdict } from "@/lib/case";
import { DeadlineStamp } from "@/components/intake/DeadlineStamp";
import { OPENING, OPENING_H2, SectionTitle } from "@/components/investigation/SectionTitle";
import { AppealLetter } from "./AppealLetter";
import { DeadlineFiling } from "./DeadlineFiling";
import { EvidenceChecklist } from "./EvidenceChecklist";
import { SelfCheck } from "./SelfCheck";

/* The anchor the status line "Appeal letter ready." links to. */
export const APPEAL_LETTER_ID = "appeal-letter";

/*
  Action. With an applicable letter: the letter, copy and download, the
  evidence checklist, then the deadline and filing path. Without one: why the
  denial holds (or why no letter was drafted) and what would have made the
  service covered, then the deadline and path in case the person appeals
  anyway. The self-check sits between the letter and the checklist.

  annotated: the finished case with a letter; its classes take the desktop
  layout at 1024px and up (CSS only, so nothing remounts): the letter is
  section 2 of the page, with its numbered opening. desk: the same at desktop
  width as the script sees it; the letter becomes the Annotated Letter, the
  checklist and the filing path become section 3 ("What to send and where to
  file") under the sheet, and the self-check is left to the page, which places
  it after the investigation record.
*/
export function ActionSection({
  letter,
  verdict,
  caseId,
  today,
  critique = null,
  critiqueFailure = null,
  annotated = false,
  desk = false,
}: {
  letter: Letter;
  verdict: Verdict | null;
  caseId: string;
  today: Date;
  critique?: Critique | null;
  critiqueFailure?: string | null;
  annotated?: boolean;
  desk?: boolean;
}) {
  const settledAgainst = verdict?.outcome === "consistent";
  const sheet = desk && letter.applicable;
  const { deadline } = letter;
  const deadlineIso = deadline.source !== "unknown" && typeof deadline.date === "string" && deadline.date !== "" ? deadline.date : null;
  return (
    <>
      <section
        id={letter.applicable ? APPEAL_LETTER_ID : undefined}
        aria-labelledby="action-heading"
        className={`land mt-10 scroll-mt-4 border-t-4 border-ink pt-4 ${annotated ? OPENING : ""}`}
        data-action={letter.applicable ? "letter" : "explanation"}>
        <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${annotated ? "lg:hidden" : ""}`}>Action</p>
        {letter.applicable ? (
          <>
            <h2 id="action-heading" className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? OPENING_H2 : ""}`}>
              <SectionTitle title="Your appeal letter" short="Appeal letter" numbered={annotated} />
            </h2>
            <p className={`mt-2 text-[16px] text-muted ${annotated ? "lg:mt-3" : ""}`}>
              {sheet
                ? "Read it before you send it. Add your name, member ID, and signature."
                : "Read it before you send it. Add your name, member ID, and signature. Tap a citation to see the quote it rests on."}
            </p>
            <AppealLetter
              letter={letter}
              caseId={caseId}
              desk={sheet}
              stamp={sheet ? <DeadlineStamp deadlineIso={deadlineIso} daysLeft={deadline.days_left} today={today} landed className="w-[128px]" /> : null}
            />
          </>
        ) : (
          <>
            <h2 id="action-heading" className="mt-1 text-[22px] leading-tight font-bold">
              {settledAgainst ? "Why the denial holds" : "Why no letter was drafted"}
            </h2>
            <p className="mt-3 text-[18px] leading-relaxed lg:text-[17px]">{letter.explanation?.trim() || "The service gave no explanation."}</p>
            {settledAgainst && verdict?.what_would_change?.trim() ? (
              <div className="mt-5 border-t border-hairline pt-4">
                <h3 className="text-[18px] font-bold">What would have made it covered</h3>
                <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.what_would_change}</p>
              </div>
            ) : null}
          </>
        )}
      </section>
      {sheet ? (
        /*
          Section 3 at desktop: what goes in the envelope and where it goes, as a
          register on the desk under the sheet. The checklist in the sheet's
          column, the deadline (date, day count, its citation) and the filing
          path in the margin column beside it.
        */
        <section aria-labelledby="send-heading" className={`land mt-10 border-t-4 border-ink pt-4 ${OPENING}`} data-send="true">
          <h2 id="send-heading" className={`mt-1 text-[22px] leading-tight font-bold ${OPENING_H2}`}>
            <SectionTitle title="What to send and where to file" short="What to send and where to file" numbered />
          </h2>
          <div className="mt-8 grid desk-cols items-start">
            <EvidenceChecklist items={letter.evidence_checklist ?? []} register />
            <DeadlineFiling letter={letter} today={today} register />
          </div>
        </section>
      ) : (
        <>
          <SelfCheck critique={critique} letter={letter} failedReason={critiqueFailure} />
          {letter.applicable ? <EvidenceChecklist items={letter.evidence_checklist ?? []} /> : null}
          <DeadlineFiling letter={letter} today={today} />
        </>
      )}
    </>
  );
}

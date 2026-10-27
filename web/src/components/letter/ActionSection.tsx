"use client";

import { dayCountLabel, daysUntil, formatShortDate, type Critique, type Letter, type Verdict } from "@/lib/case";
import { IN_SHEET, OPENING, OPENING_H2, PHONE_SHEET, PHONE_SHEET_ONLY, SHEET, SHEET_HEAD, SectionTitle } from "@/components/investigation/SectionTitle";
import { AppealLetter } from "./AppealLetter";
import { DeadlineFiling } from "./DeadlineFiling";
import { EvidenceChecklist } from "./EvidenceChecklist";
import { SelfCheck } from "./SelfCheck";

/* The anchor the status line "Appeal letter ready." links to. */
export const APPEAL_LETTER_ID = "appeal-letter";

/* The deadline beside the sheet head: the date and the day count, or "Deadline not stated". */
function deadlineLine(letter: Letter, today: Date): string {
  const d = letter.deadline;
  if (d.source === "unknown" || typeof d.date !== "string" || d.date === "") return "Deadline not stated";
  const days = typeof d.days_left === "number" ? d.days_left : daysUntil(d.date, today);
  const by = `Appeal by ${formatShortDate(d.date)}`;
  return days === null ? by : `${by}, ${dayCountLabel(days).toLowerCase()}`;
}

/*
  Action. With an applicable letter: the letter, copy and download, the
  evidence checklist, then the deadline and filing path. Without one: why the
  denial holds (or why no letter was drafted) and what would have made the
  service covered, then the deadline and path in case the person appeals
  anyway. The self-check sits between the letter and the checklist.

  annotated: the finished case with a letter; its classes take the desktop
  layout at 1024px and up (CSS only, so nothing remounts): the letter is
  section 2 of the page, with its numbered opening. desk: the same at desktop
  width as the script sees it; the letter becomes the Annotated Letter (US
  Letter pages, sidenotes, Copy, Download and the deadline in the margin
  beside the sheet head), the checklist and the filing path become section 3
  ("What to send and where to file") under the sheet, and the self-check is
  left to the page, which places it after the investigation record.
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
  n = null,
}: {
  letter: Letter;
  verdict: Verdict | null;
  caseId: string;
  today: Date;
  critique?: Critique | null;
  critiqueFailure?: string | null;
  annotated?: boolean;
  desk?: boolean;
  /* The numbers of the letter section and of "What to send and where to file" at desktop. */
  n?: { letter: number; send: number } | null;
}) {
  const settledAgainst = verdict?.outcome === "consistent";
  const sheet = desk && letter.applicable;
  return (
    <>
      <section
        id={letter.applicable ? APPEAL_LETTER_ID : undefined}
        aria-labelledby="action-heading"
        className={`land mt-10 scroll-mt-4 ${annotated ? `${PHONE_SHEET_ONLY} ${OPENING}` : PHONE_SHEET}`}
        data-action={letter.applicable ? "letter" : "explanation"}>
        {letter.applicable ? (
          <>
            <h2 id="action-heading" className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? OPENING_H2 : ""}`}>
              <SectionTitle title="Your appeal letter" short="Appeal letter" n={annotated ? (n?.letter ?? null) : null} />
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
              today={sheet ? today : null}
              deadlineLine={sheet ? deadlineLine(letter, today) : null}
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
        <div className={`land mt-10 ${SHEET}`} data-sheet-section="send">
          <section aria-labelledby="send-heading" className={`lg:border-t-4 lg:border-ink lg:pt-4 ${IN_SHEET}`} data-send="true">
            <h2 id="send-heading" className={`mt-1 text-[22px] leading-tight font-bold ${OPENING_H2} ${SHEET_HEAD}`}>
              <SectionTitle title="What to send and where to file" short="What to send and where to file" n={n?.send ?? null} />
            </h2>
            <div className="mt-8 grid desk-cols items-start">
              <EvidenceChecklist items={letter.evidence_checklist ?? []} register />
              <DeadlineFiling letter={letter} today={today} register />
            </div>
          </section>
        </div>
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

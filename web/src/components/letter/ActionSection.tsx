"use client";

import { dayCountLabel, daysUntil, formatShortDate, type Critique, type Letter, type Verdict } from "@/lib/case";
import { IN_SHEET, OPENING, OPENING_H2, PHONE_SHEET, PHONE_SHEET_ONLY, SHEET, SHEET_HEAD, SectionTitle } from "@/components/investigation/SectionTitle";
import { AppealLetter } from "./AppealLetter";
import { DeadlineFiling } from "./DeadlineFiling";
import { EvidenceChecklist } from "./EvidenceChecklist";
import { ExplanationSheet } from "./ExplanationSheet";
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

  annotated: the finished case (the letter stage done), with or without a
  letter; its classes take the desktop layout at 1024px and up (CSS only, so
  nothing remounts). With a letter: the letter is section 2 of the page, with
  its numbered opening. desk: the same at desktop width as the script sees
  it; the letter becomes the Annotated Letter (US Letter pages, sidenotes,
  Copy, Download and the deadline in the margin beside the sheet head), the
  checklist and the filing path become section 3 ("What to send and where to
  file") under the sheet, and the self-check is left to the page, which
  places it after the investigation record.

  Without a letter (consistent, not settled), at 1024 px and up: section 2 is
  the explanation sheet (ExplanationSheet: a 620 px bond sheet with the rule's
  citations as sidenotes in the margin), section 3 is "If you still want to
  appeal" on its own bond sheet in the register layout (DeadlineFiling). There
  is no self-check section: the self-check is skipped when no letter is
  drafted, and its one line stays on the phone only.
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
  /*
    The numbers of sections 2 and 3 at desktop: the letter and "What to send and where to file",
    or, without a letter, the explanation sheet and "If you still want to appeal".
  */
  n?: { main: number; filing: number } | null;
}) {
  const sheet = desk && letter.applicable;
  /* The finished case without a letter, at 1024 px and up (classes only). */
  const sibling = annotated && !letter.applicable;
  return (
    <>
      <section
        id={letter.applicable ? APPEAL_LETTER_ID : undefined}
        aria-labelledby="action-heading"
        className={`land mt-10 scroll-mt-4 ${annotated ? `${PHONE_SHEET_ONLY} ${letter.applicable ? OPENING : "lg:mt-24 tabs:mt-20"}` : PHONE_SHEET}`}
        data-action={letter.applicable ? "letter" : "explanation"}>
        {letter.applicable ? (
          <>
            <h2 id="action-heading" className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? OPENING_H2 : ""}`}>
              <SectionTitle title="Your appeal letter" short="Appeal letter" n={annotated ? (n?.main ?? null) : null} />
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
          <ExplanationSheet letter={letter} verdict={verdict} sheet={sibling} desk={desk} n={n?.main ?? null} />
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
              <SectionTitle title="What to send and where to file" short="What to send and where to file" n={n?.filing ?? null} />
            </h2>
            <div className="mt-8 grid desk-cols items-start">
              <EvidenceChecklist items={letter.evidence_checklist ?? []} register />
              <DeadlineFiling letter={letter} today={today} register />
            </div>
          </section>
        </div>
      ) : sibling ? (
        <>
          {/* The skipped self-check's one line on the phone; at desktop there is no self-check section. */}
          {desk ? null : <SelfCheck critique={critique} letter={letter} failedReason={critiqueFailure} />}
          {/* Section 3 at desktop: "If you still want to appeal" on its own bond sheet, in the register layout. */}
          <div className={`land mt-10 ${SHEET}`} data-sheet-section="appeal">
            <DeadlineFiling letter={letter} today={today} sheet n={n?.filing ?? null} />
          </div>
        </>
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

"use client";

import type { Letter, Verdict } from "@/lib/case";
import { AppealLetter } from "./AppealLetter";
import { DeadlineFiling } from "./DeadlineFiling";
import { EvidenceChecklist } from "./EvidenceChecklist";

/*
  Action. With an applicable letter: the letter, copy and download, the
  evidence checklist, then the deadline and filing path. Without one: why the
  denial holds (or why no letter was drafted) and what would have made the
  service covered, then the deadline and path in case the person appeals
  anyway.
*/
export function ActionSection({ letter, verdict, caseId, today }: { letter: Letter; verdict: Verdict | null; caseId: string; today: Date }) {
  const settledAgainst = verdict?.outcome === "consistent";
  return (
    <>
      <section aria-labelledby="action-heading" className="land mt-10 border-t-4 border-ink pt-4" data-action={letter.applicable ? "letter" : "explanation"}>
        <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Action</p>
        {letter.applicable ? (
          <>
            <h2 id="action-heading" className="mt-1 text-[22px] leading-tight font-bold">
              Your appeal letter
            </h2>
            <p className="mt-2 text-[16px] text-muted">
              Read it before you send it. Add your name, member ID, and signature. Tap a citation to see the quote it rests on.
            </p>
            <AppealLetter letter={letter} caseId={caseId} />
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
      {letter.applicable ? <EvidenceChecklist items={letter.evidence_checklist ?? []} /> : null}
      <DeadlineFiling letter={letter} today={today} />
    </>
  );
}

"use client";

import type { Letter } from "@/lib/case";
import { DeadlineStamp } from "@/components/intake/DeadlineStamp";
import { CitationChips } from "@/components/investigation/CitationChip";

const SOURCE_LINE: Record<Letter["deadline"]["source"], string> = {
  letter: "From the denial letter.",
  policy: "From the policy.",
  unknown: "No deadline found in the letter or the policy.",
};

/*
  The deadline as the postmark, with the letter's date and day count, and the
  filing path. The heading changes when no letter applies: the person may
  still choose to appeal, so the date and the path stay visible.
*/
export function DeadlineFiling({ letter, today }: { letter: Letter; today: Date }) {
  const { deadline, filing } = letter;
  const known = deadline.source !== "unknown" && typeof deadline.date === "string" && deadline.date !== "";
  return (
    <section aria-labelledby="deadline-heading" className="land mt-10 border-t-4 border-ink pt-4" data-deadline={deadline.source}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Deadline and filing path</p>
      <h2 id="deadline-heading" className="mt-1 text-[22px] leading-tight font-bold">
        {letter.applicable ? "When and where to file" : "If you still want to appeal"}
      </h2>

      <div className="mt-4 flex items-start gap-5">
        <DeadlineStamp
          deadlineIso={known ? deadline.date : null}
          daysLeft={known ? deadline.days_left : null}
          today={today}
          landed
          bottomText="RECOURSE"
          className="w-[132px] sm:w-[148px]"
        />
        <div className="min-w-0 pt-1">
          <p className="text-[16px] font-semibold">{SOURCE_LINE[deadline.source] ?? SOURCE_LINE.unknown}</p>
          {deadline.note?.trim() ? <p className="mt-1 text-[16px] leading-relaxed text-muted">{deadline.note}</p> : null}
        </div>
      </div>
      {deadline.citation ? <CitationChips citations={[deadline.citation]} label="Where the deadline comes from" /> : null}

      <dl className="mt-6 divide-y divide-hairline border-y border-hairline">
        <div className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
          <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">Where to file</dt>
          <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{filing.where}</dd>
        </div>
        <div className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
          <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">How</dt>
          <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{filing.how}</dd>
        </div>
      </dl>
      {filing.citation ? <CitationChips citations={[filing.citation]} label="Where the filing path comes from" /> : null}
    </section>
  );
}

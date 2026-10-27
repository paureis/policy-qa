"use client";

import { dayCountLabel, daysUntil, formatLongDate, type CitationRef, type Letter } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";

const SOURCE_LINE: Record<Letter["deadline"]["source"], string> = {
  letter: "From the denial letter.",
  policy: "From the policy.",
  unknown: "No deadline found in the letter or the policy.",
};

/*
  The deadline as text (the date and the day count; the postmark stays in the
  case header, the page's one stamp), the source and note, then the filing
  path. The citations behind the deadline and the path follow as one list, one
  chip per document and page. The heading changes when no letter applies: the
  person may still choose to appeal, so the date and the path stay visible.
*/
export function DeadlineFiling({ letter, today }: { letter: Letter; today: Date }) {
  const { deadline, filing } = letter;
  const known = deadline.source !== "unknown" && typeof deadline.date === "string" && deadline.date !== "";
  const days = known ? (typeof deadline.days_left === "number" ? deadline.days_left : daysUntil(deadline.date as string, today)) : null;
  const sources = [deadline.citation, filing.citation].filter((c): c is CitationRef => c !== null && c !== undefined);
  return (
    <section aria-labelledby="deadline-heading" className="land mt-10 border-t-4 border-ink pt-4" data-deadline={deadline.source}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Deadline and filing path</p>
      <h2 id="deadline-heading" className="mt-1 text-[22px] leading-tight font-bold">
        {letter.applicable ? "When and where to file" : "If you still want to appeal"}
      </h2>

      <div className="mt-4" data-deadline-date={known ? deadline.date : "unknown"}>
        <p className="text-[24px] leading-tight font-bold tabular-nums">
          {known ? `Appeal by ${formatLongDate(deadline.date as string)}` : "No deadline found"}
        </p>
        {days !== null ? <p className="mt-1 text-[18px] font-semibold tabular-nums">{dayCountLabel(days)}</p> : null}
        <p className="mt-3 text-[16px] font-semibold">{SOURCE_LINE[deadline.source] ?? SOURCE_LINE.unknown}</p>
        {deadline.note?.trim() ? <p className="mt-1 text-[16px] leading-relaxed text-muted">{deadline.note}</p> : null}
      </div>

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
      <CitationChips citations={sources} label="Where the deadline and the filing path come from" />
    </section>
  );
}

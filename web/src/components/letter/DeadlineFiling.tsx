"use client";

import { dayCountLabel, daysUntil, formatLongDate, type CitationRef, type Letter } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { IN_SHEET, OPENING_H2, PHONE_SHEET, PHONE_SHEET_ONLY, SHEET_HEAD, SectionTitle } from "@/components/investigation/SectionTitle";

const SOURCE_LINE: Record<Letter["deadline"]["source"], string> = {
  letter: "From the denial letter.",
  policy: "From the policy.",
  unknown: "No deadline found in the letter or the policy.",
};

/*
  The deadline as text (the date and the day count; the top sheet carries it
  too, as type with a mark), the source and note, then the filing
  path. The citations behind the deadline and the path follow as one list, one
  chip per document and page. The heading changes when no letter applies: the
  person may still choose to appeal, so the date and the path stay visible.
  register: part of section 3 at desktop ("What to send and where to file"),
  under the letter sheet, as an h3 without the section rule and overline.
  sheet: section 3 of a finished case without a letter at 1024 px and up
  ("If you still want to appeal"), its own bond sheet (the page's wrapper
  carries the sheet): the numbered opening under 1280 px, the sheet's head
  at tabs sizes, then the register in the letter's grid, the deadline
  (date, day count, source, note) in the 620 px column and the filing path
  (where, how, citations) label over value in the 420 px column. Under
  1024 px it is the plain section, unchanged (classes only).
*/
export function DeadlineFiling({
  letter,
  today,
  register = false,
  sheet = false,
  n = null,
}: {
  letter: Letter;
  today: Date;
  register?: boolean;
  sheet?: boolean;
  /* The section's number at desktop (sheet only). */
  n?: number | null;
}) {
  const { deadline, filing } = letter;
  const known = deadline.source !== "unknown" && typeof deadline.date === "string" && deadline.date !== "";
  const days = known ? (typeof deadline.days_left === "number" ? deadline.days_left : daysUntil(deadline.date as string, today)) : null;
  const sources = [deadline.citation, filing.citation].filter((c): c is CitationRef => c !== null && c !== undefined);
  const Heading = register ? "h3" : "h2";
  /* In the register's narrow margin column the label sits over its value. */
  const row = register ? "py-3" : `py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4 ${sheet ? "lg:block" : ""}`;
  const dt = `text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1 ${sheet ? "lg:pt-0" : ""}`;
  const dd = `mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px] ${sheet ? "lg:mt-1" : ""}`;
  const heading = letter.applicable ? "When and where to file" : "If you still want to appeal";
  return (
    <section
      aria-labelledby="deadline-heading"
      className={register ? "" : sheet ? `${PHONE_SHEET_ONLY} lg:border-t-4 lg:border-ink lg:pt-4 ${IN_SHEET}` : `land mt-10 ${PHONE_SHEET}`}
      data-deadline={deadline.source}
      data-register={register ? "true" : undefined}
    >
      <Heading
        id="deadline-heading"
        className={register ? "text-[20px] leading-tight font-semibold" : `mt-1 text-[22px] leading-tight font-bold ${sheet ? `${OPENING_H2} ${SHEET_HEAD}` : ""}`}
      >
        {sheet ? <SectionTitle title={heading} short={heading} n={n} /> : heading}
      </Heading>

      <div className={sheet ? "lg:mt-8 lg:grid lg:desk-cols lg:items-start" : ""} data-deadline-register={sheet ? "true" : undefined}>
        <div className={`mt-4 ${sheet ? "lg:mt-0" : ""}`} data-deadline-date={known ? deadline.date : "unknown"}>
          <p className={`leading-tight tabular-nums ${register ? "text-[20px] font-semibold" : `text-[24px] font-bold ${sheet ? "lg:text-[20px] lg:font-semibold" : ""}`}`}>
            {known ? `Appeal by ${formatLongDate(deadline.date as string)}` : "No deadline found"}
          </p>
          {days !== null ? <p className="mt-1 text-[18px] font-semibold tabular-nums">{dayCountLabel(days)}</p> : null}
          <p className="mt-3 text-[16px] font-semibold">{SOURCE_LINE[deadline.source] ?? SOURCE_LINE.unknown}</p>
          {deadline.note?.trim() ? <p className="mt-1 text-[16px] leading-relaxed text-muted">{deadline.note}</p> : null}
        </div>

        <div>
          <dl className={`mt-6 divide-y divide-hairline border-y border-hairline ${sheet ? "lg:mt-0" : ""}`}>
            <div className={row}>
              <dt className={dt}>Where to file</dt>
              <dd className={dd}>{filing.where}</dd>
            </div>
            <div className={row}>
              <dt className={dt}>How</dt>
              <dd className={dd}>{filing.how}</dd>
            </div>
          </dl>
          <CitationChips citations={sources} label="Where the deadline and the filing path come from" />
        </div>
      </div>
    </section>
  );
}

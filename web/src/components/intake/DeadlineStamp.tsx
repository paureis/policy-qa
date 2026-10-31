import { dayCountLabel, daysUntil, formatShortDate } from "@/lib/case";
import { CalendarLeaf, Mark } from "@/components/investigation/Marks";

/*
  The appeal deadline as a rubber stamp, where it is the only stamp on the
  sheet (the intake's case card, and the case page's header before the
  verdict exists): red ink, Archivo condensed caps, a heavy frame with a
  hairline frame inside, turned -2.6 degrees, inked unevenly (.stamp's
  filter). Once the verdict is reached the verdict is the sheet's one stamp
  and the deadline is set as type with a mark (DeadlineLine below).

  "landed" is the confirmed state: the inner frame goes from dashed to solid
  and the stamp turns to its full angle; the change steps, it does not fade.
  A missing deadline reads "No deadline found".
*/
export function DeadlineStamp({
  deadlineIso,
  today,
  landed = false,
  className = "",
  daysLeft,
  bottomText,
  small = false,
}: {
  deadlineIso: string | null;
  today: Date;
  landed?: boolean;
  className?: string;
  /* The day count the API computed; when given it wins over today's math. */
  daysLeft?: number | null;
  /* The foot line; CASE OPENED everywhere (one stamp, one foot line), before and after it lands. */
  bottomText?: string;
  /* The phone's top sheet during the run (section 17, K5): the same stamp scaled to 120 px wide (zoom 0.77). */
  small?: boolean;
}) {
  const days = deadlineIso ? (typeof daysLeft === "number" ? daysLeft : daysUntil(deadlineIso, today)) : null;
  const missing = deadlineIso === null || days === null;
  const dateText = missing ? "" : formatShortDate(deadlineIso);
  const countText = missing ? "" : dayCountLabel(days);
  const label = missing
    ? "Appeal deadline: no deadline found in the letter"
    : `Appeal deadline ${dateText}, ${countText}${landed && bottomText === undefined ? ". Case opened." : ""}`;

  /*
    The frames and the date carry the red and the uneven ink; the small lines
    (Appeal by, the day count, Case opened) are filled in ink at 14 px, as a
    dater stamp's band is, because red at 14 px measured under 4.5:1 once
    antialiased on a turned stamp. The date stays the red, inked face.
  */
  const INKED = "[filter:url(#ink-stamp)]";
  /* Scaled to 120 px (small), the frame and the date shrink with the stamp but the small lines stay 12 px: 15.6 px under zoom 0.77. */
  const SMALL = `${small ? "text-[15.6px]" : "text-[14px]"} leading-none font-semibold text-ink tabular-nums`;
  return (
    <div
      role="img"
      aria-label={label}
      className={`relative w-[156px] shrink-0 select-none text-red [transform:rotate(-2.6deg)] ${small ? "[zoom:0.77]" : ""} ${className}`}
      data-landed={landed ? "true" : "false"}
      data-stamp="deadline"
    >
      {/* The frame is the .stamp class itself (the verdict stamp's frame, ink and filter), unturned because the whole stamp turns; before it lands the inner frame is dashed. */}
      <span aria-hidden="true" className={`stamp absolute inset-0 transform-none ${landed ? "" : "[outline-style:dashed]"}`} />
      <div className="relative flex flex-col items-center px-3.5 pt-4 pb-3.5 text-center uppercase [font-stretch:62%]">
        <span className={`${SMALL} tracking-[0.12em]`}>Appeal by</span>
        {missing ? (
          <span className={`mt-1.5 mb-1 text-[20px] leading-[0.95] font-[850] ${INKED}`}>
            No deadline
            <br />
            found
          </span>
        ) : (
          <>
            <span className={`mt-1 text-[25px] leading-none font-[850] tabular-nums whitespace-nowrap sm:text-[28px] ${INKED}`}>{dateText}</span>
            <span className={`mt-1 ${SMALL} tracking-[0.05em]`}>{countText}</span>
          </>
        )}
        <span aria-hidden="true" className="mt-1.5 block w-full border-t border-red" />
        <span className={`mt-1.5 ${SMALL} tracking-[0.12em]`}>{bottomText ?? "Case opened"}</span>
      </div>
    </div>
  );
}

/*
  The deadline set as type with a mark, where the verdict is the sheet's
  stamp: "Appeal by Dec 6, 2026" with the day count under it, or "Deadline
  not stated". size "lead" is the top sheet's register at desktop; "line" is
  the phone header's line. The mark is the calendar leaf (section 19, M4):
  20 px at the lead size, in the slot the ring had (Alvaro, Oct 30), and
  16 px on the line, so the words do not move. A deadline the letter does
  not state keeps the open ring: not reached, in the marks' meaning.
*/
export function DeadlineLine({
  deadlineIso,
  today,
  daysLeft,
  size = "lead",
  className = "",
}: {
  deadlineIso: string | null;
  today: Date;
  daysLeft?: number | null;
  size?: "lead" | "line";
  className?: string;
}) {
  const days = deadlineIso ? (typeof daysLeft === "number" ? daysLeft : daysUntil(deadlineIso, today)) : null;
  const missing = deadlineIso === null || days === null;
  const lead = size === "lead";
  return (
    <p
      className={`flex items-start gap-3 tabular-nums ${lead ? "text-[30px] leading-[1.12] font-semibold tracking-[-0.015em]" : "text-[20px] leading-tight font-semibold"} ${className}`}
      data-deadline-line={missing ? "missing" : "date"}
    >
      {missing ? (
        <Mark kind="ring" className={lead ? "mt-[9px] h-5 w-5" : "mt-[4px] h-4 w-4"} />
      ) : (
        <CalendarLeaf size={lead ? 20 : 16} className={lead ? "mt-[9px] h-5 w-5" : "mt-[4px] h-4 w-4"} />
      )}
      <span>
        {missing ? (
          "Deadline not stated"
        ) : (
          <>
            Appeal by {formatShortDate(deadlineIso)}
            <span className={`block font-normal ${lead ? "" : "text-[18px]"}`}>{dayCountLabel(days)}</span>
          </>
        )}
      </span>
    </p>
  );
}


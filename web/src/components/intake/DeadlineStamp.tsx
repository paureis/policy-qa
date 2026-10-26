import { dayCountLabel, daysUntil, formatShortDate } from "@/lib/case";

/*
  The signature element: the appeal deadline as a round postmark in blue
  ink. It never turns red. A missing deadline reads "No deadline found".
  "landed" is the confirmed state; the change steps, it does not fade.
*/
export function DeadlineStamp({
  deadlineIso,
  today,
  landed = false,
  className = "",
  daysLeft,
  bottomText,
}: {
  deadlineIso: string | null;
  today: Date;
  landed?: boolean;
  className?: string;
  /* The day count the API computed; when given it wins over today's math. */
  daysLeft?: number | null;
  /* The lower arc; defaults to CASE OPENED when landed, RECOURSE otherwise. */
  bottomText?: string;
}) {
  const days = deadlineIso ? (typeof daysLeft === "number" ? daysLeft : daysUntil(deadlineIso, today)) : null;
  const missing = deadlineIso === null || days === null;
  const dateText = missing ? "" : formatShortDate(deadlineIso);
  const countText = missing ? "" : dayCountLabel(days);
  const label = missing
    ? "Appeal deadline: no deadline found in the letter"
    : `Appeal deadline ${dateText}, ${countText}${landed && bottomText === undefined ? ". Case opened." : ""}`;

  return (
    <div
      role="img"
      aria-label={label}
      className={`relative aspect-square w-[148px] shrink-0 select-none text-stamp ${landed ? "rotate-[-7deg]" : "rotate-[-3deg]"} ${className}`}
      data-landed={landed ? "true" : "false"}
    >
      <svg viewBox="0 0 148 148" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <defs>
          <path id="stamp-arc-top" d="M 20 74 A 54 54 0 0 1 128 74" />
          <path id="stamp-arc-bottom" d="M 20 74 A 54 54 0 0 0 128 74" />
        </defs>
        <circle cx="74" cy="74" r="70" fill="none" stroke="currentColor" strokeWidth={landed ? 3.5 : 2.5} />
        <circle
          cx="74"
          cy="74"
          r="63"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeDasharray={landed ? "none" : "2 3"}
        />
        {landed ? <circle cx="74" cy="74" r="48" fill="none" stroke="currentColor" strokeWidth="1" /> : null}
        <text
          fontSize="10.5"
          fontWeight="700"
          letterSpacing="2.2"
          fill="currentColor"
          fontFamily="var(--font-public-sans), 'Public Sans', system-ui, sans-serif"
        >
          <textPath href="#stamp-arc-top" startOffset="50%" textAnchor="middle">
            APPEAL BY
          </textPath>
        </text>
        <text
          fontSize="9"
          fontWeight="600"
          letterSpacing="2"
          fill="currentColor"
          fontFamily="var(--font-public-sans), 'Public Sans', system-ui, sans-serif"
        >
          <textPath href="#stamp-arc-bottom" startOffset="50%" textAnchor="middle">
            {bottomText ?? (landed ? "CASE OPENED" : "RECOURSE")}
          </textPath>
        </text>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center px-5 text-center leading-tight">
        {missing ? (
          <span className="text-[15px] font-bold uppercase tracking-wide">
            No deadline
            <br />
            found
          </span>
        ) : (
          <>
            <span className="text-[17px] font-bold uppercase tracking-wide">{dateText}</span>
            <span className="mt-1 text-[13px] font-semibold">{countText}</span>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import { useId, useState } from "react";
import { FIELD_LABELS, displayValue, type CaseRecord } from "@/lib/case";
import { CaseCard } from "@/components/intake/CaseCard";
import { DeadlineStamp } from "@/components/intake/DeadlineStamp";

const NO_FLAGS = new Set<never>();
const noop = () => {};

/*
  The locked case card, compact: payer, case id, the service and the
  letter's reason, with the landed postmark. The ten rows wait behind
  "Show the full case card" and render through the read-only CaseCard.

  strip: the finished case with a letter. At 1024px and up the header is a
  bond strip on the paper desk: the payer, one line of facts, and the
  disclosure; the postmark moves to the letter sheet's corner (the page's one
  stamp). Classes only: the same elements, so nothing remounts.
*/
export function CaseHeader({ record, today, strip = false }: { record: CaseRecord; today: Date; strip?: boolean }) {
  const [open, setOpen] = useState(false);
  const fullId = useId();
  const { card } = record;
  const deadline = card.appeal_deadline_claimed.value;
  const deadlineIso = typeof deadline === "string" && deadline !== "" ? deadline : null;
  const payer = card.payer_name.value;

  return (
    <section
      aria-labelledby="case-heading"
      className={`border-t-4 border-ink pt-4 ${
        strip
          ? "lg:grid lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:gap-x-6 lg:gap-y-1 lg:border lg:border-hairline lg:bg-bond lg:px-5 lg:py-3"
          : ""
      }`}
      data-case={record.case_id}
      data-strip={strip ? "true" : undefined}
    >
      <div className={`flex items-start justify-between gap-4 ${strip ? "lg:contents" : ""}`}>
        <div className={`min-w-0 ${strip ? "lg:flex lg:items-baseline lg:gap-3" : ""}`}>
          <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${strip ? "lg:hidden" : ""}`}>Case card</p>
          <h1 id="case-heading" className={`mt-1 text-[26px] leading-tight font-bold ${strip ? "lg:mt-0 lg:text-[20px] lg:whitespace-nowrap" : ""}`}>
            {payer ? String(payer) : "Denial letter"}
          </h1>
          <p className={`mt-2 text-[16px] text-muted ${strip ? "lg:mt-0 lg:text-[14px]" : ""}`}>
            Case <span className="font-mono text-ink">{record.case_id}</span>
          </p>
        </div>
        <DeadlineStamp deadlineIso={deadlineIso} today={today} landed className={`w-[120px] sm:w-[148px] ${strip ? "lg:hidden" : ""}`} />
      </div>

      <dl
        className={`mt-4 divide-y divide-hairline border-y border-hairline ${
          strip ? "lg:col-start-1 lg:mt-0 lg:flex lg:flex-wrap lg:gap-y-1 lg:-ml-[11px] lg:divide-y-0 lg:border-y-0 lg:[clip-path:inset(0_0_0_11px)]" : ""
        }`}
      >
        {(["service", "denial_reason", "program"] as const).map((key) => (
          <div
            key={key}
            className={`py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4 ${
              /* Each fact carries a rule on its left; the list sits 11px left and clips that strip, so a line never starts with a rule. */
              strip ? "lg:block lg:border-l lg:border-edge lg:px-2.5 lg:py-0" : ""
            }`}
          >
            <dt
              className={`text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1 ${
                strip ? "lg:sr-only" : ""
              }`}
            >
              {FIELD_LABELS[key]}
            </dt>
            <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{displayValue(key, card[key].value)}</dd>
          </div>
        ))}
      </dl>

      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? fullId : undefined}
        onClick={() => setOpen((o) => !o)}
        className={`mt-3 inline-flex min-h-11 items-center rounded-sm px-1 text-[16px] font-semibold text-ink underline underline-offset-4 ${
          strip ? "lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0 lg:whitespace-nowrap" : ""
        }`}
      >
        {open ? "Hide the full case card" : "Show the full case card"}
      </button>
      {open ? (
        <div id={fullId} className={`mt-4 ${strip ? "lg:col-span-full lg:pb-3" : ""}`}>
          <CaseCard
            card={card}
            summary={record.summary}
            flagged={NO_FLAGS}
            locked
            landed
            stamp={false}
            today={today}
            caseId={record.case_id}
            headingTag="h2"
            onChange={noop}
            onLooksRight={noop}
          />
        </div>
      ) : null}
    </section>
  );
}

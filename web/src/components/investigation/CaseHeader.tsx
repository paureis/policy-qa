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
*/
export function CaseHeader({ record, today }: { record: CaseRecord; today: Date }) {
  const [open, setOpen] = useState(false);
  const fullId = useId();
  const { card } = record;
  const deadline = card.appeal_deadline_claimed.value;
  const deadlineIso = typeof deadline === "string" && deadline !== "" ? deadline : null;
  const payer = card.payer_name.value;

  return (
    <section aria-labelledby="case-heading" className="border-t-4 border-ink pt-4" data-case={record.case_id}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Case card</p>
          <h1 id="case-heading" className="mt-1 text-[26px] leading-tight font-bold">
            {payer ? String(payer) : "Denial letter"}
          </h1>
          <p className="mt-2 text-[16px] text-muted">
            Case <span className="font-mono text-ink">{record.case_id}</span>
          </p>
        </div>
        <DeadlineStamp deadlineIso={deadlineIso} today={today} landed className="w-[120px] sm:w-[148px]" />
      </div>

      <dl className="mt-4 divide-y divide-hairline border-y border-hairline">
        {(["service", "denial_reason", "program"] as const).map((key) => (
          <div key={key} className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
            <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">{FIELD_LABELS[key]}</dt>
            <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{displayValue(key, card[key].value)}</dd>
          </div>
        ))}
      </dl>

      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? fullId : undefined}
        onClick={() => setOpen((o) => !o)}
        className="mt-3 inline-flex min-h-11 items-center rounded-sm px-1 text-[16px] font-semibold text-ink underline underline-offset-4"
      >
        {open ? "Hide the full case card" : "Show the full case card"}
      </button>
      {open ? (
        <div id={fullId} className="mt-4">
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

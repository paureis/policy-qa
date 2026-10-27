"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FIELD_LABELS, PROGRAM_LABELS, displayValue, type CaseRecord, type Program } from "@/lib/case";
import { CaseCard } from "@/components/intake/CaseCard";
import { DeadlineStamp } from "@/components/intake/DeadlineStamp";

const NO_FLAGS = new Set<never>();
const noop = () => {};

/*
  The locked case card, compact: payer, case id, the service and the
  letter's reason, with the landed postmark. The ten rows wait behind
  "Show the full case card" and render through the read-only CaseCard.

  titled: false once the verdict exists. The verdict headline is then the
  page's h1 (it names the outcome), and the payer's name is a plain line.

  register: the finished case with a letter. At 1024 px and up the header is
  the notice's reference box, floated to the top right of the outcome block:
  a ruled, tabular register of label and value (Member, Plan, Letter dated,
  Service and code, Amount, Case), the page's one postmark overlapping its
  lower right corner (the only carrier of the day count up there), and the
  disclosure under it. The phone's lines stay in the DOM, display: none at
  desktop; the register is display: none under 1024 px. Classes only, so
  nothing remounts when the letter lands.
*/
export function CaseHeader({
  record,
  today,
  register = false,
  titled = true,
  deadline = null,
}: {
  record: CaseRecord;
  today: Date;
  register?: boolean;
  titled?: boolean;
  /* The letter's deadline (date and the API's day count) for the register's postmark. */
  deadline?: { iso: string | null; daysLeft: number | null } | null;
}) {
  const [open, setOpen] = useState(false);
  const fullId = useId();
  const { card } = record;
  const claimed = card.appeal_deadline_claimed.value;
  const deadlineIso = typeof claimed === "string" && claimed !== "" ? claimed : null;
  const payer = card.payer_name.value;
  const Title = titled ? "h1" : "p";
  const toggleRef = useRef<HTMLButtonElement>(null);

  /* In the register at desktop the full card opens as an overlay over the margin; Escape closes it and returns focus. */
  useEffect(() => {
    if (!open || !register) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || !window.matchMedia("(min-width: 1024px), print").matches) return;
      setOpen(false);
      toggleRef.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, register]);

  return (
    <section
      aria-labelledby="case-heading"
      className={`border-t-4 border-ink pt-4 ${
        register ? "lg:relative lg:z-30 lg:float-right lg:mb-6 lg:ml-12 lg:w-[calc((100%-48px)*420/1040)] lg:border-t-0 lg:pt-0" : ""
      }`}
      data-case={record.case_id}
      data-register={register ? "true" : undefined}
    >
      <div className={`flex items-start justify-between gap-4 ${register ? "lg:hidden" : ""}`}>
        <div className="min-w-0">
          <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Case card</p>
          <Title id="case-heading" className="mt-1 text-[26px] leading-tight font-bold">
            {payer ? String(payer) : "Denial letter"}
          </Title>
          <p className="mt-2 text-[16px] text-muted">
            Case <span className="font-mono text-ink">{record.case_id}</span>
          </p>
        </div>
        <DeadlineStamp deadlineIso={deadlineIso} today={today} landed className="w-[120px] sm:w-[148px]" />
      </div>

      <dl className={`mt-4 divide-y divide-hairline border-y border-hairline ${register ? "lg:hidden" : ""}`}>
        {(["service", "denial_reason", "program"] as const).map((key) => (
          <div key={key} className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
            <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">{FIELD_LABELS[key]}</dt>
            <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{displayValue(key, card[key].value)}</dd>
          </div>
        ))}
      </dl>

      {register ? <Register record={record} today={today} deadline={deadline ?? { iso: deadlineIso, daysLeft: null }} /> : null}

      <button
        ref={toggleRef}
        type="button"
        aria-expanded={open}
        aria-controls={open ? fullId : undefined}
        onClick={() => setOpen((o) => !o)}
        className={`mt-3 inline-flex min-h-11 items-center rounded-sm px-1 text-[16px] font-semibold text-ink underline underline-offset-4 ${
          register ? "lg:mt-2 lg:-ml-1 lg:text-[15px]" : ""
        }`}
        data-case-card-toggle="true"
      >
        {open ? "Hide the full case card" : "Show the full case card"}
      </button>
      {open ? (
        <div
          id={fullId}
          className={`mt-4 ${register ? "lg:absolute lg:inset-x-0 lg:top-full lg:mt-0 lg:border lg:border-ink lg:bg-bond lg:px-5 lg:pt-1 lg:pb-5" : ""}`}
          data-case-card-full="true"
        >
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

/*
  The notice register: label and value on a bond box with a 1 px ink edge,
  rows ruled in hairline, labels in muted 14 px, values in ink 15 px with
  tabular numerals, the case id in mono. The postmark sits over the box's
  lower right corner, where the shortest values (the amount, the case id)
  leave room; it stays inside the frame at 1024 px.
*/
function Register({
  record,
  today,
  deadline,
}: {
  record: CaseRecord;
  today: Date;
  deadline: { iso: string | null; daysLeft: number | null };
}) {
  const { card } = record;
  const program = card.program.value;
  const programLabel = program && program !== "unknown" ? PROGRAM_LABELS[program as Program] : null;
  const payer = card.payer_name.value ? String(card.payer_name.value) : displayValue("payer_name", card.payer_name.value);
  const code = card.service_code.value ? String(card.service_code.value) : null;
  const service = displayValue("service", card.service.value);
  const rows: { label: string; value: React.ReactNode; key: string }[] = [
    { key: "member", label: "Member", value: displayValue("member_age_group", card.member_age_group.value) },
    { key: "plan", label: "Plan", value: programLabel ? `${payer}, ${programLabel}` : payer },
    { key: "dated", label: "Letter dated", value: displayValue("letter_date", card.letter_date.value) },
    { key: "service", label: "Service and code", value: code ? `${service} (${code})` : service },
    { key: "amount", label: "Amount", value: displayValue("amount_billed", card.amount_billed.value) },
    { key: "case", label: "Case", value: <span className="font-mono text-[15px]">{record.case_id}</span> },
  ];
  return (
    <div className="relative hidden lg:block" data-notice-register="true">
      <dl className="divide-y divide-hairline border border-ink bg-bond tabular-nums">
        {rows.map((r) => (
          <div key={r.key} className="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)] gap-x-3 px-4 py-[7px]" data-register-row={r.key}>
            <dt className="pt-px text-[14px] leading-5 font-semibold text-muted">{r.label}</dt>
            <dd className="text-[15px] leading-5 text-ink">{r.value}</dd>
          </div>
        ))}
      </dl>
      {/* right-2: the stamp is turned 7 degrees, so its corners reach 8 px past its box; this keeps them inside the frame. */}
      <div className="pointer-events-none absolute right-2 -bottom-14" data-register-stamp="true">
        <DeadlineStamp deadlineIso={deadline.iso} daysLeft={deadline.daysLeft} today={today} landed countClass="text-[14px]" dateWeight="font-semibold" />
      </div>
    </div>
  );
}

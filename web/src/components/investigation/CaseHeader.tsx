"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FIELD_LABELS, PROGRAM_LABELS, displayValue, type CaseRecord, type Program } from "@/lib/case";
import { CaseCard } from "@/components/intake/CaseCard";
import { PHONE_SHEET, PHONE_SHEET_ONLY } from "./SectionTitle";
import { DeadlineLine, DeadlineStamp } from "@/components/intake/DeadlineStamp";

const NO_FLAGS = new Set<never>();
const noop = () => {};

/*
  The locked case card, compact: payer, case id, the service and the
  letter's reason, with the deadline. The ten rows wait behind "Show the
  full case card" and render through the read-only CaseCard.

  titled: false once the verdict exists. The verdict headline is then the
  page's h1 (it names the outcome) and the sheet's one rubber stamp, so the
  deadline is no longer a stamp here: it is set as type with a mark. Before
  the verdict the deadline is the stamp.

  register: the finished case with a letter. At 1024 px and up the header is
  the top sheet's reference block, floated to its top right: the deadline
  as type with its mark (date, day count), then the reference rows, label
  and value under a rule (Member, Plan, Letter dated, Service and code,
  Amount; the case id is on the folder tab), and the disclosure under it.
  The phone's lines stay in the DOM, display: none at desktop; the register
  is display: none under 1024 px. Classes only, so nothing remounts when the
  letter lands.
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
  /* The letter's deadline (date and the API's day count) for the register's deadline line. */
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

  /* While the full card is open as an overlay at desktop, the document says so, and the index tabs step aside. */
  useEffect(() => {
    if (!open || !register) return;
    document.documentElement.setAttribute("data-overlay", "case-card");
    return () => document.documentElement.removeAttribute("data-overlay");
  }, [open, register]);

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
      className={`${
        /* Before the verdict the deadline is this sheet's one stamp, so the header is a bond sheet and the stamp sits on bond. */
        register ? PHONE_SHEET_ONLY : PHONE_SHEET
      } ${
        register ? "lg:relative lg:z-30 lg:float-right lg:mb-0 lg:ml-10 lg:w-[340px] lg:pt-1 xl:w-[440px]" : ""
      }`}
      data-case={record.case_id}
      data-register={register ? "true" : undefined}
    >
      <div className={`flex items-start justify-between gap-4 ${register ? "lg:hidden" : ""}`}>
        <div className="min-w-0">
          <Title id="case-heading" className="text-[26px] leading-tight font-bold">
            {payer ? String(payer) : "Denial letter"}
          </Title>
          <p className="mt-2 text-[16px] text-muted">
            Case <span className="font-mono text-ink">{record.case_id}</span>
          </p>
        </div>
        {titled ? <DeadlineStamp deadlineIso={deadlineIso} today={today} landed className="mt-1 mr-1" /> : null}
      </div>
      {titled ? null : (
        <DeadlineLine
          deadlineIso={deadline?.iso ?? deadlineIso}
          daysLeft={deadline?.daysLeft ?? null}
          today={today}
          size="line"
          className={`mt-4 ${register ? "lg:hidden" : ""}`}
        />
      )}

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
        className={`mt-3 inline-flex min-h-11 items-center px-1 text-[16px] font-semibold text-ink underline underline-offset-4 ${
          register ? "lg:mt-2 lg:-ml-1 lg:text-[15px] xl:absolute xl:right-0 xl:-bottom-3 xl:mt-0 xl:ml-0" : ""
        }`}
        data-case-card-toggle="true"
      >
        {open ? "Hide the full case card" : "Show the full case card"}
      </button>
      {open ? (
        <div
          id={fullId}
          className={`mt-4 ${register ? "lg:absolute lg:inset-x-0 lg:top-full lg:mt-0 xl:mt-4 lg:border lg:border-ink lg:bg-bond lg:px-5 lg:pt-1 lg:pb-5" : ""}`}
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
            bare
            onChange={noop}
            onLooksRight={noop}
          />
        </div>
      ) : null}
    </section>
  );
}

/*
  The reference block on the top sheet: the deadline as the lead (type and
  its mark, never a second stamp), then a rule and the rows, labels in
  muted 14 px, values in ink 15 px with tabular numerals.
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
  ];
  return (
    <div className="hidden lg:block" data-notice-register="true">
      <DeadlineLine deadlineIso={deadline.iso} daysLeft={deadline.daysLeft} today={today} size="lead" />
      <dl className="mt-5 grid grid-cols-[120px_minmax(0,1fr)] gap-x-3 gap-y-1.5 border-t border-ink/25 pt-4 tabular-nums">
        {rows.map((r) => (
          <div key={r.key} className="contents" data-register-row={r.key}>
            <dt className="pt-px text-[14px] leading-5 text-muted">{r.label}</dt>
            <dd className="text-[15px] leading-5 text-ink">{r.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FIELD_LABELS, PROGRAM_LABELS, dayCountLabel, daysUntil, displayValue, formatShortDate, type CaseRecord, type Program, type VerdictOutcome } from "@/lib/case";
import { CaseCard } from "@/components/intake/CaseCard";
import { PHONE_SHEET, PHONE_SHEET_ONLY } from "./SectionTitle";
import { DeadlineLine, DeadlineStamp } from "@/components/intake/DeadlineStamp";

const NO_FLAGS = new Set<never>();
const noop = () => {};

/*
  The reader's next step when it is not an appeal (Oct 28, 2026, critique fix G1). On a consistent or a
  not-settled verdict "Appeal by" no longer leads: the Lead line names the next action in the page's own
  words, and the deadline follows it as a 17 px line with its day count, since the reader may still
  appeal. The inconsistent verdict keeps "Appeal by" as the Lead. Short on purpose: at the Lead size
  each one sets on one line in the reference block at 1024 px (340 px) and at 1280 px (440 px), so the
  block keeps its height and nothing under it moves at decided ("See why the denial holds" measures
  328 px, "Find what would settle it" 317 px). The specific record is named under "What would change
  it" on the same sheet.
*/
const NEXT_STEP: Partial<Record<VerdictOutcome, string>> = {
  consistent: "See why the denial holds",
  not_settled: "Find what would settle it",
};

function NextStepLine({
  text,
  deadlineIso,
  daysLeft,
  today,
  lead,
  className = "",
}: {
  text: string;
  deadlineIso: string | null;
  daysLeft: number | null;
  today: Date;
  /* The Lead size of the reference block at desktop (30 px); otherwise the phone's (20 px). */
  lead: boolean;
  className?: string;
}) {
  const days = deadlineIso ? (typeof daysLeft === "number" ? daysLeft : daysUntil(deadlineIso, today)) : null;
  const when = deadlineIso !== null && days !== null ? `Appeal by ${formatShortDate(deadlineIso)} · ${dayCountLabel(days)}` : null;
  return (
    <div className={className} data-next-step="true">
      <p className={lead ? "text-[30px] leading-[1.12] font-semibold tracking-[-0.015em]" : "text-[20px] leading-tight font-semibold"}>{text}</p>
      <p className="mt-2 text-[17px] leading-[1.5] text-ink tabular-nums" data-deadline-line={when ? "date" : "missing"}>
        {when ?? "Deadline not stated"}
      </p>
    </div>
  );
}

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

  Since Oct 27 (piece 3) the register is the top sheet's reference block
  from the first poll at 1024 px and up, not only on the finished case.
  While the case runs (titled) the deadline is still the sheet's one stamp,
  pressed at the sheet's top left where the verdict will land (the page
  draws it), so the register holds the Lead line's slot (the line is laid
  out but visibility: hidden, and its rule is transparent) and shows the
  rows under it; the payer's name stays the page's h1, read by screen
  readers (the folder tab shows it at 1280 px and up). Once the verdict
  exists the Lead line shows in its slot, as on the finished case, and
  nothing under it moves.
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
  /* Set once the verdict exists, on the two verdicts whose next step is not an appeal. */
  const nextStep = record.verdict?.status === "done" ? (NEXT_STEP[record.verdict.outcome] ?? null) : null;

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
      <div className={`flex items-start justify-between gap-4 ${register ? (titled ? "lg:sr-only" : "lg:hidden") : ""}`}>
        <div className="min-w-0">
          <Title id="case-heading" className="text-[26px] leading-tight font-bold">
            {payer ? String(payer) : "Denial letter"}
          </Title>
          <p className="mt-2 text-[16px] text-muted">
            Case <span className="font-mono text-ink">{record.case_id}</span>
          </p>
        </div>
        {titled ? <DeadlineStamp deadlineIso={deadlineIso} today={today} landed className={`mt-1 mr-1 ${register ? "lg:hidden" : ""}`} /> : null}
      </div>
      {titled ? null : nextStep ? (
        <NextStepLine
          text={nextStep}
          deadlineIso={deadline?.iso ?? deadlineIso}
          daysLeft={deadline?.daysLeft ?? null}
          today={today}
          lead={false}
          className={`mt-4 ${register ? "lg:hidden" : ""}`}
        />
      ) : (
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

      {register ? <Register record={record} today={today} deadline={deadline ?? { iso: deadlineIso, daysLeft: null }} nextStep={nextStep} /> : null}

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
  nextStep,
}: {
  record: CaseRecord;
  today: Date;
  deadline: { iso: string | null; daysLeft: number | null };
  /* The next step that leads instead of the deadline (consistent and not settled, once decided). */
  nextStep: string | null;
}) {
  /* The Lead deadline line shows from the first poll (Alvaro's choice, Oct 28, 2026): the deadline is
     known at intake, so the rows never move at decided and the sheet is not empty during the run. While
     the case runs it repeats the deadline stamp on the sheet's left; once the verdict lands it is the
     sheet's only deadline. */
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
      {/*
        The Lead slot. The deadline Lead line is always laid out in it; when the next step leads, the deadline
        line stays as an unseen spacer (visibility: hidden, out of the accessibility tree) and the next step
        sits over it in the same grid cell, so the slot keeps the height it had from the first poll and the
        rows, the slip and the exhibits stay where they were at decided.
      */}
      <div className="grid" data-register-lead={nextStep ? "next-step" : "deadline"}>
        <DeadlineLine
          deadlineIso={deadline.iso}
          daysLeft={deadline.daysLeft}
          today={today}
          size="lead"
          className={`col-start-1 row-start-1 ${nextStep ? "invisible" : ""}`}
        />
        {nextStep ? (
          <NextStepLine text={nextStep} deadlineIso={deadline.iso} daysLeft={deadline.daysLeft} today={today} lead className="col-start-1 row-start-1" />
        ) : null}
      </div>
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

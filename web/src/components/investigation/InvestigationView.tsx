"use client";

import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ERROR_COPY,
  critiqueError,
  critiqueFailed,

  stageLine,
  IntakeError,
  investigate,
  isAbort,
  isFixtureCase,
  isRecordedSample,
  isWorking,
  pollCase,
  POLL_MS,
  type CaseRecord,
} from "@/lib/case";
import { Band } from "@/components/intake/Band";
import { CardLine, CaseHeader, PhoneLead } from "./CaseHeader";
import { IndexTabs, type IndexTab } from "./IndexTabs";
import { PHONE_SHEET, SHEET } from "./SectionTitle";
import { FindingsList } from "./FindingsList";
import { InvestigationProgress, progressLine } from "./InvestigationProgress";
import { LatestFinding, PhoneStatus, RoutingSlip, type SlipFailure } from "./RoutingSlip";
import { DeadlineStamp } from "@/components/intake/DeadlineStamp";
import { RouteLine } from "./RouteLine";
import { TrustPanel, verificationLines } from "./TrustPanel";
import { PageViewerFrame, PageViewerProvider, useDesktop } from "./PageViewer";
import { StageLine } from "@/components/verdict/StageLine";
import { VerdictSection } from "@/components/verdict/VerdictSection";
import { APPEAL_LETTER_ID, ActionSection } from "@/components/letter/ActionSection";
import { SelfCheck } from "@/components/letter/SelfCheck";

type View =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; error: IntakeError }
  | { kind: "ready"; record: CaseRecord };

const FAILURE_COPY = {
  investigation: {
    overline: "Investigation stopped",
    heading: "The investigation could not finish",
    note: "Try again reloads the case. An investigation cannot be restarted once the case has left intake; the findings above are kept.",
  },
  verdict: {
    overline: "Verdict stopped",
    heading: "The verdict could not be reached",
    note: "Try again reloads the case. A case cannot be restarted once it has left intake; the findings above are kept.",
  },
  letter: {
    overline: "Appeal letter stopped",
    heading: "The appeal letter could not be drafted",
    note: "Try again reloads the case. A case cannot be restarted once it has left intake; the findings and the verdict above are kept.",
  },
} as const;

const SECONDARY =
  "inline-flex min-h-12 w-full items-center justify-center border border-ink bg-bond px-5 text-[18px] font-semibold text-ink sm:w-auto";
/*
  The reader's place. Before a change the chain makes to the page (a poll's
  new record, the slip folding away) the page notes the first few blocks
  whose top is at or below the top of the window and where they sit; after
  the change commits it scrolls by however far the first of them that is
  still on the page has moved, so the block the reader was on stays where
  it was. A reader at the very top never scrolls, and a change below the
  reader moves nothing above it, so it needs no correction. The slip's own
  rows are never an anchor (they fold away).
*/
/* Whole blocks a reader is on (a finding, a letter paragraph, a heading, an exhibit, the receipt's table), not the lines inside them, which reflow when a block changes its layout. */
const ANCHOR_SELECTOR = "main :is(h1, h2, h3, figure, table, [data-finding], [data-block]):not([data-routing-slip] *)";

interface Anchor {
  el: Element;
  top: number;
}

function readAnchors(): Anchor[] | null {
  if (typeof window === "undefined" || window.scrollY <= 0) return null;
  const found: Anchor[] = [];
  for (const el of document.querySelectorAll(ANCHOR_SELECTOR)) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.top >= 0) {
      found.push({ el, top: r.top });
      if (found.length >= 8) break;
    }
  }
  return found.length > 0 ? found : null;
}

function keepAnchor(anchors: Anchor[] | null): void {
  if (!anchors) return;
  for (const { el, top } of anchors) {
    if (!el.isConnected) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const moved = r.top - top;
    if (Math.abs(moved) >= 1) window.scrollBy(0, moved);
    return;
  }
}

/* The record sheet while the case runs: bond, 1 px ink edge, 80 px under the top sheet (the gap the top sheet keeps to the next document). */
const RUN_SHEET = "lg:mt-20 lg:border lg:border-ink lg:bg-bond lg:px-10 lg:pt-8 lg:pb-10";
const PRIMARY =
  "inline-flex min-h-12 w-full items-center justify-center bg-ink px-5 text-[18px] font-semibold text-bond sm:w-auto";

/* The folder tab's "opened" date: the day the case was created, in the reader's own time zone. */
function openedDate(iso: string | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/*
  The case's home. Loads the case by id, polls GET /case/{id} every 1.5 s
  while the case works itself (investigation, verdict, appeal letter, self-check)
  until reviewed or failed, and shows findings, the verdict, and the action as they
  arrive. State changes step; nothing fades.
*/
export function InvestigationView({ caseId }: { caseId: string }) {
  const [view, setView] = useState<View>({ kind: "loading" });
  /* The stamp renders only after a client fetch, so today is read on the client. */
  const [today] = useState<Date>(() => new Date());
  const [attempt, setAttempt] = useState(0);
  const [starting, setStarting] = useState<"idle" | "busy" | "failed">("idle");
  /* Desktop width as the script sees it (the same 1024px as lg), for the pieces whose DOM order differs at desktop. */
  const desktop = useDesktop();
  /* The reader's place, noted before a change the chain makes and kept after it commits (readAnchors). */
  const anchors = useRef<Anchor[] | null>(null);
  /* This view saw the chain still working, so its last state is held on screen for one poll before the slip folds. */
  const [sawWork, setSawWork] = useState(false);
  /* The record whose final state has been held for one poll; the slip folds once it equals the current record. */
  const [heldId, setHeldId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const onRecord = (record: CaseRecord) => {
      anchors.current = readAnchors();
      if (isWorking(record)) setSawWork(true);
      setView({ kind: "ready", record });
    };
    pollCase(caseId, onRecord, controller.signal).catch((err: unknown) => {
      if (isAbort(err) || controller.signal.aborted) return;
      if (err instanceof IntakeError && err.code === "not_found") setView({ kind: "not_found" });
      else setView({ kind: "error", error: err instanceof IntakeError ? err : new IntakeError("unreachable") });
    });
    return () => controller.abort();
  }, [caseId, attempt]);

  const reload = useCallback(() => {
    setView({ kind: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  const start = async () => {
    setStarting("busy");
    try {
      await investigate(caseId);
      setStarting("idle");
      reload();
    } catch {
      setStarting("failed");
    }
  };

  /* The band marks a fixture case, also when one renders on the live dev server; the public sample as the recorded run it is. */
  const sample = isFixtureCase(caseId) ? (isRecordedSample(caseId) ? "recorded" : true) : false;
  const record = view.kind === "ready" ? view.record : null;
  const dual = record?.route?.dual === true;
  const investigation = record?.investigation ?? null;
  const verdict = record?.verdict ?? null;
  const letter = record?.letter ?? null;
  const critique = record?.critique ?? null;
  /* A failed self-check leaves the letter usable: it is reported in the self-check section, not here. */
  const selfCheckFailed = record !== null && critiqueFailed(record);
  const failedStep: "investigation" | "verdict" | "letter" | null =
    record === null || selfCheckFailed
      ? null
      : investigation?.status === "failed"
        ? "investigation"
        : verdict?.status === "failed"
          ? "verdict"
          : letter?.status === "failed"
            ? "letter"
            : record.status === "failed"
              ? verdict === null
                ? "investigation"
                : letter === null
                  ? "verdict"
                  : "letter"
              : null;
  const failed = failedStep !== null;
  const done = record !== null && record.status !== "intake" && record.status !== "investigating" && investigation?.status === "done";
  const verdictDone = verdict !== null && verdict.status === "done";
  const letterDone = letter !== null && letter.status === "done";
  const findings = investigation?.findings ?? [];
  const failure = failedStep ? FAILURE_COPY[failedStep] : null;
  const failureReason =
    (failedStep === "letter" ? letter?.error : failedStep === "verdict" ? verdict?.error : investigation?.error)?.trim() ||
    "The service reported an error and gave no reason.";
  /* The API's own words for a non-2xx answer (any status); the generic copy only when it sent none or the network failed. */
  const apiMessage =
    view.kind === "error" && view.error.message.trim() !== "" && view.error.message !== ERROR_COPY[view.error.code].body ? view.error.message : null;
  /*
    Outcome first from the moment the verdict exists: decided, drafting, drafted,
    reviewing, reviewed, and a failure after the verdict (a later step failed, the
    verdict stands). Before it the live run is the show, so the page stays
    chronological. The switch happens once, when the verdict first renders, and the
    reorder is real DOM order, so screen readers meet the outcome first too.
  */
  const outcomeFirst = record !== null && verdictDone;
  const letterHref = letterDone && letter.applicable ? `#${APPEAL_LETTER_ID}` : null;
  const proof = done && investigation && verdictDone ? verificationLines(investigation, letterDone ? letter : null) : [];
  /*
    The finished case with a letter (drafted, reviewing, reviewed) reads as the
    Case File at 1024px and up: the manila folder as the ground, a 1,120 px
    frame (1,088 px of content: the 620 px sheet, the 48 px gutter, the 420 px
    margin), the top sheet (bond, 1 px ink edge) holding the header's
    reference block at its top right, the status line and section 1, then
    numbered sections: 1 Verdict (the stamp, the counts as marks, the exhibit
    pair as clipped sheets), 2 Appeal letter (US Letter
    pages with sidenotes), 3 What to send and where to file, each opened by a
    4 px ink rule; then 4 Investigation record, 5 Self-check, 6 Receipt in the
    appendix register (a 1 px rule, 20 px titles). The numbers are passed as
    props, so an absent self-check leaves no gap. annotated switches classes
    only, so no element remounts when
    the letter lands; desk (the same at desktop width, from the script) adds
    section 3 under the sheet and moves the self-check after the record, where
    DOM order must change with the visual order. Under 1024px the page is the
    phone column. At 1280 px and up the folder's index tabs repeat the
    numbered sections down the folder's right edge.

    Since Oct 27, 2026 (piece 2) the folder is every finished case, with or
    without a letter: annotated is "the chain has finished" (the letter
    stage done), and hasLetter says whether a letter exists. A finished case
    without a letter (consistent, not settled) has the same top sheet, then
    2 the explanation sheet ("Why the denial holds" or "Why no letter was
    drafted", the rule's citations in the margin), 3 "If you still want to
    appeal" on its own sheet, 4 Investigation record, 5 Receipt; no
    self-check section (it is skipped when no letter is drafted).
  */
  const annotated = letterDone;
  const hasLetter = letterDone && letter.applicable;
  const desk = annotated && desktop;
  /*
    The live run in the folder (Oct 27, 2026, piece 3). At 1024 px and up the
    folder is open from the first poll, not only once the chain finishes:
    the band with the case tab, the manila ground, the top sheet (the
    reference block, the deadline stamp before the verdict, the routing
    slip), and the record sheet the findings land on. folder switches
    classes only, all of them from lg, so the phone is unchanged and no
    element remounts: the top sheet, the case header, the slip, the record
    and its findings, and the receipt are the same nodes from the first poll
    to the end. At decided the stamp is pressed above the slip; when the
    chain finishes (slipDone) the slip folds away (display: none) into the
    band's status line, the letter's sheets have landed, and the record and
    the receipt take their numbers, the receipt its slip, and the tabs.
  */
  const folder = record !== null && record.status !== "intake";
  const chainDone = annotated && record !== null && !isWorking(record);
  /*
    The slip folds into the band line once the chain is done, after its last state (the Trust tick)
    has been on screen for one poll interval; a case that was already finished when it opened folds
    at once. The hold is a pause, not a transition, so it applies under reduced motion too.
  */
  const slipDone = chainDone && (!sawWork || heldId === record.case_id);
  const slipFailure: SlipFailure | null =
    failedStep === null || failure === null
      ? null
      : {
          step: failedStep,
          words: failedStep === "investigation" && investigation?.status === "failed" ? progressLine(investigation) : failure.heading,
        };
  const claimedDeadline = record?.card.appeal_deadline_claimed.value;
  const holdingSlip = chainDone && !slipDone;
  const holdFor = record?.case_id ?? null;
  useEffect(() => {
    if (!holdingSlip || holdFor === null) return;
    const t = window.setTimeout(() => {
      anchors.current = readAnchors();
      setHeldId(holdFor);
    }, POLL_MS);
    return () => window.clearTimeout(t);
  }, [holdingSlip, holdFor]);
  /* After the chain's change commits, before paint: keep the reader's block where it was. */
  useLayoutEffect(() => {
    keepAnchor(anchors.current);
    anchors.current = null;
  }, [view, slipDone]);
  /* The self-check opens a numbered section only when it ran (or failed); skipped or still running, it does not. */
  const selfCheckSection =
    hasLetter && critique !== null && (selfCheckFailed || critiqueError(critique) !== null || (critique.status === "done" && !critique.skipped));
  const numbers = hasLetter
    ? { verdict: 1, main: 2, filing: 3, record: 4, selfCheck: selfCheckSection ? 5 : null, receipt: selfCheckSection ? 6 : 5 }
    : annotated
      ? { verdict: 1, main: 2, filing: 3, record: 4, selfCheck: null, receipt: 5 }
      : null;
  /* Section 2 without a letter: the explanation sheet's head, as ActionSection words it. */
  const explanationTitle = verdict?.outcome === "consistent" ? "Why the denial holds" : "Why no letter was drafted";
  /* The band and the page share one width, so the wordmark and the content share an edge. */
  const width = folder
    ? "max-w-[640px] lg:max-w-[1152px] lg:px-8"
    : dual
      ? "max-w-[640px] lg:max-w-[1120px]"
      : "max-w-[640px]";

  /*
    The folder's index tabs at 1280 px and up, one per numbered section, each
    linking to its heading; an absent self-check leaves no tab and no gap.
  */
  const tabs: IndexTab[] = numbers
    ? [
        { n: numbers.verdict, label: "Verdict", target: "verdict-heading" },
        ...(hasLetter
          ? [
              { n: numbers.main, label: "Appeal letter", target: "action-heading" },
              { n: numbers.filing, label: "What to send and where to file", target: "send-heading" },
            ]
          : [
              { n: numbers.main, label: explanationTitle, target: "action-heading" },
              { n: numbers.filing, label: "If you still want to appeal", target: "deadline-heading" },
            ]),
        { n: numbers.record, label: "Investigation record", target: "findings-heading" },
        ...(numbers.selfCheck !== null ? [{ n: numbers.selfCheck, label: "Self-check", target: "selfcheck-heading" }] : []),
        { n: numbers.receipt, label: "Receipt", target: "trust-heading" },
      ]
    : [];
  const payerName = record?.card.payer_name.value ? String(record.card.payer_name.value) : null;
  /*
    The band's status line at desktop on the finished case: one plain line, the letter's stage
    ("Letter checked. 1 of 1 issue fixed."). The question count stays with the record (section 4)
    and the receipt; with the folder tab beside it, both would not fit on one line.
  */
  const bandStatus = record ? (stageLine(record) ?? "") : "";
  /* Not on the recorded sample: its created_at is the replay's clock, so the date would be wrong on any other day (section 15, fix round). */
  const opened = sample === "recorded" ? null : openedDate(record?.created_at);
  /*
    The top sheet: the case header, the status line and the verdict on one
    bond sheet with a 1 px ink edge on the manila folder (the finished case
    with a letter, 1024 px and up). Always the same wrapper, so nothing
    remounts when the letter lands; under 1024 px it is a plain block.
  */
  /*
    Under 1024 px (section 17, K1 and K2) the top sheet is a bond sheet at the column width too, 1 px ink edge,
    20 px inset: the case line and the stages while the case runs; the stamp, the Lead line, the counts, the
    case line, the exhibits, the rule and the gap once the verdict exists.
  */
  const topSheet = folder
    ? "max-lg:border max-lg:border-ink max-lg:bg-bond max-lg:p-5 lg:flow-root lg:border lg:border-ink lg:bg-bond lg:px-10 lg:pt-8 lg:pb-10"
    : "";

  /* The letter's deadline (date and the API's day count) once the letter stage is done, for the Lead lines. */
  const letterDeadline =
    annotated && letter
      ? {
          iso: letter.deadline.source !== "unknown" && typeof letter.deadline.date === "string" && letter.deadline.date !== "" ? letter.deadline.date : null,
          daysLeft: letter.deadline.days_left,
        }
      : null;

  /*
    The verdict section is mounted for the whole run (empty until the verdict exists), so the routing
    slip inside it is one element from the first poll to the end.
  */
  const verdictBlock =
    record && folder ? (
      <div>
        <VerdictSection
          verdict={verdictDone ? verdict : null}
          changeShownBelow={letterDone && !letter.applicable && verdict?.outcome === "consistent"}
          changeInSheet={annotated && !hasLetter}
          proof={proof}
          first={outcomeFirst}
          annotated={annotated}
          folder={folder}
          slip={<RoutingSlip record={record} failure={slipFailure} collapsed={slipDone} phoneFolded={verdictDone} />}
          n={numbers?.verdict ?? null}
          card={record.card}
          secondOpinion={record.second_opinion ?? null}
          cardLine={<CardLine record={record} today={today} titled={!verdictDone} />}
          lead={<PhoneLead record={record} today={today} deadline={letterDeadline} className="mt-5" />}
          /* From decided to the end, one line of the same height (fix round: nothing under it moves after decided). */
          phoneStatus={<PhoneStatus record={record} failure={slipFailure} href={letterHref} />}
          letterPending={verdictDone && verdict?.outcome === "inconsistent" && !letterDone}
        />
      </div>
    ) : null;

  const outcome =
    record && letterDone ? (
      <div className={dual && !annotated ? "lg:max-w-[640px]" : ""}>
        <ActionSection
          letter={letter}
          verdict={verdictDone ? verdict : null}
          caseId={record.case_id}
          today={today}
          critique={critique}
          critiqueFailure={selfCheckFailed ? critique?.error?.trim() || "The service reported an error and gave no reason." : null}
          annotated={annotated}
          desk={desk}
          n={numbers ? { main: numbers.main, filing: numbers.filing } : null}
        />
      </div>
    ) : null;

  return (
    <PageViewerProvider caseId={caseId}>
      <div className="flex min-h-full flex-col" data-layout={annotated ? "annotated" : "column"}>
        <Band
          sample={sample}
          widthClass={width}
          tab={
            record ? (
              <>
                CASE <span className="font-semibold">{record.case_id}</span>
                {/* The payer and the opened date need the folder's full width: the finished case at 1280 px and up. */}
                {folder && (payerName || opened) ? (
                  <span className="hidden xl:inline">
                    {payerName ? ` · ${payerName}` : ""}
                    {opened ? ` · opened ${opened}` : ""}
                  </span>
                ) : null}
              </>
            ) : null
          }
        >
          {/*
            The status line in the band's right at desktop on the finished case, where the folder's
            edge carries it; on the phone and during the live run it stays in the page.
          */}
          {desk && slipDone && record ? (
            <p
              /*
                Plain text, not a live region: the routing slip's live region (beside the slip, kept after
                it folds) is the one that announces the chain at desktop, so nothing is heard twice.
              */
              /* Two lines at most: the stage line of a case without a letter is longer than the band's room beside the folder tab. */
              className="hidden min-w-0 text-[14px] leading-snug lg:line-clamp-2"
              title={bandStatus}
              data-band-status="true"
            >
              {bandStatus}
            </p>
          ) : null}
          <Link href="/case/new" className="inline-flex min-h-11 shrink-0 items-center px-2 text-[15px] font-semibold whitespace-nowrap underline underline-offset-4">
            New case
          </Link>
        </Band>
        {desk && tabs.length > 0 ? <IndexTabs tabs={tabs} /> : null}

        <PageViewerFrame>
          <main className={`mx-auto w-full min-w-0 flex-1 px-4 pt-6 pb-16 ${folder ? "lg:pt-9" : ""} ${width}`}>
            {view.kind === "loading" ? (
              <p className="text-[18px] lg:text-[17px]" aria-live="polite" data-view="loading">
                Loading case <span className="font-mono">{caseId}</span>…
              </p>
            ) : null}

            {view.kind === "not_found" ? (
              <section data-view="not_found" aria-labelledby="not-found-heading" className={PHONE_SHEET}>
                <h1 id="not-found-heading" className="text-[26px] leading-tight font-bold">
                  {ERROR_COPY.not_found.title}
                </h1>
                <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]" role="alert">
                  No case <span className="font-mono">{caseId}</span> on this server. The service may have restarted; start a new case.
                </p>
                <Link href="/case/new" className={`${PRIMARY} mt-5`}>
                  Start a new case
                </Link>
              </section>
            ) : null}

            {view.kind === "error" ? (
              <section role="alert" aria-labelledby="load-error-heading" className={PHONE_SHEET} data-view="error">
                <h1 id="load-error-heading" className="text-[26px] leading-tight font-bold">
                  {apiMessage && view.error.code === "unreachable" ? "The service reported an error" : ERROR_COPY[view.error.code].title}
                </h1>
                <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]" data-api-message={apiMessage ? "true" : "false"}>
                  {apiMessage ??
                    (view.error.code === "unreachable" || view.error.code === "timeout"
                      ? "Check your connection and try again. The case is kept on the service."
                      : view.error.message)}
                </p>
                <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                  <button type="button" className={PRIMARY} onClick={reload}>
                    Try again
                  </button>
                  <Link href="/case/new" className={SECONDARY}>
                    Start a new case
                  </Link>
                </div>
              </section>
            ) : null}

            {record ? (
              <div data-view={record.status}>
                <div className={topSheet} data-top-sheet={folder ? "true" : undefined}>
                <CaseHeader record={record} today={today} register={folder} titled={!verdictDone} deadline={letterDeadline} />

                {record.status === "intake" ? (
                  <section className={`mt-6 ${PHONE_SHEET}`} aria-live="polite">
                    <p className="text-[18px] leading-relaxed lg:text-[17px]">This case has not been investigated yet.</p>
                    {starting === "failed" ? (
                      <p role="alert" className="mt-2 text-[16px] font-semibold">
                        The investigation could not start. Check your connection and try again.
                      </p>
                    ) : null}
                    <button type="button" className={`${PRIMARY} mt-4`} onClick={start} disabled={starting === "busy"}>
                      {starting === "busy" ? "Starting…" : "Start the investigation"}
                    </button>
                  </section>
                ) : (
                  <>
                    {/*
                      One tree for both orders, so nothing remounts when the verdict lands: the
                      status block and the findings are the same elements throughout (open chips,
                      focus, and the live regions survive), and the outcome slot sits before the
                      findings but is empty until the verdict exists. Chronological while the case
                      works itself; outcome first once the verdict is reached.
                    */}
                    <div
                      /*
                        Under 1024 px in the folder these lines are gone (section 17): the top sheet's card line, slip,
                        latest finding and status line say the same, and the slip's live region announces the chain.
                      */
                      className={`mt-4 border-t border-hairline pt-4 ${folder ? "max-lg:hidden lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}
                      data-order={outcomeFirst ? "outcome-first" : "chronological"}
                    >
                      {/* At desktop the route line leads the record sheet instead. */}
                      {outcomeFirst ? null : <RouteLine route={record.route} lead className={folder ? "lg:hidden" : ""} />}
                      {/* One status row at tablet and up once the outcome leads, so the verdict reaches the first screen. */}
                      {desk ? null : (
                        <div className={`${outcomeFirst ? "*:mt-0 sm:flex sm:flex-wrap sm:items-baseline sm:gap-x-2" : ""} ${folder ? "lg:hidden" : ""}`}>
                          <InvestigationProgress investigation={investigation} compact={annotated} />
                          <StageLine record={record} letterHref={letterHref} inRow={outcomeFirst} compact={annotated} />
                        </div>
                      )}
                      {/*
                        The latest finding on the phone (critique fix G3), under the two stage lines, the place the
                        slip has at desktop: its line held from the first poll, gone when the chain is done (the
                        slip's fold) or stopped before the verdict. At desktop the slip carries its own.
                      */}
                      {folder ? (
                        <LatestFinding findings={findings} hidden={slipDone || (failed && !verdictDone)} className="mt-2 lg:hidden" />
                      ) : null}
                    </div>
                    {/*
                      Before the verdict, at desktop: the deadline is the sheet's one stamp, pressed at the
                      top left where the verdict stamp will land. At decided it gives way to the verdict and
                      to the Lead line in the reference block.
                    */}
                    {folder && !verdictDone ? (
                      /* The stamp's area holds the verdict stamp's and the counts' height, so nothing under it moves at decided. */
                      <div className="hidden lg:block lg:min-h-[168px] tabs:min-h-[169px]" data-stamp-area="true">
                        <DeadlineStamp
                          deadlineIso={typeof claimedDeadline === "string" && claimedDeadline !== "" ? claimedDeadline : null}
                          today={today}
                          landed
                          className="lg:mt-2 lg:ml-1"
                        />
                      </div>
                    ) : null}
                    {verdictBlock}
                  </>
                )}
                </div>
                {record.status === "intake" ? null : (
                  <>
                    {outcome}
                    {/*
                      The investigation record and, at desktop, the self-check after it share one
                      bond sheet on the finished case at 1024 px and up. The wrapper is always
                      there (classes only), so no finding remounts when the letter lands.
                    */}
                    <div
                      /* At desktop the record sheet is already on the folder when the letter lands above it: it does not land again. */
                      className={annotated ? `${desktop ? "" : "land "}mt-10 ${SHEET}` : folder ? RUN_SHEET : ""}
                      data-sheet-section={folder ? "record" : undefined}
                    >
                    <FindingsList
                      findings={findings}
                      route={record.route}
                      appendix={outcomeFirst}
                      lead={<RouteLine route={record.route} lead />}
                      annotated={annotated}
                      folder={folder}
                      n={numbers?.record ?? null}
                    />

                    {/* At desktop the self-check follows the record (on the phone it sits under the letter, inside Action). */}
                    {desk && hasLetter ? (
                      <SelfCheck
                        critique={critique}
                        letter={letter}
                        failedReason={selfCheckFailed ? critique?.error?.trim() || "The service reported an error and gave no reason." : null}
                        annotated
                        n={numbers?.selfCheck ?? null}
                      />
                    ) : null}
                    </div>

                    {failed && failure ? (
                      <section role="alert" aria-labelledby="failed-heading" className={`mt-8 ${PHONE_SHEET} ${folder ? "lg:mt-24 lg:px-10 lg:pt-8 lg:pb-10" : ""}`} data-view="failed" data-failed-step={failedStep}>
                        <h2 id="failed-heading" className={`text-[26px] leading-tight font-bold ${folder ? "lg:text-[28px]" : ""}`}>
                          {failure.heading}
                        </h2>
                        <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]">{failureReason}</p>
                        <p className="mt-2 text-[16px] text-muted">{failure.note}</p>
                        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                          <button type="button" className={PRIMARY} onClick={reload}>
                            Try again
                          </button>
                          <Link href="/case/new" className={SECONDARY}>
                            Start a new case
                          </Link>
                        </div>
                      </section>
                    ) : null}

                    {/*
                      The receipt: on the phone once the investigation is done, as before; at desktop from the
                      first poll, as the finished case's slip holding what the run has so far.
                    */}
                    {investigation && (done || folder) ? (
                      <div className={`${dual && !folder ? "lg:max-w-[640px]" : ""} ${done ? "" : "max-lg:hidden"}`}>
                        <TrustPanel
                          investigation={investigation}
                          verdict={verdict}
                          letter={letterDone ? letter : null}
                          critique={letterDone ? critique : null}
                          secondOpinion={verdictDone ? (record.second_opinion ?? null) : null}
                          annotated={annotated}
                          folder={folder}
                          n={numbers?.receipt ?? null}
                        />
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            ) : null}
          </main>
        </PageViewerFrame>
      </div>
    </PageViewerProvider>
  );
}

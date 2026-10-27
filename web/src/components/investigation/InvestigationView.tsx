"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ERROR_COPY,
  critiqueError,
  critiqueFailed,

  stageLine,
  IntakeError,
  investigate,
  isAbort,
  isFixtureCase,
  pollCase,
  type CaseRecord,
} from "@/lib/case";
import { Band } from "@/components/intake/Band";
import { CaseHeader } from "./CaseHeader";
import { IndexTabs, type IndexTab } from "./IndexTabs";
import { PHONE_SHEET, SHEET } from "./SectionTitle";
import { FindingsList } from "./FindingsList";
import { InvestigationProgress } from "./InvestigationProgress";
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

  useEffect(() => {
    const controller = new AbortController();
    pollCase(caseId, (record) => setView({ kind: "ready", record }), controller.signal).catch((err: unknown) => {
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

  /* The band marks a fixture case, also when one renders on the live dev server. */
  const sample = isFixtureCase(caseId);
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
  */
  const annotated = letterDone && letter.applicable;
  const desk = annotated && desktop;
  /* The self-check opens a numbered section only when it ran (or failed); skipped or still running, it does not. */
  const selfCheckSection =
    letterDone && critique !== null && (selfCheckFailed || critiqueError(critique) !== null || (critique.status === "done" && !critique.skipped));
  const numbers = annotated
    ? { verdict: 1, letter: 2, send: 3, record: 4, selfCheck: selfCheckSection ? 5 : null, receipt: selfCheckSection ? 6 : 5 }
    : null;
  /* The band and the page share one width, so the wordmark and the content share an edge. */
  const width = annotated
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
        { n: numbers.letter, label: "Appeal letter", target: "action-heading" },
        { n: numbers.send, label: "What to send and where to file", target: "send-heading" },
        { n: numbers.record, label: "Investigation record", target: "findings-heading" },
        ...(numbers.selfCheck !== null ? [{ n: numbers.selfCheck, label: "Self-check", target: "selfcheck-heading" }] : []),
        { n: numbers.receipt, label: "Receipt", target: "trust-heading" },
      ]
    : [];
  const payerName = record?.card.payer_name.value ? String(record.card.payer_name.value) : null;
  /*
    The band's status line at desktop on the finished case: one plain line, the letter's stage
    ("Letter checked: 1 of 1 issue fixed."). The question count stays with the record (section 4)
    and the receipt; with the folder tab beside it, both would not fit on one line.
  */
  const bandStatus = record ? (stageLine(record) ?? "") : "";
  const opened = openedDate(record?.created_at);
  /*
    The top sheet: the case header, the status line and the verdict on one
    bond sheet with a 1 px ink edge on the manila folder (the finished case
    with a letter, 1024 px and up). Always the same wrapper, so nothing
    remounts when the letter lands; under 1024 px it is a plain block.
  */
  const topSheet = annotated ? "lg:flow-root lg:border lg:border-ink lg:bg-bond lg:px-10 lg:pt-8 lg:pb-10" : "";

  const verdictBlock =
    record && verdictDone ? (
      <div className={dual ? "lg:max-w-[640px]" : ""}>
        <VerdictSection
          verdict={verdict}
          changeShownBelow={letterDone && !letter.applicable && verdict.outcome === "consistent"}
          proof={proof}
          first={outcomeFirst}
          annotated={annotated}
          n={numbers?.verdict ?? null}
          card={record.card}
        />
      </div>
    ) : null;

  const outcome =
    record && letterDone ? (
      <div className={dual ? "lg:max-w-[640px]" : ""}>
        <ActionSection
          letter={letter}
          verdict={verdictDone ? verdict : null}
          caseId={record.case_id}
          today={today}
          critique={critique}
          critiqueFailure={selfCheckFailed ? critique?.error?.trim() || "The service reported an error and gave no reason." : null}
          annotated={annotated}
          desk={desk}
          n={numbers ? { letter: numbers.letter, send: numbers.send } : null}
        />
      </div>
    ) : null;

  return (
    <PageViewerProvider>
      <div className="flex min-h-full flex-col" data-layout={annotated ? "annotated" : "column"}>
        <Band
          sample={sample}
          widthClass={width}
          tab={
            record ? (
              <>
                CASE <span className="font-semibold">{record.case_id}</span>
                {/* The payer and the opened date need the folder's full width: the finished case at 1280 px and up. */}
                {annotated && (payerName || opened) ? (
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
          {desk && record ? (
            <p
              aria-live="polite"
              aria-atomic="true"
              className="hidden min-w-0 truncate text-[14px] leading-snug lg:block"
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
          <main className={`mx-auto w-full min-w-0 flex-1 px-4 pt-6 pb-16 ${annotated ? "lg:pt-9" : ""} ${width}`}>
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
                <div className={topSheet} data-top-sheet={annotated ? "true" : undefined}>
                <CaseHeader
                  record={record}
                  today={today}
                  register={annotated}
                  titled={!verdictDone}
                  deadline={
                    annotated && letter
                      ? {
                          iso: letter.deadline.source !== "unknown" && typeof letter.deadline.date === "string" && letter.deadline.date !== "" ? letter.deadline.date : null,
                          daysLeft: letter.deadline.days_left,
                        }
                      : null
                  }
                />

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
                      className={`mt-4 border-t border-hairline pt-4 ${annotated ? "lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}
                      data-order={outcomeFirst ? "outcome-first" : "chronological"}
                    >
                      {outcomeFirst ? null : <RouteLine route={record.route} lead />}
                      {/* One status row at tablet and up once the outcome leads, so the verdict reaches the first screen. */}
                      {desk ? null : (
                        <div className={outcomeFirst ? "*:mt-0 sm:flex sm:flex-wrap sm:items-baseline sm:gap-x-2" : ""}>
                          <InvestigationProgress investigation={investigation} compact={annotated} />
                          <StageLine record={record} letterHref={letterHref} inRow={outcomeFirst} compact={annotated} />
                        </div>
                      )}
                    </div>
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
                    <div className={annotated ? `land mt-10 ${SHEET}` : ""} data-sheet-section={annotated ? "record" : undefined}>
                    <FindingsList
                      findings={findings}
                      route={record.route}
                      appendix={outcomeFirst}
                      lead={outcomeFirst ? <RouteLine route={record.route} lead /> : null}
                      annotated={annotated}
                      n={numbers?.record ?? null}
                    />

                    {/* At desktop the self-check follows the record (on the phone it sits under the letter, inside Action). */}
                    {desk && letterDone ? (
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
                      <section role="alert" aria-labelledby="failed-heading" className={`mt-8 ${PHONE_SHEET}`} data-view="failed" data-failed-step={failedStep}>
                        <h2 id="failed-heading" className="text-[26px] leading-tight font-bold">
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

                    {done && investigation ? (
                      <div className={dual ? "lg:max-w-[640px]" : ""}>
                        <TrustPanel
                          investigation={investigation}
                          verdict={verdict}
                          letter={letterDone ? letter : null}
                          critique={letterDone ? critique : null}
                          annotated={annotated}
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

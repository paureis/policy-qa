"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ERROR_COPY,
  INTAKE_MODE,
  critiqueFailed,
  dayCountLabel,
  daysUntil,
  formatShortDate,
  IntakeError,
  investigate,
  isAbort,
  pollCase,
  type CaseRecord,
  type Letter,
} from "@/lib/case";
import { Band } from "@/components/intake/Band";
import { CaseHeader } from "./CaseHeader";
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
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm border border-ink bg-bond px-5 text-[18px] font-semibold text-ink sm:w-auto";
const PRIMARY =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-federal px-5 text-[18px] font-semibold text-white sm:w-auto";

/* The deadline for the outcome block's counts line: the date and the day count, or "Deadline not stated". */
function deadlineLine(letter: Letter, today: Date): string {
  const d = letter.deadline;
  if (d.source === "unknown" || typeof d.date !== "string" || d.date === "") return "Deadline not stated";
  const days = typeof d.days_left === "number" ? d.days_left : daysUntil(d.date, today);
  const by = `Appeal by ${formatShortDate(d.date)}`;
  return days === null ? by : `${by}, ${dayCountLabel(days).toLowerCase()}`;
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

  const sample = INTAKE_MODE === "fixture";
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
    Annotated Letter at 1024px and up: a paper desk, a 1,120 px frame (1,088 px
    of content: the 620 px sheet, the 48 px gutter, the 420 px margin), the
    header as a strip, the outcome heading block, the letter sheet with its
    margin notes, the record, the self-check, the receipt. annotated switches
    classes only, so no element remounts when the letter lands; desk (the same
    at desktop width, from the script) moves the checklist and the filing path
    onto the sheet and the self-check after the record, where DOM order must
    change with the visual order. Under 1024px the page is the phone column.
  */
  const annotated = letterDone && letter.applicable;
  const desk = annotated && desktop;
  /* The band and the page share one width, so the wordmark and the content share an edge. */
  const width = annotated
    ? "max-w-[640px] lg:max-w-[1152px] lg:px-8"
    : dual
      ? "max-w-[640px] lg:max-w-[1120px]"
      : "max-w-[640px]";

  const outcome =
    record && (verdictDone || letterDone) ? (
      <div className={dual ? "lg:max-w-[640px]" : ""}>
        {verdictDone ? (
          <VerdictSection
            verdict={verdict}
            changeShownBelow={letterDone && !letter.applicable && verdict.outcome === "consistent"}
            proof={proof}
            first={outcomeFirst}
            annotated={annotated}
            deadlineLine={letterDone ? deadlineLine(letter, today) : null}
          />
        ) : null}
        {letterDone ? (
          <ActionSection
            letter={letter}
            verdict={verdictDone ? verdict : null}
            caseId={record.case_id}
            today={today}
            critique={critique}
            critiqueFailure={selfCheckFailed ? critique?.error?.trim() || "The service reported an error and gave no reason." : null}
            annotated={annotated}
            desk={desk}
          />
        ) : null}
      </div>
    ) : null;

  return (
    <PageViewerProvider>
      <div className={`flex min-h-full flex-col ${annotated ? "lg:bg-paper" : ""}`} data-layout={annotated ? "annotated" : "column"}>
        <Band sample={sample} widthClass={width}>
          <Link href="/case/new" className="min-h-11 rounded-sm px-2 py-2 text-[15px] font-semibold underline underline-offset-4 focus-visible:outline-white">
            New case
          </Link>
        </Band>

        <PageViewerFrame>
          <main className={`mx-auto w-full min-w-0 flex-1 px-4 pt-6 pb-16 ${width}`}>
            {view.kind === "loading" ? (
              <p className="text-[18px] lg:text-[17px]" aria-live="polite" data-view="loading">
                Loading case <span className="font-mono">{caseId}</span>…
              </p>
            ) : null}

            {view.kind === "not_found" ? (
              <section data-view="not_found" aria-labelledby="not-found-heading" className="border-t-4 border-ink pt-4">
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
              <section role="alert" aria-labelledby="load-error-heading" className="border-t-4 border-ink pt-4" data-view="error">
                <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Could not load the case</p>
                <h1 id="load-error-heading" className="mt-1 text-[26px] leading-tight font-bold">
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
                <CaseHeader record={record} today={today} strip={annotated} />

                {record.status === "intake" ? (
                  <section className="mt-6 border-t border-hairline pt-4" aria-live="polite">
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
                      className={`mt-4 border-t border-hairline pt-4 ${annotated ? "lg:mt-8 lg:border-t-0 lg:pt-0" : ""}`}
                      data-order={outcomeFirst ? "outcome-first" : "chronological"}
                    >
                      {outcomeFirst ? null : <RouteLine route={record.route} lead />}
                      {/* One status row at tablet and up once the outcome leads, so the verdict reaches the first screen. */}
                      <div className={outcomeFirst ? "*:mt-0 sm:flex sm:flex-wrap sm:items-baseline sm:gap-x-2" : ""}>
                        <InvestigationProgress investigation={investigation} compact={annotated} />
                        <StageLine record={record} letterHref={letterHref} inRow={outcomeFirst} compact={annotated} />
                      </div>
                    </div>
                    {outcome}
                    <FindingsList
                      findings={findings}
                      route={record.route}
                      appendix={outcomeFirst}
                      lead={outcomeFirst ? <RouteLine route={record.route} lead /> : null}
                      annotated={annotated}
                    />

                    {/* At desktop the self-check follows the record (on the phone it sits under the letter, inside Action). */}
                    {desk && letterDone ? (
                      <SelfCheck
                        critique={critique}
                        letter={letter}
                        failedReason={selfCheckFailed ? critique?.error?.trim() || "The service reported an error and gave no reason." : null}
                        annotated
                      />
                    ) : null}

                    {failed && failure ? (
                      <section role="alert" aria-labelledby="failed-heading" className="mt-8 border-t-4 border-ink pt-4" data-view="failed" data-failed-step={failedStep}>
                        <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">{failure.overline}</p>
                        <h2 id="failed-heading" className="mt-1 text-[26px] leading-tight font-bold">
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

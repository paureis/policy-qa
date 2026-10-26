"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ERROR_COPY,
  INTAKE_MODE,
  IntakeError,
  investigate,
  isAbort,
  pollCase,
  type CaseRecord,
} from "@/lib/case";
import { Band } from "@/components/intake/Band";
import { CaseHeader } from "./CaseHeader";
import { FindingsList } from "./FindingsList";
import { InvestigationProgress } from "./InvestigationProgress";
import { RouteLine } from "./RouteLine";
import { TrustPanel } from "./TrustPanel";
import { PageViewerFrame, PageViewerProvider } from "./PageViewer";
import { StageLine } from "@/components/verdict/StageLine";
import { VerdictSection } from "@/components/verdict/VerdictSection";
import { ActionSection } from "@/components/letter/ActionSection";

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

/*
  The case's home. Loads the case by id, polls GET /case/{id} every 1.5 s
  while the case works itself (investigation, verdict, appeal letter) until
  drafted or failed, and shows findings, the verdict, and the action as they
  arrive. State changes step; nothing fades.
*/
export function InvestigationView({ caseId }: { caseId: string }) {
  const [view, setView] = useState<View>({ kind: "loading" });
  /* The stamp renders only after a client fetch, so today is read on the client. */
  const [today] = useState<Date>(() => new Date());
  const [attempt, setAttempt] = useState(0);
  const [starting, setStarting] = useState<"idle" | "busy" | "failed">("idle");

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
  const failedStep: "investigation" | "verdict" | "letter" | null =
    record === null
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

  return (
    <PageViewerProvider>
      <div className="flex min-h-full flex-col">
        <Band sample={sample}>
          <Link href="/case/new" className="min-h-11 rounded-sm px-2 py-2 text-[15px] font-semibold underline underline-offset-4 focus-visible:outline-white">
            New case
          </Link>
        </Band>

        <PageViewerFrame>
          <main className={`mx-auto w-full min-w-0 flex-1 px-4 pt-6 pb-16 ${dual ? "max-w-[640px] lg:max-w-[1120px]" : "max-w-[640px]"}`}>
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
                  There is no case <span className="font-mono">{caseId}</span>. {ERROR_COPY.not_found.body}
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
                  {ERROR_COPY[view.error.code].title}
                </h1>
                <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]">
                  {view.error.code === "unreachable" || view.error.code === "timeout"
                    ? "Check your connection and try again. The case is kept on the service."
                    : view.error.message}
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
                <CaseHeader record={record} today={today} />

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
                    <RouteLine route={record.route} />
                    <InvestigationProgress investigation={investigation} />
                    <StageLine record={record} />
                    <FindingsList findings={findings} route={record.route} />

                    <div className={dual ? "lg:max-w-[640px]" : ""}>
                      {verdictDone ? (
                        <VerdictSection
                          verdict={verdict}
                          changeShownBelow={letterDone && !letter.applicable && verdict.outcome === "consistent"}
                        />
                      ) : null}
                      {letterDone ? <ActionSection letter={letter} verdict={verdictDone ? verdict : null} caseId={record.case_id} today={today} /> : null}
                    </div>

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
                        <TrustPanel investigation={investigation} verdict={verdict} letter={letterDone ? letter : null} />
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

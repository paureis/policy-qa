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

type View =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; error: IntakeError }
  | { kind: "ready"; record: CaseRecord };

const SECONDARY =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm border border-ink bg-bond px-5 text-[18px] font-semibold text-ink sm:w-auto";
const PRIMARY =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-federal px-5 text-[18px] font-semibold text-white sm:w-auto";

/*
  The case's home. Loads the case by id, polls GET /case/{id} every 1.5 s
  while the investigation runs, and shows findings as they arrive. State
  changes step; nothing fades.
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
  const failed = record !== null && (record.status === "failed" || investigation?.status === "failed");
  const done = record !== null && record.status === "investigated" && investigation?.status === "done";
  const findings = investigation?.findings ?? [];

  return (
    <div className="flex min-h-full flex-col">
      <Band sample={sample}>
        <Link href="/case/new" className="min-h-11 rounded-sm px-2 py-2 text-[15px] font-semibold underline underline-offset-4 focus-visible:outline-white">
          New case
        </Link>
      </Band>

      <main className={`mx-auto w-full flex-1 px-4 pt-6 pb-16 ${dual ? "max-w-[640px] lg:max-w-[1120px]" : "max-w-[640px]"}`}>
        {view.kind === "loading" ? (
          <p className="text-[18px] lg:text-[17px]" aria-live="polite" data-view="loading">
            Loading case <span className="font-mono">{caseId}</span>…
          </p>
        ) : null}

        {view.kind === "not_found" ? (
          <div data-view="not_found">
            <p className="text-[18px] lg:text-[17px]" role="alert">
              We could not find case <span className="font-mono">{caseId}</span>. {ERROR_COPY.not_found.body}
            </p>
            <Link href="/case/new" className={`${PRIMARY} mt-5`}>
              Start a new case
            </Link>
          </div>
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
                <FindingsList findings={findings} route={record.route} />

                {failed ? (
                  <section role="alert" aria-labelledby="failed-heading" className="mt-8 border-t-4 border-ink pt-4" data-view="failed">
                    <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Investigation stopped</p>
                    <h2 id="failed-heading" className="mt-1 text-[26px] leading-tight font-bold">
                      The investigation could not finish
                    </h2>
                    <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]">
                      {investigation?.error?.trim() || "The service reported an error and gave no reason."}
                    </p>
                    <p className="mt-2 text-[16px] text-muted">
                      Try again reloads the case. An investigation cannot be restarted once the case has left intake; the
                      findings above are kept.
                    </p>
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

                {done && investigation ? <TrustPanel investigation={investigation} /> : null}
              </>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
}

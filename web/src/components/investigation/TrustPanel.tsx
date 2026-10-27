"use client";

import { useId, useState } from "react";
import {
  FIXTURE_MODEL,
  countErrors,
  findingStatus,
  formatCost,
  formatSeconds,
  letterVerificationLine,
  selfCheckLine,
  type Critique,
  type Investigation,
  type Letter,
  type Verdict,
} from "@/lib/case";

/* The two verification counts as lines, for the receipt and for the verdict. Counts, never a percentage. */
export function verificationLines(investigation: Investigation, letter: Letter | null): string[] {
  const { coverage } = investigation;
  const lines = [`${coverage.supported} of ${coverage.claims} findings verified`];
  if (letter && letter.status === "done" && letter.applicable && letter.verification) lines.push(letterVerificationLine(letter.verification));
  return lines;
}

/*
  The Trust panel, set as a receipt on paper: the two verification counts
  large (findings verified; letter sentences verified and struck), never a
  percentage, with abstentions, struck findings, and failed questions each
  counted on their own; the self-check's issues found and fixed and the
  letter's verified sentences before and after it; then the itemized lines,
  each step's time and cost with the total at the foot; the models; and the
  trace when the API sends one. Per-question time and cost live in the trace.
*/
export function TrustPanel({
  investigation,
  verdict = null,
  letter = null,
  critique = null,
  annotated = false,
}: {
  investigation: Investigation;
  verdict?: Verdict | null;
  letter?: Letter | null;
  critique?: Critique | null;
  /* The finished case with a letter: at 1024px and up the receipt is a bond slip on the paper desk, the sheet's width. */
  annotated?: boolean;
}) {
  const [traceOpen, setTraceOpen] = useState(false);
  const traceId = useId();
  const { coverage, findings } = investigation;
  const notSettled = findings.filter((f) => findingStatus(f) === "not_settled").length;
  const struck = findings.filter((f) => findingStatus(f) === "unsupported").length;
  const errors = countErrors(investigation);
  // The API sends the trace as an object with a spans list; the fixture sends the list itself.
  const raw = investigation.trace;
  const spans = Array.isArray(raw) ? raw : raw && Array.isArray(raw.spans) ? raw.spans : [];
  const trace = spans.length > 0 ? spans : null;

  // Steps that have reported their usage: the investigation always, then the verdict and the letter once done.
  const steps: { name: string; cost: number; ms: number; model: string }[] = [
    { name: "investigation", cost: investigation.cost_usd, ms: investigation.latency_ms, model: investigation.model },
  ];
  if (verdict && verdict.status !== "running") steps.push({ name: "verdict", cost: verdict.cost_usd ?? 0, ms: verdict.latency_ms ?? 0, model: verdict.model });
  if (letter && letter.status !== "running") steps.push({ name: "letter", cost: letter.cost_usd ?? 0, ms: letter.latency_ms ?? 0, model: letter.model });
  if (critique && critique.status !== "running" && !critique.skipped)
    steps.push({ name: "self-check", cost: critique.cost_usd ?? 0, ms: critique.latency_ms ?? 0, model: critique.model });
  const totalCost = steps.reduce((s, x) => s + (Number.isFinite(x.cost) ? x.cost : 0), 0);
  const totalMs = steps.reduce((s, x) => s + (Number.isFinite(x.ms) ? x.ms : 0), 0);
  const models = [...new Set(steps.map((x) => x.model).filter((m): m is string => typeof m === "string" && m !== ""))];
  const costModel = models.every((m) => m === FIXTURE_MODEL) ? FIXTURE_MODEL : models.find((m) => m !== FIXTURE_MODEL);
  const split = steps.length > 1;
  const showLetter = letter !== null && letter.status === "done" && letter.applicable && letter.verification;
  const selfCheck = critique && critique.status === "done" && !critique.skipped && showLetter ? selfCheckLine(critique) : null;

  const notes: string[] = [];
  if (notSettled > 0) notes.push(`${notSettled} ${notSettled === 1 ? "finding" : "findings"} not settled by the documents.`);
  if (struck > 0) notes.push(`${struck} could not be verified and ${struck === 1 ? "is" : "are"} struck out in the findings.`);

  return (
    <section
      aria-labelledby="trust-heading"
      className={`land mt-10 border-t-4 border-ink bg-paper px-4 pt-4 pb-5 sm:px-6 ${
        annotated ? "lg:mt-16 lg:max-w-[620px] lg:border-x lg:border-b lg:border-x-hairline lg:border-b-hairline lg:bg-bond lg:px-8 lg:pt-6 lg:pb-7" : ""
      }`}
      data-trust="true"
    >
      <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${annotated ? "lg:hidden" : ""}`}>Trust</p>
      <h2 id="trust-heading" className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? "lg:mt-0 lg:text-[28px]" : ""}`}>
        {split ? "How this case was checked" : "How this investigation was checked"}
      </h2>

      <div className="mt-5 border-t border-hairline pt-4" data-coverage="true">
        <p className="text-[28px] leading-tight font-bold tabular-nums">
          {coverage.supported} of {coverage.claims} findings verified
        </p>
        {notes.length > 0 ? <p className="mt-1 text-[15px] text-muted">{notes.join(" ")}</p> : null}
        {errors > 0 ? (
          <p className="mt-1 text-[15px] font-semibold text-ink" data-errors={errors}>
            {errors === 1 ? "1 question could not be investigated." : `${errors} questions could not be investigated.`}
          </p>
        ) : null}
      </div>

      {showLetter ? (
        <div className="mt-4 border-t border-hairline pt-4">
          <p className="text-[28px] leading-tight font-bold tabular-nums" data-letter-verification="true">
            {letterVerificationLine(letter.verification)}
          </p>
          <p className="mt-1 text-[15px] text-muted">Struck sentences are shown crossed out in the letter and left out of the copy.</p>
        </div>
      ) : null}

      {selfCheck ? (
        <p className="mt-4 border-t border-hairline pt-4 text-[17px] leading-snug tabular-nums" data-selfcheck-trust="true">
          <span className="font-bold">Self-check: </span>
          {selfCheck.lead}
          {selfCheck.detail ? `; ${selfCheck.detail}` : ""}
        </p>
      ) : null}

      <table className="mt-5 w-full border-collapse text-left text-[16px] tabular-nums" data-receipt="true">
        <caption className="sr-only">Time and cost of each step, with the total</caption>
        <thead>
          <tr className="border-y border-ink">
            <th scope="col" className="py-2 pr-3 text-[14px] font-semibold text-muted">
              Step
            </th>
            <th scope="col" className="py-2 pr-3 text-right text-[14px] font-semibold text-muted">
              Time
            </th>
            <th scope="col" className="py-2 text-right text-[14px] font-semibold text-muted">
              Cost
            </th>
          </tr>
        </thead>
        <tbody>
          {steps.map((x) => (
            <tr key={x.name} className="border-b border-hairline">
              <th scope="row" className="py-2 pr-3 font-normal">
                {capitalize(x.name)}
              </th>
              <td className="py-2 pr-3 text-right whitespace-nowrap">{formatSeconds(x.ms)}</td>
              <td className="py-2 text-right">{formatCost(x.cost, x.model)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-b border-ink">
            <th scope="row" className="py-2 pr-3 font-bold">
              Total
            </th>
            <td className="py-2 pr-3 text-right font-bold whitespace-nowrap">{formatSeconds(totalMs)}</td>
            <td className="py-2 text-right font-bold" data-total-cost="true">
              {formatCost(totalCost, costModel)}
            </td>
          </tr>
        </tfoot>
      </table>
      <p className="mt-3 text-[15px] text-muted">
        {models.length > 1 ? "Models" : "Model"}:{" "}
        <span className="font-mono text-ink">{models.length > 0 ? models.join(", ") : investigation.model}</span>
      </p>

      {trace ? (
        <div className="mt-4">
          <button
            type="button"
            aria-expanded={traceOpen}
            aria-controls={traceOpen ? traceId : undefined}
            onClick={() => setTraceOpen((o) => !o)}
            className="inline-flex min-h-11 items-center rounded-sm border border-ink bg-bond px-4 text-[16px] font-semibold text-ink"
          >
            {traceOpen ? "Hide the trace" : "Show the trace"}
          </button>
          {traceOpen ? (
            <ol id={traceId} className="mt-3 divide-y divide-hairline border-t border-hairline text-[16px]" aria-label="Trace">
              {trace.map((span, i) => (
                <li key={`${span.name}-${i}`} className="flex items-baseline justify-between gap-4 py-2">
                  <span>{span.name}</span>
                  <span className="shrink-0 font-mono text-[15px] text-muted">{Math.round(span.ms)} ms</span>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

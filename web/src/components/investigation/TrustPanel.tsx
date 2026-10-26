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

/*
  The Trust panel: verification coverage as a count, never a percentage,
  with abstentions, struck findings, and failed questions each counted on
  their own;
  the letter's sentences verified and struck, as counts; the self-check's
  issues found and fixed and the letter's verified sentences before and after
  it; the cost of the case to four decimals and the time, each the sum of the
  investigation, verdict, letter, and self-check with the split shown; the
  models; and the trace when the API sends one.
*/
export function TrustPanel({
  investigation,
  verdict = null,
  letter = null,
  critique = null,
}: {
  investigation: Investigation;
  verdict?: Verdict | null;
  letter?: Letter | null;
  critique?: Critique | null;
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
  if (struck > 0) notes.push(`${struck} could not be verified and ${struck === 1 ? "is" : "are"} struck out above.`);

  return (
    <section aria-labelledby="trust-heading" className="land mt-10 border-t-4 border-ink pt-4" data-trust="true">
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Trust</p>
      <h2 id="trust-heading" className="mt-1 text-[22px] leading-tight font-bold">
        {split ? "How this case was checked" : "How this investigation was checked"}
      </h2>
      <dl className="mt-4 divide-y divide-hairline border-b border-hairline">
        <Row label="Verification coverage">
          <span className="font-bold">
            {coverage.supported} of {coverage.claims} findings verified
          </span>
          {notes.length > 0 ? <span className="mt-1 block text-[15px] text-muted">{notes.join(" ")}</span> : null}
          {errors > 0 ? (
            <span className="mt-1 block text-[15px] font-semibold text-ink" data-errors={errors}>
              {errors === 1 ? "1 question could not be investigated." : `${errors} questions could not be investigated.`}
            </span>
          ) : null}
        </Row>
        {showLetter ? (
          <Row label="Appeal letter">
            <span className="font-bold" data-letter-verification="true">
              {letterVerificationLine(letter.verification)}
            </span>
            <span className="mt-1 block text-[15px] text-muted">Struck sentences are shown crossed out in the letter and left out of the copy.</span>
          </Row>
        ) : null}
        {selfCheck ? (
          <Row label="Self-check">
            <span className="font-bold" data-selfcheck-trust="true">
              {selfCheck.lead}
              {selfCheck.detail ? `; ${selfCheck.detail}` : ""}
            </span>
          </Row>
        ) : null}
        <Row label="Cost of this case">
          <span data-total-cost="true">{formatCost(totalCost, costModel)}</span>
          {split ? (
            <span className="mt-1 block text-[15px] text-muted">
              {steps.map((x) => `${capitalize(x.name)} ${formatCost(x.cost, x.model)}`).join(", ")}
            </span>
          ) : null}
        </Row>
        <Row label="Time taken">
          {formatSeconds(totalMs)}
          {split ? (
            <span className="mt-1 block text-[15px] text-muted">{steps.map((x) => `${capitalize(x.name)} ${formatSeconds(x.ms)}`).join(", ")}</span>
          ) : null}
        </Row>
        <Row label={models.length > 1 ? "Models" : "Model"}>
          <span className="font-mono text-[16px]">{models.length > 0 ? models.join(", ") : investigation.model}</span>
        </Row>
      </dl>
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

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
      <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">{label}</dt>
      <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{children}</dd>
    </div>
  );
}

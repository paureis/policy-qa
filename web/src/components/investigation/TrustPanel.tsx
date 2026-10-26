"use client";

import { useId, useState } from "react";
import { formatCost, formatSeconds, type Investigation } from "@/lib/case";

/*
  The Trust panel: verification coverage as a count, never a percentage;
  the cost of the case to four decimals; the time; the model; and the trace
  when the API sends one.
*/
export function TrustPanel({ investigation }: { investigation: Investigation }) {
  const [traceOpen, setTraceOpen] = useState(false);
  const traceId = useId();
  const { coverage, findings } = investigation;
  const notSettled = findings.filter((f) => f.status === "not_settled").length;
  const struck = findings.filter((f) => f.status === "unsupported").length;
  // The API sends the trace as an object with a spans list; the fixture sends the list itself.
  const raw = investigation.trace;
  const spans = Array.isArray(raw) ? raw : raw && Array.isArray(raw.spans) ? raw.spans : [];
  const trace = spans.length > 0 ? spans : null;

  const notes: string[] = [];
  if (notSettled > 0) notes.push(`${notSettled} ${notSettled === 1 ? "finding" : "findings"} not settled by the documents.`);
  if (struck > 0) notes.push(`${struck} could not be verified and ${struck === 1 ? "is" : "are"} struck out above.`);

  return (
    <section aria-labelledby="trust-heading" className="mt-10 border-t-4 border-ink pt-4" data-trust="true">
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Trust</p>
      <h2 id="trust-heading" className="mt-1 text-[22px] leading-tight font-bold">
        How this investigation was checked
      </h2>
      <dl className="mt-4 divide-y divide-hairline border-b border-hairline">
        <Row label="Verification coverage">
          <span className="font-bold">
            {coverage.supported} of {coverage.claims} findings verified
          </span>
          {notes.length > 0 ? <span className="mt-1 block text-[15px] text-muted">{notes.join(" ")}</span> : null}
        </Row>
        <Row label="Cost of this case">{formatCost(investigation.cost_usd)}</Row>
        <Row label="Time taken">{formatSeconds(investigation.latency_ms)}</Row>
        <Row label="Model">
          <span className="font-mono text-[16px]">{investigation.model}</span>
        </Row>
      </dl>
      {trace ? (
        <div className="mt-4">
          <button
            type="button"
            aria-expanded={traceOpen}
            aria-controls={traceId}
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

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-3 sm:grid sm:grid-cols-[200px_minmax(0,1fr)] sm:gap-4">
      <dt className="text-[14px] font-semibold tracking-wide text-muted uppercase sm:pt-1">{label}</dt>
      <dd className="mt-1 text-[18px] leading-snug sm:mt-0 lg:text-[17px]">{children}</dd>
    </div>
  );
}

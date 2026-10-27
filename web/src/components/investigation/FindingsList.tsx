"use client";

import type { ReactNode } from "react";
import { JURISDICTION_HEADINGS, groupFindings, type Finding, type Route } from "@/lib/case";
import { FindingCard } from "./FindingCard";
import { APPENDIX, APPENDIX_H2, SectionTitle } from "./SectionTitle";

/*
  Findings in arrival order, newest at the bottom. A dual case groups them
  by jurisdiction with the jurisdiction as a subheading: side by side at
  desktop width, stacked on the phone.

  While the case runs, the list sits under the progress line as "Findings"
  (the live run is the show). Once the outcome is reached the page reads
  outcome first and the list becomes the closing section, "How the case was
  investigated", with the route line as its lead (appendix). Both are the
  same element tree, only the heading, the lead, and the classes change, so
  the switch never remounts a finding: open quotes and focus survive it.

  annotated: the finished case with a letter at 1024 px and up. The record
  takes the appendix register (a 1 px rule, a 20 px title) and is compact:
  each finding shows its question and the answer's first sentence, and the
  question opens the full answer and its citations.
*/
export function FindingsList({
  findings,
  route,
  appendix = false,
  lead = null,
  annotated = false,
  n = null,
}: {
  findings: Finding[];
  route: Route | null;
  appendix?: boolean;
  lead?: ReactNode;
  annotated?: boolean;
  /* The section's number at desktop on the finished case. */
  n?: number | null;
}) {
  const dual = route?.dual === true;
  if (findings.length === 0) return null;
  const order = route?.jurisdictions?.length ? route.jurisdictions : undefined;
  const record = annotated && appendix;

  return (
    <section
      aria-labelledby="findings-heading"
      className={appendix ? `land mt-10 border-t-4 border-ink pt-4 ${annotated ? APPENDIX : ""}` : "mt-6"}
      data-findings={appendix ? "appendix" : "live"}
    >
      {appendix ? <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${annotated ? "lg:hidden" : ""}`}>Investigation</p> : null}
      <h2
        id="findings-heading"
        className={appendix ? `mt-1 text-[22px] leading-tight font-bold ${annotated ? APPENDIX_H2 : ""}` : "text-[20px] font-bold"}
      >
        <SectionTitle title={appendix ? "How the case was investigated" : "Findings"} short="Investigation record" n={record ? n : null} />
      </h2>
      {appendix ? lead : null}
      <div className={dual ? "mt-4 lg:grid lg:grid-cols-2 lg:gap-x-10" : appendix ? "mt-4" : ""} aria-live={appendix ? undefined : "polite"}>
        {dual
          ? groupFindings(findings, order).map((g) => (
              <div key={g.jurisdiction} className="mb-8 lg:mb-0" data-jurisdiction={g.jurisdiction}>
                <h3 className="text-[20px] font-bold">{JURISDICTION_HEADINGS[g.jurisdiction]}</h3>
                {g.findings.map((f) => (
                  <FindingCard key={f.id} finding={f} level={4} />
                ))}
              </div>
            ))
          : findings.map((f) => <FindingCard key={f.id} finding={f} record={record} />)}
      </div>
    </section>
  );
}

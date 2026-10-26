"use client";

import { JURISDICTION_LABELS, groupFindings, type Finding, type Route } from "@/lib/case";
import { FindingCard } from "./FindingCard";

/*
  Findings in arrival order, newest at the bottom. A dual case groups them
  by jurisdiction with the jurisdiction as the heading: side by side at
  desktop width, stacked on the phone.
*/
export function FindingsList({ findings, route }: { findings: Finding[]; route: Route | null }) {
  const dual = route?.dual === true;
  if (findings.length === 0) return null;

  if (!dual) {
    return (
      <section aria-label="Findings" className="mt-6" aria-live="polite">
        <h2 className="text-[20px] font-bold">Findings</h2>
        {findings.map((f) => (
          <FindingCard key={f.id} finding={f} />
        ))}
      </section>
    );
  }

  const order = route?.jurisdictions?.length ? route.jurisdictions : undefined;
  const groups = groupFindings(findings, order);
  return (
    <section aria-label="Findings" className="mt-6 lg:grid lg:grid-cols-2 lg:gap-x-10" aria-live="polite">
      {groups.map((g) => (
        <div key={g.jurisdiction} className="mb-8 lg:mb-0" data-jurisdiction={g.jurisdiction}>
          <h2 className="text-[20px] font-bold">{JURISDICTION_LABELS[g.jurisdiction]}</h2>
          {g.findings.map((f) => (
            <FindingCard key={f.id} finding={f} />
          ))}
        </div>
      ))}
    </section>
  );
}

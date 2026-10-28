"use client";

import type { ReactNode } from "react";
import { JURISDICTION_HEADINGS, groupFindings, type Finding, type Route } from "@/lib/case";
import { FindingCard } from "./FindingCard";
import { useDesktop } from "./PageViewer";
import { APPENDIX_H2, IN_SHEET, PHONE_SHEET, PHONE_SHEET_ONLY, SHEET_HEAD, SectionTitle } from "./SectionTitle";

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

  folder (Oct 27, piece 3): the record sheet at 1024 px and up from the first
  poll. The list is the record from the start: its head reads "Investigation
  record" (the number comes with the tabs when the chain finishes), the route
  line is its lead, and the findings land one by one in a 640 px column in
  the record's compact form; when the chain finishes the column lifts to the
  record's full layout (a finding with struck citations takes two columns).
  The section is mounted before the first finding at desktop (display: none
  under 1024 px, where the phone shows nothing until a finding exists), so no
  finding and no heading remounts. Classes only; the phone is unchanged.
*/
export function FindingsList({
  findings,
  route,
  appendix = false,
  lead = null,
  annotated = false,
  folder = false,
  n = null,
}: {
  findings: Finding[];
  route: Route | null;
  appendix?: boolean;
  lead?: ReactNode;
  annotated?: boolean;
  /* The folder layout at 1024 px and up (every status after intake). */
  folder?: boolean;
  /* The section's number at desktop on the finished case. */
  n?: number | null;
}) {
  const dual = route?.dual === true;
  /* At desktop the land is each finding's own, not the whole record's when the outcome first renders. */
  const desktop = useDesktop();
  if (findings.length === 0 && !folder) return null;
  const order = route?.jurisdictions?.length ? route.jurisdictions : undefined;
  const record = annotated && appendix;
  const phoneSheet = folder ? PHONE_SHEET_ONLY : PHONE_SHEET;
  const phone = appendix ? `${folder && desktop ? "" : "land"} mt-10 ${phoneSheet}` : `mt-6 ${phoneSheet}`;
  const desk = folder ? `lg:border-t lg:border-ink lg:pt-3 ${IN_SHEET}` : "";

  return (
    <section
      aria-labelledby="findings-heading"
      className={`${phone} ${desk} ${findings.length === 0 ? "max-lg:hidden" : ""}`}
      data-findings={appendix ? "appendix" : "live"}
    >
      {appendix ? <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${folder ? "lg:hidden" : ""}`}>Investigation</p> : null}
      <h2
        id="findings-heading"
        className={`${appendix ? "mt-1 text-[22px] leading-tight font-bold" : "text-[20px] font-bold"} ${folder ? `${APPENDIX_H2} ${SHEET_HEAD}` : ""}`}
      >
        <SectionTitle title={appendix ? "How the case was investigated" : "Findings"} short="Investigation record" n={record ? n : null} deskShort={folder} />
      </h2>
      {/* The route line leads the record: on the phone once the outcome leads, at desktop from the start. */}
      <div className={appendix ? "" : "hidden lg:block"}>{lead}</div>
      <div
        className={`${dual ? "mt-4 lg:grid lg:grid-cols-2 lg:gap-x-10" : appendix ? "mt-4" : ""} ${
          folder && !dual ? `lg:mt-4 ${annotated ? "" : "lg:max-w-[640px]"}` : ""
        }`}
        aria-live={appendix ? undefined : "polite"}
        data-record-column={folder && !dual ? (annotated ? "full" : "640") : undefined}
      >
        {dual
          ? groupFindings(findings, order).map((g) => (
              <div key={g.jurisdiction} className="mb-8 lg:mb-0" data-jurisdiction={g.jurisdiction}>
                <h3 className="text-[20px] font-bold">{JURISDICTION_HEADINGS[g.jurisdiction]}</h3>
                {g.findings.map((f) => (
                  <FindingCard key={f.id} finding={f} level={4} />
                ))}
              </div>
            ))
          : findings.map((f) => <FindingCard key={f.id} finding={f} record={folder} wide={record} />)}
      </div>
    </section>
  );
}

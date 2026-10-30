"use client";

import { useSyncExternalStore } from "react";
import { formatShortDate, parseIsoDate, type PageHighlight, type VisionCheck } from "@/lib/case";
import { SAMPLE_PAGES, SAMPLE_RECORD } from "@/lib/sample-case";
import { DeadlineLine } from "@/components/intake/DeadlineStamp";
import { TOP_SHEET } from "@/components/intake/Frame";
import { PhoneLead } from "@/components/investigation/CaseHeader";
import { PageViewerFrame, PageViewerProvider } from "@/components/investigation/PageViewer";
import { verificationLines } from "@/components/investigation/TrustPanel";
import { ExhibitPair, type SettledExhibit } from "@/components/verdict/ExhibitPair";
import { ProofCounts, SecondOpinionMark, VerdictStamp } from "@/components/verdict/VerdictSection";

/*
  The landing's proof (case-page-brief section 18, L1 to L11): a second bond sheet under the top sheet, holding
  the public sample as it stands at the end of its recorded run (SAMPLE_RECORD, the record c_sample replays):
  the head line, the verdict stamp as an h2 already pressed, the Lead line, the counts as marks one per line,
  the second opinion, then the exhibit pair as the case page renders it at reviewed. Every piece is the case
  page's own component or a piece extracted from it, fed the record the replay serves at reviewed, so the words,
  the marks, the paper clips and the highlight are the case page's. Nothing lands: the policy exhibit gets the
  recorded highlight and vision check in hand (no request), and "See the page" opens the recorded page through
  the case page's viewer on the c_sample family, which answers from the recording (no API call).
*/

const SAMPLE_ID = "c_sample";
const record = SAMPLE_RECORD;
/* The sample's record has its verdict (the replay serves it from decided on). */
const verdict = record.verdict!;
/* The counts as the case page computes them at reviewed: the findings, then the letter's sentences. */
const proof = verificationLines(record.investigation!, record.letter ?? null);
/* The rule's first citation is the policy exhibit, as VerdictSection derives it. */
const ruleCitation = verdict.rule?.citations?.[0] ?? null;
const ruleUnsupported = verdict.rule?.unsupported === true;
/* The letter's deadline, as the case page reads it once the letter is done; the day count is computed from today. */
const deadlineIso =
  record.letter && record.letter.deadline.source !== "unknown" && typeof record.letter.deadline.date === "string" && record.letter.deadline.date !== ""
    ? record.letter.deadline.date
    : null;
/* The day the run was recorded, for the head line. */
const recordedIso = (record.created_at ?? "").slice(0, 10);

/* The policy exhibit's recorded answers, mapped as getHighlight and visionCheck map them for the sample family. */
function settledExhibit(): SettledExhibit | null {
  if (!ruleCitation) return null;
  const p = SAMPLE_PAGES.find((x) => x.doc_id === ruleCitation.doc_id && x.page === ruleCitation.page && x.quote === ruleCitation.quote);
  if (!p) return null;
  const highlight: PageHighlight = {
    doc_id: p.doc_id,
    title: p.title,
    page: p.page,
    dpi: p.dpi,
    width_px: p.width_px,
    height_px: p.height_px,
    boxes_px: p.boxes_px.map((b) => ({ ...b })),
    score: p.score,
    found: p.found,
    image_url: p.image_url,
  };
  const v = p.vision;
  const vision: VisionCheck = {
    checked: v.checked,
    model: v.model,
    text_in_highlight: v.text_in_highlight ?? "",
    agrees: v.agrees ?? false,
    latency_ms: v.latency_ms ?? 0,
    cost_usd: v.cost_usd ?? 0,
    error: v.error ?? null,
  };
  /* A check that did not run is not settled: the exhibit then asks the recording as the case page does. */
  return v.checked && !v.error ? { highlight, vision } : null;
}
const settled = settledExhibit();

/*
  Today on the reader's machine. The landing is prerendered, so the server has no reader's day: before hydration
  the Lead line is laid out with the recorded day and kept invisible, then shown with today's count, in place.
*/
let clientToday: Date | null = null;
const subscribeToday = () => () => {};
const readToday = () => (clientToday ??= new Date());
const serverToday = () => null;

export function ProofSheet() {
  const today = useSyncExternalStore(subscribeToday, readToday, serverToday);
  const day = today ?? parseIsoDate(recordedIso) ?? new Date(0);
  const unseen = today ? "" : "invisible";
  return (
    <PageViewerProvider caseId={SAMPLE_ID}>
      <PageViewerFrame>
        <section
          /*
            Under 1024 px a bond sheet at the column width with the phone case page's 1 px ink edge and 20 px
            inset, 40 px under the sample links; from 1024 px the top sheet's style and width, 80 px under it
            (the case page's gap under its top sheet at 1280, measured on c_sample).
          */
          className={`mt-10 max-lg:border max-lg:border-ink max-lg:bg-bond max-lg:p-5 lg:mt-20 lg:flow-root ${TOP_SHEET}`}
          data-proof-sheet="landing"
        >
          <p className="text-[17px] leading-snug text-ink" data-proof-head="true">
            <span className="font-semibold">The sample case, decided.</span>{" "}
            <span className="text-muted max-lg:block max-lg:text-[15px]">A sample letter, run for real on {formatShortDate(recordedIso)}.</span>
          </p>
          <VerdictStamp
            verdict={verdict}
            level={2}
            pressed={false}
            /*
              The case page's sizes and measure (28, 34 from 640, 32 from 1024, 38 from 1280; the same line breaks), set
              down from the head line so its turned right end clears it: it rises about 15 px at 390, 26 at 768, 24 at 1280.
            */
            className="mt-7 text-[28px] text-balance sm:mt-9 sm:text-[34px] lg:mt-9 lg:max-w-[calc(100%-380px)] lg:text-[32px] xl:max-w-[calc(100%-480px)] xl:text-[38px]"
          />
          {/* The Lead line: the phone's under 1024 px (PhoneLead), the reference block's Lead size from 1024 px. */}
          <PhoneLead record={record} today={day} deadline={{ iso: deadlineIso, daysLeft: null }} className={`mt-5 ${unseen}`} />
          <div className={`hidden lg:mt-6 lg:block ${unseen}`} data-proof-lead="desktop">
            <DeadlineLine deadlineIso={deadlineIso} today={day} size="lead" />
          </div>
          <ProofCounts proof={proof} className="mt-5 flex flex-col gap-y-1 text-[17px] leading-snug text-ink tabular-nums lg:mt-6 lg:text-[15px]" />
          <SecondOpinionMark
            secondOpinion={record.second_opinion ?? null}
            className="mt-1 flex items-start gap-2 text-[17px] leading-snug text-ink tabular-nums lg:text-[15px]"
            markClassName="mt-1 h-4 w-4 lg:mt-0.5"
            stepTick={false}
          />
          <ExhibitPair card={record.card} citation={ruleCitation} unsupported={ruleUnsupported} settled={settled} />
        </section>
      </PageViewerFrame>
    </PageViewerProvider>
  );
}

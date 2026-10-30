import { useState } from "react";
import { NO_LETTER_LINE, critiqueFailed, findingStatus, secondOpinionLine, stageLine, type CaseRecord, type Finding, type FindingStatus } from "@/lib/case";
import { progressLine } from "./InvestigationProgress";
import { Mark, type MarkKind } from "./Marks";

/* The latest finding's mark and the words a screen reader hears for it (the mark is never the only signal). */
const LATEST_MARK: Record<FindingStatus, MarkKind> = { supported: "tick", not_settled: "ring", unsupported: "strike", error: "ring" };
const LATEST_WORDS: Record<FindingStatus, string> = {
  supported: "supported",
  not_settled: "not settled",
  unsupported: "struck, could not verify",
  error: "could not be checked",
};

/*
  The latest finding, in view during the run (Oct 28, 2026, critique fix G3): one 17 px line that reads
  the newest landed finding's question in ink with its mark (a tick for supported, an open ring for not
  settled, a strike for unsupported), so the reader sees the clerk's work land without scrolling to the
  record. One element from the first poll to the end: its words and mark change in place as findings
  land, and it holds its one-line height (24 px) while it is still empty, so its arrival moves nothing.
  Plain text, not a live region: the slip's region already says "Question 3 of 5…". At desktop it sits
  in the slip's block under the stages and folds away with the slip; on the phone the page sets it under
  the two stage lines (InvestigationView). One line: a long question ends in an ellipsis.
*/
export function LatestFinding({ findings, hidden = false, className = "" }: { findings: Finding[]; hidden?: boolean; className?: string }) {
  const latest: Finding | null = findings.length > 0 ? findings[findings.length - 1] : null;
  const status = latest ? findingStatus(latest) : null;
  return (
    <p className={`${hidden ? "hidden" : "flex"} min-h-6 items-center gap-2 text-[17px] leading-6 text-ink ${className}`} data-latest-finding={status ?? "none"}>
      {latest && status ? (
        <>
          <Mark kind={LATEST_MARK[status]} className="h-4 w-4" />
          <span className="min-w-0 truncate">
            {/* One string for the reader (no join artifacts between nodes: "? , supported"); the visible question is hidden from it. */}
            <span className="sr-only">{`Latest finding: ${latest.question.trim()}, ${LATEST_WORDS[status]}`}</span>
            <span aria-hidden="true">{latest.question}</span>
          </span>
        </>
      ) : null}
    </p>
  );
}

/*
  The letter's row on the phone's top sheet (section 17, fix round), under the counts in their idiom, 17 px
  ink, from decided to the end: one line that never changes height, so nothing under it moves after the
  stamp lands (K6). Short words of its own, one line at 360 px and up (the full stage line is the live
  region's): an open ring while a stage runs or when one stopped, a tick for a finished state. "Appeal
  letter ready." links to the letter, a 44 px target that does not grow the line, and stays through reviewed.
  Plain text, not a live region: the slip's live region announces the chain. Under 1024 px only.
*/
export function phoneStatusLine(record: CaseRecord, failure: SlipFailure | null): { text: string; mark: MarkKind; ready: boolean } {
  const letter = record.letter;
  if (failure?.step === "letter") return { text: "The letter could not be drafted.", mark: "ring", ready: false };
  if (letter?.status === "done") {
    if (!letter.applicable) return { text: "No appeal letter was drafted.", mark: "tick", ready: false };
    if (record.status === "reviewing") return { text: "Checking the letter…", mark: "ring", ready: false };
    return { text: "Appeal letter ready.", mark: "tick", ready: true };
  }
  if (record.status === "drafting") return { text: "Drafting the appeal letter…", mark: "ring", ready: false };
  return { text: "Verdict reached.", mark: "ring", ready: false };
}

export function PhoneStatus({ record, failure, href }: { record: CaseRecord; failure: SlipFailure | null; href: string | null }) {
  const { text, mark, ready } = phoneStatusLine(record, failure);
  return (
    <p className="mt-1 flex items-start gap-2 text-[17px] leading-snug text-ink lg:hidden" data-phone-status={ready ? "ready" : mark}>
      <Mark kind={mark} className={`mt-1 h-4 w-4 ${mark === "tick" ? "tick-step" : ""}`} />
      {href && ready ? (
        <a href={href} className="-my-[10.5px] inline-block truncate py-[10.5px] underline underline-offset-4" data-letter-link="true">
          {text}
        </a>
      ) : (
        <span className="min-w-0 truncate">{text}</span>
      )}
    </p>
  );
}

type StageState = "todo" | "doing" | "done" | "failed";

interface Stage {
  key: string;
  label: string;
  state: StageState;
  /* The stage's own words beside its mark: the live line while it runs, the failure words when it stopped. */
  text: string | null;
}

/* A failed step and the words the page already uses for it (the failed section's heading, or the progress line). */
export interface SlipFailure {
  step: "investigation" | "verdict" | "letter";
  words: string;
}

const STATE_WORDS: Record<StageState, string> = {
  todo: "not reached",
  doing: "in progress",
  done: "done",
  failed: "stopped",
};

/*
  The seven stages of the chain, from the case record alone (never from a
  timer), so a live case and a fixture read the same.
*/
function stages(record: CaseRecord, failure: SlipFailure | null): Stage[] {
  const inv = record.investigation;
  const verdictDone = record.verdict?.status === "done";
  const letterDone = record.letter?.status === "done";
  const noLetter = letterDone && record.letter?.applicable === false;
  const c = record.critique;
  const line = stageLine(record);
  const s = record.status;

  const routing: Stage = record.route
    ? { key: "routing", label: "Routing", state: "done", text: null }
    : { key: "routing", label: "Routing", state: "doing", text: "Working out which program governs this service." };

  const investigation: Stage =
    failure?.step === "investigation"
      ? { key: "investigation", label: "Investigation", state: "failed", text: failure.words }
      : inv?.status === "done"
        ? { key: "investigation", label: "Investigation", state: "done", text: null }
        : record.route
          ? { key: "investigation", label: "Investigation", state: "doing", text: progressLine(inv) }
          : { key: "investigation", label: "Investigation", state: "todo", text: null };

  const steelman: Stage = verdictDone
    ? { key: "steelman", label: "Steelman", state: "done", text: null }
    : s === "deciding" && failure === null
      ? { key: "steelman", label: "Steelman", state: "doing", text: line }
      : { key: "steelman", label: "Steelman", state: "todo", text: null };

  const verdict: Stage = verdictDone
    ? { key: "verdict", label: "Verdict", state: "done", text: null }
    : failure?.step === "verdict"
      ? { key: "verdict", label: "Verdict", state: "failed", text: failure.words }
      : { key: "verdict", label: "Verdict", state: "todo", text: null };

  const action: Stage = letterDone
    ? { key: "action", label: "Action", state: "done", text: noLetter ? NO_LETTER_LINE : null }
    : failure?.step === "letter"
      ? { key: "action", label: "Action", state: "failed", text: failure.words }
      : s === "drafting"
        ? { key: "action", label: "Action", state: "doing", text: line }
        : { key: "action", label: "Action", state: "todo", text: null };

  const checked = s === "reviewed" || (c !== null && c !== undefined && c.status !== "running");
  const trust: Stage = critiqueFailed(record)
    ? { key: "trust", label: "Trust", state: "failed", text: line }
    : checked
    ? { key: "trust", label: "Trust", state: "done", text: null }
    : s === "reviewing"
      ? /* Without a letter the Action stage already carries the words; the ring and the weight say this one is running. */
        { key: "trust", label: "Trust", state: "doing", text: noLetter ? null : line }
      : { key: "trust", label: "Trust", state: "todo", text: null };

  return [{ key: "intake", label: "Intake", state: "done", text: null }, routing, investigation, steelman, verdict, action, trust];
}

/* The one line a screen reader hears as the chain moves: the failure words, the stage line, or the question count. */
export function slipLine(record: CaseRecord, failure: SlipFailure | null): string {
  return failure?.words ?? stageLine(record) ?? progressLine(record.investigation);
}

/*
  The second opinion settling, as news for a live region that already exists: when this view saw
  second_opinion go from running to done or failed, its line ("Second opinion: Muse Spark Open agrees.")
  is the news until the stage line changes again, so it is announced once. When the stage line changed
  in the same poll, both are said (withLine). A case opened with the second opinion already settled
  announces nothing; the line is on the page. State is adjusted during render (React's pattern for
  state derived from a changing prop), so the news and the record commit together.
*/
export function useSecondOpinionNews(record: CaseRecord, line: string | null): { text: string; withLine: boolean } | null {
  const status = record.second_opinion?.status ?? null;
  const [seen, setSeen] = useState<{ status: string | null; line: string | null }>({ status, line });
  const [news, setNews] = useState<{ line: string | null; text: string; withLine: boolean } | null>(null);
  if (seen.status !== status || seen.line !== line) {
    setSeen({ status, line });
    const so = secondOpinionLine(record.second_opinion);
    if (seen.status === "running" && (status === "done" || status === "failed") && so) setNews({ line, text: so.text, withLine: seen.line !== line });
  }
  return news !== null && news.line === line ? { text: news.text, withLine: news.withLine } : null;
}

/*
  The routing slip: the live run's stage header on the top sheet at 1024 px
  and up (display: none under it, where the phone keeps its two lines).
  Seven stages left to right, each a drawn mark and a word: an open ring
  for a stage not reached, a tick for a stage done (it steps in), and for
  the stage in progress the ring with its live words beside it. A stage
  that stopped keeps its ring and carries the failure words. Marks only, in
  ink; nothing turns red, nothing fades.

  collapsed: the chain has finished and its last state has been on screen
  for one poll interval (the page holds it, so the Trust tick is seen).
  The slip stays in the tree with display: none and its last state is the
  band's status line (one sentence), so nothing remounts. The polite live
  region sits beside the slip, not inside it, and it is the page's one
  live region for the chain at desktop: the band line is plain text, so
  nothing is announced twice, and the last line is still heard once the
  slip is folded away. It is the same element from the first poll to the
  end.

  From 1024 to 1279 px the slip can take two rows (a long stage line wraps),
  so it holds the two-row height from the start and nothing under it moves
  when it wraps.
*/
export function RoutingSlip({
  record,
  failure,
  collapsed,
  phoneFolded = false,
}: {
  record: CaseRecord;
  failure: SlipFailure | null;
  collapsed: boolean;
  /*
    Under 1024 px the slip is the top sheet's stage list from the first poll until the verdict exists, and
    folds when the stamp is pressed (section 17, K5 and K6); from 1024 px it folds when the chain is done.
  */
  phoneFolded?: boolean;
}) {
  const list = stages(record, failure);
  const line = slipLine(record, failure);
  /* The second opinion's news, in this live region (no new one): its words alone, or after the stage line when that changed too. */
  const news = useSecondOpinionNews(record, line);
  const live = news === null ? line : news.withLine ? `${line} ${news.text}` : news.text;
  /* The phone's note under the list: the words of the stage that is running or stopped (the desktop sets them beside the stage). */
  const noted = list.find((st) => st.text && (st.state === "doing" || st.state === "failed")) ?? null;
  return (
    <>
      <div
        /* Once the verdict is pressed above it, 16 px more under the slip keeps the exhibits' paper clips clear of its rule. */
        className={
          collapsed
            ? "hidden"
            : `${phoneFolded ? "hidden" : "mt-4"} lg:mt-0 lg:block lg:clear-both lg:pt-8 ${record.verdict?.status === "done" ? "lg:pb-4" : ""}`
        }
        data-routing-slip={collapsed ? "collapsed" : "open"}
      >
        <ol
          aria-label="Case stages"
          /*
            Under 1024 px: two columns of marks (four and three, 15 px), read down the first column and then the
            second, the stage's words on their own line under the list.
          */
          className="flex flex-wrap items-center gap-x-6 gap-y-2 border-y border-hairline py-3 text-[14px] leading-6 text-ink tabular-nums max-lg:grid max-lg:grid-flow-col max-lg:grid-cols-2 max-lg:grid-rows-4 max-lg:gap-x-4 max-lg:gap-y-0.5 max-lg:py-2 max-lg:text-[15px] lg:min-h-[82px] xl:min-h-0"
        >
          {list.map((st) => (
            <li key={st.key} className="flex min-h-6 items-center gap-2" data-slip-stage={st.key} data-state={st.state}>
              <Mark kind={st.state === "done" ? "tick" : "ring"} className={`h-4 w-4 ${st.state === "done" ? "tick-step" : ""}`} />
              <span className={st.state === "doing" || st.state === "failed" ? "font-semibold" : ""}>{st.label}</span>
              <span className="sr-only">{`, ${STATE_WORDS[st.state]}`}</span>
              {st.text ? <span className="text-[17px] leading-6 max-lg:hidden">{st.text}</span> : null}
            </li>
          ))}
        </ol>
        {/*
          The running stage's words under the list on the phone, its line held from the first poll (beside the stage
          they are display: none there). Hidden from assistive technology: the live region after the slip says the
          same words, so they are heard once (fix round).
        */}
        <p aria-hidden="true" className="mt-2 min-h-6 text-[17px] leading-6 text-ink lg:hidden" data-slip-note={noted?.key ?? "none"}>
          {noted?.text ?? ""}
        </p>
        {/*
          The latest finding under the stages, from the first poll (its line reserved while empty), so the
          exhibits never move when it fills. A run that stopped before the verdict drops it (no exhibits
          exist to move): the slip's words say where it stopped, and the record holds the findings.
        */}
        <LatestFinding
          findings={record.investigation?.findings ?? []}
          hidden={failure !== null && record.verdict?.status !== "done"}
          className="mt-1 lg:mt-3"
        />
      </div>
      {/* The page's one live region for the chain at every width (the phone's own status lines are gone, section 17). */}
      <p className="sr-only" aria-live="polite" aria-atomic="true" data-slip-live="true">
        {live}
      </p>
    </>
  );
}

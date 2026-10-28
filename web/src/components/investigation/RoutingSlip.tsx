import { NO_LETTER_LINE, critiqueFailed, stageLine, type CaseRecord } from "@/lib/case";
import { progressLine } from "./InvestigationProgress";
import { Mark } from "./Marks";

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
}: {
  record: CaseRecord;
  failure: SlipFailure | null;
  collapsed: boolean;
}) {
  const list = stages(record, failure);
  return (
    <>
      <div
        /* Once the verdict is pressed above it, 16 px more under the slip keeps the exhibits' paper clips clear of its rule. */
        className={collapsed ? "hidden" : `hidden lg:block lg:clear-both lg:pt-8 ${record.verdict?.status === "done" ? "lg:pb-4" : ""}`}
        data-routing-slip={collapsed ? "collapsed" : "open"}
      >
        <ol
          aria-label="Case stages"
          className="flex flex-wrap items-center gap-x-6 gap-y-2 border-y border-hairline py-3 text-[14px] leading-6 text-ink tabular-nums lg:min-h-[82px] xl:min-h-0"
        >
          {list.map((st) => (
            <li key={st.key} className="flex min-h-6 items-center gap-2" data-slip-stage={st.key} data-state={st.state}>
              <Mark kind={st.state === "done" ? "tick" : "ring"} className={`h-4 w-4 ${st.state === "done" ? "tick-step" : ""}`} />
              <span className={st.state === "doing" || st.state === "failed" ? "font-semibold" : ""}>{st.label}</span>
              <span className="sr-only">{`, ${STATE_WORDS[st.state]}`}</span>
              {st.text ? <span className="text-[17px] leading-6">{st.text}</span> : null}
            </li>
          ))}
        </ol>
      </div>
      <p className="sr-only hidden lg:block" aria-live="polite" aria-atomic="true" data-slip-live="true">
        {slipLine(record, failure)}
      </p>
    </>
  );
}

import { countErrors, type Investigation } from "@/lib/case";

/*
  The investigation's one line, by its state: "Planning the questions…",
  "Question 3 of 6…", "5 questions investigated.", "Stopped after question 2
  of 5.". Shared by the phone's progress line and the desktop routing slip, so
  both say the same words.
*/
export function progressLine(investigation: Investigation | null): string {
  const planned = investigation?.questions_planned ?? 0;
  const done = investigation?.questions_done ?? 0;
  const running = investigation === null || investigation.status === "running";
  if (investigation === null || planned === 0) return "Planning the questions…";
  if (running) return `Question ${Math.min(done + 1, planned)} of ${planned}…`;
  if (investigation.status === "done") {
    // A question whose model call failed was not investigated; it is never counted as answered.
    const errors = countErrors(investigation);
    const investigated = Math.max(0, done - errors);
    const lead = `${investigated} ${investigated === 1 ? "question" : "questions"} investigated`;
    return errors > 0 ? `${lead}, ${errors} could not be completed.` : `${lead}.`;
  }
  return `Stopped after question ${done} of ${planned}.`;
}

/*
  One stepped line: "Question 3 of 6". It is a polite live region, so a
  screen reader hears each step without the page moving. No bar, no art.
*/
export function InvestigationProgress({ investigation, compact = false }: { investigation: Investigation | null; compact?: boolean }) {
  const planned = investigation?.questions_planned ?? 0;
  const done = investigation?.questions_done ?? 0;
  const running = investigation === null || investigation.status === "running";
  const line = progressLine(investigation);

  return (
    <div className="mt-4" data-progress={`${done}/${planned}`}>
      <p className={`text-[20px] font-bold ${compact ? "lg:text-[17px] lg:font-semibold" : ""}`} aria-live="polite" aria-atomic="true">
        {line}
      </p>
      {running ? <p className="mt-1 text-[16px] text-muted">Findings appear below as each question is answered. Keep this screen open.</p> : null}
    </div>
  );
}

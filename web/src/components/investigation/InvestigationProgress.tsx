import { countErrors, type Investigation } from "@/lib/case";

/*
  One stepped line: "Question 3 of 6". It is a polite live region, so a
  screen reader hears each step without the page moving. No bar, no art.
*/
export function InvestigationProgress({ investigation }: { investigation: Investigation | null }) {
  const planned = investigation?.questions_planned ?? 0;
  const done = investigation?.questions_done ?? 0;
  const running = investigation === null || investigation.status === "running";

  let line: string;
  if (investigation === null || planned === 0) line = "Planning the questions…";
  else if (running) line = `Question ${Math.min(done + 1, planned)} of ${planned}…`;
  else if (investigation.status === "done") {
    // A question whose model call failed was not investigated; it is never counted as answered.
    const errors = countErrors(investigation);
    const investigated = Math.max(0, done - errors);
    const lead = `${investigated} ${investigated === 1 ? "question" : "questions"} investigated`;
    line = errors > 0 ? `${lead}, ${errors} could not be completed.` : `${lead}.`;
  }
  else line = `Stopped after question ${done} of ${planned}.`;

  return (
    <div className="mt-4" data-progress={`${done}/${planned}`}>
      <p className="text-[20px] font-bold" aria-live="polite" aria-atomic="true">
        {line}
      </p>
      {running ? <p className="mt-1 text-[16px] text-muted">Findings appear below as each question is answered. Keep this screen open.</p> : null}
    </div>
  );
}

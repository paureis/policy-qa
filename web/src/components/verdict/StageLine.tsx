import { stageLine, type CaseRecord } from "@/lib/case";

/*
  The steps after the investigation, one stepped line under the question
  count: weighing the payer's side, verdict reached, drafting the letter,
  letter ready. A polite live region; the text changes, nothing fades.
*/
export function StageLine({ record }: { record: CaseRecord }) {
  const line = stageLine(record);
  const working = record.status === "deciding" || record.status === "drafting";
  return (
    <div className="mt-1" data-stage={record.status}>
      <p className="text-[20px] font-bold" aria-live="polite" aria-atomic="true">
        {line ?? ""}
      </p>
      {working ? <p className="mt-1 text-[16px] text-muted">Keep this screen open.</p> : null}
    </div>
  );
}

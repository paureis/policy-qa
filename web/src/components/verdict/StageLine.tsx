import { stageLine, stageNote, type CaseRecord } from "@/lib/case";

/*
  The steps after the investigation, one stepped line under the question
  count: weighing the payer's side, verdict reached, drafting the letter,
  letter ready, checking the letter, letter checked. A polite live region;
  the text changes, nothing fades. Once an appeal letter is ready the line is
  a link that jumps to it (letterHref), with a 46px tall hit area. inRow: the
  line sits in the status row beside the question count (its wrapper becomes
  display: contents at tablet and up), and the notes wrap to their own line at
  the row's left edge. The live region is the same element either way.
*/
export function StageLine({
  record,
  letterHref = null,
  inRow = false,
}: {
  record: CaseRecord;
  letterHref?: string | null;
  inRow?: boolean;
}) {
  const line = stageLine(record);
  const note = stageNote(record);
  const working = record.status === "deciding" || record.status === "drafting" || record.status === "reviewing";
  const noteClass = `mt-1 text-[16px] text-muted ${inRow ? "sm:basis-full" : ""}`;
  return (
    <div className={`mt-1 ${inRow ? "sm:contents" : ""}`} data-stage={record.status}>
      <p className="text-[20px] font-bold" aria-live="polite" aria-atomic="true" data-stage-line="true">
        {line && letterHref ? (
          <a href={letterHref} className="-my-2 inline-block py-2 text-ink underline decoration-2 underline-offset-4" data-letter-link="true">
            {line}
          </a>
        ) : (
          (line ?? "")
        )}
      </p>
      {note ? (
        <p className={noteClass} data-stage-note="true">
          {note}
        </p>
      ) : null}
      {working ? <p className={noteClass}>Keep this screen open.</p> : null}
    </div>
  );
}

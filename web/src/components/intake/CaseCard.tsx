"use client";

import { FIELD_ORDER, type CaseCard as CaseCardData, type FieldKey, type FieldValue } from "@/lib/case";
import { DeadlineStamp } from "./DeadlineStamp";
import { FieldRow } from "./FieldRow";

export interface CaseCardProps {
  card: CaseCardData;
  summary: string;
  flagged: ReadonlySet<FieldKey>;
  locked: boolean;
  landed: boolean;
  today: Date;
  caseId?: string;
  onChange: (key: FieldKey, value: FieldValue) => void;
  onLooksRight: (key: FieldKey) => void;
}

/*
  The case card: one plain-language reading of the letter, the postmark,
  then the ten contract fields in contract order.
*/
export function CaseCard({ card, summary, flagged, locked, landed, today, caseId, onChange, onLooksRight }: CaseCardProps) {
  const deadline = card.appeal_deadline_claimed.value;
  const deadlineIso = typeof deadline === "string" && deadline !== "" ? deadline : null;
  const payer = card.payer_name.value;
  const toCheck = flagged.size;

  return (
    <section aria-labelledby="case-card-heading" className="border-t-4 border-ink pt-4" data-locked={locked ? "true" : "false"}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">{locked ? "Case card" : "Case card, draft"}</p>
          <h1 id="case-card-heading" className="mt-1 text-[26px] leading-tight font-bold">
            {payer ? String(payer) : "Denial letter"}
          </h1>
          {caseId ? (
            <p className="mt-2 text-[16px] text-muted">
              Case <span className="font-mono text-ink">{caseId}</span>
            </p>
          ) : null}
        </div>
        <DeadlineStamp deadlineIso={deadlineIso} today={today} landed={landed} />
      </div>

      <p className="mt-5 text-[18px] leading-relaxed lg:text-[17px]">{summary}</p>

      <h2 className="mt-8 border-b border-hairline pb-2 text-[20px] font-bold">
        {locked ? "Details as confirmed" : "Check these details"}
      </h2>
      {!locked ? (
        <p className="mt-2 text-[16px] text-muted">
          {toCheck === 0
            ? "Every detail has been checked. Edit anything that is wrong."
            : `Rows marked Check were read with less certainty. Edit them or tap Looks right. ${toCheck} to go.`}
        </p>
      ) : null}

      <div>
        {FIELD_ORDER.map((key) => (
          <FieldRow
            key={key}
            fieldKey={key}
            value={card[key].value}
            flagged={flagged.has(key)}
            locked={locked}
            onChange={onChange}
            onLooksRight={onLooksRight}
          />
        ))}
      </div>
    </section>
  );
}

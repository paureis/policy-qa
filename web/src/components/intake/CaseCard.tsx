"use client";

import { FIELD_ORDER, type CaseCard as CaseCardData, type FieldKey, type FieldValue } from "@/lib/case";
import { DeadlineStamp } from "./DeadlineStamp";
import { FieldRow } from "./FieldRow";
import { PHONE_SHEET } from "@/components/investigation/SectionTitle";

export interface CaseCardProps {
  card: CaseCardData;
  summary: string;
  flagged: ReadonlySet<FieldKey>;
  locked: boolean;
  landed: boolean;
  today: Date;
  caseId?: string;
  /* h1 on the intake screen; h2 where the page already has its heading. */
  headingTag?: "h1" | "h2";
  /* false where the page already shows the deadline (the case page): one stamp per sheet. */
  stamp?: boolean;
  /* true inside a page that already draws the sheet (the case header): no sheet of its own. */
  bare?: boolean;
  onChange: (key: FieldKey, value: FieldValue) => void;
  onLooksRight: (key: FieldKey) => void;
}

/*
  The case card: one plain-language reading of the letter, the deadline stamp,
  then the ten contract fields in contract order.

  On the intake at 1024 px and up the card is the top sheet's document in the
  620 px column (case-page-brief section 12, E7): no sheet of its own (the top
  sheet is the bond and the edge), its heading at the sheet head's 28 px.
*/
const IN_DESK = "lg:border-0 lg:bg-transparent lg:px-0 lg:pt-0 lg:pb-0";
export function CaseCard({
  card,
  summary,
  flagged,
  locked,
  landed,
  today,
  caseId,
  headingTag: Heading = "h1",
  stamp = true,
  bare = false,
  onChange,
  onLooksRight,
}: CaseCardProps) {
  const deadline = card.appeal_deadline_claimed.value;
  const deadlineIso = typeof deadline === "string" && deadline !== "" ? deadline : null;
  const payer = card.payer_name.value;
  const toCheck = flagged.size;

  return (
    <section aria-labelledby="case-card-heading" className={bare ? "" : `${PHONE_SHEET} ${IN_DESK}`} data-locked={locked ? "true" : "false"}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Heading id="case-card-heading" className={`text-[26px] leading-tight font-bold ${bare ? "" : "lg:text-[28px]"}`}>
            {payer ? String(payer) : "Denial letter"}
          </Heading>
          {caseId ? (
            <p className="mt-2 text-[16px] text-muted">
              Case <span className="font-mono text-ink">{caseId}</span>
            </p>
          ) : null}
        </div>
        {stamp ? <DeadlineStamp deadlineIso={deadlineIso} today={today} landed={landed} /> : null}
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

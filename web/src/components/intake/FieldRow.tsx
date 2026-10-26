"use client";

import {
  AGE_GROUPS,
  AGE_GROUP_LABELS,
  AMOUNT_MAX,
  DENIAL_REASON_MAX,
  FIELD_HINTS,
  FIELD_LABELS,
  PROGRAMS,
  PROGRAM_LABELS,
  SERVICE_MAX,
  displayValue,
  joinDateRange,
  splitDateRange,
  type FieldKey,
  type FieldValue,
} from "@/lib/case";

const INPUT =
  "block w-full min-h-11 rounded-sm border border-edge bg-bond px-3 py-2 text-[18px] leading-snug text-ink placeholder:text-muted lg:text-[17px]";
const LABEL = "block text-[14px] font-semibold uppercase tracking-wide text-muted";

export interface FieldRowProps {
  fieldKey: FieldKey;
  value: FieldValue;
  flagged: boolean;
  locked: boolean;
  onChange: (key: FieldKey, value: FieldValue) => void;
  onLooksRight: (key: FieldKey) => void;
}

/*
  One label and one editable value. Medium and low confidence rows carry
  the gold bar and the word Check; color is never the only signal.
*/
export function FieldRow({ fieldKey, value, flagged, locked, onChange, onLooksRight }: FieldRowProps) {
  const id = `field-${fieldKey}`;
  const hintId = FIELD_HINTS[fieldKey] ? `${id}-hint` : undefined;
  const label = FIELD_LABELS[fieldKey];

  return (
    <div
      className={`relative border-b border-hairline py-4 ${flagged ? "bg-gold-wash pl-4 pr-3" : ""}`}
      data-field={fieldKey}
      data-flagged={flagged ? "true" : "false"}
    >
      {flagged ? <span aria-hidden="true" className="absolute top-0 left-0 h-full w-1.5 bg-gold" /> : null}
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={locked ? undefined : id} className={LABEL}>
          {label}
        </label>
        {flagged ? (
          <span className="rounded-sm bg-gold px-2 py-0.5 text-[13px] font-bold tracking-wide text-ink uppercase">
            Check
          </span>
        ) : null}
      </div>
      {hintId && !locked ? (
        <p id={hintId} className="mt-0.5 text-[15px] text-muted">
          {FIELD_HINTS[fieldKey]}
        </p>
      ) : null}
      <div className="mt-2">
        {locked ? (
          <p className="text-[18px] leading-snug lg:text-[17px]">{displayValue(fieldKey, value)}</p>
        ) : (
          <Control fieldKey={fieldKey} id={id} hintId={hintId} value={value} onChange={onChange} />
        )}
      </div>
      {flagged && !locked ? (
        <button
          type="button"
          onClick={() => onLooksRight(fieldKey)}
          className="mt-3 inline-flex min-h-11 items-center rounded-sm border border-ink bg-bond px-4 text-[16px] font-semibold text-ink"
        >
          Looks right
        </button>
      ) : null}
    </div>
  );
}

function Control({
  fieldKey,
  id,
  hintId,
  value,
  onChange,
}: {
  fieldKey: FieldKey;
  id: string;
  hintId?: string;
  value: FieldValue;
  onChange: (key: FieldKey, value: FieldValue) => void;
}) {
  const str = value === null ? "" : String(value);

  switch (fieldKey) {
    case "program":
      return (
        <select id={id} className={INPUT} value={str} onChange={(e) => onChange(fieldKey, e.target.value)}>
          {PROGRAMS.map((p) => (
            <option key={p} value={p}>
              {PROGRAM_LABELS[p]}
            </option>
          ))}
        </select>
      );
    case "member_age_group":
      return (
        <select id={id} className={INPUT} value={str} onChange={(e) => onChange(fieldKey, e.target.value)}>
          {AGE_GROUPS.map((g) => (
            <option key={g} value={g}>
              {AGE_GROUP_LABELS[g]}
            </option>
          ))}
        </select>
      );
    case "dates_of_service": {
      const { from, to } = splitDateRange(value);
      return (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor={id} className="mb-1 block text-[15px] text-muted">
              First day
            </label>
            <input
              id={id}
              type="date"
              className={INPUT}
              value={from}
              aria-describedby={hintId}
              onChange={(e) => onChange(fieldKey, joinDateRange(e.target.value, to))}
            />
          </div>
          <div>
            <label htmlFor={`${id}-to`} className="mb-1 block text-[15px] text-muted">
              Last day (if a range)
            </label>
            <input
              id={`${id}-to`}
              type="date"
              className={INPUT}
              value={to}
              min={from || undefined}
              onChange={(e) => onChange(fieldKey, joinDateRange(from, e.target.value))}
            />
          </div>
        </div>
      );
    }
    case "amount_billed":
      return (
        <div className="relative">
          <span aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted">
            $
          </span>
          <input
            id={id}
            type="number"
            inputMode="decimal"
            min={0}
            max={AMOUNT_MAX}
            step="0.01"
            className={`${INPUT} pl-7`}
            value={str}
            aria-describedby={hintId}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") return onChange(fieldKey, null);
              const n = Number(raw);
              onChange(fieldKey, Number.isNaN(n) ? null : Math.min(n, AMOUNT_MAX));
            }}
          />
        </div>
      );
    case "denial_reason":
      return (
        <textarea
          id={id}
          rows={3}
          maxLength={DENIAL_REASON_MAX}
          className={INPUT}
          value={str}
          aria-describedby={hintId}
          onChange={(e) => onChange(fieldKey, e.target.value)}
        />
      );
    case "letter_date":
    case "appeal_deadline_claimed":
      return (
        <input
          id={id}
          type="date"
          className={INPUT}
          value={str}
          onChange={(e) => onChange(fieldKey, e.target.value === "" ? null : e.target.value)}
        />
      );
    case "service":
      return (
        <input
          id={id}
          type="text"
          maxLength={SERVICE_MAX}
          className={INPUT}
          value={str}
          aria-describedby={hintId}
          onChange={(e) => onChange(fieldKey, e.target.value)}
        />
      );
    default:
      return (
        <input
          id={id}
          type="text"
          className={INPUT}
          value={str}
          aria-describedby={hintId}
          onChange={(e) => onChange(fieldKey, e.target.value)}
        />
      );
  }
}

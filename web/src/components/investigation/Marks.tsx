/*
  The world's marks for state, drawn, one stroke weight, in ink: a tick for
  verified, a strike for struck, an open ring for not settled or still
  checking. The words beside a mark carry the meaning; the mark is never the
  only signal. A paper clip holds a clipped sheet.
*/
export type MarkKind = "tick" | "strike" | "ring";

export function Mark({ kind, className = "h-4 w-4" }: { kind: MarkKind; className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" className={`shrink-0 text-ink ${className}`} data-mark={kind}>
      {kind === "tick" ? (
        <path d="M2.5 8.5l3.6 3.6L13.5 4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="square" />
      ) : kind === "strike" ? (
        <>
          <path d="M2 8h12" stroke="currentColor" strokeWidth="2.2" />
          <path d="M4 4.5h8M4 11.5h8" stroke="currentColor" strokeWidth="1" opacity=".5" />
        </>
      ) : (
        <circle cx="8" cy="8" r="5.2" fill="none" stroke="currentColor" strokeWidth="2" />
      )}
    </svg>
  );
}

/*
  A drawn paper clip, wire in ink at a light weight, set over the top edge
  of a clipped sheet. Decorative: aria-hidden, no pointer events.
*/
export function PaperClip({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 52"
      aria-hidden="true"
      focusable="false"
      className={`pointer-events-none absolute h-[52px] w-5 text-ink ${className}`}
      data-clip="true"
    >
      <path
        d="M6 16V8.5a4 4 0 0 1 8 0V40a6.5 6.5 0 0 1-13 0V12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity=".72"
      />
      <path d="M6 16v22a3 3 0 0 0 6 0V14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".72" />
    </svg>
  );
}

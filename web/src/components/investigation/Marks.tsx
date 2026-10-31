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
  The calendar leaf: the deadline's mark where the deadline is the Lead line (section 19, M4), a page of a
  wall calendar in the marks' hand: the leaf as a square-cornered frame, the header rule across its top,
  two binding rings over the top edge, ink, 2 px strokes with square caps. Two sizes, each drawn on its own
  pixel grid so the stroke stays 2 px (redrawn, not scaled): 16 by 16 px, the marks' size, on the phone's
  Lead; 20 by 20 px beside the 30 px Lead type from 1024 px, the slot the ring had there (Alvaro, Oct 30).
  Unlike the state marks it is not a state: it names what the line beside it is, so it carries reader text
  ("Deadline") and the words after it carry the date. The open ring stays the mark for not settled or not
  reached.
*/
export function CalendarLeaf({ size = 16, className = "h-4 w-4", label = "Deadline" }: { size?: 16 | 20; className?: string; label?: string }) {
  return (
    <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label} focusable="false" className={`shrink-0 text-ink ${className}`} data-mark="calendar">
      {size === 20 ? (
        <>
          <path d="M2 5h16v13H2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="miter" />
          <path d="M2 10h16" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M6 2v3M14 2v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
        </>
      ) : (
        <>
          <path d="M2 4h12v10H2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="miter" />
          <path d="M2 8h12" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M5 2v2M11 2v2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
        </>
      )}
    </svg>
  );
}

/*
  The disclosure mark beside a control that opens and closes: a drawn plus
  when closed, a drawn minus when open, in the marks' stroke. The control's
  aria-expanded carries the state; the mark is decorative.
*/
export function Disclosure({ open, className = "h-3.5 w-3.5" }: { open: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" className={`shrink-0 text-current ${className}`} data-mark={open ? "minus" : "plus"}>
      <path d="M2.5 8h11" stroke="currentColor" strokeWidth="2" />
      {open ? null : <path d="M8 2.5v11" stroke="currentColor" strokeWidth="2" />}
    </svg>
  );
}

/*
  Corner marks: four small ink corners inside a clipped sheet, the way plates
  are marked for trimming. Decorative.
*/
export function CornerMarks() {
  const c = "pointer-events-none absolute h-2.5 w-2.5 border-ink/60";
  return (
    <>
      <span aria-hidden="true" className={`${c} top-2 left-2 border-t border-l`} />
      <span aria-hidden="true" className={`${c} top-2 right-2 border-t border-r`} />
      <span aria-hidden="true" className={`${c} bottom-2 left-2 border-b border-l`} />
      <span aria-hidden="true" className={`${c} right-2 bottom-2 border-r border-b`} />
    </>
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

/*
  A top-level section's title and, on the finished case with a letter at
  1024 px and up, its opening: the section's number, small and tabular, then
  the short title, on one line under the heavy ink rule the section carries.
  On the phone, and on every page without a letter, the plain title. The same
  three elements either way (classes only), so nothing remounts when the
  letter lands.

  The number is a CSS counter (reset on the case wrapper, see SECTION_COUNTER),
  so a section that is absent (a self-check still running, or skipped) never
  leaves a gap in the sequence. Chrome and the screen readers we test read
  generated content, so the heading's name is "2. Appeal letter".
*/
export function SectionTitle({ title, short, numbered }: { title: string; short: string; numbered: boolean }) {
  return (
    <>
      <span
        className={
          numbered
            ? "hidden lg:inline lg:text-[17px] lg:font-semibold lg:tabular-nums lg:[counter-increment:case-section] lg:before:content-[counter(case-section)]"
            : "hidden"
        }
        data-section-number="true"
      >
        <span className="sr-only">. </span>
      </span>
      <span className={numbered ? "lg:hidden" : ""}>{title}</span>
      <span className={numbered ? "hidden lg:inline" : "hidden"} data-section-title={short}>
        {short}
      </span>
    </>
  );
}

/* On the element that holds every numbered section: the counter starts there. */
export const SECTION_COUNTER = "lg:[counter-reset:case-section]";

/*
  The section opening's classes at 1024 px and up: the 4 px ink rule across
  the frame, 96 px above it and 16 px under it, so the space above a section
  is clearly larger than the space under its opening. The h2 sets the number
  and the title on one baseline.
*/
export const OPENING = "lg:mt-24 lg:border-t-4 lg:border-ink lg:pt-4";
export const OPENING_H2 = "lg:mt-0 lg:flex lg:items-baseline lg:gap-3 lg:text-[28px] lg:leading-tight lg:font-bold";

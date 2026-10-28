/*
  A top-level section's title and, on the finished case with a letter at
  1024 px and up, its opening: the section's number, small and tabular, then
  the short title, on one line under the rule the section carries. On the
  phone, and on every page without a letter, the plain title. The same three
  elements either way (classes only), so nothing remounts when the letter
  lands.

  The number is real text, not generated content, so the heading's
  accessible name at desktop is "2. Appeal letter" in every screen reader.
  The page passes the numbers, so a section that is absent (a self-check
  still running, or skipped) never leaves a gap in the sequence. Under
  1024 px the number is display: none and the name is the plain title.

  deskShort (Oct 27, piece 3): a section of the folder while the case still
  runs, before the sections are numbered (the record, the receipt). At
  1024 px and up it carries the short title without a number, the way the
  finished case's sheet head reads at tabs sizes; under 1024 px the plain
  title, as before.
*/
export function SectionTitle({ title, short, n, deskShort = false }: { title: string; short: string; n: number | null; deskShort?: boolean }) {
  const numbered = n !== null;
  if (!numbered && deskShort) {
    return (
      <>
        <span className="lg:hidden">{title}</span>
        <span className="hidden lg:inline" data-section-title={short}>
          {short}
        </span>
      </>
    );
  }
  return (
    <>
      {numbered ? (
        <span aria-hidden="true" className="hidden lg:inline lg:text-[17px] lg:font-semibold lg:tabular-nums tabs:hidden" data-section-number={n}>
          {n}
        </span>
      ) : null}
      <span className={numbered ? "lg:hidden" : ""}>{title}</span>
      {numbered ? (
        <>
          <span aria-hidden="true" className="hidden lg:inline" data-section-title={short}>
            {short}
          </span>
          {/* The desktop name in one text node, so it reads "2. Appeal letter", not "2 . Appeal letter". */}
          <span className="hidden lg:sr-only lg:inline">{`${n}. ${short}`}</span>
        </>
      ) : null}
    </>
  );
}

/*
  The section opening's classes at 1024 px and up: the 4 px ink rule across
  the frame, 96 px above it and 16 px under it, so the space above a section
  is clearly larger than the space under its opening. The h2 sets the number
  and the title on one baseline.
*/
export const OPENING = "lg:mt-24 lg:border-t-4 lg:border-ink lg:pt-4 tabs:mt-20 tabs:border-t-0 tabs:pt-0";
export const OPENING_H2 = "lg:mt-0 lg:flex lg:items-baseline lg:gap-3 lg:text-[28px] lg:leading-tight lg:font-bold";

/*
  The appendix register for the closing sections (the investigation record,
  the self-check, the receipt): a 1 px ink rule instead of the 4 px one, less
  space above, and a 20 px title, so the record reads as the answer's
  apparatus, not as three more chapters.
*/
export const APPENDIX = "lg:mt-16 lg:border-t lg:border-ink lg:pt-3 tabs:border-t-0 tabs:pt-0";
export const APPENDIX_H2 = "lg:mt-0 lg:flex lg:items-baseline lg:gap-3 lg:text-[20px] lg:leading-tight lg:font-semibold";

/*
  A section set on its own bond sheet at 1024 px and up (What to send and
  where to file; the investigation record with the self-check): the sheet,
  then inside it the opening as the sections above (number and rule) under
  1280 px, and at tabs sizes the h2 as the sheet's head, 20 px, 600, with a
  hairline under it, the number on the folder's tab instead. Under 1024 px
  none of this applies.
*/
export const PHONE_SHEET = "border border-ink bg-bond px-4 pt-4 pb-5 sm:px-6";
/* The same sheet under 1024 px only, for the finished case, whose desktop sections take the folder layout above. */
export const PHONE_SHEET_ONLY = "max-lg:border max-lg:border-ink max-lg:bg-bond max-lg:px-4 max-lg:pt-4 max-lg:pb-5 sm:max-lg:px-6";
export const SHEET = "lg:mt-24 lg:border lg:border-ink lg:bg-bond lg:px-10 lg:pt-8 lg:pb-10";
export const IN_SHEET = "lg:mt-0 tabs:border-t-0 tabs:pt-0";
export const SHEET_HEAD = "tabs:block tabs:border-b tabs:border-hairline tabs:pb-3 tabs:text-[20px] tabs:font-semibold";

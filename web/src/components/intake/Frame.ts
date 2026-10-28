/*
  The folder frame the landing and the intake share with the case page at
  1024 px and up (case-page-brief section 12, E1): the band and the page
  share one width (1,152 px with 32 px of padding, so 1,088 px of content,
  the case page's numbers), the top sheet starts 101 px from the top of the
  window (the 65 px band and 36 px of ground), and the sheet is bond with a
  1 px ink edge and the 32 / 40 / 40 insets. Under 1024 px every class here
  is inert: the phone and tablet keep their one 640 px column.
*/
export const FRAME_WIDTH = "max-w-[640px] lg:max-w-[1152px] lg:px-8";
export const FRAME_MAIN = "lg:max-w-[1152px] lg:px-8 lg:pt-9 lg:pb-16";
export const TOP_SHEET = "lg:border lg:border-ink lg:bg-bond lg:px-10 lg:pt-8 lg:pb-10";

/* The intro paragraph under the sheet's head, and its 70ch cap at desktop. */
export const INTRO = "mt-3 text-[18px] leading-relaxed lg:max-w-[70ch] lg:text-[17px]";

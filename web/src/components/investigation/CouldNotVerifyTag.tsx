import { COULD_NOT_VERIFY_LABEL } from "@/lib/case";

/*
  "Could not verify" as a filled ink tag, white on ink, so it reads as a mark
  and never as a button or a field. The words carry the meaning; the strike
  beside it is reinforcement. Inline sits in a line of the letter.
*/
export function CouldNotVerifyTag({ inline = false }: { inline?: boolean }) {
  if (inline) {
    return (
      /* 14 px semibold at desktop: the type scale's floor, and 700 is kept for the verdict and the h2s. */
      <span className="inline-block bg-ink px-1.5 align-baseline text-[13px] leading-5 font-bold text-white lg:text-[14px] lg:font-semibold" data-tag="could-not-verify">
        {COULD_NOT_VERIFY_LABEL}
      </span>
    );
  }
  return (
    <p className="mt-2 inline-block bg-ink px-2 py-0.5 text-[14px] font-bold text-white lg:font-semibold" data-tag="could-not-verify">
      {COULD_NOT_VERIFY_LABEL}
    </p>
  );
}

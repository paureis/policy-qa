import Link from "next/link";
import { Band } from "@/components/intake/Band";
import { FRAME_MAIN, FRAME_WIDTH, TOP_SHEET } from "@/components/intake/Frame";
import { INTAKE_MODE } from "@/lib/case";

/*
  The landing. At 1024 px and up it is the case page's folder frame with one
  top sheet (case-page-brief section 12, E9): the h1 at the Lead size, the
  paragraph, the scope line, then the one button and one text action to the
  sample case. Under 1024 px it is the one column as before; the sample link
  is a desktop addition (E12: nothing changes under 1024 px).
*/
export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <Band sample={INTAKE_MODE === "fixture"} widthClass={FRAME_WIDTH} />
      <main className={`mx-auto w-full max-w-[640px] flex-1 px-4 pt-10 pb-16 ${FRAME_MAIN}`}>
        <div className={TOP_SHEET} data-top-sheet="landing">
          <h1 className="text-[34px] leading-tight font-bold lg:text-[30px] lg:leading-[1.12] lg:tracking-[-0.015em]">
            A coverage denial becomes a case, and the case works itself.
          </h1>
          <p className="mt-5 text-[18px] leading-relaxed lg:max-w-[70ch] lg:text-[17px]">
            Photograph the denial letter, or paste its text. Recourse reads it into a case card you check, finds the
            written rule that governs the service, and tells you whether the denial holds. If it does not, you get the
            appeal letter, the evidence list, the deadline, and where to file.
          </p>
          <p className="mt-3 text-[16px] text-muted lg:text-[15px]">
            Florida Medicaid and Medicare. Coverage and billing rules only, never medical advice.
          </p>
          <div className="lg:mt-8 lg:flex lg:flex-wrap lg:items-center lg:gap-x-8 lg:gap-y-3">
            <Link
              href="/case/new"
              className="mt-8 inline-flex min-h-12 w-full items-center justify-center bg-ink px-6 text-[18px] font-semibold text-bond sm:w-auto lg:mt-0"
            >
              Start with your letter
            </Link>
            <Link
              href="/case/c_sample"
              className="hidden min-h-11 items-center text-[17px] font-semibold underline underline-offset-4 lg:inline-flex"
            >
              See a sample case
            </Link>
            <Link
              href="/case/new#sample-letters"
              className="hidden min-h-11 items-center text-[17px] font-semibold underline underline-offset-4 lg:inline-flex"
            >
              Try a sample letter
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

import Link from "next/link";
import { Band } from "@/components/intake/Band";
import { INTAKE_MODE } from "@/lib/case";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <Band sample={INTAKE_MODE === "fixture"} />
      <main className="mx-auto w-full max-w-[640px] flex-1 px-4 pt-10 pb-16">
        <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Coverage denial appeals</p>
        <h1 className="mt-2 text-[34px] leading-tight font-bold">A coverage denial becomes a case, and the case works itself.</h1>
        <p className="mt-5 text-[18px] leading-relaxed lg:text-[17px]">
          Photograph the denial letter, or paste its text. Recourse reads it into a case card you check, finds the
          written rule that governs the service, and tells you whether the denial holds. If it does not, you get the
          appeal letter, the evidence list, the deadline, and where to file.
        </p>
        <p className="mt-3 text-[16px] text-muted">
          Florida Medicaid and Medicare. Coverage and billing rules only, never medical advice.
        </p>
        <Link
          href="/case/new"
          className="mt-8 inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-federal px-6 text-[18px] font-semibold text-white sm:w-auto"
        >
          Start with your letter
        </Link>
      </main>
    </div>
  );
}

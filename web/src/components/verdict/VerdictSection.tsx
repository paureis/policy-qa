"use client";

import { useId, useState } from "react";
import { verdictHeadline, type CitationRef, type Verdict, type VerdictOutcome } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";

/* The headline's ink: the stamp's blue for an inconsistent denial, ink when it holds, muted when unsettled. Never red or green. */
const HEADLINE_INK: Record<VerdictOutcome, string> = {
  inconsistent: "text-stamp",
  consistent: "text-ink",
  not_settled: "text-muted",
};

/*
  The verdict: one of three headlines, verbatim, as the biggest text on the
  page; the rule with its citations; the gap between the letter's reason and
  the rule; what would change it; and, one tap away, the payer's best
  argument. A rule or steelman the verifier could not support is struck out
  on screen with "Could not verify", never hidden. The verification counts
  (proof) sit under the headline, so the proof is read with the claim.
*/
export function VerdictSection({
  verdict,
  changeShownBelow = false,
  proof = [],
  first = false,
}: {
  verdict: Verdict;
  changeShownBelow?: boolean;
  proof?: string[];
  /* The page reads outcome first: the verdict sits right under the status line, a little closer. */
  first?: boolean;
}) {
  const [steelOpen, setSteelOpen] = useState(false);
  const steelId = useId();
  const outcome = verdict.outcome;
  const ink = HEADLINE_INK[outcome] ?? "text-ink";

  return (
    <section aria-labelledby="verdict-heading" className={`land ${first ? "mt-8" : "mt-10"} border-t-4 border-ink pt-4`} data-verdict={outcome}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Verdict</p>
      <h2 id="verdict-heading" className="mt-1 text-[22px] leading-tight font-bold">
        What the documents say
      </h2>

      <p
        className={`stamp-in mt-4 border-l-[6px] border-current pl-4 text-[32px] leading-[1.15] font-bold tracking-tight sm:text-[38px] ${ink}`}
        data-headline={outcome}
      >
        {verdictHeadline(verdict)}
      </p>
      {proof.length > 0 ? (
        <p className="mt-3 pl-[22px] text-[18px] leading-snug font-semibold text-ink tabular-nums lg:text-[17px]" data-verdict-proof="true">
          {proof.map((line, i) => (
            <span key={line}>
              {i > 0 ? (
                <span aria-hidden="true" className="px-2 text-muted">
                  ·
                </span>
              ) : null}
              <span className="whitespace-nowrap max-[400px]:whitespace-normal">{line}</span>
              {i < proof.length - 1 ? <span className="sr-only">. </span> : null}
            </span>
          ))}
        </p>
      ) : null}

      <div className="mt-6 border-t border-hairline pt-4">
        <h3 className="text-[18px] font-bold">The rule</h3>
        <Claim text={verdict.rule?.statement ?? ""} unsupported={verdict.rule?.unsupported === true} citations={verdict.rule?.citations ?? []} />
      </div>

      <div className="mt-5 border-t border-hairline pt-4">
        <h3 className="text-[18px] font-bold">The gap</h3>
        <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.gap}</p>
      </div>

      {/* For a denial that holds, Action shows this as "What would have made it covered"; it is not repeated here. */}
      {verdict.what_would_change?.trim() && !changeShownBelow ? (
        <div className="mt-5 border-t border-hairline pt-4" data-what-would-change="true">
          <h3 className="text-[18px] font-bold">What would change it</h3>
          <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.what_would_change}</p>
        </div>
      ) : null}

      <div className="mt-5 border-y border-hairline py-2">
        <h3 className="text-[18px] font-bold">
          <button
            type="button"
            aria-expanded={steelOpen}
            aria-controls={steelOpen ? steelId : undefined}
            onClick={() => setSteelOpen((o) => !o)}
            className="inline-flex min-h-11 w-full items-center gap-3 rounded-sm text-left"
          >
            <span aria-hidden="true" className="w-4 shrink-0 font-bold">
              {steelOpen ? "–" : "+"}
            </span>
            <span>The payer&apos;s best argument</span>
          </button>
        </h3>
        {steelOpen ? (
          <div id={steelId} className="pb-3 pl-7" data-steelman="true">
            <p className="text-[16px] text-muted">Before deciding, the agent argued the payer&apos;s side as strongly as the documents allow.</p>
            <Claim
              text={verdict.steelman?.argument ?? ""}
              unsupported={verdict.steelman?.unsupported === true}
              citations={verdict.steelman?.citations ?? []}
            />
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Claim({ text, unsupported, citations }: { text: string; unsupported: boolean; citations: CitationRef[] }) {
  if (unsupported) {
    return (
      <div className="mt-2" data-unsupported="true">
        <p className="text-[18px] leading-relaxed lg:text-[17px]">
          <s className="decoration-ink decoration-2">{text}</s>
        </p>
        <CouldNotVerifyTag />
        <p className="mt-2 text-[16px] text-muted">No quote on a cited page supports this, so it is struck out and not relied on.</p>
        <CitationChips citations={citations} />
      </div>
    );
  }
  return (
    <div className="mt-2">
      <p className="text-[18px] leading-relaxed lg:text-[17px]">{text}</p>
      <CitationChips citations={citations} />
    </div>
  );
}

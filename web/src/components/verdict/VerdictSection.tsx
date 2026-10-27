"use client";

import { useId, useState } from "react";
import { verdictHeadline, type CaseCard, type CitationRef, type Verdict, type VerdictOutcome } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { OPENING_H2, SectionTitle } from "@/components/investigation/SectionTitle";
import { ExhibitPair } from "./ExhibitPair";

/* The headline's ink: the stamp's blue for an inconsistent denial, ink when it holds, muted when unsettled. Never red or green. */
const HEADLINE_INK: Record<VerdictOutcome, string> = {
  inconsistent: "text-stamp",
  consistent: "text-ink",
  not_settled: "text-muted",
};

/*
  The verdict: one of three headlines, verbatim, as the biggest text on the
  page and the page's h1 (it names the outcome); the rule with its
  citations; the gap between the letter's reason and the rule; what would
  change it; and, one tap away, the payer's best argument. A rule or
  steelman the verifier could not support is struck out on screen with
  "Could not verify", never hidden. The verification counts (proof) sit
  under the headline, so the proof is read with the claim.

  annotated: the finished case with a letter. At 1024px and up the section is
  section 1 of the page under its numbered opening ("1 Verdict"), beside the
  notice register that floats at the top right (the opening rule is drawn on
  the h2, which sits beside the float): the headline at 46 px, the two counts
  on one line, then the exhibit pair across the frame ("The letter says",
  "The policy says"), then the rule, the gap, what would change it, and the
  steelman in one column at the sheet's width. Classes only, so the block
  never remounts when the letter lands.
*/
export function VerdictSection({
  verdict,
  changeShownBelow = false,
  proof = [],
  first = false,
  annotated = false,
  n = null,
  card = null,
}: {
  verdict: Verdict;
  changeShownBelow?: boolean;
  proof?: string[];
  /* The page reads outcome first: the verdict sits right under the status line, a little closer. */
  first?: boolean;
  annotated?: boolean;
  /* The section's number at desktop on the finished case. */
  n?: number | null;
  /* The case card, for the exhibit pair's "The letter says" (annotated only). */
  card?: CaseCard | null;
}) {
  const [steelOpen, setSteelOpen] = useState(false);
  const steelId = useId();
  const outcome = verdict.outcome;
  const ink = HEADLINE_INK[outcome] ?? "text-ink";
  /* The brief's desktop scale: h3 at 20 px, weight 600 (700 is kept for the verdict and the h2s). */
  const h3 = `text-[18px] font-bold ${annotated ? "lg:text-[20px] lg:font-semibold" : ""}`;
  const ruleCitation = verdict.rule?.citations?.[0] ?? null;

  return (
    <section
      aria-labelledby="verdict-heading"
      className={`land ${first ? "mt-8" : "mt-10"} border-t-4 border-ink pt-4 ${annotated ? "lg:mt-4 lg:border-t-0 lg:pt-0" : ""}`}
      data-verdict={outcome}
    >
      <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${annotated ? "lg:hidden" : ""}`}>Verdict</p>
      <h2
        id="verdict-heading"
        className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? `${OPENING_H2} lg:border-t-4 lg:border-ink lg:pt-4` : ""}`}
      >
        <SectionTitle title="What the documents say" short="Verdict" n={annotated ? n : null} />
      </h2>

      <h1
        className={`stamp-in mt-4 border-l-[6px] border-current pl-4 text-[32px] leading-[1.15] font-bold tracking-tight sm:text-[38px] ${ink} ${
          annotated ? "lg:mt-6 lg:max-w-[26ch] lg:border-l-0 lg:pl-0 lg:text-[46px] lg:leading-[1.08] lg:text-balance" : ""
        }`}
        data-headline={outcome}
      >
        {verdictHeadline(verdict)}
      </h1>
      {proof.length > 0 ? (
        <p
          className={`mt-3 pl-[22px] text-[18px] leading-snug font-semibold text-ink tabular-nums ${annotated ? "lg:mt-4 lg:pl-0 lg:text-[18px]" : "lg:text-[17px]"}`}
          data-verdict-proof="true"
        >
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

      {annotated && card ? <ExhibitPair card={card} citation={ruleCitation} unsupported={verdict.rule?.unsupported === true} /> : null}

      {/* At desktop, annotated: one column at the sheet's width under the exhibits, read top to bottom. */}
      <div className={annotated ? "lg:mt-10 lg:max-w-[calc((100%-48px)*620/1040)] lg:clear-both" : ""} data-verdict-body="true">
        <div className={`mt-6 border-t border-hairline pt-4 ${annotated ? "lg:mt-0 lg:border-edge" : ""}`}>
          <h3 className={h3}>The rule</h3>
          <Claim text={verdict.rule?.statement ?? ""} unsupported={verdict.rule?.unsupported === true} citations={verdict.rule?.citations ?? []} />
        </div>

        <div className={`mt-5 border-t border-hairline pt-4 ${annotated ? "lg:border-edge" : ""}`}>
          <h3 className={h3}>The gap</h3>
          <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.gap}</p>
        </div>

        {/* For a denial that holds, Action shows this as "What would have made it covered"; it is not repeated here. */}
        {verdict.what_would_change?.trim() && !changeShownBelow ? (
          <div className={`mt-5 border-t border-hairline pt-4 ${annotated ? "lg:border-edge" : ""}`} data-what-would-change="true">
            <h3 className={h3}>What would change it</h3>
            <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.what_would_change}</p>
          </div>
        ) : null}

        <div className={`mt-5 border-y border-hairline py-2 ${annotated ? "lg:border-edge" : ""}`}>
          <h3 className={h3}>
            <button
              type="button"
              aria-expanded={steelOpen}
              aria-controls={steelOpen ? steelId : undefined}
              onClick={() => setSteelOpen((o) => !o)}
              className="inline-flex min-h-11 w-full items-center gap-3 rounded-sm text-left"
            >
              <span aria-hidden="true" className={`w-4 shrink-0 font-bold ${annotated ? "lg:font-semibold" : ""}`}>
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

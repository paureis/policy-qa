"use client";

import { useId, useState } from "react";
import { verdictHeadline, type CaseCard, type CitationRef, type Verdict } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { Disclosure, Mark } from "@/components/investigation/Marks";
import { OPENING_H2, PHONE_SHEET, PHONE_SHEET_ONLY, SectionTitle } from "@/components/investigation/SectionTitle";
import { ExhibitPair } from "./ExhibitPair";

/*
  A count of the proof as marks: "5 of 5 findings verified" with a tick;
  the letter's line "4 of 4 letter sentences verified; 0 struck" as a tick
  for the verified part and a strike for the struck part. The words carry
  the meaning, the mark reinforces it.
*/
function proofMarks(proof: string[]): { text: string; mark: "tick" | "strike" | "ring" }[] {
  return proof.flatMap((line) =>
    line.split("; ").map((part) => {
      if (/ struck$/.test(part)) return { text: part, mark: "strike" as const };
      /* A tick only when every item verified ("5 of 5"); an open ring when some did not ("3 of 4"). */
      const m = /^(\d+) of (\d+)\b/.exec(part);
      return { text: part, mark: m && m[1] === m[2] ? ("tick" as const) : ("ring" as const) };
    }),
  );
}

/*
  The verdict: one of three headlines, verbatim, as the page's h1 (it names
  the outcome) and its rubber stamp: red, condensed caps, turned, inked
  unevenly, the one stamp on the sheet (.stamp in globals.css); the rule with its
  citations; the gap between the letter's reason and the rule; what would
  change it; and, one tap away, the payer's best argument. A rule or
  steelman the verifier could not support is struck out on screen with
  "Could not verify", never hidden. The verification counts (proof) sit
  under the headline, so the proof is read with the claim.

  annotated: the finished case with a letter. At 1024px and up the section is
  section 1 of the page, on the top sheet, beside the reference block that
  floats at its top right: the opening ("1 Verdict", visually hidden at
  1280 px and up, where the index tab carries it), the stamp, the counts as
  marks under it, then the exhibit pair as two clipped sheets ("The letter
  says", "The policy says"), then the rule and the gap under them, each
  under its exhibit, then what would change it and the steelman. Classes
  only, so the block never remounts when the letter lands.

  changeInSheet: a finished case without a letter (not settled). At 1024 px
  and up "What would change it" is read on the explanation sheet (section 2),
  so here it is display: none from lg; on the phone it stays here as always.
*/
export function VerdictSection({
  verdict,
  changeShownBelow = false,
  changeInSheet = false,
  proof = [],
  first = false,
  annotated = false,
  n = null,
  card = null,
}: {
  verdict: Verdict;
  changeShownBelow?: boolean;
  changeInSheet?: boolean;
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
  const marks = proofMarks(proof);
  /* The desktop scale: h3 at 20 px, weight 600 (the page sets 400 and 600; the stamp alone is 850). */
  const h3 = `text-[18px] font-bold ${annotated ? "lg:text-[20px] lg:font-semibold" : ""}`;
  const ruleCitation = verdict.rule?.citations?.[0] ?? null;

  return (
    <section
      aria-labelledby="verdict-heading"
      className={`land ${first ? "mt-8" : "mt-10"} ${annotated ? `${PHONE_SHEET_ONLY} lg:mt-0` : PHONE_SHEET}`}
      data-verdict={outcome}
    >
      <h2
        id="verdict-heading"
        className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? `${OPENING_H2} lg:mt-0 lg:text-[20px] tabs:sr-only` : ""}`}
      >
        <SectionTitle title="What the documents say" short="Verdict" n={annotated ? n : null} />
      </h2>

      <h1
        className={`stamp stamp-in mt-6 text-[28px] text-balance sm:text-[34px] ${annotated ? "lg:mt-6 lg:max-w-[calc(100%-380px)] lg:text-[32px] xl:max-w-[calc(100%-480px)] xl:text-[38px] tabs:mt-3" : ""}`}
        data-headline={outcome}
      >
        {verdictHeadline(verdict)}
      </h1>
      {marks.length > 0 ? (
        <p
          className={`mt-5 flex flex-wrap gap-x-6 gap-y-1 text-[17px] leading-snug text-ink tabular-nums ${annotated ? "lg:mt-6 lg:gap-x-4 lg:text-[15px] xl:flex-nowrap" : ""}`}
          data-verdict-proof="true"
        >
          {marks.map((m, i) => (
            <span key={m.text} className="inline-flex items-center gap-2" data-proof-mark={m.mark}>
              <Mark kind={m.mark} />
              <span>{m.text}</span>
              {i < marks.length - 1 ? <span className="sr-only">. </span> : null}
            </span>
          ))}
        </p>
      ) : null}

      {annotated && card ? <ExhibitPair card={card} citation={ruleCitation} unsupported={verdict.rule?.unsupported === true} /> : null}

      {/*
        At desktop, annotated: the rule under the letter's exhibit and the gap under the policy's, on the
        exhibits' grid; what would change it and the steelman under both, at a reading measure.
      */}
      <div
        className={annotated ? "lg:clear-both lg:mt-8 lg:grid lg:grid-cols-2 lg:gap-x-10" : ""}
        data-verdict-body="true"
      >
        <div className={`mt-6 border-t border-hairline pt-4 ${annotated ? "lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}>
          <h3 className={h3}>The rule</h3>
          <Claim text={verdict.rule?.statement ?? ""} unsupported={verdict.rule?.unsupported === true} citations={verdict.rule?.citations ?? []} />
        </div>

        <div className={`mt-5 border-t border-hairline pt-4 ${annotated ? "lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}>
          <h3 className={h3}>The gap</h3>
          <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.gap}</p>
        </div>

        {/* For a denial that holds, Action shows this as "What would have made it covered"; it is not repeated here. */}
        {verdict.what_would_change?.trim() && !changeShownBelow ? (
          <div
            className={`mt-5 border-t border-hairline pt-4 ${annotated ? "lg:col-span-2 lg:mt-8 lg:max-w-[70ch]" : ""} ${changeInSheet ? "lg:hidden" : ""}`}
            data-what-would-change="true"
          >
            <h3 className={h3}>What would change it</h3>
            <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.what_would_change}</p>
          </div>
        ) : null}

        {/* With nothing between them at desktop (a case without a letter), the steelman keeps the 32 px the grid gives what would change it. */}
        <div
          className={`mt-5 border-y border-hairline py-2 ${annotated ? "lg:col-span-2 lg:max-w-[70ch]" : ""} ${
            annotated && (changeInSheet || changeShownBelow || !verdict.what_would_change?.trim()) ? "lg:mt-8" : ""
          }`}
        >
          <h3 className={h3}>
            <button
              type="button"
              aria-expanded={steelOpen}
              aria-controls={steelOpen ? steelId : undefined}
              onClick={() => setSteelOpen((o) => !o)}
              className="inline-flex min-h-11 w-full items-center gap-3 text-left"
            >
              <span aria-hidden="true" className="flex w-4 shrink-0 justify-center">
                <Disclosure open={steelOpen} />
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

"use client";

import { Fragment, useId, useState } from "react";
import { secondOpinionLine, verdictHeadline, type CaseCard, type CitationRef, type SecondOpinion, type Verdict } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { Disclosure, Mark } from "@/components/investigation/Marks";
import { OPENING_H2, PHONE_SHEET, SectionTitle } from "@/components/investigation/SectionTitle";
import { useDesktop } from "@/components/investigation/PageViewer";
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
  The steelman's first sentence, for the one-line strip on the top sheet: up to the first full stop,
  question or exclamation mark that ends the text or is followed by a space and a capital. A full stop
  that ends an abbreviation does not count: a dotted token ("U.S.", "C.F.R."), a single letter, or one
  of the abbreviations legal and policy text uses before a capital ("Fla. Admin. Code", "Dr. Reyes",
  "No. 5", "Sec. 3"). The whole argument when it has no such stop. (Oct 28, 2026: the evaluator found
  "Under 42 C.F.R. Part 409" cut to "Under 42 C.F.R.")
*/
const ABBREVIATIONS = new Set([
  "fla", "admin", "stat", "sec", "secs", "subsec", "subd", "para", "ch", "pt", "art", "reg", "regs", "rev", "supp",
  "no", "nos", "vol", "ed", "eds", "ex", "fig", "cf", "viz", "vs", "etc", "approx", "al",
  "dr", "mr", "mrs", "ms", "st", "ave", "inc", "co", "corp", "ltd", "dept", "div",
  "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
]);

function firstSentence(text: string): string {
  const t = text.trim();
  /* A closing quote or bracket after the stop belongs to the sentence ("not authorized." The plan…). */
  const stops = /[.!?]["”’')\]]*(?=\s+[A-Z"“(]|$)/g;
  let m: RegExpExecArray | null;
  while ((m = stops.exec(t)) !== null) {
    const end = m.index;
    if (t[end] === ".") {
      const word = /[A-Za-z][A-Za-z.]*$/.exec(t.slice(0, end))?.[0] ?? "";
      if (word.includes(".") || word.length === 1 || ABBREVIATIONS.has(word.toLowerCase())) continue;
    }
    return t.slice(0, end + m[0].length);
  }
  return t;
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

  folder (Oct 27, piece 3): the folder layout at 1024 px and up from the
  first poll, not only once the chain finishes. The section is mounted for
  the whole run, empty until the verdict exists, and holds the routing slip
  (slip): before the verdict the slip is all it shows; at decided the stamp
  is pressed above the slip, the counts under the stamp, and the exhibits,
  the rule and the gap take their places under the slip. One tree from the
  first poll to the end, so the slip never remounts. Under 1024 px the
  section is display: none until the verdict exists and the slip is
  display: none throughout, so the phone is unchanged.
*/
export function VerdictSection({
  verdict: maybeVerdict,
  changeShownBelow = false,
  changeInSheet = false,
  proof = [],
  first = false,
  annotated = false,
  folder = false,
  slip = null,
  n = null,
  card = null,
  secondOpinion = null,
  cardLine = null,
  lead = null,
  phoneStatus = null,
  letterPending = false,
}: {
  /* Null while the case runs before the verdict: the section then holds the slip alone. */
  verdict: Verdict | null;
  changeShownBelow?: boolean;
  changeInSheet?: boolean;
  proof?: string[];
  /* The page reads outcome first: the verdict sits right under the status line, a little closer. */
  first?: boolean;
  annotated?: boolean;
  /* The folder layout at 1024 px and up (every status after intake). */
  folder?: boolean;
  /* The routing slip and its live region (desktop only). */
  slip?: React.ReactNode;
  /* The section's number at desktop on the finished case. */
  n?: number | null;
  /* The case card, for the exhibit pair's "The letter says" (annotated only). */
  card?: CaseCard | null;
  /* The second opinion on the verdict (Muse Spark Open), shown as one line under the counts; absent, null or skipped shows nothing. */
  secondOpinion?: SecondOpinion | null;
  /*
    The phone's top sheet (section 17, under 1024 px; each node is display: none from 1024 px). cardLine: the
    case as one line, the sheet's first line while the case runs and under the counts once the verdict exists
    (keyed, so it moves without remounting). lead: the Lead line under the stamp. phoneStatus: the running
    stage's words under the counts from the verdict until the chain is done.
  */
  cardLine?: React.ReactNode;
  lead?: React.ReactNode;
  phoneStatus?: React.ReactNode;
  /*
    An appeal letter is coming (the inconsistent verdict, its letter not done yet): under 1024 px the counts hold
    the two letter lines' places from decided (unseen spacers), so the counts fill in place and nothing under
    them moves when the letter lands (section 17, fix round).
  */
  letterPending?: boolean;
}) {
  const [steelOpen, setSteelOpen] = useState(false);
  const steelId = useId();
  /*
    At desktop in the folder the section is already on the sheet (it holds the slip), so it does not
    land as a whole when the verdict arrives: the stamp is pressed, and the counts, the exhibits and
    the rule and the gap land under it; the slip stays still. On the phone the section lands as before.
  */
  const desktop = useDesktop();
  const parts = folder && desktop ? "land" : "";
  /*
    The slip is keyed, so React matches it by its key, not by its position among the section's children:
    the verdict's tree has more children before it than the pending one (the opening, the stamp, its h2,
    the counts, the second opinion line), and an index match remounted the slip at decided (found on
    Oct 28, 2026, measuring the latest-finding line's node; padding the pending tree with nulls had
    drifted out of step when the second opinion line was added).
  */
  const slipNode = <Fragment key="slip">{slip}</Fragment>;
  /* The same for the phone's card line: the sheet's first line before the verdict, under the counts after it (K6). */
  const cardLineNode = <Fragment key="card-line">{cardLine}</Fragment>;
  if (maybeVerdict === null) {
    /* Shown at every width: under 1024 px it holds the card line and the slip, the phone's top sheet during the run (K5). */
    return (
      <section data-verdict-pending="true">
        {cardLineNode}
        {slipNode}
      </section>
    );
  }
  const verdict = maybeVerdict;
  const outcome = verdict.outcome;
  const marks = proofMarks(proof);
  const second = secondOpinionLine(secondOpinion);
  /* The desktop scale: h3 at 20 px, weight 600 (the page sets 400 and 600; the stamp alone is 850). */
  const h3 = `text-[18px] font-bold ${folder ? "lg:text-[20px] lg:font-semibold" : ""}`;
  const ruleCitation = verdict.rule?.citations?.[0] ?? null;
  const steelText = verdict.steelman?.argument?.trim() ?? "";
  const steelStruck = verdict.steelman?.unsupported === true;

  return (
    <section
      aria-labelledby="verdict-h2"
      /*
        In the folder the section is part of the top sheet at every width (section 17): under 1024 px the sheet
        is the page's top sheet, so the section has no sheet, no margin and no land of its own; the stamp's
        press is the one motion at decided (K6).
      */
      className={folder ? "" : `land ${first ? "mt-8" : "mt-10"} ${PHONE_SHEET}`}
      data-verdict={outcome}
    >
      {/*
        The section's opening as it is seen (the plain title on the phone, the number and "Verdict" from
        1024 px, unseen at tabs sizes where the index tab carries it), and the index tab's target. It is not
        the heading (Oct 28, 2026, critique fix G4): read before the stamp it put an h2 ahead of the page's
        h1, so it is hidden from assistive technology and the h2 below, after the h1, carries the same name.
      */}
      <p
        id="verdict-heading"
        aria-hidden="true"
        /* Under 1024 px in the folder the stamp opens the top sheet (section 17, K2), so the opening is not shown there. */
        className={`mt-1 text-[22px] leading-tight font-bold ${folder ? `max-lg:hidden ${OPENING_H2} lg:mt-0 lg:text-[20px] tabs:sr-only` : ""}`}
      >
        <SectionTitle title="What the documents say" short="Verdict" n={annotated ? n : null} />
      </p>

      <h1
        /*
          In the folder under 1024 px the stamp is the sheet's first line, set down so its turned right end (it rises
          about 15 px at 390 and 26 px at 768) stays about 14 px inside the sheet's edge: 8 px, 20 px from 640.
        */
        className={`stamp stamp-in ${folder ? "mt-2 sm:mt-5" : "mt-6"} text-[28px] text-balance sm:text-[34px] ${folder ? "lg:mt-6 lg:max-w-[calc(100%-380px)] lg:text-[32px] xl:max-w-[calc(100%-480px)] xl:text-[38px] tabs:mt-3" : ""}`}
        data-headline={outcome}
      >
        {verdictHeadline(verdict)}
      </h1>
      {/*
        The section's heading, after the h1 so the outline reads h1, h2, then the h3s (G4); unseen at every width.
        Under 1024 px in the folder it is "Verdict" (K8), the visible opening being gone there.
      */}
      <h2 id="verdict-h2" className="sr-only">
        {folder ? (
          <>
            <span className="lg:hidden">Verdict</span>
            <span className="max-lg:hidden">
              <SectionTitle title="What the documents say" short="Verdict" n={annotated ? n : null} />
            </span>
          </>
        ) : (
          <SectionTitle title="What the documents say" short="Verdict" n={annotated ? n : null} />
        )}
      </h2>
      {lead}
      {marks.length > 0 ? (
        <p
          /* One count per line under 1024 px in the folder (K2). */
          className={`${parts} mt-5 flex flex-wrap gap-x-6 gap-y-1 text-[17px] leading-snug text-ink tabular-nums ${folder ? "max-lg:flex-col lg:mt-6 lg:gap-x-4 lg:text-[15px] xl:flex-nowrap" : ""}`}
          data-verdict-proof="true"
        >
          {marks.map((m, i) => (
            <span key={m.text} className="inline-flex items-center gap-2" data-proof-mark={m.mark}>
              <Mark kind={m.mark} />
              <span>{m.text}</span>
              {i < marks.length - 1 ? <span className="sr-only">. </span> : null}
            </span>
          ))}
          {/* The letter's two count lines held while it is drafted (phone only, unseen, out of the accessibility tree). */}
          {letterPending
            ? ["0 of 0 letter sentences verified", "0 struck"].map((t) => (
                <span key={`pending-${t}`} aria-hidden="true" className="invisible inline-flex items-center gap-2 lg:hidden" data-proof-pending="true">
                  <Mark kind="ring" />
                  <span>{t}</span>
                </span>
              ))
            : null}
        </p>
      ) : null}

      {/*
        The second opinion: one line directly under the counts, at every width, a mark and the words in
        ink at the counts' size, weight and leading (15 px at desktop, 17 px on the phone) and 4 px under
        them (the counts' own row gap), so the two read as one group. It is there from decided, when the verdict stage runs again beside the letter, so
        its row arrives with the counts; it then changes its words and its mark in place (the same
        element, no land on a text change), and the tick steps in when Muse Spark Open agrees. Absent,
        null or skipped: not rendered, so a case without one looks exactly as before.
      */}
      {second ? (
        <p
          /* The mark sits centred on the first line (4 px down the phone's 23 px line, 2 px down desktop's 21 px) when the words wrap. */
          className={`${parts} mt-1 flex items-start gap-2 text-[17px] leading-snug text-ink tabular-nums ${folder ? "lg:text-[15px]" : ""}`}
          data-second-opinion={secondOpinion?.status}
          data-agrees={secondOpinion?.agrees === null || secondOpinion?.agrees === undefined ? undefined : String(secondOpinion.agrees)}
        >
          <Mark kind={second.mark} className={`mt-1 h-4 w-4 ${folder ? "lg:mt-0.5" : ""} ${second.mark === "tick" ? "tick-step" : ""}`} />
          <span>{second.text}</span>
        </p>
      ) : null}

      {phoneStatus}
      {cardLineNode}
      {slipNode}

      {folder && card ? <ExhibitPair card={card} citation={ruleCitation} unsupported={verdict.rule?.unsupported === true} className={parts} /> : null}

      {/*
        At desktop, annotated: the rule under the letter's exhibit and the gap under the policy's, on the
        exhibits' grid; what would change it and the steelman under both, at a reading measure.
      */}
      <div
        className={`${parts} ${folder ? "lg:clear-both lg:mt-8 lg:grid lg:grid-cols-2 lg:gap-x-10" : ""}`}
        data-verdict-body="true"
      >
        <div className={`mt-6 border-t border-hairline pt-4 ${folder ? "lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}>
          <h3 className={h3}>The rule</h3>
          <Claim text={verdict.rule?.statement ?? ""} unsupported={verdict.rule?.unsupported === true} citations={verdict.rule?.citations ?? []} />
        </div>

        <div className={`mt-5 border-t border-hairline pt-4 ${folder ? "lg:mt-0 lg:border-t-0 lg:pt-0" : ""}`}>
          <h3 className={h3}>The gap</h3>
          <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.gap}</p>
        </div>

        {/* For a denial that holds, Action shows this as "What would have made it covered"; it is not repeated here. */}
        {verdict.what_would_change?.trim() && !changeShownBelow ? (
          <div
            className={`mt-5 border-t border-hairline pt-4 ${folder ? "lg:col-span-2 lg:mt-8 lg:max-w-[70ch]" : ""} ${changeInSheet ? "lg:hidden" : ""}`}
            data-what-would-change="true"
          >
            <h3 className={h3}>What would change it</h3>
            <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">{verdict.what_would_change}</p>
          </div>
        ) : null}

        {/* With nothing between them at desktop (a case without a letter), the steelman keeps the 32 px the grid gives what would change it. */}
        <div
          className={`mt-5 border-y border-hairline py-2 ${folder ? "lg:col-span-2 lg:max-w-[70ch]" : ""} ${
            folder && (changeInSheet || changeShownBelow || !verdict.what_would_change?.trim()) ? "lg:mt-8" : ""
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
          {/*
            The payer's side in view (Oct 28, 2026, critique fix G2): "The payer would say" in 14 px faded ink
            and the steelman's first sentence in 17 px ink, one line, ending in an ellipsis when it is longer
            than the line; the disclosure above still opens the full argument under it. Under its heading, so
            the heading introduces it; on the phone the label sits over the sentence (a shared 326 px line
            leaves the sentence about 20 characters). A struck steelman is struck here too.
          */}
          {steelText ? (
            <p className="flex min-w-0 flex-col pb-1 pl-7 lg:flex-row lg:items-baseline lg:gap-3" data-payer-strip={steelStruck ? "struck" : "true"}>
              <span className="shrink-0 text-[14px] leading-5 text-muted">The payer would say</span>
              <span className="min-w-0 truncate text-[17px] leading-[26px] text-ink">
                {steelStruck ? (
                  <>
                    <span className="sr-only">Struck, could not verify: </span>
                    <s className="decoration-ink decoration-2">{firstSentence(steelText)}</s>
                  </>
                ) : (
                  firstSentence(steelText)
                )}
              </span>
            </p>
          ) : null}
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

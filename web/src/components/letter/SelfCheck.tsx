"use client";

import { useId, useState } from "react";
import {
  acceptedRounds,
  asClause,
  critiqueError,
  issueFixed,
  issueKindLabel,
  sentenceChanges,
  sentenceStruck,
  severityLabel,
  type Critique,
  type CritiqueIssue,
  type CritiqueRound,
  type Letter,
  type SentenceChange,
} from "@/lib/case";
import { QuoteFigure } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { APPENDIX, APPENDIX_H2, SectionTitle } from "@/components/investigation/SectionTitle";
import { InlineChip, LetterFrame } from "./AppealLetter";

/*
  Self-check: how the letter checked itself. Between the letter and the
  evidence checklist. The issues the critic found as a plain list (kind and
  severity in words, Fixed or Not fixed), then each sentence that changed as
  a before and after pair, then the first draft behind a toggle. The letter
  above stays the one people copy. A rejected revision says so and the first
  draft stands; a critic error names itself; a skipped check is one muted line.
*/
export function SelfCheck({
  critique,
  letter,
  failedReason,
  annotated = false,
  n = null,
}: {
  critique: Critique | null;
  letter: Letter;
  failedReason: string | null;
  /* The finished case with a letter at desktop: after the investigation record, at the sheet's width. */
  annotated?: boolean;
  /* The section's number at desktop on the finished case. */
  n?: number | null;
}) {
  const error = failedReason ?? critiqueError(critique);
  if (critique?.skipped && !error) {
    return (
      <p className={`land mt-8 text-[16px] text-muted ${annotated ? "lg:mt-16" : ""}`} data-selfcheck="skipped">
        Self-check skipped: {critique.reason?.trim() || "the service gave no reason."}
      </p>
    );
  }
  if (!letter.applicable) return null;
  if (error) {
    return (
      <Shell state="error" annotated={annotated} n={n}>
        <p className="mt-3 text-[18px] leading-relaxed lg:text-[17px]">The self-check could not run: {asClause(error)}.</p>
        <p className="mt-2 text-[16px] text-muted">The letter above is the first draft, checked sentence by sentence against its citations.</p>
      </Shell>
    );
  }
  if (!critique || critique.status !== "done") return null;

  const rounds = critique.rounds ?? [];
  const issues = rounds.flatMap((round) => (round.issues ?? []).map((issue) => ({ issue, round })));
  const accepted = acceptedRounds(critique);
  const changes = accepted.flatMap((r) => sentenceChanges(r.before ?? [], r.after ?? []).map((c) => ({ ...c, round: r.round })));
  const rejected = [...rounds].reverse().find((r) => !r.accepted);
  const rejectedWhy = rejected?.rejected_reason?.trim() || rejected?.error?.trim() || "";
  /* A later round that errored after an accepted one: the accepted revision stands. */
  const laterError = critique.accepted ? (critique.error?.trim() || rounds.find((r) => !r.accepted && r.error?.trim())?.error?.trim() || "") : "";
  const kept = critique.accepted && accepted.length > 0;
  const draft = letter.draft_paragraphs ?? [];
  /* The brief's desktop scale on the finished case: h3 at 20 px, weight 600. */
  const h3 = annotated ? "lg:text-[20px] lg:font-semibold" : "";

  return (
    <Shell state={kept ? "accepted" : "rejected"} annotated={annotated} n={n}>
      <p className={`mt-2 text-[16px] text-muted ${annotated ? "lg:mt-3" : ""}`}>
        {kept
          ? "A second pass read the draft for problems and revised it. The letter above is the revised one."
          : "A second pass read the draft for problems. The letter above is the first draft."}
      </p>

      <h3 className={`mt-5 text-[18px] font-bold ${h3}`}>What it found</h3>
      {issues.length > 0 ? (
        <ul className="mt-2 divide-y divide-hairline border-y border-hairline" data-issues={issues.length}>
          {issues.map(({ issue, round }, i) => (
            <IssueRow key={i} issue={issue} round={round} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[18px] leading-relaxed lg:text-[17px]">No issues found.</p>
      )}

      {!kept ? (
        <p className="mt-4 text-[18px] leading-relaxed font-semibold lg:text-[17px]" data-rejected="true">
          {rejectedWhy ? `The revision was not accepted: ${asClause(rejectedWhy)}. The first draft stands.` : "The first draft stands."}
        </p>
      ) : null}
      {kept && laterError ? (
        <p className="mt-4 text-[16px] text-muted" data-later-error="true">
          A further round could not finish: {asClause(laterError)}. The accepted revision stands.
        </p>
      ) : null}

      {kept && changes.length > 0 ? (
        <>
          <h3 className={`mt-6 text-[18px] font-bold ${h3}`}>What changed</h3>
          <ol className="mt-3 space-y-4" data-changes={changes.length}>
            {changes.map((c, i) => (
              <ChangePair key={i} change={c} order={i} round={accepted.length > 1 ? c.round : null} />
            ))}
          </ol>
        </>
      ) : null}

      {kept && draft.length > 0 ? <FirstDraft letter={letter} /> : null}
    </Shell>
  );
}

function Shell({
  state,
  annotated,
  n,
  children,
}: {
  state: "accepted" | "rejected" | "error";
  annotated: boolean;
  n: number | null;
  children: React.ReactNode;
}) {
  return (
    <section
      aria-labelledby="selfcheck-heading"
      className={`land mt-10 border-t-4 border-ink pt-4 ${annotated ? `${APPENDIX} lg:*:max-w-[620px]` : ""}`}
      data-selfcheck={state}
    >
      <p className={`text-[14px] font-semibold tracking-wide text-muted uppercase ${annotated ? "lg:hidden" : ""}`}>Self-check</p>
      <h2 id="selfcheck-heading" className={`mt-1 text-[22px] leading-tight font-bold ${annotated ? APPENDIX_H2 : ""}`}>
        <SectionTitle title="How the letter checked itself" short="Self-check" n={annotated ? n : null} />
      </h2>
      {children}
    </section>
  );
}

function IssueRow({ issue, round }: { issue: CritiqueIssue; round: CritiqueRound }) {
  const fixed = issueFixed(issue, round);
  return (
    <li className="py-3" data-issue={issue.kind} data-fixed={fixed ? "true" : "false"}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="text-[18px] leading-snug font-bold lg:text-[17px] lg:font-semibold">{issueKindLabel(issue.kind)}</p>
        {/* Plain words, no box or fill: the filled ink tag belongs to "Could not verify" only. */}
        <p className="text-[16px] leading-6 font-semibold text-ink">{fixed ? "Fixed" : "Not fixed"}</p>
      </div>
      <p className="mt-1 text-[15px] font-semibold text-ink">{severityLabel(issue.severity)}</p>
      <p className="mt-1 text-[17px] leading-relaxed">{issue.note}</p>
    </li>
  );
}

/*
  One changed sentence. The before text is struck in muted ink and carries
  "Before:" for screen readers only; the after text is plain, with its chip
  when cited. The pair steps in (transform only; reduced motion: still).
*/
function ChangePair({ change, order, round }: { change: SentenceChange & { round: number }; order: number; round: number | null }) {
  const [open, setOpen] = useState(false);
  const quoteId = useId();
  const { before, after } = change;
  const n = change.paragraph + 1;
  const kind = before && after ? "changed" : before ? "removed" : "added";
  const label = kind === "changed" ? `Changed in paragraph ${n}` : kind === "removed" ? `Removed from paragraph ${n}` : `Added to paragraph ${n}`;
  const afterStruck = after ? sentenceStruck(after) : false;
  const chip = after && !afterStruck && after.claim && after.citation ? after.citation : null;
  return (
    <li className="step-in border-l-2 border-ink py-1 pl-4" style={{ animationDelay: `${order * 60}ms` }} data-change={kind}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">
        {round !== null ? `Round ${round}: ` : ""}
        {label}
      </p>
      {before ? (
        <p className="mt-1 text-[17px] leading-relaxed text-muted" data-before="true">
          <span className="sr-only">Before: </span>
          <s className="decoration-muted decoration-2">{before.text}</s>
        </p>
      ) : null}
      {after ? (
        <p className="mt-1 text-[18px] leading-[1.9] lg:text-[17px]" data-after="true">
          <span className="sr-only">After: </span>
          {afterStruck ? (
            <>
              <s className="decoration-ink decoration-2">{after.text}</s> <CouldNotVerifyTag inline />
            </>
          ) : (
            after.text
          )}
          {chip ? (
            <>
              {" "}
              <InlineChip citation={chip} open={open} controls={quoteId} onToggle={() => setOpen((o) => !o)} />
            </>
          ) : null}
        </p>
      ) : null}
      {open && chip ? <QuoteFigure id={quoteId} citation={chip} /> : null}
    </li>
  );
}

/* The original draft, read-only, in the letter block's style. Nothing here is copied. */
function FirstDraft({ letter }: { letter: Letter }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="mt-6">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex min-h-11 w-full items-center justify-center rounded-sm border border-ink bg-bond px-4 text-[16px] font-semibold text-ink sm:w-auto"
        data-draft-toggle="true"
      >
        {open ? "Hide the first draft" : "Show the first draft"}
      </button>
      {open ? (
        <div id={id} className="step-in mt-4">
          <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">First draft</p>
          <div className="mt-2">
            <LetterFrame to={letter.to} re={letter.re} paragraphs={letter.draft_paragraphs ?? []} label="First draft of the appeal letter" kind="draft" />
          </div>
          <p className="mt-2 text-[16px] text-muted">For comparison only. Copy and download use the letter above.</p>
        </div>
      ) : null}
    </div>
  );
}

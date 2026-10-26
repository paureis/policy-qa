"use client";

import { ERROR_COPY, type IntakeError } from "@/lib/case";

export interface ErrorActions {
  onRetake: () => void;
  onChoose: () => void;
  onEditText: () => void;
  onStartOver: () => void;
  onRetry: () => void;
}

const PRIMARY =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-federal px-5 text-[18px] font-semibold text-white sm:w-auto";
const SECONDARY =
  "inline-flex min-h-12 w-full items-center justify-center rounded-sm border border-ink bg-bond px-5 text-[18px] font-semibold text-ink sm:w-auto";

/* Each error in plain words, with the one action that fixes it first. */
export function ErrorNotice({ error, actions }: { error: IntakeError; actions: ErrorActions }) {
  const copy = ERROR_COPY[error.code];
  const body = error.message || copy.body;

  return (
    <section role="alert" aria-labelledby="error-heading" className="border-t-4 border-ink pt-4" data-error={error.code}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">
        {error.code === "timeout"
          ? "Still waiting"
          : error.code === "out_of_scope"
            ? "Outside what Recourse does"
            : error.code === "not_a_denial_letter"
              ? "Not a denial letter"
              : "Could not read the letter"}
      </p>
      <h1 id="error-heading" className="mt-1 text-[26px] leading-tight font-bold">
        {copy.title}
      </h1>
      <p className="mt-4 text-[18px] leading-relaxed lg:text-[17px]">{body}</p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        {copy.action === "retake" ? (
          <>
            <button type="button" className={PRIMARY} onClick={actions.onRetake}>
              Retake
            </button>
            <button type="button" className={SECONDARY} onClick={actions.onChoose}>
              Choose a file instead
            </button>
          </>
        ) : null}
        {copy.action === "choose" ? (
          <>
            <button type="button" className={PRIMARY} onClick={actions.onChoose}>
              Choose another file
            </button>
            <button type="button" className={SECONDARY} onClick={actions.onStartOver}>
              Start over
            </button>
          </>
        ) : null}
        {copy.action === "edit_text" ? (
          <button type="button" className={PRIMARY} onClick={actions.onEditText}>
            Edit the text
          </button>
        ) : null}
        {copy.action === "start_over" ? (
          <button type="button" className={PRIMARY} onClick={actions.onStartOver}>
            Start over
          </button>
        ) : null}
        {copy.action === "retry" ? (
          <>
            <button type="button" className={PRIMARY} onClick={actions.onRetry}>
              {error.code === "timeout" ? "Retry" : "Try again"}
            </button>
            <button type="button" className={SECONDARY} onClick={actions.onStartOver}>
              Start over
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}

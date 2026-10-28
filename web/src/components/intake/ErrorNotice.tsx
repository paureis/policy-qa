"use client";

import { ERROR_COPY, type IntakeError } from "@/lib/case";
import { PHONE_SHEET } from "@/components/investigation/SectionTitle";

export interface ErrorActions {
  onRetake: () => void;
  onChoose: () => void;
  onEditText: () => void;
  onStartOver: () => void;
  onRetry: () => void;
}

const PRIMARY =
  "inline-flex min-h-12 w-full items-center justify-center bg-ink px-5 text-[18px] font-semibold text-bond sm:w-auto";
const SECONDARY =
  "inline-flex min-h-12 w-full items-center justify-center border border-ink bg-bond px-5 text-[18px] font-semibold text-ink sm:w-auto";

/*
  At 1024 px and up the notice sits in the desk's 420 px column on the top
  sheet, where the stages were, with the letter still beside it
  (case-page-brief section 12, E6): ink on bond with a 4 px ink rule at its
  left, no sheet of its own, no red.
*/
const IN_DESK = "lg:border-y-0 lg:border-r-0 lg:border-l-4 lg:bg-transparent lg:py-1 lg:pr-0 lg:pl-6";

/* Each error in plain words, with the one action that fixes it first. */
export function ErrorNotice({ error, actions }: { error: IntakeError; actions: ErrorActions }) {
  const copy = ERROR_COPY[error.code];
  const body = error.message || copy.body;

  return (
    <section role="alert" aria-labelledby="error-heading" className={`${PHONE_SHEET} ${IN_DESK}`} data-error={error.code}>
      <h2 id="error-heading" className="text-[26px] leading-tight font-bold lg:text-[20px] lg:leading-[1.25]">
        {copy.title}
      </h2>
      <p className="mt-4 text-[18px] leading-relaxed lg:mt-3 lg:text-[17px]">{body}</p>
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

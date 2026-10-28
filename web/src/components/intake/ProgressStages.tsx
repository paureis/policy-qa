"use client";

import { PHONE_SHEET } from "@/components/investigation/SectionTitle";
import { Mark } from "@/components/investigation/Marks";

export const STAGES = ["Reading the letter", "Finding the program", "Filling the card"] as const;

/*
  Inside the desk's 420 px column at 1024 px and up the stages are on the
  top sheet already: no sheet of their own, a 20 px heading.
*/
export const IN_DESK = "lg:border-0 lg:bg-transparent lg:px-0 lg:pt-0 lg:pb-0";

/*
  Three staged messages that step forward on a timer and hold on the last
  until the response arrives. No stepper chrome: a plain list, the current
  line in ink, finished lines ticked, the rest waiting.

  At 1024 px and up the list takes the routing slip's idiom (case-page-brief
  section 12, E5): each stage a drawn mark and its words, an open ring for a
  stage not reached or running, a tick stepped in for a stage done, the
  running stage at 600, all in ink between two hairlines; Cancel is a text
  action under it. One polite, atomic live region at every width.
*/
export function ProgressStages({ stage, onCancel }: { stage: number; onCancel: () => void }) {
  const current = STAGES[Math.min(stage, STAGES.length - 1)];
  return (
    <section aria-labelledby="progress-heading" className={`${PHONE_SHEET} ${IN_DESK}`} data-desk="stages">
      <h2 id="progress-heading" className="text-[26px] leading-tight font-bold lg:text-[20px] lg:leading-[1.25]">
        Reading your letter
      </h2>
      <p className="mt-2 text-[16px] text-muted lg:text-[15px]">This usually takes under half a minute. Keep this screen open.</p>
      <ol className="mt-6 space-y-3 lg:mt-4 lg:border-y lg:border-hairline lg:py-3" aria-label="Progress">
        {STAGES.map((label, i) => {
          const done = i < stage;
          const now = i === stage;
          return (
            <li
              key={label}
              className={`flex items-center gap-3 text-[18px] lg:min-h-6 lg:gap-2 lg:text-[17px] lg:leading-6 lg:text-ink ${now ? "font-bold text-ink" : done ? "text-muted" : "text-muted"}`}
              aria-current={now ? "step" : undefined}
              data-stage-state={done ? "done" : now ? "doing" : "todo"}
            >
              <span
                aria-hidden="true"
                className={`inline-flex h-6 w-6 shrink-0 items-center justify-center border text-[13px] font-bold lg:hidden ${
                  now ? "border-ink bg-ink text-bond" : done ? "border-ink text-ink" : "border-hairline text-muted"
                }`}
              >
                {done ? "✓" : now ? "•" : ""}
              </span>
              <Mark kind={done ? "tick" : "ring"} className={`hidden h-4 w-4 lg:block ${done ? "tick-step" : ""}`} />
              <span>
                {label}
                {now ? "…" : done ? ", done" : ""}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {current}
      </p>
      <button
        type="button"
        onClick={onCancel}
        className="mt-8 inline-flex min-h-11 items-center border border-ink bg-bond px-5 text-[16px] font-semibold text-ink lg:mt-3 lg:min-w-11 lg:border-0 lg:bg-transparent lg:px-0 lg:text-[15px] lg:underline lg:underline-offset-4"
      >
        Cancel
      </button>
    </section>
  );
}

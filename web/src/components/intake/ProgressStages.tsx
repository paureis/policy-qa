"use client";

export const STAGES = ["Reading the letter", "Finding the program", "Filling the card"] as const;

/*
  Three staged messages that step forward on a timer and hold on the last
  until the response arrives. No stepper chrome: a plain list, the current
  line in ink, finished lines ticked, the rest waiting.
*/
export function ProgressStages({ stage, onCancel }: { stage: number; onCancel: () => void }) {
  const current = STAGES[Math.min(stage, STAGES.length - 1)];
  return (
    <section aria-labelledby="progress-heading" className="border-t-4 border-ink pt-4">
      <h1 id="progress-heading" className="text-[26px] leading-tight font-bold">
        Reading your letter
      </h1>
      <p className="mt-2 text-[16px] text-muted">This usually takes under half a minute. Keep this screen open.</p>
      <ol className="mt-6 space-y-3" aria-label="Progress">
        {STAGES.map((label, i) => {
          const done = i < stage;
          const now = i === stage;
          return (
            <li
              key={label}
              className={`flex items-center gap-3 text-[18px] lg:text-[17px] ${now ? "font-bold text-ink" : done ? "text-muted" : "text-muted"}`}
              aria-current={now ? "step" : undefined}
            >
              <span
                aria-hidden="true"
                className={`inline-flex h-6 w-6 shrink-0 items-center justify-center border text-[13px] font-bold ${
                  now ? "border-ink bg-ink text-bond" : done ? "border-ink text-ink" : "border-hairline text-muted"
                }`}
              >
                {done ? "✓" : now ? "•" : ""}
              </span>
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
        className="mt-8 inline-flex min-h-11 items-center rounded-sm border border-ink bg-bond px-5 text-[16px] font-semibold text-ink"
      >
        Cancel
      </button>
    </section>
  );
}

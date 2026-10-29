import Link from "next/link";

const DEFAULT_WIDTH = "max-w-[640px] lg:max-w-[1120px]";

const FIXTURE_TITLE = "Fixture mode: every submit returns the Sunshine Health sample case";
/* The intake page in fixture mode: every submit opens the recorded run (c_sample<n>). */
const INTAKE_TITLE = "Fixture mode: every submit opens the recorded run of the Sample Health Plan letter (October 28, 2026)";
/* The one disclosure on the public sample (case-page-brief section 15, H6). */
const RECORDED_TITLE =
  "A recorded run of October 28, 2026 on a denial letter written for this demonstration. The policy pages, quotes, checks, costs and the second opinion are the API's own.";

/*
  The band at the top of every page: the folder's top edge. Kraft, the
  back of the folder showing above the front; the wordmark at the left; on
  a case, the folder's tab beside it in manila, joined to the manila ground
  below (its bottom edge is open), with the case id, the payer and the date
  the case was opened in mono; the page's links at the right. widthClass
  matches the page's content column, so the wordmark and the page share an
  edge.
  sample marks a fixture case: true for the synthetic fixtures ("sample case"), "recorded" for the
  public sample, the recorded run ("recorded run, sample letter" in the tab, "recorded run" under 640 px);
  "intake" for the intake page in fixture mode, whose submits open the recorded run.
*/
export function Band({
  sample = false,
  widthClass = DEFAULT_WIDTH,
  tab = null,
  children,
}: {
  sample?: boolean | "recorded" | "intake";
  widthClass?: string;
  /* The folder tab's text, on a case page. */
  tab?: React.ReactNode;
  children?: React.ReactNode;
}) {
  const recorded = sample === "recorded";
  const title = recorded ? RECORDED_TITLE : sample === "intake" ? INTAKE_TITLE : FIXTURE_TITLE;
  return (
    <header className="border-b border-ink/25 bg-kraft text-ink" data-band="true">
      <div className={`mx-auto flex min-h-14 w-full items-end gap-x-3 px-4 sm:gap-x-5 lg:min-h-16 ${widthClass}`}>
        <Link
          href="/"
          className="self-center py-3 text-[21px] leading-none font-bold tracking-[-0.01em] [font-stretch:88%]"
        >
          Recourse
        </Link>
        {tab ? (
          <p
            className="relative -mb-px hidden shrink-0 self-end border border-b-0 border-ink/25 bg-manila px-4 font-mono text-[14px] leading-[42px] whitespace-nowrap sm:block lg:px-6"
            data-folder-tab="true"
          >
            {tab}
            {sample ? <span title={title}>{recorded ? " · recorded run, sample letter" : " · sample case"}</span> : null}
          </p>
        ) : null}
        <div className="ml-auto flex min-w-0 items-center gap-3 self-center text-[15px]">
          {children}
          {/* Without a tab (and under 640 px, where the tab is hidden) the sample mark is plain mono text. */}
          {sample ? (
            <span
              className={`font-mono text-[14px] whitespace-nowrap ${tab ? "sm:hidden" : ""}`}
              title={title}
            >
              {recorded ? "recorded run" : "sample case"}
            </span>
          ) : null}
        </div>
      </div>
    </header>
  );
}

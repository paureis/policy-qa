import Link from "next/link";

const DEFAULT_WIDTH = "max-w-[640px] lg:max-w-[1120px]";

/*
  The band at the top of every page: the folder's top edge. Kraft, the
  back of the folder showing above the front; the wordmark at the left; on
  a case, the folder's tab beside it in manila, joined to the manila ground
  below (its bottom edge is open), with the case id, the payer and the date
  the case was opened in mono; the page's links at the right. widthClass
  matches the page's content column, so the wordmark and the page share an
  edge.
*/
export function Band({
  sample = false,
  widthClass = DEFAULT_WIDTH,
  tab = null,
  children,
}: {
  sample?: boolean;
  widthClass?: string;
  /* The folder tab's text, on a case page. */
  tab?: React.ReactNode;
  children?: React.ReactNode;
}) {
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
          </p>
        ) : null}
        <div className="ml-auto flex min-w-0 items-center gap-3 self-center text-[15px]">
          {children}
          {sample ? (
            <span
              className="border border-ink px-2 py-0.5 text-[13px] font-semibold tracking-wide uppercase sm:whitespace-nowrap"
              title="Fixture mode: every submit returns the Sunshine Health sample case"
            >
              Sample case
            </span>
          ) : null}
        </div>
      </div>
    </header>
  );
}

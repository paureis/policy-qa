import Link from "next/link";

const DEFAULT_WIDTH = "max-w-[640px] lg:max-w-[1120px]";

/*
  The one federal blue band at the top of every page in this world. widthClass
  matches the page's content column, so the wordmark and the page share an edge.
*/
export function Band({
  sample = false,
  widthClass = DEFAULT_WIDTH,
  children,
}: {
  sample?: boolean;
  widthClass?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="bg-federal text-white" data-band="true">
      <div className={`mx-auto flex min-h-14 w-full items-center justify-between gap-4 px-4 ${widthClass}`}>
        <Link
          href="/"
          className="py-3 text-[17px] font-semibold tracking-wide uppercase focus-visible:outline-white"
        >
          Recourse
        </Link>
        <div className="flex items-center gap-3 text-[15px]">
          {children}
          {sample ? (
            <span
              className="rounded-sm border border-white/70 px-2 py-0.5 text-[13px] font-semibold tracking-wide uppercase"
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

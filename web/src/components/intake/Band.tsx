import Link from "next/link";

/* The one federal blue band at the top of every page in this world. */
export function Band({ sample = false, children }: { sample?: boolean; children?: React.ReactNode }) {
  return (
    <header className="bg-federal text-white">
      <div className="mx-auto flex min-h-14 w-full max-w-[640px] items-center justify-between gap-4 px-4 lg:max-w-[1120px]">
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

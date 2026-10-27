"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { usePageViewer } from "./PageViewer";

/* The case card overlay marks the document while it is open (CaseHeader); the tabs read it. */
function subscribeOverlay(onChange: () => void): () => void {
  const mo = new MutationObserver(onChange);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-overlay"] });
  return () => mo.disconnect();
}

export interface IndexTab {
  n: number;
  label: string;
  /* The id of the section's h2, the link's target. */
  target: string;
}

/*
  The folder's index tabs: the numbered sections as kraft tabs down the
  right edge of the folder, at 1280 px and up on screens at least 760 px
  tall (under that the numbered openings in the page are the wayfinding,
  as they are at every width). Fixed to the folder's edge, so they stay in
  reach while the letter is read. Each tab is a real link to its section's
  heading, at least 44 px wide and tall, with the page's focus ring. The
  tab of the section in view is the darker kraft, juts a little further
  out, and carries aria-current, so its state is a position and a word for
  assistive technology, not only a tone.

  In the DOM right after the band, before the page's main content: the
  sections' contents, the way a reader meets a folder's tabs first.
*/
export function IndexTabs({ tabs }: { tabs: IndexTab[] }) {
  const [current, setCurrent] = useState<string | null>(tabs[0]?.target ?? null);
  /* While a page viewer or the case card overlay is open, the tabs step aside: nothing paints over an open overlay. */
  const viewerOpen = usePageViewer()?.state.open != null;
  const cardOpen = useSyncExternalStore(
    subscribeOverlay,
    () => document.documentElement.hasAttribute("data-overlay"),
    () => false,
  );
  const away = viewerOpen || cardOpen;

  useEffect(() => {
    const heads = tabs.map((t) => document.getElementById(t.target)).filter((el): el is HTMLElement => el !== null);
    if (heads.length === 0) return;
    let raf = 0;
    /* The section in view: the last heading above the upper third of the window. */
    const pick = () => {
      const line = window.innerHeight * 0.34;
      let at = heads[0].id;
      for (const h of heads) if (h.getBoundingClientRect().top <= line) at = h.id;
      setCurrent((c) => (c === at ? c : at));
    };
    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(pick);
    };
    pick();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [tabs]);

  return (
    <nav
      aria-label="Sections of the case"
      className={`pointer-events-none fixed top-[88px] left-[calc(50%+544px)] z-40 print:hidden ${away ? "hidden" : "hidden tabs:block"}`}
      data-index-tabs="true"
      data-away={away ? "true" : undefined}    >
      <ol className="flex flex-col gap-1">
        {tabs.map((t) => {
          const on = t.target === current;
          return (
            <li key={t.target} className="pointer-events-auto">
              <a
                href={`#${t.target}`}
                aria-current={on ? "location" : undefined}
                className={`flex min-h-11 items-center justify-center border border-l-0 border-ink/30 px-[6px] py-2.5 text-[14px] leading-4 text-ink [writing-mode:vertical-rl] ${
                  on ? "w-[54px] bg-kraft-deep font-semibold" : "w-[46px] bg-kraft-pale hover:bg-kraft"
                }`}
                data-index-tab={t.n}
                data-current={on ? "true" : "false"}
              >
                <span className="max-h-[124px]">
                  <span className="tabular-nums">{t.n}</span> {t.label}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

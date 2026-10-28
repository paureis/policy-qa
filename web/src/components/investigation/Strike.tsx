"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

/* The land (120 ms) runs first, then the strike draws, 150 ms in all across the struck lines. */
const AFTER_LAND_MS = 120;
const DRAW_MS = 150;

/*
  Struck text: the verifier's strike, an ink line through the words (the
  same <s> and text decoration as always, so the struck state reads with no
  script and prints). On arrival, when motion is allowed, the strike draws
  left to right: once the finding has landed, one ink line per line box
  scales from the left edge across that line's words (transform only),
  line after line within 150 ms, then the lines are removed and the text's
  own line-through shows again. The text itself never fades or moves. Under
  reduced motion nothing is drawn and the strike is simply there.
*/
export function Strike({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const s = ref.current;
    const host = s?.parentElement;
    if (!s || !host || !window.matchMedia("(prefers-reduced-motion: no-preference)").matches) return;
    s.style.textDecorationColor = "transparent";
    const lines: HTMLElement[] = [];
    let hostPosition: string | null = null;
    const restore = () => {
      for (const l of lines) l.remove();
      lines.length = 0;
      s.style.textDecorationColor = "";
      if (hostPosition !== null) host.style.position = hostPosition;
    };
    const draw = window.setTimeout(() => {
      if (getComputedStyle(host).position === "static") {
        hostPosition = host.style.position;
        host.style.position = "relative";
      }
      const base = host.getBoundingClientRect();
      const rects = [...s.getClientRects()].filter((r) => r.width > 0);
      const total = rects.reduce((sum, r) => sum + r.width, 0) || 1;
      const thickness = parseFloat(getComputedStyle(s).textDecorationThickness) || 2;
      let delay = 0;
      for (const r of rects) {
        const line = document.createElement("span");
        line.setAttribute("aria-hidden", "true");
        line.dataset.strikeDraw = "true";
        Object.assign(line.style, {
          position: "absolute",
          left: `${r.left - base.left}px`,
          top: `${r.top - base.top + r.height * 0.52 - thickness / 2}px`,
          width: `${r.width}px`,
          height: `${thickness}px`,
          background: "var(--ink)",
          transformOrigin: "0 50%",
          pointerEvents: "none",
        });
        host.appendChild(line);
        lines.push(line);
        const duration = (DRAW_MS * r.width) / total;
        line.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration, delay, easing: "linear", fill: "backwards" });
        delay += duration;
      }
    }, AFTER_LAND_MS);
    const done = window.setTimeout(restore, AFTER_LAND_MS + DRAW_MS + 40);
    return () => {
      window.clearTimeout(draw);
      window.clearTimeout(done);
      restore();
    };
  }, []);

  return (
    <s ref={ref} className={className}>
      {children}
    </s>
  );
}

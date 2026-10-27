"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  PAGE_ERROR_COPY,
  PageError,
  getHighlight,
  isAbort,
  pageImageSrc,
  visionCheck,
  type PageHighlight,
  type VisionCheck,
} from "@/lib/case";
import type { ChipCitation } from "./CitationChip";

/*
  "See the page": the cited PDF page as an image with the quoted lines
  highlighted in gold, and a vision check line under it. One viewer is open
  at a time. On the phone it is a section under the quote; at 1024px and up
  it is a sticky side panel beside the case column. The provider holds which
  quote is open; the panel holds its own requests and aborts them on close.
*/

/* print: a printed page is about 816 px wide, and the desk form (the paginated sheet) is the one that prints. */
const DESKTOP_QUERY = "(min-width: 1024px), print";

interface OpenViewer {
  key: string;
  citation: ChipCitation;
  /* "margin": the viewer opens in place inside a margin note of the appeal letter at desktop, not in the side panel. */
  placement?: "margin";
  /* Where focus returns on close; the chip that opened the quote when not given. */
  returnTo?: HTMLElement | null;
}

export interface ToggleOptions {
  placement?: "margin";
  returnTo?: HTMLElement | null;
}

interface ViewerState {
  open: OpenViewer | null;
  desktop: boolean;
}

interface ViewerActions {
  toggle: (key: string, citation: ChipCitation, options?: ToggleOptions) => void;
  close: () => void;
  /* Close without moving focus, when the quote that owns the viewer goes away. */
  closeIf: (key: string) => void;
}

const StateContext = createContext<ViewerState | null>(null);
const ActionsContext = createContext<ViewerActions | null>(null);

function subscribeDesktop(onChange: () => void): () => void {
  const mq = window.matchMedia(DESKTOP_QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

/* True at 1024px and up, Tailwind's lg. False on the server and during hydration. */
export function useDesktop(): boolean {
  return useSyncExternalStore(
    subscribeDesktop,
    () => window.matchMedia(DESKTOP_QUERY).matches,
    () => false,
  );
}

/* The chip that opened this quote: its aria-controls lists the quote's id (a deduped chip lists several). */
function chipFor(key: string): HTMLElement | null {
  if (typeof document === "undefined") return null;
  return document.querySelector<HTMLElement>(`[aria-controls~="${CSS.escape(key)}"]`);
}

export function PageViewerProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState<OpenViewer | null>(null);
  const desktop = useDesktop();
  const openRef = useRef<OpenViewer | null>(null);
  useEffect(() => {
    openRef.current = open;
  }, [open]);

  const close = useCallback(() => {
    const current = openRef.current;
    setOpen(null);
    if (current) (current.returnTo ?? chipFor(current.key))?.focus();
  }, []);

  const toggle = useCallback(
    (key: string, citation: ChipCitation, options?: ToggleOptions) => {
      if (openRef.current?.key === key) close();
      else setOpen({ key, citation, placement: options?.placement, returnTo: options?.returnTo ?? null });
    },
    [close],
  );

  const closeIf = useCallback((key: string) => {
    setOpen((o) => (o?.key === key ? null : o));
  }, []);

  const actions = useMemo(() => ({ toggle, close, closeIf }), [toggle, close, closeIf]);
  const state = useMemo(() => ({ open, desktop }), [open, desktop]);

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}

/* Null outside a provider: the quote then shows no See the page button. */
export function usePageViewer(): { state: ViewerState; actions: ViewerActions } | null {
  const state = useContext(StateContext);
  const actions = useContext(ActionsContext);
  return state && actions ? { state, actions } : null;
}

export function viewerPanelId(key: string): string {
  return `${key}-page`;
}

/*
  The page frame: the case column alone, or at desktop width with a viewer
  open, the column and the sticky side panel side by side.
*/
export function PageViewerFrame({ children }: { children: ReactNode }) {
  const state = useContext(StateContext);
  const actions = useContext(ActionsContext);
  const side = state?.desktop && state.open && state.open.placement !== "margin" ? state.open : null;
  if (!side || !actions) return <div className="flex flex-1 flex-col">{children}</div>;
  return (
    <div className="flex flex-1 items-start justify-center gap-6 pl-4" data-viewer-layout="side">
      {children}
      <div className="sticky top-0 h-dvh w-[min(540px,44vw)] shrink-0 border-l border-hairline bg-bond">
        <PageViewerPanel key={side.key} panelId={viewerPanelId(side.key)} citation={side.citation} variant="side" onClose={actions.close} />
      </div>
    </div>
  );
}

/* The viewer under a quote on the phone, when this quote's viewer is open. */
export function InlinePageViewer({ viewerKey }: { viewerKey: string }) {
  const state = useContext(StateContext);
  const actions = useContext(ActionsContext);
  if (!state || !actions || state.desktop || state.open?.key !== viewerKey) return null;
  return (
    <PageViewerPanel
      key={viewerKey}
      panelId={viewerPanelId(viewerKey)}
      citation={state.open.citation}
      variant="inline"
      onClose={actions.close}
    />
  );
}

/*
  The viewer inside a margin note of the appeal letter at desktop width. It
  opens in place under the note, so the letter never shifts sideways. A
  non-modal dialog like the side panel: focus moves in, Escape closes, and
  focus returns to the note's button.
*/
export function MarginPageViewer({ viewerKey }: { viewerKey: string }) {
  const state = useContext(StateContext);
  const actions = useContext(ActionsContext);
  if (!state || !actions || !state.desktop || state.open?.key !== viewerKey || state.open.placement !== "margin") return null;
  return (
    <PageViewerPanel
      key={viewerKey}
      panelId={viewerPanelId(viewerKey)}
      citation={state.open.citation}
      variant="margin"
      onClose={actions.close}
    />
  );
}

type Load = { kind: "loading" } | { kind: "error"; error: PageError } | { kind: "ready"; highlight: PageHighlight };
export type Vision =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "done"; vision: VisionCheck }
  | { kind: "unavailable"; error: string };

const BUTTON =
  "inline-flex min-h-11 min-w-11 items-center justify-center rounded-sm border border-ink bg-bond px-3 text-[16px] font-semibold text-ink";

function pct(n: number): string {
  return `${(n * 100).toFixed(4)}%`;
}

export function cleanError(text: string): string {
  return text.trim().replace(/\.$/, "") || "the vision model gave no reason";
}

/*
  The vision line under a highlighted page. named: at desktop width the check
  is labeled with the model that ran it ("Muse Spark vision check"), so the
  reader knows which model read the page image; the phone keeps the short
  label.
*/
export function visionLine(located: boolean, vision: Vision, named = false): string {
  if (!located) return "The quote was not located on this page image; the verifier matched the text layer.";
  if (vision.kind === "checking") return "Checking the highlight with vision…";
  if (vision.kind === "done" && vision.vision.model === "fixture")
    return "Vision check not run: no model key on this server, so the stand-in echoed the quote. The highlight above comes from the page's text layer.";
  if (vision.kind === "done") {
    const label = named && /^muse-spark/i.test(vision.vision.model) ? "Muse Spark vision check" : "Vision check";
    return `${label}: the highlighted text reads “${vision.vision.text_in_highlight}” and ${
      vision.vision.agrees ? "matches the quote." : "does not match the quote."
    }`;
  }
  if (vision.kind === "unavailable") return `Vision check unavailable: ${vision.error}.`;
  return "";
}

function PageViewerPanel({
  citation,
  variant,
  panelId,
  onClose,
}: {
  citation: ChipCitation;
  variant: "side" | "inline" | "margin";
  panelId: string;
  onClose: () => void;
}) {
  const title = citation.title?.trim() || citation.doc_id;
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [vision, setVision] = useState<Vision>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [drawn, setDrawn] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const placedRef = useRef(false);

  /* The highlight first, then the vision check on the highlighted area. Both abort on close. */
  useEffect(() => {
    const controller = new AbortController();
    const { doc_id, page, quote } = citation;
    (async () => {
      let highlight: PageHighlight;
      try {
        highlight = await getHighlight(doc_id, page, quote, controller.signal);
      } catch (err) {
        if (controller.signal.aborted || isAbort(err)) return;
        setLoad({ kind: "error", error: err instanceof PageError ? err : new PageError("unreachable") });
        return;
      }
      setLoad({ kind: "ready", highlight });
      if (!highlight.found || highlight.boxes_px.length === 0) return;
      setVision({ kind: "checking" });
      try {
        const res = await visionCheck(doc_id, page, quote, controller.signal);
        const v = res.vision;
        if (!v || !v.checked || v.error) setVision({ kind: "unavailable", error: cleanError(v?.error ?? "") });
        else setVision({ kind: "done", vision: v });
      } catch (err) {
        if (controller.signal.aborted || isAbort(err)) return;
        setVision({ kind: "unavailable", error: cleanError(err instanceof PageError ? err.message : "") });
      }
    })();
    return () => controller.abort();
  }, [citation, attempt]);

  /* Focus moves into the panel on open; Escape closes it. */
  useEffect(() => {
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const highlight = load.kind === "ready" ? load.highlight : null;

  /* Place the first box in the top third of the view; zoomed, center the highlight across. */
  useLayoutEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller || !highlight || highlight.boxes_px.length === 0) return;
    const content = scroller.firstElementChild as HTMLElement | null;
    if (!content) return;
    const sx = content.clientWidth / highlight.width_px;
    const sy = content.clientHeight / highlight.height_px;
    const first = highlight.boxes_px[0];
    scroller.scrollTop = Math.max(0, first.y0 * sy - scroller.clientHeight / 3);
    if (zoom) {
      const left = Math.min(...highlight.boxes_px.map((b) => b.x0));
      const right = Math.max(...highlight.boxes_px.map((b) => b.x1));
      scroller.scrollLeft = Math.max(0, ((left + right) / 2) * sx - scroller.clientWidth / 2);
    } else {
      scroller.scrollLeft = 0;
    }
    /*
      On the phone the image usually fits its box, so the window moves
      instead, once: the panel top when the box then sits in the top third,
      otherwise the box itself into the top third.
    */
    if (variant === "inline" && !placedRef.current && panelRef.current) {
      placedRef.current = true;
      const third = window.innerHeight / 3;
      const panelTop = panelRef.current.getBoundingClientRect().top;
      const boxTop = content.getBoundingClientRect().top + first.y0 * sy;
      const delta = boxTop - panelTop + 8 <= third - 16 ? panelTop - 8 : boxTop - third + 16;
      window.scrollBy({ top: delta, behavior: "instant" });
    }
  }, [highlight, zoom, variant]);

  const onImageLoad = () => {
    /* Two frames so the boxes paint at zero width before they draw. */
    requestAnimationFrame(() => requestAnimationFrame(() => setDrawn(true)));
  };

  const retry = () => {
    setLoad({ kind: "loading" });
    setVision({ kind: "idle" });
    setDrawn(false);
    setImageFailed(false);
    setZoom(false);
    placedRef.current = false;
    setAttempt((n) => n + 1);
  };

  const side = variant === "side";
  const header = (
    <div className="flex items-start gap-2">
      {/* In a margin note the note above already names the document and page (and the dialog's name carries the full title), so the header keeps only its controls. */}
      <p className={variant === "margin" ? "sr-only" : "min-w-0 flex-1 pt-2 text-[16px] leading-snug font-semibold"} data-viewer-title="true">
        {title}, page {citation.page}
      </p>
      {variant === "margin" ? <span aria-hidden="true" className="flex-1" /> : null}
      {highlight && !imageFailed ? (
        <button
          type="button"
          aria-pressed={zoom}
          onClick={() => setZoom((z) => !z)}
          className={`${BUTTON} ${zoom ? "bg-paper" : ""}`}
          data-viewer-zoom="true"
        >
          Zoom
        </button>
      ) : null}
      <button type="button" onClick={onClose} className={BUTTON} data-viewer-close="true">
        Close
      </button>
    </div>
  );

  let body: ReactNode;
  if (load.kind === "loading") {
    body = (
      <p className="mt-3 text-[17px] leading-relaxed" data-viewer-state="loading">
        Loading page {citation.page} of {title}…
      </p>
    );
  } else if (load.kind === "error") {
    body = <ViewerError error={load.error} title={title} onRetry={retry} />;
  } else {
    const h = load.highlight;
    const located = h.found && h.boxes_px.length > 0;
    body = (
      <>
        <div
          ref={scrollerRef}
          className={`mt-3 overflow-auto border border-hairline bg-paper ${
            side ? "min-h-0 flex-1" : variant === "margin" ? "page-sticky max-h-[min(70vh,560px)]" : "max-h-[70vh]"
          }`}
          data-viewer-scroller="true"
        >
          <div
            className="relative"
            style={{ width: zoom ? "200%" : "100%", aspectRatio: `${h.width_px} / ${h.height_px}` }}
            data-viewer-page="true"
            data-zoomed={zoom ? "true" : "false"}
          >
            {imageFailed ? (
              <p className="p-4 text-[17px]">The page image could not be loaded.</p>
            ) : (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={pageImageSrc(h)}
                alt={located ? `Page ${h.page} of ${title}, with the cited text highlighted` : `Page ${h.page} of ${title}`}
                width={h.width_px}
                height={h.height_px}
                onLoad={onImageLoad}
                onError={() => setImageFailed(true)}
                className="absolute inset-0 h-full w-full bg-bond"
                draggable={false}
              />
            )}
            {located && !imageFailed
              ? h.boxes_px.map((b, i) => (
                  <span
                    key={i}
                    aria-hidden="true"
                    className="hl-box pointer-events-none absolute bg-gold/45 mix-blend-multiply"
                    style={{
                      left: pct(b.x0 / h.width_px),
                      top: pct(b.y0 / h.height_px),
                      height: pct((b.y1 - b.y0) / h.height_px),
                      width: drawn ? pct((b.x1 - b.x0) / h.width_px) : "0px",
                    }}
                    data-highlight-box={i}
                  />
                ))
              : null}
          </div>
        </div>
        <p aria-live="polite" className="mt-3 min-h-7 text-[16px] leading-relaxed text-ink" data-viewer-vision={located ? vision.kind : "not_located"}>
          {visionLine(located, vision, variant !== "inline")}
        </p>
        {imageFailed ? (
          <button type="button" onClick={retry} className={`${BUTTON} mt-2 self-start`}>
            Try again
          </button>
        ) : null}
      </>
    );
  }

  if (variant === "margin") {
    return (
      <div
        ref={panelRef}
        id={panelId}
        role="dialog"
        aria-label={`Page ${citation.page} of ${title}`}
        tabIndex={-1}
        /* An overlay over the margin below the note: absolute, so the note, the notes under it, and the letter never move. */
        className="step-in absolute inset-x-0 top-full z-20 mt-2 flex flex-col border border-ink bg-bond px-3 pt-2 pb-3"
        data-page-viewer="margin"
      >
        {header}
        {body}
      </div>
    );
  }
  if (side) {
    return (
      <div
        ref={panelRef}
        id={panelId}
        role="dialog"
        aria-label={`Page ${citation.page} of ${title}`}
        tabIndex={-1}
        className="step-in flex h-full flex-col px-4 pt-4 pb-4"
        data-page-viewer="side"
      >
        {header}
        {body}
      </div>
    );
  }
  return (
    <section
      ref={panelRef}
      id={panelId}
      tabIndex={-1}
      className="step-in mt-3 mb-4 flex flex-col border-t-4 border-ink pt-3"
      data-page-viewer="inline"
    >
      {header}
      {body}
    </section>
  );
}

function ViewerError({ error, title, onRetry }: { error: PageError; title: string; onRetry: () => void }) {
  const retryable = error.code === "unreachable" || error.code === "timeout" || error.code === "rejected";
  return (
    <div className="mt-3" data-viewer-state={`error-${error.code}`}>
      <p className="text-[17px] leading-relaxed">{error.code === "no_pdf" ? PAGE_ERROR_COPY.no_pdf : error.message}</p>
      {error.code === "no_pdf" && error.sourceUrl ? (
        <a
          href={error.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex min-h-11 items-center text-[17px] font-semibold text-federal underline underline-offset-4"
        >
          Open {title} at its source
        </a>
      ) : null}
      {retryable ? (
        <button type="button" onClick={onRetry} className={`${BUTTON} mt-3`}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

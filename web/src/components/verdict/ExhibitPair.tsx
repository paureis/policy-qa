"use client";

import { useEffect, useState } from "react";
import {
  PAGE_ERROR_COPY,
  PageError,
  displayValue,
  getHighlight,
  isAbort,
  pageImageSrc,
  visionCheck,
  type CaseCard,
  type CitationRef,
  type PageHighlight,
} from "@/lib/case";
import { pageFolio, shortDocName } from "@/components/investigation/CitationChip";
import { CouldNotVerifyTag } from "@/components/investigation/CouldNotVerifyTag";
import { CornerMarks, Mark, PaperClip, type MarkKind } from "@/components/investigation/Marks";
import { usePageViewer, viewerPanelId } from "@/components/investigation/PageViewer";
import { cleanError, visionLine, type Vision } from "@/components/investigation/PageViewer";

/*
  The exhibit pair, the proof in the first screen at 1024 px and up: two
  facing documents clipped to the top sheet, each bond with a 1 px ink edge
  and a drawn paper clip over its top edge, no shadow. Left, the payer's
  stated reason verbatim with its source line. Right, a crop of the real
  policy page showing only the highlighted lines, large enough to read,
  with the red highlight drawn over them, the folio, and the vision check
  as the caption with its mark (tick: the highlight matches the quote;
  strike: it does not; open ring: not checked yet or not available). The policy side is the wider one: the crop must be legible at the
  page's own line length (a cited line runs about 630 page pixels), and the
  reason reflows at any width.

  When the page cannot be shown (not located, no PDF, the image fails), the
  right exhibit shows the quote as text on bond with the same folio and the
  page viewer's own state line. Never a broken image.
*/

/* Page pixels kept around the highlighted lines: a little air at the sides, less above and below, so the neighbouring lines stay out. */
const CROP_PAD_X = 0;
const CROP_PAD_Y = 1;
/* A short crop (one partial line) stops growing at this scale of the 110 dpi page. */
const MAX_SCALE = 1.2;

type Load = { kind: "loading" } | { kind: "error"; error: PageError } | { kind: "ready"; highlight: PageHighlight };

function pct(n: number): string {
  return `${(n * 100).toFixed(4)}%`;
}

/* The exhibit's title, set as a heading face, not an overline. */
const TITLE = "text-[21px] leading-tight font-semibold tracking-[-0.01em] text-ink";
const EXHIBIT = "relative flex min-w-0 flex-col border border-ink bg-bond px-7 pt-6 pb-5";

export function ExhibitPair({
  card,
  citation,
  unsupported,
  className = "",
}: {
  card: CaseCard;
  citation: CitationRef | null;
  unsupported: boolean;
  /* The land when the pair arrives on a sheet that is already there (the live run at desktop). */
  className?: string;
}) {
  const payer = card.payer_name.value ? String(card.payer_name.value) : null;
  const dated = card.letter_date.value ? displayValue("letter_date", card.letter_date.value) : null;
  const source = [payer, dated ? `letter dated ${dated}` : null].filter(Boolean).join(", ");
  return (
    <div className={`mt-2 hidden lg:clear-both lg:grid lg:grid-cols-2 lg:gap-x-10 lg:pt-6 ${className}`} data-exhibits="true">
      <figure className={EXHIBIT} data-exhibit="letter">
        <PaperClip className="-top-[22px] left-8" />
        <CornerMarks />
        <ExhibitHead title="The letter says" n={1} />
        <blockquote className="mt-3 text-[19px] leading-[1.45] text-ink">“{displayValue("denial_reason", card.denial_reason.value)}”</blockquote>
        {source ? <figcaption className="mt-auto pt-4 text-[14px] leading-snug text-muted">{source}</figcaption> : null}
      </figure>
      {citation ? <PolicyExhibit citation={citation} unsupported={unsupported} /> : <div aria-hidden="true" />}
    </div>
  );
}

function PolicyExhibit({ citation, unsupported }: { citation: CitationRef; unsupported: boolean }) {
  const title = citation.title?.trim() || citation.doc_id;
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [vision, setVision] = useState<Vision>({ kind: "idle" });
  const [drawn, setDrawn] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const viewer = usePageViewer();
  const viewKey = `exhibit-${citation.doc_id}-${citation.page}`;
  const pageOpen = viewer?.state.open?.key === viewKey;
  const onCropLoad = () => requestAnimationFrame(() => requestAnimationFrame(() => setDrawn(true)));

  /* Keyed on the citation's fields, not the object: every poll rebuilds the record, and an effect
     keyed on the object re-ran the highlight and the Muse Spark vision check on each poll (nine
     checks on one live case, Oct 28, 2026). */
  const { doc_id, page, quote } = citation;
  useEffect(() => {
    if (unsupported) return;
    const controller = new AbortController();
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
  }, [doc_id, page, quote, unsupported]);

  const folio = (
    <p className="mt-4 font-mono text-[14px] leading-snug text-ink" data-exhibit-folio="true">
      {shortDocName(citation)}, {pageFolio(citation)}
    </p>
  );

  const h = load.kind === "ready" ? load.highlight : null;
  const located = h !== null && h.found && h.boxes_px.length > 0;
  let body: React.ReactNode;
  let caption: string;
  let mark: MarkKind = "ring";
  if (unsupported) {
    body = <QuoteText quote={citation.quote} struck />;
    caption = "";
  } else if (located && !imageFailed) {
    /*
      The quoted sentence once, as the exhibit's text (and its accessible text), then the
      page crop under it as the proof: the exhibit's full inner width, edge to edge inside
      the 1 px frame, the 220 dpi raster so it stays sharp when zoomed; clicking it opens
      the page viewer.
    */
    body = (
      <>
        <QuoteText quote={citation.quote} />
        <div className="-mx-7 mt-4">
          {viewer ? (
            <button
              type="button"
              onClick={(e) => viewer.actions.toggle(viewKey, citation, { returnTo: e.currentTarget })}
              aria-expanded={pageOpen}
              aria-controls={pageOpen ? viewerPanelId(viewKey) : undefined}
              aria-label={`See page ${citation.page} of ${title}`}
              className="block w-full cursor-zoom-in"
              data-exhibit-open="true"
            >
              <Crop highlight={h} title={title} drawn={drawn} onLoad={onCropLoad} onError={() => setImageFailed(true)} />
            </button>
          ) : (
            <Crop highlight={h} title={title} drawn={drawn} onLoad={onCropLoad} onError={() => setImageFailed(true)} />
          )}
        </div>
      </>
    );
    /* One line: the check's name and its result; the long forms (not run, unavailable) keep the viewer's own words. */
    if (vision.kind === "done" && vision.vision.model !== "fixture") {
      const name = /^muse-spark/i.test(vision.vision.model) ? "Muse Spark vision check" : "Vision check";
      caption = vision.vision.agrees ? `${name}: matches the quote.` : `${name}: does not match the quote.`;
      mark = vision.vision.agrees ? "tick" : "strike";
    } else {
      caption = visionLine(true, vision, true);
    }
  } else {
    body = <QuoteText quote={citation.quote} />;
    caption =
      load.kind === "loading"
        ? `Loading page ${citation.page} of ${title}…`
        : load.kind === "error"
          ? load.error.code === "no_pdf"
            ? PAGE_ERROR_COPY.no_pdf
            : load.error.message
          : imageFailed
            ? "The page image could not be loaded."
            : visionLine(false, vision, true);
  }

  return (
    <figure className={EXHIBIT} data-exhibit="policy" data-exhibit-state={unsupported ? "unsupported" : located && !imageFailed ? "crop" : load.kind === "ready" ? "text" : load.kind}>
      <PaperClip className="-top-[22px] left-8" />
      <CornerMarks />
      <ExhibitHead title="The policy says" n={2} />
      {/* The crop is cut at the lines' own left and right edges and sits in the exhibit's 24 px inset, so the page text starts where the overline does. */}
      <div className="mt-3">{body}</div>
      {folio}
      {unsupported ? (
        <CouldNotVerifyTag />
      ) : (
        <figcaption
          aria-live="polite"
          className="mt-1.5 flex min-h-6 items-start gap-2 text-[15px] leading-[1.45] text-muted"
          data-exhibit-vision={located ? vision.kind : load.kind}
        >
          {caption ? <Mark kind={mark} className="mt-[3px] h-4 w-4" /> : null}
          <span>{caption}</span>
        </figcaption>
      )}
    </figure>
  );
}

/*
  The crop is drawn smaller than the 110 dpi page in a half-width exhibit, so
  it asks the API for the same page at 220 dpi (the endpoint's dpi parameter,
  50 to 300): the geometry is in percentages, so the boxes still line up, and
  the reduced page stays sharp. Bundled fixture pages have no dpi and pass
  through unchanged.
*/
function sharpSrc(src: string): string {
  return src.replace(/([?&]dpi=)\d+/, (_m, key: string) => key + "220");
}

/* The exhibit's head: its title, and its plate number at the right, small, in mono. */
function ExhibitHead({ title, n }: { title: string; n: number }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <p className={TITLE}>{title}</p>
      <p className="shrink-0 font-mono text-[14px] text-muted" data-exhibit-number={n}>
        Exhibit {n}
      </p>
    </div>
  );
}

function QuoteText({ quote, struck = false }: { quote: string; struck?: boolean }) {
  return (
    <blockquote className="text-[17px] leading-[1.6] text-ink" data-exhibit-quote="text">
      {struck ? (
        <s className="decoration-ink decoration-2">“{quote}”</s>
      ) : (
        <mark className="box-decoration-clone border-b-2 border-red/60 bg-red/15 py-0.5 text-ink">“{quote}”</mark>
      )}
    </blockquote>
  );
}

/*
  The crop: the page image inside an overflow-hidden frame that has the
  aspect ratio of the highlighted lines plus a small margin. The image is
  sized and offset in percentages of the frame, so it scales with the
  exhibit's width (up to MAX_SCALE for a short crop) with no measuring
  script. The highlight boxes are the page viewer's, red-tinted with a red
  underline, drawn left to right.
*/
function Crop({
  highlight: h,
  title,
  drawn,
  onLoad,
  onError,
}: {
  highlight: PageHighlight;
  title: string;
  drawn: boolean;
  onLoad: () => void;
  onError: () => void;
}) {
  const x0 = Math.max(0, Math.min(...h.boxes_px.map((b) => b.x0)) - CROP_PAD_X);
  const y0 = Math.max(0, Math.min(...h.boxes_px.map((b) => b.y0)) - CROP_PAD_Y);
  const x1 = Math.min(h.width_px, Math.max(...h.boxes_px.map((b) => b.x1)) + CROP_PAD_X);
  const y1 = Math.min(h.height_px, Math.max(...h.boxes_px.map((b) => b.y1)) + CROP_PAD_Y);
  const cw = x1 - x0;
  const ch = y1 - y0;
  return (
    <div
      className="relative w-full overflow-hidden border-y border-hairline bg-bond"
      style={{ maxWidth: `${Math.round(cw * MAX_SCALE)}px`, aspectRatio: `${cw} / ${ch}` }}
      data-exhibit-crop={`${Math.round(cw)}x${Math.round(ch)}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- the API's page PNG, cropped by CSS offsets; next/image would re-encode it and break the percentage geometry */}
      <img
        src={sharpSrc(pageImageSrc(h))}
        alt={`Page ${h.page} of ${title}, with the cited text highlighted`}
        width={h.width_px}
        height={h.height_px}
        onLoad={onLoad}
        onError={onError}
        draggable={false}
        className="absolute max-w-none"
        style={{ width: pct(h.width_px / cw), height: pct(h.height_px / ch), left: pct(-x0 / cw), top: pct(-y0 / ch) }}
      />
      {h.boxes_px.map((b, i) => (
        <span
          key={i}
          aria-hidden="true"
          className="hl-box pointer-events-none absolute border-b-2 border-red/70 bg-red/20 mix-blend-multiply"
          style={{
            left: pct((b.x0 - x0) / cw),
            top: pct((b.y0 - y0) / ch),
            height: pct((b.y1 - b.y0) / ch),
            width: drawn ? pct((b.x1 - b.x0) / cw) : "0px",
          }}
          data-highlight-box={i}
        />
      ))}
    </div>
  );
}

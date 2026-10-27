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
import { cleanError, visionLine, type Vision } from "@/components/investigation/PageViewer";

/*
  The exhibit pair, the proof in the first screen at 1024 px and up: two
  facing documents on bond with a 1 px ink edge, no shadow. Left, the
  payer's stated reason verbatim with its source line. Right, a crop of the
  real policy page showing only the highlighted lines, large enough to read,
  with the gold box drawn over them, the folio, and the vision check as the
  caption. The policy side is the wider one: the crop must be legible at the
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

const OVERLINE = "text-[14px] font-semibold tracking-wide text-muted uppercase";
const EXHIBIT = "flex min-w-0 flex-col border border-ink bg-bond px-6 pt-5 pb-6";

export function ExhibitPair({ card, citation, unsupported }: { card: CaseCard; citation: CitationRef | null; unsupported: boolean }) {
  const payer = card.payer_name.value ? String(card.payer_name.value) : null;
  const dated = card.letter_date.value ? displayValue("letter_date", card.letter_date.value) : null;
  const source = [payer, dated ? `letter dated ${dated}` : null].filter(Boolean).join(", ");
  return (
    <div className="mt-2 hidden lg:clear-both lg:grid lg:grid-cols-[minmax(0,380fr)_minmax(0,660fr)] lg:gap-x-12" data-exhibits="true">
      <figure className={EXHIBIT} data-exhibit="letter">
        <p className={OVERLINE}>The letter says</p>
        <blockquote className="mt-3 text-[22px] leading-[1.4] text-ink">“{displayValue("denial_reason", card.denial_reason.value)}”</blockquote>
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

  useEffect(() => {
    if (unsupported) return;
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
  }, [citation, unsupported]);

  const folio = (
    <p className="mt-4 text-[15px] leading-snug font-semibold text-ink tabular-nums" data-exhibit-folio="true">
      {shortDocName(citation)}, {pageFolio(citation)}
    </p>
  );

  const h = load.kind === "ready" ? load.highlight : null;
  const located = h !== null && h.found && h.boxes_px.length > 0;
  let body: React.ReactNode;
  let caption: string;
  if (unsupported) {
    body = <QuoteText quote={citation.quote} struck />;
    caption = "";
  } else if (located && !imageFailed) {
    body = <Crop highlight={h} title={title} drawn={drawn} onLoad={() => requestAnimationFrame(() => requestAnimationFrame(() => setDrawn(true)))} onError={() => setImageFailed(true)} />;
    caption = visionLine(true, vision, true);
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
      <p className={OVERLINE}>The policy says</p>
      {/* The crop is cut at the lines' own left and right edges and sits in the exhibit's 24 px inset, so the page text starts where the overline does. */}
      <div className="mt-3">{body}</div>
      {folio}
      {unsupported ? (
        <CouldNotVerifyTag />
      ) : (
        <figcaption aria-live="polite" className="mt-1 min-h-6 text-[15px] leading-[1.45] text-muted" data-exhibit-vision={located ? vision.kind : load.kind}>
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

function QuoteText({ quote, struck = false }: { quote: string; struck?: boolean }) {
  return (
    <blockquote className="border-l-4 border-federal pl-4 text-[17px] leading-relaxed text-ink" data-exhibit-quote="text">
      {struck ? <s className="decoration-ink decoration-2">“{quote}”</s> : <>“{quote}”</>}
    </blockquote>
  );
}

/*
  The crop: the page image inside an overflow-hidden frame that has the
  aspect ratio of the highlighted lines plus a small margin. The image is
  sized and offset in percentages of the frame, so it scales with the
  exhibit's width (up to MAX_SCALE for a short crop) with no measuring
  script. The gold boxes are the page viewer's, drawn left to right.
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
        src={pageImageSrc(h)}
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
          className="hl-box pointer-events-none absolute bg-gold/45 mix-blend-multiply"
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

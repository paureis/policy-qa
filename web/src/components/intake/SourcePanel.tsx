"use client";

import { useEffect, useId, useRef, useState } from "react";
import { formatBytes, type IntakeInput } from "@/lib/case";
import { CornerMarks, PaperClip } from "@/components/investigation/Marks";

/*
  The letter stays on screen from submit onward: an image thumbnail, the
  PDF name and size, or a text excerpt. Once the card exists, "Show the
  letter as read" reveals the raw text.

  At 1024 px and up, once the card exists, the letter is beside the card for
  the whole review (case-page-brief section 12, E7): a clipped exhibit, "The
  letter as read", with the raw text in a scrolling frame, and the panel
  with its "Show the letter as read" button is not shown there.
*/
export function SourcePanel({ input, rawText }: { input: IntakeInput; rawText: string | null }) {
  const [open, setOpen] = useState(false);
  const rawId = useId();

  return (
    <>
    {rawText !== null ? <LetterExhibit rawText={rawText} /> : null}
    <aside aria-label="Your letter" className={`border border-hairline bg-paper p-4 ${rawText !== null ? "lg:hidden" : ""}`}>
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase lg:font-normal lg:tracking-normal lg:normal-case">Your letter</p>
      <div className="mt-3">
        {input.kind === "text" ? <TextExcerpt text={input.text} /> : <FilePreview file={input.file} />}
      </div>
      {rawText !== null ? (
        <div className="mt-4">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={rawId}
            onClick={() => setOpen((o) => !o)}
            className="inline-flex min-h-11 items-center border border-ink bg-bond px-4 text-[16px] font-semibold text-ink"
          >
            {open ? "Hide the letter" : "Show the letter as read"}
          </button>
          {open ? (
            <pre
              id={rawId}
              className="mt-3 max-h-[60vh] overflow-auto border border-hairline bg-bond p-3 font-sans text-[15px] leading-relaxed whitespace-pre-wrap text-ink"
            >
              {rawText}
            </pre>
          ) : null}
        </div>
      ) : null}
    </aside>
    </>
  );
}

/*
  The letter as read, clipped beside the card at desktop: bond, 1 px ink
  edge, the paper clip over its top edge and the corner marks, as the case
  page's exhibits are; the text at 15 px in a frame that scrolls (capped at
  about 60 vh) and takes the keyboard, so the whole letter can be read.
*/
function LetterExhibit({ rawText }: { rawText: string }) {
  const headId = useId();
  return (
    <figure
      className="relative hidden min-w-0 border border-ink bg-bond px-7 pt-6 pb-5 lg:flex lg:flex-col"
      aria-labelledby={headId}
      data-exhibit="letter-as-read"
    >
      <PaperClip className="-top-[22px] left-8" />
      <CornerMarks />
      <p id={headId} className="text-[21px] leading-tight font-semibold tracking-[-0.01em] text-ink">
        The letter as read
      </p>
      <pre
        tabIndex={0}
        role="region"
        aria-labelledby={headId}
        /* Its own scrollbar (thin, ink on bond) and 8 px inside the frame, so the 3 px focus ring clears the text; scoped here, not global. */
        className="mt-3 max-h-[60vh] overflow-auto border-t border-hairline px-2 pt-3 pb-2 font-sans text-[15px] leading-relaxed whitespace-pre-wrap text-ink [scrollbar-color:var(--ink)_var(--bond)] [scrollbar-width:thin]"
      >
        {rawText}
      </pre>
    </figure>
  );
}

function TextExcerpt({ text }: { text: string }) {
  const trimmed = text.trim();
  const excerpt = trimmed.length > 280 ? `${trimmed.slice(0, 280).trimEnd()}…` : trimmed;
  return (
    <div>
      <p className="line-clamp-6 text-[16px] leading-relaxed whitespace-pre-line text-ink">{excerpt}</p>
      <p className="mt-2 text-[14px] text-muted">{trimmed.length.toLocaleString("en-US")} characters pasted</p>
    </div>
  );
}

function FilePreview({ file }: { file: File }) {
  const isPdf = file.type === "application/pdf";
  const imgRef = useRef<HTMLImageElement>(null);

  // The blob URL lives as long as this preview; it is set on the element and revoked with it.
  useEffect(() => {
    const img = imgRef.current;
    if (isPdf || !img) return;
    const objectUrl = URL.createObjectURL(file);
    img.src = objectUrl;
    return () => {
      img.removeAttribute("src");
      URL.revokeObjectURL(objectUrl);
    };
  }, [file, isPdf]);

  if (isPdf) {
    return (
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-14 w-11 shrink-0 items-center justify-center border border-ink bg-bond text-[12px] font-bold tracking-wide"
        >
          PDF
        </span>
        <div className="min-w-0">
          <p className="truncate text-[16px] font-semibold">{file.name}</p>
          <p className="text-[14px] text-muted">{formatBytes(file.size)}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* The thumbnail is a blob URL from the user's own file; next/image adds nothing here. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        alt={`Your photo of the letter, ${file.name}`}
        className="max-h-[320px] w-auto max-w-full border border-hairline bg-bond object-contain"
      />
      <p className="mt-2 truncate text-[14px] text-muted">
        {file.name}, {formatBytes(file.size)}
      </p>
    </div>
  );
}

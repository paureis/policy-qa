"use client";

import { useEffect, useId, useRef, useState } from "react";
import { formatBytes, type IntakeInput } from "@/lib/case";

/*
  The letter stays on screen from submit onward: an image thumbnail, the
  PDF name and size, or a text excerpt. Once the card exists, "Show the
  letter as read" reveals the raw text.
*/
export function SourcePanel({ input, rawText }: { input: IntakeInput; rawText: string | null }) {
  const [open, setOpen] = useState(false);
  const rawId = useId();

  return (
    <aside aria-label="Your letter" className="rounded-sm border border-hairline bg-paper p-4">
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">Your letter</p>
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
            className="inline-flex min-h-11 items-center rounded-sm border border-ink bg-bond px-4 text-[16px] font-semibold text-ink"
          >
            {open ? "Hide the letter" : "Show the letter as read"}
          </button>
          {open ? (
            <pre
              id={rawId}
              className="mt-3 max-h-[60vh] overflow-auto rounded-sm border border-hairline bg-bond p-3 font-sans text-[15px] leading-relaxed whitespace-pre-wrap text-ink"
            >
              {rawText}
            </pre>
          ) : null}
        </div>
      ) : null}
    </aside>
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
          className="flex h-14 w-11 shrink-0 items-center justify-center rounded-sm border border-ink bg-bond text-[12px] font-bold tracking-wide"
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
        className="max-h-[320px] w-auto max-w-full rounded-sm border border-hairline bg-bond object-contain"
      />
      <p className="mt-2 truncate text-[14px] text-muted">
        {file.name}, {formatBytes(file.size)}
      </p>
    </div>
  );
}

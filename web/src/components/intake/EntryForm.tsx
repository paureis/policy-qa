"use client";

import { useEffect, useId, useRef } from "react";
import { TEXT_MAX, TEXT_MIN } from "@/lib/case";

export interface EntryFormProps {
  text: string;
  textOpen: boolean;
  onTextChange: (text: string) => void;
  onTextOpen: (open: boolean) => void;
  onTakePhoto: () => void;
  onChooseFile: () => void;
  onSubmitText: () => void;
  focusText?: boolean;
}

const WAY =
  "flex min-h-[72px] w-full flex-col items-start justify-center border border-edge bg-bond px-4 py-3 text-left text-ink hover:border-ink";

/* Three equal ways in: a photo, a file, or pasted text. */
export function EntryForm({
  text,
  textOpen,
  onTextChange,
  onTextOpen,
  onTakePhoto,
  onChooseFile,
  onSubmitText,
  focusText = false,
}: EntryFormProps) {
  const textareaId = useId();
  const countId = useId();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const length = text.trim().length;
  const inRange = length >= TEXT_MIN && length <= TEXT_MAX;

  useEffect(() => {
    if (textOpen && focusText) textareaRef.current?.focus();
  }, [textOpen, focusText]);

  return (
    <section aria-labelledby="entry-heading">
      <h1 id="entry-heading" className="text-[28px] leading-tight font-bold">
        Start with your letter
      </h1>
      <p className="mt-3 text-[18px] leading-relaxed lg:text-[17px]">
        Recourse reads a coverage denial letter into a case card. You check the card before anything else happens.
      </p>

      <ul className="mt-6 space-y-3" aria-label="Three ways to add the letter">
        <li>
          <button type="button" className={WAY} onClick={onTakePhoto}>
            <span className="text-[19px] font-semibold">Take a photo</span>
            <span className="text-[15px] text-muted">Use your phone camera. Lay the letter flat in good light.</span>
          </button>
        </li>
        <li>
          <button type="button" className={WAY} onClick={onChooseFile}>
            <span className="text-[19px] font-semibold">Choose a PDF or image</span>
            <span className="text-[15px] text-muted">JPEG, PNG, WebP, or PDF up to 10 MB.</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            className={`${WAY} ${textOpen ? "border-ink" : ""}`}
            aria-expanded={textOpen}
            aria-controls={`${textareaId}-panel`}
            onClick={() => onTextOpen(!textOpen)}
          >
            <span className="text-[19px] font-semibold">Paste text</span>
            <span className="text-[15px] text-muted">Copy in the words of the letter. 200 to 6,000 characters.</span>
          </button>
        </li>
      </ul>

      {textOpen ? (
        <form
          id={`${textareaId}-panel`}
          className="mt-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (inRange) onSubmitText();
          }}
        >
          <label htmlFor={textareaId} className="block text-[14px] font-semibold tracking-wide text-muted uppercase">
            Text of the letter
          </label>
          <textarea
            ref={textareaRef}
            id={textareaId}
            rows={9}
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
            aria-describedby={countId}
            placeholder="Paste the whole letter, including the date and any deadline it gives."
            className="mt-2 block w-full border border-edge bg-bond px-3 py-2 text-[18px] leading-relaxed text-ink placeholder:text-muted lg:text-[17px]"
          />
          <p id={countId} aria-live="polite" className="mt-2 text-[15px] text-muted">
            {length.toLocaleString("en-US")} of {TEXT_MAX.toLocaleString("en-US")} characters.{" "}
            {length < TEXT_MIN ? `At least ${TEXT_MIN} needed.` : length > TEXT_MAX ? "Too long." : "Ready."}
          </p>
          <div className="sticky bottom-0 -mx-4 mt-4 border-t border-hairline bg-bond px-4 py-3 lg:static lg:mx-0 lg:border-0 lg:px-0">
            <button
              type="submit"
              disabled={!inRange}
              className="inline-flex min-h-12 w-full items-center justify-center bg-ink px-5 text-[18px] font-semibold text-bond disabled:cursor-not-allowed disabled:bg-hairline disabled:text-muted"
            >
              Read this letter
            </button>
          </div>
        </form>
      ) : null}

      <p className="mt-8 border-t border-hairline pt-4 text-[15px] text-muted">
        Recourse reads coverage denials and drafts appeals. It does not give medical advice.
      </p>
    </section>
  );
}

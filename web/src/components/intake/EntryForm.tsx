"use client";

import { useEffect, useId, useRef } from "react";
import { TEXT_MAX, TEXT_MIN } from "@/lib/case";
import { INTRO } from "./Frame";

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

/* A way in. Under 1024 px a 72 px panel with its hint inside; at desktop a secondary button (bond, 1 px ink edge, 48 px). */
const WAY =
  "flex min-h-[72px] w-full flex-col items-start justify-center border border-edge bg-bond px-4 py-3 text-left text-ink hover:border-ink lg:min-h-12 lg:items-center lg:border-ink lg:px-5 lg:py-0 lg:text-center lg:hover:bg-paper";
const WAY_TITLE = "text-[19px] font-semibold lg:text-[18px]";
const WAY_HINT = "text-[15px] text-muted lg:hidden";
/* The hint under a door at desktop, outside the button; it is the button's description at every width. */
const DOOR_HINT = "mt-2 hidden text-[14px] leading-snug text-muted lg:block";
/*
  The paste box's label and the doors' label share one style, so the two columns start level. At
  desktop it is DESIGN.md's label (14 px, 400, sentence case, no tracking, faded ink); the phone keeps
  the uppercase register.
*/
const LABEL = "block text-[14px] font-semibold tracking-wide text-muted uppercase lg:font-normal lg:tracking-normal lg:normal-case";

const PHOTO = { title: "Take a photo", hint: "Use your phone camera. Lay the letter flat in good light." };
const FILE = { title: "Choose a PDF or image", hint: "JPEG, PNG, WebP, or PDF up to 10 MB." };

/*
  Three equal ways in: a photo, a file, or pasted text (under 1024 px, as
  the intake brief has it). At 1024 px and up the paste box is the desk:
  open from the start in the letter's 620 px column, with the photo and the
  file as two secondary doors in the 420 px column beside it; the "Paste
  text" door is not shown there (case-page-brief section 12, E2 and E3).
*/
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
    <section aria-labelledby="entry-heading" className="lg:grid lg:desk-cols lg:items-start" data-desk="entry">
      <div className="lg:col-span-2">
        <h1 id="entry-heading" className="text-[28px] leading-tight font-bold">
          Start with your letter
        </h1>
        <p className={INTRO}>
          Recourse reads a coverage denial letter into a case card. You check the card before anything else happens.
        </p>
      </div>

      <div className="lg:col-start-2 lg:row-start-2 lg:mt-6" data-desk-doors="true">
        <p className={`hidden lg:block ${LABEL}`}>Or add the letter as a file</p>
        <ul className="mt-6 space-y-3 lg:mt-2 lg:space-y-5" aria-label="Three ways to add the letter">
          <li>
            <button
              type="button"
              className={WAY}
              onClick={onTakePhoto}
              aria-label={PHOTO.title}
              aria-describedby={`${textareaId}-photo-hint`}
            >
              <span className={WAY_TITLE}>{PHOTO.title}</span>
              <span className={WAY_HINT} aria-hidden="true">
                {PHOTO.hint}
              </span>
            </button>
            <p id={`${textareaId}-photo-hint`} className={DOOR_HINT}>
              {PHOTO.hint}
            </p>
          </li>
          <li>
            <button
              type="button"
              className={WAY}
              onClick={onChooseFile}
              aria-label={FILE.title}
              aria-describedby={`${textareaId}-file-hint`}
            >
              <span className={WAY_TITLE}>{FILE.title}</span>
              <span className={WAY_HINT} aria-hidden="true">
                {FILE.hint}
              </span>
            </button>
            <p id={`${textareaId}-file-hint`} className={DOOR_HINT}>
              {FILE.hint}
            </p>
          </li>
          <li className="lg:hidden">
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
      </div>

      {/*
        Under 1024 px the panel opens from the "Paste text" door, under the three ways; at desktop it is
        open from the start. The source order stays the phone's (the ways, then the panel they open), so
        at desktop the keyboard meets the two doors before the paste box.
      */}
      <form
        id={`${textareaId}-panel`}
        className={`mt-6 lg:col-start-1 lg:row-start-2 lg:block ${textOpen ? "" : "hidden"}`}
        data-desk-paste="true"
        onSubmit={(e) => {
          e.preventDefault();
          if (inRange) onSubmitText();
        }}
      >
        <label htmlFor={textareaId} className={LABEL}>
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
          className="mt-2 block w-full border border-edge bg-bond px-3 py-2 text-[18px] leading-relaxed text-ink placeholder:text-muted lg:h-[calc(14lh+18px)] lg:text-[17px] lg:focus:border-ink"
        />
        <p id={countId} aria-live="polite" className="mt-2 text-[15px] text-muted">
          {length.toLocaleString("en-US")} of {TEXT_MAX.toLocaleString("en-US")} characters.{" "}
          {length < TEXT_MIN ? `At least ${TEXT_MIN} needed.` : length > TEXT_MAX ? "Too long." : "Ready."}
        </p>
        <div className="sticky bottom-0 -mx-4 mt-4 border-t border-hairline bg-bond px-4 py-3 lg:static lg:mx-0 lg:mt-5 lg:border-0 lg:px-0 lg:py-0">
          <button
            type="submit"
            disabled={!inRange}
            className="inline-flex min-h-12 w-full items-center justify-center bg-ink px-5 text-[18px] font-semibold text-bond disabled:cursor-not-allowed disabled:bg-hairline disabled:text-muted lg:w-auto"
          >
            Read this letter
          </button>
        </div>
      </form>

      <p className="mt-8 border-t border-hairline pt-4 text-[15px] text-muted lg:col-span-2">
        Recourse reads coverage denials and drafts appeals. It does not give medical advice.
      </p>
    </section>
  );
}

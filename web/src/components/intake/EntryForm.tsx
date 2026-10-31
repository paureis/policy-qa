"use client";

import { useEffect, useId, useRef, useState } from "react";
import { TEXT_MAX, TEXT_MIN } from "@/lib/case";
import { SAMPLE_LETTERS, type SampleLetter } from "@/lib/sample-letters";
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
  /* The sample letters list under the third door, desktop only (case-page-brief section 16). */
  lettersOpen?: boolean;
  onLettersOpen?: (open: boolean) => void;
}

/* The list's id: the landing's "Try a sample letter" links to /case/new#sample-letters (J5). */
export const SAMPLE_LETTERS_ID = "sample-letters";

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
const LETTERS_HINT = "Ten letters written for this demo. Pick one and read it as your own.";

/*
  Three equal ways in: a photo, a file, or pasted text (under 1024 px, as
  the intake brief has it). At 1024 px and up the paste box is the desk:
  open from the start in the letter's 620 px column, with the file as the
  secondary door in the 420 px column beside it; the "Paste text" door is
  not shown there (case-page-brief section 12, E2 and E3), nor the photo
  door (section 19, M6: a desktop has no phone camera to offer, and the file
  door takes a scanned letter or a photo already on the computer).
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
  lettersOpen = false,
  onLettersOpen = () => {},
}: EntryFormProps) {
  const textareaId = useId();
  const countId = useId();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const lettersDoorRef = useRef<HTMLButtonElement>(null);
  const phoneLettersDoorRef = useRef<HTMLButtonElement>(null);
  const [loaded, setLoaded] = useState<{ n: number; message: string }>({ n: 0, message: "" });
  const length = text.trim().length;
  const inRange = length >= TEXT_MIN && length <= TEXT_MAX;

  useEffect(() => {
    if (textOpen && focusText) textareaRef.current?.focus();
  }, [textOpen, focusText]);

  /* After a sample letter loads, focus goes to "Read this letter", enabled in the same render (J4). */
  useEffect(() => {
    if (loaded.n > 0) submitRef.current?.focus();
  }, [loaded.n]);

  const chooseLetter = (letter: SampleLetter) => {
    onTextChange(letter.text);
    onLettersOpen(false);
    /* Under 1024 px the paste box opens with the letter in it (section 17, K9); at desktop it is always open. */
    onTextOpen(true);
    setLoaded((l) => ({ n: l.n + 1, message: `Sample letter loaded: ${letter.service}, ${letter.payer}.` }));
  };

  /* Escape on a door or in its open list closes the list; focus goes back to that door. */
  const closeLettersOnEscape = (door: "desk" | "phone") => (e: React.KeyboardEvent) => {
    if (e.key !== "Escape" || !lettersOpen) return;
    e.preventDefault();
    onLettersOpen(false);
    (door === "desk" ? lettersDoorRef : phoneLettersDoorRef).current?.focus();
  };

  /* The ten rows (J3), shared by the desktop column and the phone's fourth door; ids differ, the rows do not. */
  const letterRows = (labelId: string, listId: string) => (
    <>
      <p id={labelId} className="text-[14px] text-muted">
        Sample letters
      </p>
      <ul id={listId} aria-labelledby={labelId} className="mt-2 space-y-2">
        {SAMPLE_LETTERS.map((letter) => (
          <li key={letter.id}>
            <button
              type="button"
              onClick={() => chooseLetter(letter)}
              aria-label={`${letter.service}, ${letter.payer}. ${letter.program}. ${letter.reason}`}
              className="block min-h-11 w-full border border-edge bg-bond p-3 text-left text-ink hover:border-ink hover:bg-paper"
            >
              <span className="block text-[16px] leading-snug">
                <span className="font-semibold">{letter.service}</span>
                <span className="text-muted">{"\u00a0· "}</span>
                {letter.payer}
              </span>
              <span className="mt-1 line-clamp-2 text-[14px] leading-snug text-muted">
                {letter.program} · {letter.reason}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );

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
        <ul className="mt-6 space-y-3 lg:mt-2 lg:space-y-5" aria-label="Ways to add the letter">
          {/* The photo door under 1024 px only (section 19, M6). */}
          <li className="lg:hidden">
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
          {/*
            The fourth door under 1024 px (section 17, K9; J6 reversed): "Try a sample letter" in the three doors'
            style, the ten rows (J3) opening under it. Choosing a row opens the paste box with the letter in it,
            as J4 does. The list's open state is the desktop list's (one shows at a width), so the landing's
            link opens it on the phone too. Display: none from 1024 px, where the desktop door stands (J2).
          */}
          <li className="lg:hidden" data-phone-letters="true" onKeyDown={closeLettersOnEscape("phone")}>
            <button
              ref={phoneLettersDoorRef}
              type="button"
              className={`${WAY} ${lettersOpen ? "border-ink" : ""}`}
              aria-label="Try a sample letter"
              aria-describedby={`${textareaId}-letters-hint`}
              aria-expanded={lettersOpen}
              aria-controls={`${SAMPLE_LETTERS_ID}-phone`}
              onClick={() => onLettersOpen(!lettersOpen)}
            >
              <span className={WAY_TITLE}>Try a sample letter</span>
              <span className={WAY_HINT} aria-hidden="true">
                {LETTERS_HINT}
              </span>
            </button>
            <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
              <span key={loaded.n}>{loaded.message}</span>
            </p>
            <div className="mt-4 mb-2" hidden={!lettersOpen}>
              {letterRows(`${textareaId}-letters-label-phone`, `${SAMPLE_LETTERS_ID}-phone`)}
            </div>
          </li>
        </ul>

        {/*
          The third door, desktop only (section 16, J2 to J4): the ten demo letters as a list of buttons
          under it. Under 1024 px it is display: none, so the phone and tablet render as before (J6).
        */}
        <div className="hidden lg:mt-8 lg:block" data-desk-letters="true" onKeyDown={closeLettersOnEscape("desk")}>
          <p className={LABEL}>Or start from a sample</p>
          <button
            ref={lettersDoorRef}
            type="button"
            className={`${WAY} lg:mt-2`}
            aria-expanded={lettersOpen}
            aria-controls={SAMPLE_LETTERS_ID}
            aria-describedby={`${textareaId}-letters-hint`}
            onClick={() => onLettersOpen(!lettersOpen)}
          >
            <span className={WAY_TITLE}>Try a sample letter</span>
          </button>
          <p id={`${textareaId}-letters-hint`} className={DOOR_HINT}>
            {LETTERS_HINT}
          </p>
          {/* The message's node is keyed on the load count, so choosing the same letter again is read again. */}
          <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">
            <span key={loaded.n}>{loaded.message}</span>
          </p>
          {/* Always rendered, so the door's aria-controls resolves; the hidden attribute closes it. */}
          <div className="mt-6" hidden={!lettersOpen}>
            {letterRows(`${textareaId}-letters-label`, SAMPLE_LETTERS_ID)}
          </div>
        </div>
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
            ref={submitRef}
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

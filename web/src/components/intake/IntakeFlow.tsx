"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ACCEPTED_FILE_TYPES,
  INTAKE_MODE,
  IntakeError,
  TIMEOUT_MS,
  diffCard,
  intake,
  investigate,
  isAbort,
  isFlagged,
  patchCase,
  type CaseCard as CaseCardData,
  type FieldKey,
  type FieldValue,
  type IntakeInput,
  type IntakeResponse,
} from "@/lib/case";
import { Band } from "./Band";
import { CaseCard } from "./CaseCard";
import { EntryForm } from "./EntryForm";
import { ErrorNotice } from "./ErrorNotice";
import { ProgressStages, STAGES } from "./ProgressStages";
import { SourcePanel } from "./SourcePanel";

type Phase = "entry" | "processing" | "error" | "reviewing" | "confirming" | "confirmed";
type Investigation = "pending" | "started" | "failed";

const STAGE_MS = 2000;

/*
  The intake screen. Three states on the brief (uploading, reviewing,
  confirmed) with the error and in-flight sub-states. State changes step.
*/
export function IntakeFlow() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("entry");
  const [text, setText] = useState("");
  const [textOpen, setTextOpen] = useState(false);
  const [focusText, setFocusText] = useState(false);
  const [input, setInput] = useState<IntakeInput | null>(null);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<IntakeError | null>(null);
  const [response, setResponse] = useState<IntakeResponse | null>(null);
  const [card, setCard] = useState<CaseCardData | null>(null);
  const [flagged, setFlagged] = useState<ReadonlySet<FieldKey>>(new Set());
  const [today, setToday] = useState<Date>(() => new Date(0));
  const [saveError, setSaveError] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<Investigation>("pending");

  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const timersRef = useRef<number[]>([]);

  const clearTimers = useCallback(() => {
    for (const t of timersRef.current) window.clearTimeout(t);
    timersRef.current = [];
  }, []);

  const abortInFlight = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    clearTimers();
  }, [clearTimers]);

  useEffect(() => () => abortInFlight(), [abortInFlight]);

  const submit = useCallback(
    (next: IntakeInput) => {
      abortInFlight();
      const controller = new AbortController();
      controllerRef.current = controller;
      setInput(next);
      setError(null);
      setStage(0);
      setPhase("processing");

      for (let i = 1; i < STAGES.length; i += 1) {
        timersRef.current.push(window.setTimeout(() => setStage(i), STAGE_MS * i));
      }
      timersRef.current.push(
        window.setTimeout(() => {
          if (controllerRef.current !== controller) return;
          controller.abort();
          controllerRef.current = null;
          setError(new IntakeError("timeout"));
          setPhase("error");
        }, TIMEOUT_MS),
      );

      intake(next, controller.signal)
        .then((res) => {
          if (controllerRef.current !== controller) return;
          clearTimers();
          controllerRef.current = null;
          const flags = new Set<FieldKey>();
          for (const key of Object.keys(res.card) as FieldKey[]) {
            if (isFlagged(res.card[key])) flags.add(key);
          }
          setResponse(res);
          setCard(structuredClone(res.card));
          setFlagged(flags);
          setToday(new Date());
          setSaveError(null);
          setInvestigation("pending");
          setPhase("reviewing");
          window.scrollTo({ top: 0 });
        })
        .catch((err: unknown) => {
          if (controllerRef.current !== controller) return;
          clearTimers();
          controllerRef.current = null;
          if (isAbort(err)) return;
          setError(err instanceof IntakeError ? err : new IntakeError("unreachable"));
          setPhase("error");
        });
    },
    [abortInFlight, clearTimers],
  );

  const onFilePicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) submit({ kind: "file", file });
  };

  // After a successful read the letter has become a case, so Start over begins
  // clean. After an error the person is usually fixing the same letter, so the
  // pasted text stays (decided by Alvaro, Oct 26).
  const startOver = () => {
    abortInFlight();
    const keepText = phase === "error";
    setInput(null);
    setError(null);
    setResponse(null);
    setCard(null);
    setFlagged(new Set());
    setFocusText(false);
    if (!keepText) {
      setText("");
      setTextOpen(false);
    }
    setPhase("entry");
    window.scrollTo({ top: 0 });
  };

  const cancel = () => {
    abortInFlight();
    setPhase("entry");
    if (input?.kind === "text") setTextOpen(true);
  };

  const editText = () => {
    abortInFlight();
    if (input?.kind === "text") setText(input.text);
    setTextOpen(true);
    setFocusText(true);
    setPhase("entry");
  };

  const onChange = (key: FieldKey, value: FieldValue) => {
    setCard((c) => (c ? { ...c, [key]: { ...c[key], value } } : c));
    // A typed value clears the flag. A cleared value re-flags the row: the person
    // then confirms with "Looks right" that the letter does not state it.
    const cleared = value === null || value === undefined || value === "";
    setFlagged((f) => {
      if (cleared ? f.has(key) : !f.has(key)) return f;
      const n = new Set(f);
      if (cleared) n.add(key);
      else n.delete(key);
      return n;
    });
  };

  const onLooksRight = (key: FieldKey) => {
    setFlagged((f) => {
      const n = new Set(f);
      n.delete(key);
      return n;
    });
  };

  const confirm = async () => {
    if (!response || !card || flagged.size > 0) return;
    setPhase("confirming");
    setSaveError(null);
    let saved: IntakeResponse;
    try {
      saved = await patchCase(response.case_id, diffCard(response.card, card), { ...response, card });
    } catch (e) {
      const rejected = e instanceof IntakeError && e.code === "rejected";
      setSaveError(
        rejected
          ? `Your edits could not be saved: ${e.message} Fix that detail and tap Confirm again.`
          : "Your edits could not be saved. Check your connection and tap Confirm again.",
      );
      setPhase("reviewing");
      return;
    }
    setResponse(saved);
    setCard(structuredClone(saved.card));
    setPhase("confirmed");
    window.scrollTo({ top: 0 });
    void startInvestigation(saved.case_id);
  };

  // Once the investigate POST returns, the case's home is /case/{id}. The
  // "Case opened" line below stays only as the fallback when the POST fails.
  const startInvestigation = async (caseId: string) => {
    setInvestigation("pending");
    try {
      await investigate(caseId);
      setInvestigation("started");
      router.push(`/case/${encodeURIComponent(caseId)}`);
    } catch {
      setInvestigation("failed");
    }
  };

  const sample = INTAKE_MODE === "fixture";
  const showSource = input !== null && phase !== "entry";
  const locked = phase === "confirmed";
  const rawText = response && (phase === "reviewing" || phase === "confirming" || phase === "confirmed") ? response.raw_text : null;

  return (
    <div className="flex min-h-full flex-col">
      <Band sample={sample}>
        {phase !== "entry" ? (
          <button
            type="button"
            onClick={startOver}
            className="min-h-11 rounded-sm px-2 text-[15px] font-semibold underline underline-offset-4 focus-visible:outline-white"
          >
            Start over
          </button>
        ) : null}
      </Band>

      {/* Hidden inputs shared by the entry buttons and the error actions. */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={onFilePicked}
      />
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED_FILE_TYPES.join(",")}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={onFilePicked}
      />

      <main
        className={`mx-auto w-full flex-1 px-4 pt-6 pb-10 ${
          showSource ? "max-w-[640px] lg:grid lg:max-w-[1120px] lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)] lg:gap-12" : "max-w-[640px]"
        }`}
      >
        {showSource && input ? (
          <div className="mb-6 lg:mb-0 lg:self-start lg:sticky lg:top-6">
            <SourcePanel input={input} rawText={rawText} />
          </div>
        ) : null}

        <div className="min-w-0">
          {phase === "entry" ? (
            <EntryForm
              text={text}
              textOpen={textOpen}
              focusText={focusText}
              onTextChange={setText}
              onTextOpen={setTextOpen}
              onTakePhoto={() => cameraRef.current?.click()}
              onChooseFile={() => fileRef.current?.click()}
              onSubmitText={() => submit({ kind: "text", text: text.trim() })}
            />
          ) : null}

          {phase === "processing" ? <ProgressStages stage={stage} onCancel={cancel} /> : null}

          {phase === "error" && error ? (
            <ErrorNotice
              error={error}
              actions={{
                onRetake: () => cameraRef.current?.click(),
                onChoose: () => fileRef.current?.click(),
                onEditText: editText,
                onStartOver: startOver,
                onRetry: () => input && submit(input),
              }}
            />
          ) : null}

          {(phase === "reviewing" || phase === "confirming" || phase === "confirmed") && response && card ? (
            <>
              <CaseCard
                card={card}
                summary={response.summary}
                flagged={flagged}
                locked={locked}
                landed={locked}
                today={today}
                caseId={locked ? response.case_id : undefined}
                onChange={onChange}
                onLooksRight={onLooksRight}
              />

              {!locked ? (
                <div className="sticky bottom-0 -mx-4 mt-6 border-t border-hairline bg-bond px-4 py-3 lg:static lg:mx-0 lg:border-0 lg:px-0">
                  {saveError ? (
                    <p role="alert" className="mb-3 text-[16px] font-semibold text-ink">
                      {saveError}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    onClick={confirm}
                    disabled={flagged.size > 0 || phase === "confirming"}
                    aria-describedby="confirm-help"
                    className="inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-federal px-5 text-[18px] font-semibold text-white disabled:cursor-not-allowed disabled:bg-hairline disabled:text-muted"
                  >
                    {phase === "confirming" ? "Opening the case…" : "Confirm"}
                  </button>
                  <p id="confirm-help" className="mt-2 text-center text-[15px] text-muted" aria-live="polite">
                    {flagged.size > 0
                      ? `${flagged.size} ${flagged.size === 1 ? "detail" : "details"} still to check before you can confirm.`
                      : "Confirm opens the case and starts the investigation."}
                  </p>
                </div>
              ) : (
                <div className="mt-6 border-t border-hairline pt-4" aria-live="polite">
                  <p className="text-[20px] font-bold">
                    Case opened: <span className="font-mono font-semibold">{response.case_id}</span>
                  </p>
                  <p className="mt-2 text-[17px] text-muted">
                    {investigation === "pending"
                      ? "Starting the investigation…"
                      : investigation === "started"
                        ? "The investigation has started. Opening the case…"
                        : "The investigation could not start."}
                  </p>
                  {investigation === "failed" ? (
                    <button
                      type="button"
                      onClick={() => startInvestigation(response.case_id)}
                      className="mt-3 inline-flex min-h-11 items-center rounded-sm border border-ink bg-bond px-4 text-[16px] font-semibold text-ink"
                    >
                      Try again
                    </button>
                  ) : null}
                </div>
              )}
            </>
          ) : null}
        </div>
      </main>
    </div>
  );
}

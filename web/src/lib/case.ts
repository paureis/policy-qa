/*
  Case card contract, fixture data, deadline math, and the API client for
  the intake screen. The contract lives in web/README.md; keep this file
  in step with it.
*/

export const PROGRAMS = [
  "florida_medicaid_mma",
  "florida_medicaid_ltc",
  "florida_kidcare",
  "medicare_a",
  "medicare_b",
  "medicare_advantage",
  "medicare_part_d",
  "unknown",
] as const;
export type Program = (typeof PROGRAMS)[number];

export const AGE_GROUPS = ["under_21", "adult", "65_plus", "unknown"] as const;
export type AgeGroup = (typeof AGE_GROUPS)[number];

export const CONFIDENCES = ["high", "medium", "low"] as const;
export type Confidence = (typeof CONFIDENCES)[number];

/* The ten contract fields, in the order the screen shows them. */
export const FIELD_ORDER = [
  "payer_name",
  "program",
  "member_age_group",
  "service",
  "service_code",
  "dates_of_service",
  "amount_billed",
  "denial_reason",
  "letter_date",
  "appeal_deadline_claimed",
] as const;
export type FieldKey = (typeof FIELD_ORDER)[number];

export type FieldValue = string | number | null;

export interface CardField {
  value: FieldValue;
  confidence: Confidence;
}

export type CaseCard = Record<FieldKey, CardField>;

export type Source = "image" | "pdf" | "text";

export interface IntakeResponse {
  case_id: string;
  source: Source;
  raw_text: string;
  summary: string;
  card: CaseCard;
  status: string;
}

export interface InvestigateResponse {
  case_id: string;
  status: string;
}

export const ERROR_CODES = [
  "unsupported_type",
  "too_large",
  "text_length",
  "unreadable",
  "not_a_denial_letter",
  "out_of_scope",
  "unreachable",
  "rejected",
  "timeout",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

export class IntakeError extends Error {
  code: ErrorCode;
  constructor(code: ErrorCode, message?: string) {
    super(message ?? ERROR_COPY[code].body);
    this.name = "IntakeError";
    this.code = code;
  }
}

/* Plain words for each error, and the action that fixes it. */
export const ERROR_COPY: Record<
  ErrorCode,
  { title: string; body: string; action: "retake" | "choose" | "edit_text" | "start_over" | "retry" }
> = {
  unreadable: {
    title: "We could not read this photo",
    body: "Lay the letter flat in good light, keep the whole page in the frame, and take the photo again.",
    action: "retake",
  },
  unsupported_type: {
    title: "That file type will not work",
    body: "Use a JPEG, PNG, WebP, or PDF up to 10 MB.",
    action: "choose",
  },
  too_large: {
    title: "That file is too large",
    body: "Use a JPEG, PNG, WebP, or PDF up to 10 MB.",
    action: "choose",
  },
  text_length: {
    title: "The text is the wrong length",
    body: "Paste between 200 and 6,000 characters. A whole denial letter usually fits.",
    action: "edit_text",
  },
  not_a_denial_letter: {
    title: "This does not read like a denial letter",
    body: "Recourse reads coverage denial letters and explanations of benefits from Florida Medicaid and Medicare. Check that the whole letter is included, then try again.",
    action: "start_over",
  },
  out_of_scope: {
    title: "Recourse cannot answer that",
    body: "Recourse reads coverage denial letters and drafts appeals. It does not give medical advice. For questions about treatment, dosage, or diagnosis, ask your doctor or pharmacist. If you have a denial letter, start with that.",
    action: "start_over",
  },
  rejected: {
    title: "The service could not accept that",
    body: "Check the details and try again. Your letter is still on this screen.",
    action: "retry",
  },
  unreachable: {
    title: "We could not reach the service",
    body: "Check your connection and try again. Your letter is still on this screen.",
    action: "retry",
  },
  timeout: {
    title: "This is taking longer than it should",
    body: "The letter has not come back after 30 seconds. Your letter is still on this screen.",
    action: "retry",
  },
};

/* Plain labels. */
export const PROGRAM_LABELS: Record<Program, string> = {
  florida_medicaid_mma: "Florida Medicaid (MMA)",
  florida_medicaid_ltc: "Florida Medicaid Long-Term Care",
  florida_kidcare: "Florida KidCare",
  medicare_a: "Medicare Part A",
  medicare_b: "Medicare Part B",
  medicare_advantage: "Medicare Advantage",
  medicare_part_d: "Medicare Part D",
  unknown: "Not sure yet",
};

export const AGE_GROUP_LABELS: Record<AgeGroup, string> = {
  under_21: "Under 21",
  adult: "Adult, 21 to 64",
  "65_plus": "65 or older",
  unknown: "Not sure yet",
};

export const FIELD_LABELS: Record<FieldKey, string> = {
  payer_name: "Who sent the letter",
  program: "Program",
  member_age_group: "Member's age group",
  service: "Service that was denied",
  service_code: "Service code",
  dates_of_service: "Dates of service",
  amount_billed: "Amount billed",
  denial_reason: "Reason the letter gives",
  letter_date: "Date on the letter",
  appeal_deadline_claimed: "Appeal deadline the letter claims",
};

export const FIELD_HINTS: Partial<Record<FieldKey, string>> = {
  service: "Up to 80 characters",
  service_code: "The billing code, if the letter shows one",
  dates_of_service: "One day, or a first and last day",
  amount_billed: "Dollars, up to five figures",
  denial_reason: "In the letter's own words, up to three sentences",
};

/* Limits from the brief. */
export const TEXT_MIN = 200;
export const TEXT_MAX = 6000;
export const FILE_MAX_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_FILE_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"] as const;
export const SERVICE_MAX = 80;
export const AMOUNT_MAX = 99999.99;
export const DENIAL_REASON_MAX = 420;
export const TIMEOUT_MS = 30_000;

/* Modes. NEXT_PUBLIC_ values are inlined at build time. */
export type IntakeMode = "fixture" | "live";
export const INTAKE_MODE: IntakeMode = process.env.NEXT_PUBLIC_INTAKE_MODE === "live" ? "live" : "fixture";
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/* ---------- Fixture: the Sunshine Health sample from the contract ---------- */

export const SAMPLE_CARD: CaseCard = {
  program: { value: "florida_medicaid_mma", confidence: "high" },
  member_age_group: { value: "under_21", confidence: "medium" },
  service: { value: "private duty nursing, 8 hours/day", confidence: "high" },
  service_code: { value: "T1000", confidence: "low" },
  dates_of_service: { value: "2026-09-01/2026-09-30", confidence: "high" },
  amount_billed: { value: 4320.0, confidence: "medium" },
  denial_reason: { value: "Services exceed the authorized amount.", confidence: "high" },
  letter_date: { value: "2026-10-14", confidence: "high" },
  appeal_deadline_claimed: { value: "2026-12-13", confidence: "medium" },
  payer_name: { value: "Sunshine Health", confidence: "high" },
};

export const SAMPLE_SUMMARY =
  "Sunshine Health, a Florida Medicaid managed care plan, denied private duty nursing at 8 hours a day for a member under 21. " +
  "The claim covers September 1 to 30, 2026, under code T1000, billed at $4,320.00. " +
  "The letter, dated October 14, 2026, says the services exceed the authorized amount. " +
  "It says an appeal must be filed by December 13, 2026.";

/* A short synthetic letter for photo and PDF input in fixture mode. Clearly not real. */
export const SAMPLE_LETTER_TEXT = `SAMPLE LETTER FOR DEMONSTRATION. NOT A REAL NOTICE.

Sunshine Health
Florida Medicaid Managed Medical Assistance
Notice of Adverse Benefit Determination

Date: October 14, 2026
Member: J. Sample (age 9)
Member ID: 00000000-SAMPLE
Provider: Sample Home Nursing LLC

This letter is about the request for private duty nursing, 8 hours per day, service code T1000, for dates of service September 1, 2026 through September 30, 2026. The amount billed was $4,320.00.

We have denied this request. Reason: Services exceed the authorized amount. The plan approved fewer hours than were billed for this period.

You have the right to appeal this decision. Your appeal must be received within 60 days of the date of this letter, by December 13, 2026. You may ask for a copy of the rule we used and the records we reviewed at no cost.

This is a synthetic sample written for a software demonstration. It does not describe a real member, provider, or claim.`;

const FIXTURE_DELAY_MS = 4200;
const SCOPE_TRIGGERS = ["dose", "dosage", "should i take", "diagnos", "is it safe"];

/* ---------- Deadline math ---------- */

export function parseIsoDate(value: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

/* Whole days from today (local midnight) to the deadline. Positive means still ahead. */
export function daysUntil(deadlineIso: string, today: Date = new Date()): number | null {
  const deadline = parseIsoDate(deadlineIso);
  if (!deadline) return null;
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const ms = deadline.getTime() - start.getTime();
  return Math.round(ms / 86_400_000);
}

export function dayCountLabel(days: number): string {
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  if (days > 1) return `${days} days left`;
  if (days === -1) return "1 day past";
  return `${-days} days past`;
}

const LONG_DATE = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" });
const SHORT_DATE = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

export function formatLongDate(iso: string): string {
  const d = parseIsoDate(iso);
  return d ? LONG_DATE.format(d) : iso;
}

export function formatShortDate(iso: string): string {
  const d = parseIsoDate(iso);
  return d ? SHORT_DATE.format(d) : iso;
}

export function splitDateRange(value: FieldValue): { from: string; to: string } {
  if (typeof value !== "string" || value === "") return { from: "", to: "" };
  const [from, to = ""] = value.split("/");
  return { from, to };
}

export function joinDateRange(from: string, to: string): string {
  if (!from) return "";
  return to && to !== from ? `${from}/${to}` : from;
}

export function formatDateRange(value: FieldValue): string {
  const { from, to } = splitDateRange(value);
  if (!from) return "";
  return to ? `${formatShortDate(from)} to ${formatShortDate(to)}` : formatLongDate(from);
}

export function formatAmount(value: FieldValue): string {
  if (value === null || value === "") return "";
  const n = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(n)) return String(value);
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

/* How a value reads when the card is locked. */
export function displayValue(key: FieldKey, value: FieldValue): string {
  if (value === null || value === "") return "Not found";
  switch (key) {
    case "program":
      return PROGRAM_LABELS[value as Program] ?? String(value);
    case "member_age_group":
      return AGE_GROUP_LABELS[value as AgeGroup] ?? String(value);
    case "dates_of_service":
      return formatDateRange(value);
    case "amount_billed":
      return formatAmount(value);
    case "letter_date":
    case "appeal_deadline_claimed":
      return formatLongDate(String(value));
    default:
      return String(value);
  }
}

export function isFlagged(field: CardField): boolean {
  return field.confidence !== "high" || field.value === null || field.value === "";
}

/* ---------- Input validation shared by both modes ---------- */

export type IntakeInput = { kind: "file"; file: File } | { kind: "text"; text: string };

export function validateInput(input: IntakeInput): IntakeError | null {
  if (input.kind === "text") {
    const n = input.text.trim().length;
    if (n < TEXT_MIN || n > TEXT_MAX) return new IntakeError("text_length");
    return null;
  }
  const { file } = input;
  if (!(ACCEPTED_FILE_TYPES as readonly string[]).includes(file.type)) return new IntakeError("unsupported_type");
  if (file.size > FILE_MAX_BYTES) return new IntakeError("too_large");
  return null;
}

export function sourceOf(input: IntakeInput): Source {
  if (input.kind === "text") return "text";
  return input.file.type === "application/pdf" ? "pdf" : "image";
}

/* ---------- API client ---------- */

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(abortError());
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(abortError());
      },
      { once: true },
    );
  });
}

function abortError(): Error {
  return new DOMException("Aborted", "AbortError");
}

export function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

let fixtureCounter = 0;

async function fixtureIntake(input: IntakeInput, signal?: AbortSignal): Promise<IntakeResponse> {
  const invalid = validateInput(input);
  if (invalid) {
    await sleep(600, signal);
    throw invalid;
  }
  if (input.kind === "file" && /blank/i.test(input.file.name)) {
    await sleep(FIXTURE_DELAY_MS, signal);
    throw new IntakeError("unreadable");
  }
  if (input.kind === "file" && /slow/i.test(input.file.name)) {
    await sleep(TIMEOUT_MS + 5_000, signal);
  }
  if (input.kind === "text") {
    const lower = input.text.toLowerCase();
    if (SCOPE_TRIGGERS.some((t) => lower.includes(t))) {
      await sleep(FIXTURE_DELAY_MS, signal);
      throw new IntakeError("out_of_scope");
    }
    if (lower.includes("[not a letter]")) {
      await sleep(FIXTURE_DELAY_MS, signal);
      throw new IntakeError("not_a_denial_letter");
    }
    if (lower.includes("[slow]")) {
      await sleep(TIMEOUT_MS + 5_000, signal);
    }
  }
  await sleep(FIXTURE_DELAY_MS, signal);
  fixtureCounter += 1;
  const card: CaseCard = structuredClone(SAMPLE_CARD);
  return {
    case_id: `c_sample${fixtureCounter}`,
    source: sourceOf(input),
    raw_text: input.kind === "text" ? input.text : SAMPLE_LETTER_TEXT,
    summary: SAMPLE_SUMMARY,
    card,
    status: "intake",
  };
}

function withTimeout(signal: AbortSignal | undefined): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(new IntakeError("timeout")), TIMEOUT_MS);
  signal?.addEventListener("abort", () => controller.abort(abortError()), { once: true });
  return { signal: controller.signal, clear: () => clearTimeout(t) };
}

async function readError(res: Response): Promise<IntakeError> {
  if (res.status >= 500) return new IntakeError("unreachable");
  try {
    const body = (await res.json()) as { detail?: { code?: string; message?: string } | string };
    const detail = typeof body.detail === "object" && body.detail ? body.detail : undefined;
    const code = detail?.code;
    if (code && (ERROR_CODES as readonly string[]).includes(code)) {
      return new IntakeError(code as ErrorCode, detail?.message || undefined);
    }
    if (res.status < 500 && detail?.message) {
      return new IntakeError("rejected", detail.message);
    }
  } catch {
    /* fall through */
  }
  return new IntakeError("unreachable");
}

async function liveFetch(path: string, init: RequestInit, outer?: AbortSignal): Promise<Response> {
  const { signal, clear } = withTimeout(outer);
  try {
    return await fetch(`${API_URL}${path}`, { ...init, signal });
  } catch {
    if (signal.aborted && signal.reason instanceof IntakeError) throw signal.reason;
    if (outer?.aborted) throw abortError();
    throw new IntakeError("unreachable");
  } finally {
    clear();
  }
}

async function liveIntake(input: IntakeInput, signal?: AbortSignal): Promise<IntakeResponse> {
  const invalid = validateInput(input);
  if (invalid) throw invalid;
  const form = new FormData();
  if (input.kind === "file") form.append("file", input.file, input.file.name);
  else form.append("text", input.text);
  const res = await liveFetch("/case/intake", { method: "POST", body: form }, signal);
  if (!res.ok) throw await readError(res);
  return (await res.json()) as IntakeResponse;
}

export function intake(input: IntakeInput, signal?: AbortSignal): Promise<IntakeResponse> {
  return INTAKE_MODE === "live" ? liveIntake(input, signal) : fixtureIntake(input, signal);
}

export type CasePatch = Partial<Record<FieldKey, FieldValue>>;

export async function patchCase(caseId: string, patch: CasePatch, current: IntakeResponse): Promise<IntakeResponse> {
  if (INTAKE_MODE !== "live") {
    await sleep(300);
    const card = structuredClone(current.card);
    for (const [k, v] of Object.entries(patch) as [FieldKey, FieldValue][]) {
      card[k] = { value: v, confidence: "high" };
    }
    return { ...current, card };
  }
  if (Object.keys(patch).length === 0) return current;
  const res = await liveFetch(`/case/${encodeURIComponent(caseId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw await readError(res);
  return (await res.json()) as IntakeResponse;
}

export async function investigate(caseId: string): Promise<InvestigateResponse> {
  if (INTAKE_MODE !== "live") {
    await sleep(400);
    return { case_id: caseId, status: "investigating" };
  }
  const res = await liveFetch(`/case/${encodeURIComponent(caseId)}/investigate`, { method: "POST" });
  if (!res.ok) throw await readError(res);
  return (await res.json()) as InvestigateResponse;
}

/* The plain values the PATCH body carries, for every field whose value changed. */
export function diffCard(original: CaseCard, edited: CaseCard): CasePatch {
  const patch: CasePatch = {};
  for (const key of FIELD_ORDER) {
    const a = original[key].value;
    const b = edited[key].value;
    if (a !== b) patch[key] = b;
  }
  return patch;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

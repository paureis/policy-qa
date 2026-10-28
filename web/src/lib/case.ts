/*
  Case card contract, fixture data, deadline math, and the API client for
  the intake screen. The contract lives in web/README.md; keep this file
  in step with it.
*/

import { PAGE_FIXTURES } from "./page-fixtures";

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
  "not_found",
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
  not_found: {
    title: "We could not find that case",
    body: "Cases live only while the service is running. Start a new case from your letter.",
    action: "start_over",
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
    startFixtureInvestigation(caseId);
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

/* ---------- Investigation: contract, fixture, client ---------- */

export type CaseStatus =
  | "intake"
  | "investigating"
  | "investigated"
  | "deciding"
  | "decided"
  | "drafting"
  | "drafted"
  | "reviewing"
  | "reviewed"
  | "failed";
export type Jurisdiction = "Florida" | "Federal";
export const JURISDICTIONS: readonly Jurisdiction[] = ["Florida", "Federal"];

export type FindingTopic = "coverage" | "limits" | "conditions" | "exclusions" | "appeal" | "reason" | "other";
/* "error" means the model call failed: nothing was investigated, which is not an abstention. */
export type FindingStatus = "supported" | "not_settled" | "unsupported" | "error";

export interface Route {
  program: string;
  jurisdictions: Jurisdiction[];
  dual: boolean;
  /* One full sentence from the API, ending with a period. */
  reason: string;
}

export interface Citation {
  doc_id: string;
  title: string | null;
  page: number;
  quote: string;
  overlap: number;
}

/* A citation the verifier dropped. A quote from a passage that was not shown has no document, title, or page. */
export interface StruckCitation {
  doc_id: string | null;
  title: string | null;
  page: number | null;
  quote: string;
  reason: string;
}

/* A passage retrieved and shown to the model for one question. */
export interface PassageShown {
  chunk_id: string;
  doc_id: string;
  title: string | null;
  page: number;
}

export interface Finding {
  id: string;
  question: string;
  topic: FindingTopic;
  jurisdiction: Jurisdiction;
  status: FindingStatus;
  answer: string;
  citations: Citation[];
  struck: StruckCitation[];
  /* Set when status is "error": what went wrong with the model call. */
  error?: string | null;
  passages?: PassageShown[];
  model: string;
  input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  latency_ms: number;
  cost_usd: number;
}

/* A trace span as the API may send it; only name and ms are read. */
export interface TraceSpan {
  name: string;
  ms: number;
  [extra: string]: unknown;
}

export interface Investigation {
  status: "running" | "done" | "failed";
  started_at: string | null;
  finished_at: string | null;
  questions_planned: number;
  questions_done: number;
  findings: Finding[];
  coverage: { claims: number; supported: number; errors?: number };
  cost_usd: number;
  latency_ms: number;
  model: string;
  error: string | null;
  trace?: TraceSpan[] | { spans?: TraceSpan[] } | null;
}

/* The case as GET /case/{id} returns it: intake fields plus route and investigation. */
export interface CaseRecord extends IntakeResponse {
  status: CaseStatus;
  route: Route | null;
  investigation: Investigation | null;
  /* Steelman and verdict, once the investigation is done. Absent on older API builds. */
  verdict?: Verdict | null;
  /* The appeal letter and the action around it, once the verdict is reached. */
  letter?: Letter | null;
  /* The critic's self-check of the letter, once drafted. Null until it starts; absent on older API builds. */
  critique?: Critique | null;
  created_at?: string;
  model?: string;
  cost_usd?: number;
  latency_ms?: number;
}

export const POLL_MS = 1500;

export const TOPIC_LABELS: Record<FindingTopic, string> = {
  coverage: "Coverage",
  limits: "Limits",
  conditions: "Conditions and prior authorization",
  exclusions: "Exclusions",
  appeal: "Appeal rights and deadline",
  reason: "The letter's reason",
  other: "Other",
};

/* Program names for the route line. */
export const JURISDICTION_LABELS: Record<Jurisdiction, string> = {
  Florida: "Florida Medicaid",
  Federal: "Medicare",
};

/* Group headings on a dual case: the federal corpus holds more than Medicare. */
export const JURISDICTION_HEADINGS: Record<Jurisdiction, string> = {
  Florida: "Florida Medicaid",
  Federal: "Medicare and federal rules",
};

export const NOT_SETTLED_LABEL = "The documents do not settle this";
export const COULD_NOT_VERIFY_LABEL = "Could not verify";
export const COULD_NOT_INVESTIGATE_LABEL = "Could not investigate this question";

/* The verifier's three reasons, exactly as the API sends them. */
export const STRUCK_NOT_FOUND = "quote not found on the cited page";
export const STRUCK_NOT_SHOWN = "cited a passage that was not shown";
export const STRUCK_TOO_SHORT = "quote too short to verify";

/* The model name the fixture reports, so no screen mistakes it for a real run. */
export const FIXTURE_MODEL = "fixture";

const LEGACY_ERROR_PREFIX = "Could not investigate";

/*
  The status the screen renders. Older API builds sent a failed model call as
  not_settled with an answer starting "Could not investigate"; that is an
  error, never an abstention.
*/
export function findingStatus(finding: Finding): FindingStatus {
  if (finding.status === "error") return "error";
  if (finding.status === "not_settled" && finding.answer.trim().startsWith(LEGACY_ERROR_PREFIX)) return "error";
  return finding.status;
}

/* What went wrong with an error finding, in the API's words. Empty when it gave none. */
export function findingError(finding: Finding): string {
  const direct = finding.error?.trim();
  if (direct) return direct;
  const answer = finding.answer.trim();
  if (!answer.startsWith(LEGACY_ERROR_PREFIX)) return "";
  const colon = answer.indexOf(":");
  return colon >= 0 ? answer.slice(colon + 1).trim() : "";
}

/* Questions whose model call failed. The API's count wins; the findings are the fallback. */
export function countErrors(investigation: Investigation): number {
  const sent = investigation.coverage?.errors;
  if (typeof sent === "number" && Number.isFinite(sent)) return sent;
  return investigation.findings.filter((f) => findingStatus(f) === "error").length;
}

/* "Claimed from {title}, page {n}", never with an empty title or page. */
export function struckSource(s: StruckCitation): string {
  const title = s.title?.trim() || s.doc_id?.trim() || "";
  const page = typeof s.page === "number" ? s.page : null;
  if (title && page !== null) return `Claimed from ${title}, page ${page}.`;
  if (title) return `Claimed from ${title}.`;
  if (page !== null) return `Claimed from page ${page} of a document that was not named.`;
  return "Claimed from a passage that was not shown.";
}

/* Why an unsupported finding is struck out, in words that fit the verifier's reasons. */
export function unsupportedExplanation(struck: StruckCitation[]): string {
  const tail = "so the answer is struck out and not used.";
  if (struck.length === 0) return `The model answered but gave no citation, ${tail}`;
  const reasons = new Set(struck.map((s) => s.reason.trim()));
  if (reasons.size === 1 && reasons.has(STRUCK_NOT_SHOWN)) {
    return `The model answered, but it cited passages it was not given, ${tail}`;
  }
  if (reasons.size === 1 && reasons.has(STRUCK_NOT_FOUND)) {
    return `The model answered, but the verifier could not find its quote on the cited page, ${tail}`;
  }
  if (reasons.size === 1 && reasons.has(STRUCK_TOO_SHORT)) {
    return `The model answered, but its quotes were too short to check against the page, ${tail}`;
  }
  return `The model answered, but none of its quotes could be checked on the cited page, ${tail}`;
}

/* A reason as one sentence: capital first letter, exactly one period. */
function asSentence(text: string): string {
  const t = text.trim().replace(/[.\s]+$/, "");
  if (!t) return "";
  return `${t.charAt(0).toUpperCase()}${t.slice(1)}.`;
}

/* The route in plain words, then the API's reason as its own sentence. */
export function routeLine(route: Route): string {
  let lead: string;
  if (route.dual) {
    const names = route.jurisdictions.map((j) => JURISDICTION_LABELS[j]);
    const pair = names.length >= 2 ? `${names[0]} and ${names[1]}` : (names[0] ?? "two programs");
    lead = `Investigating under ${pair}, side by side.`;
  } else {
    const known = route.program !== "unknown" ? PROGRAM_LABELS[route.program as Program] : undefined;
    const label = known ?? (route.jurisdictions[0] ? JURISDICTION_LABELS[route.jurisdictions[0]] : route.program);
    lead = `Investigating under ${label}.`;
  }
  const why = asSentence(route.reason ?? "");
  return why ? `${lead} ${why}` : lead;
}

/* Dollars to four decimals. A zero from a real model means its prices are not configured, not that it was free. */
export function formatCost(usd: number, model?: string): string {
  const base = `$${usd.toFixed(4)}`;
  return usd === 0 && model !== undefined && model !== FIXTURE_MODEL ? `${base} (prices not set)` : base;
}

export function formatSeconds(ms: number): string {
  const s = ms / 1000;
  return s >= 10 ? `${Math.round(s)} seconds` : `${s.toFixed(1)} seconds`;
}

/* ---------- Fixture: the Sunshine Health sample investigated ---------- */

const FIXTURE_REVEAL_MS = 800;

/*
  Synthetic quotes, marked as such the way the API fixture marks them,
  attributed to real rows of corpus/manifest.csv. They are demonstration
  text, not the documents' words; live mode shows verified quotes. Cost is
  zero and latencies are the reveal delay: nothing here is a recorded run.
*/
const SYNTHETIC = "[synthetic fixture quote, not from the document] ";
const ABSTAIN_TEXT = "Not covered by the corpus.";

const DOC_PDN = {
  doc_id: "fl-04",
  title: "Florida Medicaid Private Duty Nursing and Family Home Health Aide Services Coverage Policy (Rule 59G-4.261)",
};
const DOC_MMA = {
  doc_id: "fl-21",
  title: "SMMC Model Health Plan Contract, Exhibit II-A: Managed Medical Assistance (MMA) Program",
};
const DOC_HOME_HEALTH = {
  doc_id: "fed-02",
  title: "Medicare Benefit Policy Manual (Pub 100-02), Chapter 7: Home Health Services",
};
const DOC_APPEALS = {
  doc_id: "fed-17",
  title: "Medicare Parts A & B Appeals Process (MLN006562)",
};

function cite(doc: { doc_id: string; title: string }, page: number, quote: string, overlap = 1.0): Citation {
  return { ...doc, page, quote: SYNTHETIC + quote, overlap };
}

function strike(doc: { doc_id: string; title: string } | null, page: number | null, quote: string, reason: string): StruckCitation {
  return doc ? { ...doc, page, quote: SYNTHETIC + quote, reason } : { doc_id: null, title: null, page: null, quote: SYNTHETIC + quote, reason };
}

function shown(id: string, jurisdiction: Jurisdiction): PassageShown[] {
  const docs = jurisdiction === "Florida" ? [DOC_PDN, DOC_PDN, DOC_PDN, DOC_MMA, DOC_MMA] : [DOC_HOME_HEALTH, DOC_HOME_HEALTH, DOC_HOME_HEALTH, DOC_APPEALS, DOC_APPEALS];
  const pages = jurisdiction === "Florida" ? [3, 4, 5, 41, 43] : [42, 44, 51, 6, 7];
  return docs.map((d, i) => ({ chunk_id: `${d.doc_id}:p${pages[i]}:${id}`, doc_id: d.doc_id, title: d.title, page: pages[i] }));
}

function fixtureFinding(
  id: string,
  jurisdiction: Jurisdiction,
  topic: FindingTopic,
  question: string,
  status: FindingStatus,
  answer: string,
  citations: Citation[],
  struck: StruckCitation[],
  extra: Partial<Finding> = {},
): Finding {
  return {
    id,
    question,
    topic,
    jurisdiction,
    status,
    answer,
    citations,
    struck,
    passages: shown(id, jurisdiction),
    model: FIXTURE_MODEL,
    input_tokens: 0,
    output_tokens: 0,
    reasoning_tokens: 0,
    latency_ms: FIXTURE_REVEAL_MS,
    cost_usd: 0,
    ...extra,
  };
}

const FIXTURE_FINDINGS_FLORIDA: Finding[] = [
  fixtureFinding(
    "f_1",
    "Florida",
    "coverage",
    "Is private duty nursing a covered service for a Florida Medicaid member under 21?",
    "supported",
    "Yes. The policy covers private duty nursing for members under 21 when a physician orders it and the member needs continuous skilled nursing at home.",
    [
      cite(
        DOC_PDN,
        3,
        "Florida Medicaid covers private duty nursing services for recipients under the age of 21 who require continuous skilled nursing care in the home, as ordered by the treating physician.",
      ),
    ],
    [],
  ),
  fixtureFinding(
    "f_2",
    "Florida",
    "limits",
    "Does the policy set a limit on the hours of private duty nursing a member can receive each day?",
    "supported",
    "The policy does not fix a daily cap. Hours are set by the plan's medical necessity review for each authorization period, and the authorization states the number approved.",
    [
      cite(
        DOC_PDN,
        5,
        "The number of hours authorized is determined through the medical necessity review and is stated on the authorization for each authorization period.",
      ),
      cite(DOC_MMA, 38, "Services rendered in excess of the authorized amount are subject to the plan's reimbursement limits.", 0.93),
    ],
    [strike(null, null, "Private duty nursing is limited to 16 hours per day for any recipient.", STRUCK_NOT_SHOWN)],
  ),
  fixtureFinding(
    "f_3",
    "Florida",
    "conditions",
    "Must the plan tell the member how many hours it authorized before the services start?",
    "not_settled",
    ABSTAIN_TEXT,
    [],
    [],
  ),
  fixtureFinding(
    "f_4",
    "Florida",
    "exclusions",
    "Can the plan deny hours that exceed the authorization when the physician's order supports the higher amount?",
    "unsupported",
    "No. The policy states that a physician's order for additional hours overrides the authorized amount for the same period.",
    [],
    [strike(DOC_PDN, 7, "A physician's order for additional hours overrides the authorized amount for the same period.", STRUCK_NOT_FOUND)],
  ),
  fixtureFinding(
    "f_5",
    "Florida",
    "appeal",
    "How long does a Florida Medicaid managed care member have to appeal an adverse benefit determination?",
    "supported",
    "60 calendar days from the date on the notice, which matches the December 13, 2026 deadline the letter claims. The member may also ask for continued services while the appeal is pending if the request is made within 10 days.",
    [
      cite(DOC_MMA, 41, "An enrollee may file an appeal within sixty (60) calendar days from the date on the notice of adverse benefit determination."),
      cite(
        DOC_MMA,
        43,
        "Benefits shall continue if the enrollee files the appeal within ten (10) days of the date of the notice of adverse benefit determination.",
        0.97,
      ),
    ],
    [strike(DOC_MMA, 43, "within ten days", STRUCK_TOO_SHORT)],
  ),
];

const FIXTURE_FINDINGS_FEDERAL: Finding[] = [
  fixtureFinding(
    "f_6",
    "Federal",
    "coverage",
    "Does Medicare cover private duty nursing at home?",
    "supported",
    "No. Medicare home health covers intermittent skilled nursing only; continuous or full-time nursing at home is excluded.",
    [cite(DOC_HOME_HEALTH, 42, "Private duty nursing is not a covered home health service under Medicare.")],
    [],
  ),
  fixtureFinding(
    "f_7",
    "Federal",
    "limits",
    "Does Medicare limit how many hours of home health nursing a member can receive each week?",
    "unsupported",
    "Yes. Medicare pays for at most 28 hours a week of combined skilled nursing and home health aide services.",
    [],
    [strike(null, null, "Combined skilled nursing and home health aide services may not exceed 28 hours per week.", STRUCK_NOT_SHOWN)],
  ),
  fixtureFinding(
    "f_8",
    "Federal",
    "appeal",
    "How long does a Medicare beneficiary have to request a redetermination?",
    "supported",
    "120 days from the date of receipt of the initial determination.",
    [cite(DOC_APPEALS, 7, "A request for redetermination must be filed within 120 days of the date of receipt of the notice of initial determination.")],
    [],
  ),
];

/* c_error*: the sample with one question whose model call failed. */
const FIXTURE_FINDINGS_ERROR: Finding[] = [
  ...FIXTURE_FINDINGS_FLORIDA.slice(0, 3),
  fixtureFinding(
    "f_e",
    "Florida",
    "reason",
    "What do the rules say when services exceed the authorized amount?",
    "error",
    "",
    [],
    [],
    { error: "ReadTimeout: the model did not answer within the time limit.", passages: undefined },
  ),
  ...FIXTURE_FINDINGS_FLORIDA.slice(3),
];

/* Route reasons as the API words them: one full sentence each. */
const ROUTE_SAMPLE: Route = {
  program: "florida_medicaid_mma",
  jurisdictions: ["Florida"],
  dual: false,
  reason: "The letter is about Florida Medicaid (MMA), so the Florida Medicaid rules decide this case.",
};
const ROUTE_DUAL: Route = {
  program: "unknown",
  jurisdictions: ["Florida", "Federal"],
  dual: true,
  reason:
    "The letter does not say which program paid for the care, so the Florida Medicaid rules and the federal Medicare rules are checked side by side.",
};

const fixtureStarts = new Map<string, number>();

/* Called when the fixture investigate POST returns, so the reveal clock starts then. */
function startFixtureInvestigation(caseId: string, at: number = Date.now()): void {
  if (!fixtureStarts.has(caseId)) fixtureStarts.set(caseId, at);
}

const FIXTURE_ID = /^c_(sample\d*|dual\d*|fail\d*|error\d*|consistent\d*|notsettled\d*|rejected\d*|checkerror\d*)$/;

/*
  Fixture ids never collide with the API's (c_ and six hex digits), so outside
  a production build they render from the fixture in live mode too: every
  state stays reachable for screenshots on the live dev server.
*/
export function isFixtureCase(caseId: string): boolean {
  return INTAKE_MODE !== "live" || (process.env.NODE_ENV !== "production" && FIXTURE_ID.test(caseId));
}

function fixtureCase(caseId: string, now: number): CaseRecord | null {
  if (!FIXTURE_ID.test(caseId)) return null;
  const dual = caseId.startsWith("c_dual");
  const consistent = caseId.startsWith("c_consistent");
  const notSettled = caseId.startsWith("c_notsettled");
  const fail = caseId.startsWith("c_fail");
  const withError = caseId.startsWith("c_error");
  const rejected = caseId.startsWith("c_rejected");
  const checkError = caseId.startsWith("c_checkerror");
  startFixtureInvestigation(caseId, now);
  const startedAt = fixtureStarts.get(caseId) ?? now;
  const planned = dual
    ? [...FIXTURE_FINDINGS_FLORIDA, ...FIXTURE_FINDINGS_FEDERAL]
    : withError
      ? FIXTURE_FINDINGS_ERROR
      : FIXTURE_FINDINGS_FLORIDA;
  const elapsed = Math.max(0, now - startedAt);
  const revealed = Math.min(planned.length, Math.floor(elapsed / FIXTURE_REVEAL_MS));
  const failAt = 2;
  const done = fail ? Math.min(revealed, failAt) : revealed;
  const findings = planned.slice(0, done);
  const finished = fail ? revealed >= failAt : done === planned.length;
  const supported = findings.filter((f) => f.status === "supported").length;
  const unsupported = findings.filter((f) => f.status === "unsupported").length;
  const errors = findings.filter((f) => f.status === "error").length;
  const latency = finished ? planned.slice(0, done).reduce((s, f) => s + f.latency_ms, 0) + 120 : elapsed;
  const card: CaseCard = structuredClone(SAMPLE_CARD);
  if (dual) {
    card.program = { value: "unknown", confidence: "high" };
    card.member_age_group = { value: "65_plus", confidence: "high" };
  }
  /* After the last finding, the chain continues: deciding, decided, drafting, drafted, reviewing, reviewed. */
  const kind = dual
    ? "dual"
    : consistent
      ? "consistent"
      : notSettled
        ? "notsettled"
        : rejected
          ? "rejected"
          : checkError
            ? "checkerror"
            : "sample";
  const chain = finished && !fail ? fixtureChain(kind, now - (startedAt + latency)) : null;
  const trace: TraceSpan[] = [
    { name: "route", ms: 2 },
    { name: "plan questions", ms: 1 },
    ...findings.map((f, i) => ({ name: `question ${i + 1}: retrieve, answer, verify`, ms: f.latency_ms })),
  ];
  return {
    case_id: caseId,
    source: "text",
    raw_text: SAMPLE_LETTER_TEXT,
    summary: SAMPLE_SUMMARY,
    card,
    status: finished ? (fail ? "failed" : (chain?.status ?? "investigated")) : "investigating",
    route: dual ? ROUTE_DUAL : ROUTE_SAMPLE,
    investigation: {
      status: finished ? (fail ? "failed" : "done") : "running",
      started_at: new Date(startedAt).toISOString(),
      finished_at: finished ? new Date(startedAt + latency).toISOString() : null,
      questions_planned: planned.length,
      questions_done: done,
      findings,
      coverage: { claims: supported + unsupported, supported, errors },
      cost_usd: 0,
      latency_ms: latency,
      model: FIXTURE_MODEL,
      error: fail && finished ? "TimeoutError: the model did not answer question 3 after three attempts." : null,
      trace,
    },
    verdict: chain?.verdict ?? null,
    letter: chain?.letter ?? null,
    critique: chain?.critique ?? null,
    created_at: new Date(startedAt - 60_000).toISOString(),
  };
}

async function fixtureGetCase(caseId: string, signal?: AbortSignal): Promise<CaseRecord> {
  await sleep(250, signal);
  const record = fixtureCase(caseId, Date.now());
  if (!record) throw new IntakeError("not_found");
  return record;
}

async function liveGetCase(caseId: string, signal?: AbortSignal): Promise<CaseRecord> {
  return liveRequest(`/case/${encodeURIComponent(caseId)}`, { method: "GET" }, signal, async (res) => {
    if (res.status === 404) throw new IntakeError("not_found");
    if (!res.ok) throw await readCaseError(res);
    return (await res.json()) as CaseRecord;
  });
}

/*
  A request whose timeout also covers reading the body: the timer is cleared
  only after read() finishes, so a response whose headers arrive but whose
  body stalls still ends at TIMEOUT_MS with IntakeError("timeout").
*/
async function liveRequest<T>(path: string, init: RequestInit, outer: AbortSignal | undefined, read: (res: Response) => Promise<T>): Promise<T> {
  const { signal, clear } = withTimeout(outer);
  const failure = (): Error => {
    if (signal.aborted && signal.reason instanceof IntakeError) return signal.reason;
    if (outer?.aborted) return abortError();
    return new IntakeError("unreachable");
  };
  try {
    let res: Response;
    try {
      res = await fetch(`${API_URL}${path}`, { ...init, signal });
    } catch {
      throw failure();
    }
    try {
      return await read(res);
    } catch (err) {
      if (err instanceof IntakeError) throw err;
      throw failure();
    }
  } finally {
    clear();
  }
}

/*
  Any other non-2xx from GET /case/{id}: keep the API's own message (5xx
  included) so the case page can show it, instead of the generic copy. A
  response with no readable message says which status came back.
*/
async function readCaseError(res: Response): Promise<IntakeError> {
  let detail: { code?: string; message?: string } | string | undefined;
  try {
    detail = ((await res.json()) as { detail?: { code?: string; message?: string } | string }).detail;
  } catch {
    detail = undefined;
  }
  const obj = typeof detail === "object" && detail ? detail : undefined;
  const message = obj?.message?.trim() || (typeof detail === "string" ? detail.trim() : "") || `The service answered ${res.status}.`;
  const code: ErrorCode =
    obj?.code && (ERROR_CODES as readonly string[]).includes(obj.code) ? (obj.code as ErrorCode) : res.status >= 500 ? "unreachable" : "rejected";
  return new IntakeError(code, message);
}

/* GET /case/{id}. Throws IntakeError("not_found") on 404. */
export function getCase(caseId: string, signal?: AbortSignal): Promise<CaseRecord> {
  return isFixtureCase(caseId) ? fixtureGetCase(caseId, signal) : liveGetCase(caseId, signal);
}

/* Keep polling while the investigation runs (the investigation step alone). */
export function isInvestigating(record: CaseRecord): boolean {
  return record.status === "investigating" && (record.investigation === null || record.investigation.status === "running");
}

/*
  Fetch the case, hand each version to onUpdate, and poll every POLL_MS while
  the case works itself (investigation, verdict, letter) until drafted or failed. Resolves with the final record. Aborting the signal
  stops the loop quietly. Errors (including not_found) propagate.
*/
export async function pollCase(
  caseId: string,
  onUpdate: (record: CaseRecord) => void,
  signal?: AbortSignal,
  intervalMs: number = POLL_MS,
): Promise<CaseRecord> {
  for (;;) {
    const record = await getCase(caseId, signal);
    if (signal?.aborted) throw abortError();
    onUpdate(record);
    if (!isWorking(record)) return record;
    await sleep(intervalMs, signal);
  }
}

/* Findings grouped by jurisdiction, in the route's order, empty groups dropped. */
export function groupFindings(findings: Finding[], order: Jurisdiction[] = [...JURISDICTIONS]): { jurisdiction: Jurisdiction; findings: Finding[] }[] {
  return order
    .map((jurisdiction) => ({ jurisdiction, findings: findings.filter((f) => f.jurisdiction === jurisdiction) }))
    .filter((g) => g.findings.length > 0);
}

/* ---------- Verdict and Action: contract, helpers, fixture ---------- */

/* A citation the verdict or letter borrows from a finding: the finding's verified quote. */
export interface CitationRef {
  finding_id: string | null;
  doc_id: string;
  title: string | null;
  page: number;
  quote: string;
}

export type StepStatus = "running" | "done" | "failed";
export type VerdictOutcome = "consistent" | "inconsistent" | "not_settled";

/* The three verdicts, verbatim. The screen renders these from the outcome so the wording cannot drift. */
export const VERDICT_HEADLINES: Record<VerdictOutcome, string> = {
  consistent: "The denial matches the policy.",
  inconsistent: "The denial appears inconsistent with the policy.",
  not_settled: "The documents do not settle it.",
};

export interface Usage {
  model: string;
  input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  latency_ms: number;
  cost_usd: number;
  error: string | null;
}

export interface Verdict extends Usage {
  status: StepStatus;
  steelman: { argument: string; citations: CitationRef[]; unsupported?: boolean };
  outcome: VerdictOutcome;
  headline: string;
  rule: { statement: string; citations: CitationRef[]; unsupported?: boolean };
  gap: string;
  what_would_change: string | null;
}

export interface LetterSentence {
  text: string;
  claim: boolean;
  citation: CitationRef | null;
  verified: boolean;
  struck: boolean;
}

export interface EvidenceItem {
  item: string;
  why: string;
  citation: CitationRef | null;
}

export interface LetterDeadline {
  date: string | null;
  days_left: number | null;
  source: "letter" | "policy" | "unknown";
  citation: CitationRef | null;
  note: string;
}

export interface Paragraph {
  sentences: LetterSentence[];
}

export interface Letter extends Usage {
  status: StepStatus;
  applicable: boolean;
  explanation: string | null;
  to: string;
  re: string;
  /* The accepted revision when the critic's round was accepted, else the draft. This is what is copied. */
  paragraphs: Paragraph[];
  /* The original draft, always. Absent on older API builds. */
  draft_paragraphs?: Paragraph[];
  evidence_checklist: EvidenceItem[];
  deadline: LetterDeadline;
  filing: { where: string; how: string; citation: CitationRef | null };
  verification: { claims: number; verified: number; struck: number };
}

/* The headline for an outcome, verbatim; the API's own text only if the outcome is unknown. */
export function verdictHeadline(verdict: Pick<Verdict, "outcome" | "headline">): string {
  return VERDICT_HEADLINES[verdict.outcome] ?? verdict.headline;
}

/*
  A sentence is struck when the verifier struck it, or when it makes a claim
  that was not verified: no claim reaches the person without a verified
  citation.
*/
export function sentenceStruck(s: LetterSentence): boolean {
  return s.struck || (s.claim && !s.verified);
}

export function citationLabel(c: { title: string | null; doc_id: string }): string {
  return c.title?.trim() || c.doc_id;
}

/*
  The letter as plain text: To, Re, then the paragraphs. Struck sentences are
  left out; each verified claim is followed by "[cite: title, p. N]".
*/
export function letterPlainText(letter: Pick<Letter, "to" | "re" | "paragraphs">): string {
  const head = [`To: ${letter.to}`, `Re: ${letter.re}`];
  const body = (letter.paragraphs ?? [])
    .map((p) =>
      (p.sentences ?? [])
        .filter((s) => !sentenceStruck(s))
        .map((s) => {
          const text = s.text.trim();
          if (s.claim && s.verified && s.citation) return `${text} [cite: ${citationLabel(s.citation)}, p. ${s.citation.page}]`;
          return text;
        })
        .join(" "),
    )
    .filter((p) => p !== "");
  return `${head.join("\n")}\n\n${body.join("\n\n")}\n`;
}

/* The letter's counts as a sentence: counts, never a percentage. */
export function letterVerificationLine(v: Letter["verification"]): string {
  const noun = v.claims === 1 ? "letter sentence" : "letter sentences";
  return `${v.verified} of ${v.claims} ${noun} verified; ${v.struck} struck`;
}

/* The stage line after the investigation line, by case status. Null while investigating. */
export function stageLine(record: Pick<CaseRecord, "status" | "letter" | "critique">): string | null {
  const noLetter = record.letter?.applicable === false;
  const c = record.critique ?? null;
  if (critiqueFailed(record)) return noLetter ? NO_LETTER_LINE : "Appeal letter ready. The self-check could not run.";
  switch (record.status) {
    case "deciding":
      return "Weighing the payer's side…";
    case "decided":
      return "Verdict reached.";
    case "drafting":
      return "Drafting the appeal letter…";
    case "drafted":
      return noLetter ? NO_LETTER_LINE : "Appeal letter ready.";
    case "reviewing":
      return noLetter ? NO_LETTER_LINE : "Checking the letter against itself…";
    case "reviewed":
      if (noLetter) return NO_LETTER_LINE;
      if (c && c.status === "done" && !c.skipped && c.accepted) {
        if (c.issues_found === 0) return "Letter checked: no issues found.";
        return `Letter checked: ${c.issues_fixed} of ${c.issues_found} ${c.issues_found === 1 ? "issue" : "issues"} fixed.`;
      }
      return "Letter checked: the first draft stands.";
    default:
      return null;
  }
}

const NO_LETTER_LINE = "Verdict reached. No appeal letter was drafted.";

/* The muted line under the stage line: the critic's reason when it skipped the letter. */
export function stageNote(record: Pick<CaseRecord, "status" | "critique">): string | null {
  const c = record.critique ?? null;
  if (record.status === "reviewed" && c?.skipped) return c.reason?.trim() || null;
  return null;
}

/*
  The critic failed: its own status says so, or the case failed after the
  letter was drafted. The letter stays usable; the self-check section says so.
*/
export function critiqueFailed(record: Pick<CaseRecord, "status" | "letter" | "critique">): boolean {
  if (critiqueError(record.critique ?? null) !== null) return true;
  return record.status === "failed" && record.letter?.status === "done";
}

const WORKING: readonly CaseStatus[] = ["investigating", "investigated", "deciding", "decided", "drafting", "reviewing"];

/*
  Keep polling until the case is reviewed or failed, or any stage failed (one
  POST drives the whole chain). A record at drafted with no critique key is an
  older API build, whose chain ends there.
*/
export function isWorking(record: CaseRecord): boolean {
  if (
    record.investigation?.status === "failed" ||
    record.verdict?.status === "failed" ||
    record.letter?.status === "failed" ||
    record.critique?.status === "failed"
  )
    return false;
  if (record.status === "drafted") return "critique" in record;
  return WORKING.includes(record.status);
}

/* ---------- Critic: the letter checks itself ---------- */

export type CritiqueIssueKind =
  | "unverified_claim"
  | "missing_deadline"
  | "wrong_program"
  | "medical_statement"
  | "unsupported_fact"
  | "missing_request"
  | "tone"
  | "other";
export type Severity = "high" | "medium" | "low";

export interface CritiqueIssue {
  kind: CritiqueIssueKind;
  severity: Severity;
  where: { paragraph: number; sentence: number } | null;
  note: string;
  fixed: boolean;
}

export interface SentenceCounts {
  claims: number;
  verified: number;
  struck: number;
}

export interface CritiqueRound extends Usage {
  round: number;
  issues: CritiqueIssue[];
  before: Paragraph[];
  after: Paragraph[];
  verification_before: SentenceCounts;
  verification_after: SentenceCounts;
  accepted: boolean;
  rejected_reason: string | null;
}

export interface Critique {
  status: StepStatus;
  skipped: boolean;
  reason: string | null;
  rounds: CritiqueRound[];
  issues_found: number;
  issues_fixed: number;
  accepted: boolean;
  model: string;
  cost_usd: number;
  latency_ms: number;
  error: string | null;
}

export const ISSUE_KIND_LABELS: Record<CritiqueIssueKind, string> = {
  unverified_claim: "Unverified claim",
  missing_deadline: "Missing deadline",
  wrong_program: "Wrong program named",
  medical_statement: "Medical statement",
  unsupported_fact: "Fact not in the letter",
  missing_request: "Missing request",
  tone: "Tone",
  other: "Other",
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  high: "High severity",
  medium: "Medium severity",
  low: "Low severity",
};

export function issueKindLabel(kind: string): string {
  return ISSUE_KIND_LABELS[kind as CritiqueIssueKind] ?? ISSUE_KIND_LABELS.other;
}

export function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity as Severity] ?? "Severity not given";
}

/* Text for a sentence slot: drops one trailing period so the caller can add its own. */
export function withoutStop(text: string): string {
  return text.trim().replace(/[.]+$/, "");
}

/* One sentence that changed between a round's before and after. */
export interface SentenceChange {
  paragraph: number;
  before: LetterSentence | null;
  after: LetterSentence | null;
}

function sameSentence(a: LetterSentence, b: LetterSentence): boolean {
  return (
    a.text.trim() === b.text.trim() &&
    sentenceStruck(a) === sentenceStruck(b) &&
    (a.citation?.doc_id ?? null) === (b.citation?.doc_id ?? null) &&
    (a.citation?.page ?? null) === (b.citation?.page ?? null)
  );
}

/*
  The sentences that changed, paragraph by paragraph (matched by index).
  Within a paragraph the unchanged sentences are aligned first (longest common
  run), so removing one sentence does not mark every later one as changed;
  the removed and added sentences between two unchanged ones are then paired
  in order. A removed sentence has no after; an added one has no before.
*/
export function sentenceChanges(before: Paragraph[], after: Paragraph[]): SentenceChange[] {
  const out: SentenceChange[] = [];
  const count = Math.max(before.length, after.length);
  for (let p = 0; p < count; p++) {
    const b = before[p]?.sentences ?? [];
    const a = after[p]?.sentences ?? [];
    const lcs: number[][] = Array.from({ length: b.length + 1 }, () => new Array<number>(a.length + 1).fill(0));
    for (let i = b.length - 1; i >= 0; i--)
      for (let j = a.length - 1; j >= 0; j--)
        lcs[i][j] = sameSentence(b[i], a[j]) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    let i = 0;
    let j = 0;
    let removed: LetterSentence[] = [];
    let added: LetterSentence[] = [];
    const flush = () => {
      for (let k = 0; k < Math.max(removed.length, added.length); k++)
        out.push({ paragraph: p, before: removed[k] ?? null, after: added[k] ?? null });
      removed = [];
      added = [];
    };
    while (i < b.length || j < a.length) {
      if (i < b.length && j < a.length && sameSentence(b[i], a[j])) {
        flush();
        i++;
        j++;
      } else if (j >= a.length || (i < b.length && lcs[i + 1][j] >= lcs[i][j + 1])) {
        removed.push(b[i++]);
      } else {
        added.push(a[j++]);
      }
    }
    flush();
  }
  return out;
}

/* The rounds whose revision reached the letter. */
export function acceptedRounds(critique: Critique): CritiqueRound[] {
  return (critique.rounds ?? []).filter((r) => r.accepted);
}

/* An issue counts as fixed only when its round's revision was accepted. */
export function issueFixed(issue: CritiqueIssue, round: CritiqueRound): boolean {
  return issue.fixed && round.accepted;
}

/*
  The critic errored: its status failed, or it finished with an error and no
  round reached the letter (the API reports a model error as status done with
  error set). An error after an accepted round leaves that revision standing.
*/
export function critiqueError(critique: Critique | null): string | null {
  if (!critique) return null;
  const message = critique.error?.trim() || "";
  if (critique.status === "failed") return message || "The service reported an error and gave no reason.";
  if (message !== "" && acceptedRounds(critique).length === 0) return message;
  return null;
}

/* A reason as a clause after a colon: one trailing period dropped, a leading capital lowered ("The revision" to "the revision"). */
export function asClause(text: string): string {
  const t = withoutStop(text);
  return /^[A-Z][a-z]+\s/.test(t) ? t.charAt(0).toLowerCase() + t.slice(1) : t;
}

/*
  The Trust panel's self-check line, counts only: issues found and fixed,
  then the letter's verified sentences after the check and before it.
*/
export function selfCheckLine(critique: Critique): { lead: string; detail: string } {
  const rounds = critique.rounds ?? [];
  const accepted = acceptedRounds(critique);
  const first = rounds[0];
  const last = accepted[accepted.length - 1];
  const found = critique.issues_found;
  const fixed = accepted.length > 0 ? critique.issues_fixed : 0;
  const lead = `${found} ${found === 1 ? "issue" : "issues"} found, ${fixed} fixed`;
  if (!first) return { lead, detail: "" };
  const vb = first.verification_before;
  if (!last) return { lead, detail: `the first draft stands, letter sentences verified ${vb.verified} of ${vb.claims}` };
  const va = last.verification_after;
  return { lead, detail: `letter sentences verified ${va.verified} of ${va.claims} after the check (was ${vb.verified} of ${vb.claims})` };
}

/* ----- Fixture: verdicts and letters for the sample cases ----- */

/* Each step lasts longer than one poll (1.5 s) so every stage line is seen. */
const FIXTURE_DECIDE_MS = 2400;
const FIXTURE_DECIDED_MS = 1800;
const FIXTURE_DRAFT_MS = 2400;
const FIXTURE_DRAFTED_MS = 1800;
const FIXTURE_REVIEW_MS = 2400;

const ALL_FIXTURE_FINDINGS = [...FIXTURE_FINDINGS_FLORIDA, ...FIXTURE_FINDINGS_FEDERAL];

/* The verified citation `index` of finding `id`, as a CitationRef. */
function ref(id: string, index = 0): CitationRef {
  const f = ALL_FIXTURE_FINDINGS.find((x) => x.id === id);
  const c = f?.citations[index];
  if (!f || !c) throw new Error(`fixture citation ${id}[${index}] missing`);
  return { finding_id: f.id, doc_id: c.doc_id, title: c.title, page: c.page, quote: c.quote };
}

function usage(latency_ms: number): Usage {
  return { model: FIXTURE_MODEL, input_tokens: 0, output_tokens: 0, reasoning_tokens: 0, latency_ms, cost_usd: 0, error: null };
}

function said(text: string): LetterSentence {
  return { text, claim: false, citation: null, verified: false, struck: false };
}
function claimed(text: string, citation: CitationRef): LetterSentence {
  return { text, claim: true, citation, verified: true, struck: false };
}
function struckClaim(text: string): LetterSentence {
  return { text, claim: true, citation: null, verified: false, struck: true };
}

function fixtureDeadline(): LetterDeadline {
  return {
    date: "2026-12-13",
    days_left: daysUntil("2026-12-13"),
    source: "letter",
    citation: ref("f_5", 0),
    note: "The denial letter gives this date. It falls 60 days after the October 14, 2026 notice, which matches the appeal window in the plan contract.",
  };
}

const FILING_SAMPLE: Letter["filing"] = {
  where: "Sunshine Health, the plan that sent the denial letter. Use the appeals address or fax number printed on the letter.",
  how: "File the appeal in writing within 60 calendar days of the date on the notice. To keep services going while the appeal is pending, file within 10 days of that date.",
  citation: ref("f_5", 0),
};

const VERDICT_SAMPLE = (): Verdict => ({
  status: "done",
  steelman: {
    argument:
      "Services rendered in excess of the authorized amount are subject to the plan's reimbursement limits, so the plan may refuse to pay for hours billed beyond the authorization.",
    citations: [ref("f_2", 1)],
  },
  outcome: "inconsistent",
  headline: VERDICT_HEADLINES.inconsistent,
  rule: {
    statement:
      "The number of private duty nursing hours is set through the medical necessity review and stated on the authorization for each period. The policy sets no fixed daily cap.",
    citations: [ref("f_2", 0), ref("f_1", 0)],
  },
  gap: "The letter says the services exceed the authorized amount, but it never states how many hours were authorized for September. Under the policy, that number comes from a medical necessity review and must appear on the authorization, so the denial rests on a figure the letter does not show.",
  what_would_change:
    "A copy of the September authorization showing that fewer than 8 hours a day were approved after a medical necessity review would make the denial consistent with the policy.",
  ...usage(FIXTURE_DECIDE_MS),
});

const LETTER_SAMPLE = (): Letter => ({
  status: "done",
  applicable: true,
  explanation: null,
  to: "Sunshine Health, Appeals",
  re: "Appeal of the adverse benefit determination dated October 14, 2026: private duty nursing, 8 hours a day (T1000), September 1 to 30, 2026",
  paragraphs: [
    {
      sentences: [
        said(
          "I am writing to appeal the adverse benefit determination dated October 14, 2026, which denied private duty nursing at 8 hours a day for September 1 to 30, 2026.",
        ),
        claimed(
          "Florida Medicaid covers private duty nursing for members under 21 who need continuous skilled nursing at home, as ordered by the treating physician.",
          ref("f_1", 0),
        ),
      ],
    },
    {
      sentences: [
        said("The notice says the services exceed the authorized amount, but it does not state how many hours were authorized."),
        claimed(
          "Under the coverage policy, the number of hours is set through a medical necessity review and stated on the authorization for each period.",
          ref("f_2", 0),
        ),
        struckClaim("A physician's order for additional hours overrides the authorized amount for the same period."),
        said("Please send me the authorization and the medical necessity review used for this decision."),
      ],
    },
    {
      sentences: [
        claimed("This appeal is filed within sixty calendar days of the date on the notice, as the plan contract allows.", ref("f_5", 0)),
        said("Please review the denial against the coverage policy and approve the hours billed for September 2026."),
      ],
    },
  ],
  evidence_checklist: [
    { item: "The denial letter dated October 14, 2026", why: "It is the decision you are appealing.", citation: null },
    {
      item: "The physician's order for private duty nursing at 8 hours a day",
      why: "The policy covers private duty nursing as ordered by the treating physician.",
      citation: ref("f_1", 0),
    },
    {
      item: "The plan's authorization for September 2026, or your written request for it",
      why: "The policy says the authorized hours are stated on the authorization for each period.",
      citation: ref("f_2", 0),
    },
    {
      item: "Nursing visit records for September 1 to 30, 2026",
      why: "They show the hours of nursing given at home on the dates billed.",
      citation: null,
    },
    {
      item: "The plan's medical necessity review for this request",
      why: "The authorized hours are set through that review, so it shows how the plan reached its number.",
      citation: ref("f_2", 0),
    },
  ],
  deadline: fixtureDeadline(),
  filing: FILING_SAMPLE,
  verification: { claims: 4, verified: 3, struck: 1 },
  ...usage(FIXTURE_DRAFT_MS),
});

const VERDICT_CONSISTENT = (): Verdict => ({
  status: "done",
  steelman: {
    argument:
      "Hours are set by the plan's medical necessity review and stated on the authorization, and hours billed beyond that amount are subject to the plan's reimbursement limits.",
    citations: [ref("f_2", 0), ref("f_2", 1)],
  },
  outcome: "consistent",
  headline: VERDICT_HEADLINES.consistent,
  rule: {
    statement:
      "Services rendered in excess of the authorized amount are subject to the plan's reimbursement limits, and the authorized hours are those stated on the authorization for the period.",
    /* The located page first, so the policy exhibit shows its crop; page 38 (not located on its image) stays as note 2. */
    citations: [ref("f_2", 0), ref("f_2", 1)],
  },
  gap: "There is no gap. The letter's reason is the rule: the hours billed for September exceeded the hours on the authorization, and no document found allows the plan to pay hours beyond it.",
  what_would_change:
    "An authorization covering 8 hours a day for September, or a request for more hours approved before the care was given.",
  ...usage(FIXTURE_DECIDE_MS),
});

const LETTER_CONSISTENT = (): Letter => ({
  status: "done",
  applicable: false,
  explanation:
    "The plan's reason matches the written rule. Hours of private duty nursing are set on the authorization for each period, and hours billed beyond it are subject to the plan's reimbursement limits. The September claim billed more hours than were authorized, so no appeal letter is drafted.",
  to: "",
  re: "",
  paragraphs: [],
  evidence_checklist: [],
  deadline: fixtureDeadline(),
  filing: FILING_SAMPLE,
  verification: { claims: 0, verified: 0, struck: 0 },
  ...usage(FIXTURE_DRAFT_MS),
});

const VERDICT_DUAL = (): Verdict => ({
  status: "done",
  steelman: {
    argument: "Medicare pays for at most 28 hours a week of home health nursing, so 8 hours a day is more than Medicare pays.",
    citations: [],
    unsupported: true,
  },
  outcome: "not_settled",
  headline: VERDICT_HEADLINES.not_settled,
  rule: {
    statement:
      "Florida Medicaid covers private duty nursing for members under 21. Medicare does not cover private duty nursing as a home health service.",
    citations: [ref("f_1", 0), ref("f_6", 0)],
  },
  gap: "The letter does not say which program processed the claim, and the two programs answer differently. The case card puts the member at 65 or older, so the Florida rule for members under 21 does not apply as written, and nothing found says which rule decides this claim.",
  what_would_change:
    "The program named on the member's ID card, or a notice stating which program processed the claim, would let one set of rules decide this case.",
  ...usage(FIXTURE_DECIDE_MS),
});

const LETTER_DUAL = (): Letter => ({
  status: "done",
  applicable: false,
  explanation:
    "The documents do not settle whether the denial holds, so no appeal letter is drafted. Find out which program processed the claim, then start a new case with the notice that names it.",
  to: "",
  re: "",
  paragraphs: [],
  evidence_checklist: [],
  deadline: fixtureDeadline(),
  filing: {
    where: "The plan or office named on the denial letter.",
    how: "Ask in writing which program processed the claim. The appeal path depends on the answer.",
    citation: null,
  },
  verification: { claims: 0, verified: 0, struck: 0 },
  ...usage(FIXTURE_DRAFT_MS),
});

/*
  c_notsettled*: the common live not-settled case on a single route, so it has a
  clean demo state. Modeled on case dc-010's pattern (the rule leaves the number
  to a member-specific document outside the corpus), drafted Oct 27, 2026, on the
  sample case's own facts: the letter says the hours exceed the authorized
  amount; the policy sets the hours on the authorization after a medical
  necessity review; the September authorization itself is not among the
  documents, so they do not settle whether the denial holds. Fixture data only.
*/
const VERDICT_NOT_SETTLED = (): Verdict => ({
  status: "done",
  steelman: {
    argument:
      "Services rendered in excess of the authorized amount are subject to the plan's reimbursement limits, so the plan may refuse to pay for hours billed beyond the authorization.",
    citations: [ref("f_2", 1)],
  },
  outcome: "not_settled",
  headline: VERDICT_HEADLINES.not_settled,
  rule: {
    statement:
      "The number of private duty nursing hours is set through the medical necessity review and stated on the authorization for each period. The service is covered for members under 21 as ordered by the treating physician.",
    citations: [ref("f_2", 0), ref("f_1", 0)],
  },
  gap: "The letter says the hours billed exceed the authorized amount. Under the policy, that amount is the number stated on the September authorization after a medical necessity review, and the authorization is a document issued for this member, not one of the policy documents. Nothing found states how many hours it approved, so the documents do not settle whether the denial holds.",
  what_would_change:
    "A copy of the September authorization stating the number of hours approved would show whether the hours billed exceed it.",
  ...usage(FIXTURE_DECIDE_MS),
});

const LETTER_NOT_SETTLED = (): Letter => ({
  status: "done",
  applicable: false,
  explanation:
    "The documents do not settle whether the denial holds, so no appeal letter is drafted. Ask the plan for a copy of the September authorization that states the approved hours, then start a new case with it.",
  to: "",
  re: "",
  paragraphs: [],
  evidence_checklist: [],
  deadline: fixtureDeadline(),
  filing: FILING_SAMPLE,
  verification: { claims: 0, verified: 0, struck: 0 },
  ...usage(FIXTURE_DRAFT_MS),
});

/* ----- Fixture: the critic's self-check ----- */

const SAMPLE_DRAFT = (): Paragraph[] => LETTER_SAMPLE().paragraphs;

/* The sample draft with the struck unverified claim removed and a request for a written decision added. */
const SAMPLE_REVISED = (): Paragraph[] => {
  const [p1, p2, p3] = SAMPLE_DRAFT();
  return [
    p1,
    { sentences: p2.sentences.filter((x) => !x.struck) },
    { sentences: [...p3.sentences, said("Please send me your decision on this appeal in writing.")] },
  ];
};

/* A revision that dropped the citation from the second paragraph's claim: fewer verified sentences, so it is rejected. */
const REJECTED_REVISION = (): Paragraph[] => {
  const [p1, p2, p3] = SAMPLE_DRAFT();
  return [
    p1,
    {
      sentences: [
        p2.sentences[0],
        {
          text: "The number of hours is set by a medical necessity review and stated on each authorization.",
          claim: true,
          citation: null,
          verified: false,
          struck: true,
        },
        p2.sentences[3],
      ],
    },
    { sentences: [p3.sentences[0], said("I ask that you review the denial and approve the 8 hours a day billed for September 2026.")] },
  ];
};

function fixtureRound(fields: Pick<CritiqueRound, "issues" | "before" | "after" | "verification_before" | "verification_after" | "accepted" | "rejected_reason">): CritiqueRound {
  return { round: 1, ...fields, ...usage(FIXTURE_REVIEW_MS) };
}

const CRITIQUE_SAMPLE = (): Critique => ({
  status: "done",
  skipped: false,
  reason: null,
  rounds: [
    fixtureRound({
      issues: [
        {
          kind: "unverified_claim",
          severity: "high",
          where: { paragraph: 1, sentence: 2 },
          note: "The sentence saying a physician's order overrides the authorized amount has no verified citation. It was removed.",
          fixed: true,
        },
        {
          kind: "missing_request",
          severity: "medium",
          where: { paragraph: 2, sentence: 2 },
          note: "The letter did not ask the plan for a written decision on the appeal. The request was added to the last paragraph.",
          fixed: true,
        },
      ],
      before: SAMPLE_DRAFT(),
      after: SAMPLE_REVISED(),
      verification_before: { claims: 4, verified: 3, struck: 1 },
      verification_after: { claims: 3, verified: 3, struck: 0 },
      accepted: true,
      rejected_reason: null,
    }),
  ],
  issues_found: 2,
  issues_fixed: 2,
  accepted: true,
  model: FIXTURE_MODEL,
  cost_usd: 0,
  latency_ms: FIXTURE_REVIEW_MS,
  error: null,
});

const CRITIQUE_REJECTED = (): Critique => ({
  status: "done",
  skipped: false,
  reason: null,
  rounds: [
    fixtureRound({
      issues: [
        {
          kind: "unverified_claim",
          severity: "high",
          where: { paragraph: 1, sentence: 2 },
          note: "The sentence saying a physician's order overrides the authorized amount has no verified citation.",
          fixed: true,
        },
        {
          kind: "tone",
          severity: "low",
          where: { paragraph: 2, sentence: 1 },
          note: "The closing request could name the hours billed so the reviewer does not have to look them up.",
          fixed: true,
        },
      ],
      before: SAMPLE_DRAFT(),
      after: REJECTED_REVISION(),
      verification_before: { claims: 4, verified: 3, struck: 1 },
      verification_after: { claims: 3, verified: 2, struck: 1 },
      accepted: false,
      rejected_reason: "the revised letter verified fewer sentences than the first draft (2, was 3)",
    }),
  ],
  issues_found: 2,
  issues_fixed: 0,
  accepted: false,
  model: FIXTURE_MODEL,
  cost_usd: 0,
  latency_ms: FIXTURE_REVIEW_MS,
  error: null,
});

const CRITIQUE_SKIPPED = (reason: string): Critique => ({
  status: "done",
  skipped: true,
  reason,
  rounds: [],
  issues_found: 0,
  issues_fixed: 0,
  accepted: false,
  model: FIXTURE_MODEL,
  cost_usd: 0,
  latency_ms: 0,
  error: null,
});

/* As the API reports a critic model error: the critique is done with error set, the round has no revision, the draft stands. */
const CRITIQUE_FAILED = (): Critique => {
  const error = "TimeoutError: the model did not answer the self-check after three attempts.";
  return {
    status: "done",
    skipped: false,
    reason: null,
    rounds: [
      {
        ...fixtureRound({
          issues: [],
          before: SAMPLE_DRAFT(),
          after: [],
          verification_before: { claims: 4, verified: 3, struck: 1 },
          verification_after: { claims: 0, verified: 0, struck: 0 },
          accepted: false,
          rejected_reason: null,
        }),
        error,
      },
    ],
    issues_found: 0,
    issues_fixed: 0,
    accepted: false,
    model: FIXTURE_MODEL,
    cost_usd: 0,
    latency_ms: FIXTURE_REVIEW_MS,
    error,
  };
};

const CRITIQUE_RUNNING = (): Critique => ({
  status: "running",
  skipped: false,
  reason: null,
  rounds: [],
  issues_found: 0,
  issues_fixed: 0,
  accepted: false,
  model: FIXTURE_MODEL,
  cost_usd: 0,
  latency_ms: 0,
  error: null,
});

type FixtureKind = "sample" | "consistent" | "dual" | "notsettled" | "rejected" | "checkerror";

/* The letter as drafted, then as GET /case/{id} returns it once reviewed. */
function draftedLetter(kind: FixtureKind): Letter {
  const letter =
    kind === "dual" ? LETTER_DUAL() : kind === "consistent" ? LETTER_CONSISTENT() : kind === "notsettled" ? LETTER_NOT_SETTLED() : LETTER_SAMPLE();
  return { ...letter, draft_paragraphs: structuredClone(letter.paragraphs) };
}

function reviewed(kind: FixtureKind): { status: CaseStatus; letter: Letter; critique: Critique } {
  const letter = draftedLetter(kind);
  switch (kind) {
    case "sample":
      return {
        status: "reviewed",
        letter: { ...letter, paragraphs: SAMPLE_REVISED(), verification: { claims: 3, verified: 3, struck: 0 } },
        critique: CRITIQUE_SAMPLE(),
      };
    case "rejected":
      return { status: "reviewed", letter, critique: CRITIQUE_REJECTED() };
    case "checkerror":
      return { status: "reviewed", letter, critique: CRITIQUE_FAILED() };
    case "consistent":
      return { status: "reviewed", letter, critique: CRITIQUE_SKIPPED("No letter was drafted for a consistent denial.") };
    case "dual":
    case "notsettled":
      return { status: "reviewed", letter, critique: CRITIQUE_SKIPPED("No letter was drafted because the documents do not settle the denial.") };
  }
}

/* The verdict, letter, and self-check steps, `t` ms after the investigation finished. */
function fixtureChain(
  kind: FixtureKind,
  t: number,
): { status: CaseStatus; verdict: Verdict | null; letter: Letter | null; critique: Critique | null } {
  const verdict =
    kind === "dual" ? VERDICT_DUAL() : kind === "consistent" ? VERDICT_CONSISTENT() : kind === "notsettled" ? VERDICT_NOT_SETTLED() : VERDICT_SAMPLE();
  const draftedAt = FIXTURE_DECIDE_MS + FIXTURE_DECIDED_MS + FIXTURE_DRAFT_MS;
  if (t < 0) return { status: "investigated", verdict: null, letter: null, critique: null };
  if (t < FIXTURE_DECIDE_MS) return { status: "deciding", verdict: null, letter: null, critique: null };
  if (t < FIXTURE_DECIDE_MS + FIXTURE_DECIDED_MS) return { status: "decided", verdict, letter: null, critique: null };
  if (t < draftedAt) return { status: "drafting", verdict, letter: null, critique: null };
  if (t < draftedAt + FIXTURE_DRAFTED_MS) return { status: "drafted", verdict, letter: draftedLetter(kind), critique: null };
  if (t < draftedAt + FIXTURE_DRAFTED_MS + FIXTURE_REVIEW_MS)
    return { status: "reviewing", verdict, letter: draftedLetter(kind), critique: CRITIQUE_RUNNING() };
  return { verdict, ...reviewed(kind) };
}

/* ---------- Page viewer: the cited PDF page with the quote highlighted ---------- */

export const PAGE_DPI = 110;
/* The API answers 422 for a quote shorter than this. */
export const QUOTE_MIN = 15;

/* One box per line of the quote, in image pixels at PAGE_DPI. */
export interface PageBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/* GET /doc/{doc_id}/page/{page}/highlight */
export interface PageHighlight {
  doc_id: string;
  title: string | null;
  page: number;
  dpi: number;
  width_px: number;
  height_px: number;
  boxes_px: PageBox[];
  score: number;
  found: boolean;
  /* "/doc/{doc_id}/page/{page}.png?dpi=110", relative to the API. */
  image_url: string;
}

export interface VisionCheck {
  checked: boolean;
  model: string;
  text_in_highlight: string;
  agrees: boolean;
  latency_ms: number;
  cost_usd: number;
  error?: string | null;
}

/* POST /doc/{doc_id}/page/{page}/vision-check: the highlight fields plus the vision result. */
export interface VisionCheckResponse extends PageHighlight {
  vision: VisionCheck;
}

export type PageErrorCode = "no_pdf" | "not_found" | "too_short" | "unreachable" | "timeout" | "rejected";

export class PageError extends Error {
  code: PageErrorCode;
  /* The document's public source, when known: from the API's no_pdf detail or the manifest. */
  sourceUrl: string | null;
  constructor(code: PageErrorCode, message?: string, sourceUrl: string | null = null) {
    super(message ?? PAGE_ERROR_COPY[code]);
    this.name = "PageError";
    this.code = code;
    this.sourceUrl = sourceUrl;
  }
}

export const PAGE_ERROR_COPY: Record<PageErrorCode, string> = {
  no_pdf: "The PDF for this document is not on this server. Open it at its source.",
  not_found: "This document is not in the corpus this server knows.",
  too_short: "This quote is too short to place on the page.",
  unreachable: "We could not reach the service to load the page. Check your connection and try again.",
  timeout: "The page has not come back after 30 seconds.",
  rejected: "The service could not show this page.",
};

/* Source URLs from corpus/manifest.csv for the documents the fixture cites. */
const DOC_SOURCES: Record<string, string> = {
  "fl-04": "https://ahca.myflorida.com//file/medicaid/Private_Duty_Nursing_Services_February2026.pdf",
  "fl-21":
    "https://ahca.myflorida.com/file/medicaid/Health_Exhibit%20II-A_Managed%20Medical%20Assistance%20(MMA)%20Program_July%202026.pdf",
  "fed-02": "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/bp102c07.pdf",
  "fed-17": "https://www.cms.gov/files/document/mln006562-medicare-parts-b-appeals-process.pdf",
};

export function docSourceUrl(docId: string): string | null {
  return DOC_SOURCES[docId] ?? null;
}

/* The <img> src for a highlight: the API's image_url in live mode, the bundled fixture page otherwise. */
export function pageImageSrc(h: Pick<PageHighlight, "image_url">): string {
  if (/^https?:\/\//.test(h.image_url)) return h.image_url;
  return INTAKE_MODE === "live" && !h.image_url.startsWith("/fixtures/") ? `${API_URL}${h.image_url}` : h.image_url;
}

function pagePath(docId: string, page: number): string {
  return `/doc/${encodeURIComponent(docId)}/page/${encodeURIComponent(String(page))}`;
}

async function readPageError(res: Response, docId: string): Promise<PageError> {
  let detail: { code?: string; message?: string; source_url?: string; url?: string } | undefined;
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "object" && body.detail) detail = body.detail as typeof detail;
  } catch {
    /* no body */
  }
  if (res.status === 404) return new PageError("not_found");
  if (res.status === 422) return new PageError("too_short");
  if (detail?.code === "no_pdf") {
    return new PageError("no_pdf", undefined, detail.source_url || detail.url || docSourceUrl(docId));
  }
  if (res.status >= 500) return new PageError("unreachable");
  return new PageError("rejected", detail?.message || undefined);
}

async function pageFetch(path: string, init: RequestInit, signal?: AbortSignal): Promise<Response> {
  try {
    return await liveFetch(path, init, signal);
  } catch (err) {
    if (err instanceof IntakeError) throw new PageError(err.code === "timeout" ? "timeout" : "unreachable");
    throw err;
  }
}

/* Fixture mode, or a fixture case's synthetic quote on the live dev server. */
function fixtureQuote(quote: string): boolean {
  return INTAKE_MODE !== "live" || (process.env.NODE_ENV !== "production" && quote.startsWith(SYNTHETIC));
}

function checkQuote(quote: string): void {
  if (quote.trim().length < QUOTE_MIN) throw new PageError("too_short");
}

const FIXTURE_HIGHLIGHT_MS = 450;
const FIXTURE_VISION_MS = 1200;
const FIXTURE_NO_PDF = new Set(["fed-02", "fed-17"]);

function fixtureHighlightFor(docId: string, page: number, quote: string): PageHighlight {
  if (FIXTURE_NO_PDF.has(docId)) throw new PageError("no_pdf", undefined, docSourceUrl(docId));
  const fx = PAGE_FIXTURES.find((f) => f.doc_id === docId && f.page === page);
  if (!fx) throw new PageError(DOC_SOURCES[docId] ? "no_pdf" : "not_found", undefined, docSourceUrl(docId));
  const found = fx.found && quote.includes(fx.quote);
  return {
    doc_id: fx.doc_id,
    title: fx.title,
    page: fx.page,
    dpi: PAGE_DPI,
    width_px: fx.width_px,
    height_px: fx.height_px,
    boxes_px: found ? fx.boxes_px.map((b) => ({ ...b })) : [],
    score: found ? 1 : 0,
    found,
    image_url: fx.image_url,
  };
}

/* GET /doc/{doc_id}/page/{page}/highlight?quote=…&dpi=110. Throws PageError. */
export async function getHighlight(docId: string, page: number, quote: string, signal?: AbortSignal): Promise<PageHighlight> {
  checkQuote(quote);
  if (fixtureQuote(quote)) {
    await sleep(FIXTURE_HIGHLIGHT_MS, signal);
    return fixtureHighlightFor(docId, page, quote);
  }
  const q = `quote=${encodeURIComponent(quote)}&dpi=${PAGE_DPI}`;
  const res = await pageFetch(`${pagePath(docId, page)}/highlight?${q}`, { method: "GET" }, signal);
  if (!res.ok) throw await readPageError(res, docId);
  return (await res.json()) as PageHighlight;
}

/* POST /doc/{doc_id}/page/{page}/vision-check with {quote}. Throws PageError. */
export async function visionCheck(docId: string, page: number, quote: string, signal?: AbortSignal): Promise<VisionCheckResponse> {
  checkQuote(quote);
  if (fixtureQuote(quote)) {
    await sleep(FIXTURE_VISION_MS, signal);
    const h = fixtureHighlightFor(docId, page, quote);
    const fx = PAGE_FIXTURES.find((f) => f.doc_id === docId && f.page === page);
    return {
      ...h,
      vision: {
        checked: true,
        model: FIXTURE_MODEL,
        text_in_highlight: `[synthetic fixture] ${fx?.quote ?? ""}`,
        agrees: true,
        latency_ms: FIXTURE_VISION_MS,
        cost_usd: 0,
        error: null,
      },
    };
  }
  const res = await pageFetch(
    `${pagePath(docId, page)}/vision-check`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ quote }) },
    signal,
  );
  if (!res.ok) throw await readPageError(res, docId);
  return (await res.json()) as VisionCheckResponse;
}

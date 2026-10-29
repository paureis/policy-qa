/*
  Exports the recorded run behind the public sample case (c_sample).

  Reads ../data/cases/c_f3b3d0.json (gitignored; the demo letter dc-001 run through the local API
  on October 28, 2026 at 4:04 pm with the second opinion on) and, from the local API, the cited
  pages and their highlights and vision checks. Writes:
    public/sample/<doc_id>-p<page>.png   each cited page at 110 dpi (GET /doc/{doc_id}/page/{page}.png)
    src/lib/sample-case.ts               the record with case_id c_sample, the highlight table and the
                                         vision table, keyed by (doc_id, page, quote)

  Fail-closed: everything is fetched into memory first. If any quote is not found on its page, or any
  vision check did not run (checked false, an error, a provider timeout), it writes nothing, names each
  failure and exits 1. Otherwise it compares each would-be file with the one on disk and writes only
  the ones that differ; when none differ it says "nothing changed".
  The API caches vision results in process, so only the first run against a fresh API spends anything
  (about $0.005 a check).

  Run from web/, with the API on http://localhost:8000: node scripts/sample-case.mjs
  RECOURSE_API_URL points it at another API (a stub, for testing the refusal).
*/
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const API = (process.env.RECOURSE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SOURCE = "data/cases/c_f3b3d0.json";
const DPI = 110;
const SAMPLE_ID = "c_sample";

const record = JSON.parse(await readFile(path.join(root, "..", SOURCE), "utf-8"));
if (record.status !== "reviewed") throw new Error(`${SOURCE} is at ${record.status}, not reviewed`);
const sourceId = record.case_id;

/* Every distinct (doc_id, page, quote) the record cites, in the order the record first cites it. */
const cited = new Map();
function add(c) {
  if (!c || typeof c.doc_id !== "string" || typeof c.page !== "number" || typeof c.quote !== "string") return;
  const key = JSON.stringify([c.doc_id, c.page, c.quote]);
  if (!cited.has(key)) cited.set(key, { doc_id: c.doc_id, page: c.page, quote: c.quote });
}
function addParagraphs(paragraphs) {
  for (const p of paragraphs ?? []) for (const s of p.sentences ?? []) add(s.citation);
}
for (const f of record.investigation?.findings ?? []) {
  for (const c of f.citations ?? []) add(c);
  for (const c of f.struck ?? []) add(c);
}
const v = record.verdict ?? {};
for (const c of v.steelman?.citations ?? []) add(c);
for (const c of v.rule?.citations ?? []) add(c);
const letter = record.letter ?? {};
addParagraphs(letter.paragraphs);
addParagraphs(letter.draft_paragraphs);
for (const r of record.critique?.rounds ?? []) {
  addParagraphs(r.before);
  addParagraphs(r.after);
}
for (const e of letter.evidence_checklist ?? []) add(e.citation);
add(letter.deadline?.citation);
add(letter.filing?.citation);

async function api(p, init) {
  const res = await fetch(`${API}${p}`, init);
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${p} answered ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res;
}
const pagePath = (doc, page) => `/doc/${encodeURIComponent(doc)}/page/${page}`;
const imageUrl = (doc, page) => `/sample/${doc}-p${page}.png`;

/* 1. Fetch everything into memory. */
const pages = [];
const failures = [];
let visionCost = 0;
for (const { doc_id, page, quote } of cited.values()) {
  const q = `quote=${encodeURIComponent(quote)}&dpi=${DPI}`;
  const where = `${doc_id} p${page} "${quote.slice(0, 50)}..."`;
  const h = await (await api(`${pagePath(doc_id, page)}/highlight?${q}`)).json();
  const res = await (
    await api(`${pagePath(doc_id, page)}/vision-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quote, dpi: DPI }),
    })
  ).json();
  const vis = res.vision ?? {};
  const vision = { checked: vis.checked === true, model: vis.model ?? "" };
  for (const k of ["text_in_highlight", "agrees", "latency_ms", "cost_usd", "error"]) if (k in vis) vision[k] = vis[k];
  if (h.found !== true || !Array.isArray(h.boxes_px) || h.boxes_px.length === 0) failures.push(`${where}: highlight not found (score ${h.score})`);
  if (!vision.checked || vision.error) failures.push(`${where}: vision check did not run (${vision.error ?? "checked false"})`);
  visionCost += Number(vis.cost_usd ?? 0);
  pages.push({
    doc_id,
    page,
    quote,
    title: h.title,
    dpi: h.dpi,
    width_px: h.width_px,
    height_px: h.height_px,
    boxes_px: h.boxes_px,
    score: h.score,
    found: h.found,
    matched: h.matched,
    image_url: imageUrl(doc_id, page),
    vision,
  });
  console.log(`${where} found=${h.found} boxes=${h.boxes_px?.length ?? 0} vision=${vision.checked ? (vision.agrees ? "agrees" : "disagrees") : "not checked"}`);
}

if (failures.length > 0) {
  console.error(`REFUSED: ${failures.length} failure(s); nothing was written.`);
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}

const distinctPages = [...new Map(pages.map((p) => [`${p.doc_id}|${p.page}`, p])).values()];
const outputs = [];
for (const p of distinctPages) {
  const png = Buffer.from(await (await api(`${pagePath(p.doc_id, p.page)}.png?dpi=${DPI}`)).arrayBuffer());
  if (png.length < 8 || png.readUInt32BE(0) !== 0x89504e47) {
    console.error(`REFUSED: ${p.doc_id} p${p.page} is not a PNG (${png.length} bytes); nothing was written.`);
    process.exit(1);
  }
  outputs.push({ rel: `public${imageUrl(p.doc_id, p.page)}`, bytes: png });
}

/* The record as the API stored it at reviewed, with case_id rewritten and nothing else changed. */
const sample = { ...record, case_id: SAMPLE_ID };

const ts = `/*
  Generated by scripts/sample-case.mjs. Do not edit by hand: change the script and run it again.
  Source: ${SOURCE} (case ${sourceId}), the demo letter dc-001 run through the local API on
  October 28, 2026 at 4:04 pm with the second opinion on. Only the denial letter is synthetic (it was
  written for the demo and says so in its first line); the policy pages, quotes, highlights, vision
  checks, costs, seconds and the second opinion are what the API produced. case_id is rewritten to
  ${SAMPLE_ID}; nothing else in the record is changed. Page images: public/sample/, at ${DPI} dpi.
*/
import type { CaseRecord } from "./case";

/* GET .../highlight for one quote, image_url rewritten to the bundled page. */
export interface RecordedHighlight {
  doc_id: string;
  page: number;
  quote: string;
  title: string | null;
  dpi: number;
  width_px: number;
  height_px: number;
  boxes_px: { x0: number; y0: number; x1: number; y1: number }[];
  score: number;
  found: boolean;
  matched: string;
  image_url: string;
  /* POST .../vision-check's vision field for the same quote. */
  vision: {
    checked: boolean;
    model: string;
    text_in_highlight?: string;
    agrees?: boolean;
    latency_ms?: number;
    cost_usd?: number;
    error?: string | null;
  };
}

export const SAMPLE_SOURCE_CASE = ${JSON.stringify(sourceId)};

export const SAMPLE_RECORD = ${JSON.stringify(sample, null, 2)} as unknown as CaseRecord;

export const SAMPLE_PAGES: RecordedHighlight[] = ${JSON.stringify(pages, null, 2)};
`;
outputs.push({ rel: "src/lib/sample-case.ts", bytes: Buffer.from(ts, "utf-8") });

/* 2. Compare every would-be file with the one on disk; write only those that differ. */
const changed = [];
for (const o of outputs) {
  let old = null;
  try {
    old = await readFile(path.join(root, o.rel));
  } catch {
    old = null;
  }
  if (old && Buffer.compare(old, o.bytes) === 0) console.log(`unchanged ${o.rel} (${o.bytes.length} bytes)`);
  else changed.push({ ...o, existed: old !== null });
}
for (const o of changed) {
  const file = path.join(root, o.rel);
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, o.bytes);
  console.log(`${o.existed ? "rewrote" : "wrote"} ${o.rel} (${o.bytes.length} bytes)`);
}

console.log(`${cited.size} quotes on ${distinctPages.length} pages, all found and vision-checked; recorded vision cost $${visionCost.toFixed(6)} (the API's cache means a re-run spends nothing)`);
console.log(changed.length === 0 ? "nothing changed" : `${changed.length} file(s) written`);

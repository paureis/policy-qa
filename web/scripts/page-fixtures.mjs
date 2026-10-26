/*
  Draws the synthetic fixture page images for the page viewer and measures
  the highlight boxes from the rendered text, one box per line of the quote.
  Writes public/fixtures/{doc_id}-p{page}.png (1100 x 1420) and
  src/lib/page-fixtures.ts. Nothing here is the documents' words.

  Run from web/: PLAYWRIGHT_MODULE=/opt/node-tools/node_modules/playwright/index.mjs node scripts/page-fixtures.mjs
*/
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? "playwright");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const WIDTH = 1100;
const HEIGHT = 1420;
const PAD_X = 3;
const PAD_Y = 2;

const PDN = "Florida Medicaid Private Duty Nursing and Family Home Health Aide Services Coverage Policy (Rule 59G-4.261)";
const MMA = "SMMC Model Health Plan Contract, Exhibit II-A: Managed Medical Assistance (MMA) Program";

/* The quote bodies match the fixture citations in src/lib/case.ts, without the synthetic prefix. */
const PAGES = [
  {
    doc_id: "fl-04",
    page: 3,
    title: PDN,
    section: "2.1 Covered recipients",
    quote:
      "Florida Medicaid covers private duty nursing services for recipients under the age of 21 who require continuous skilled nursing care in the home, as ordered by the treating physician.",
    at: 1,
  },
  {
    doc_id: "fl-04",
    page: 5,
    title: PDN,
    section: "4.2 Authorization periods",
    quote:
      "The number of hours authorized is determined through the medical necessity review and is stated on the authorization for each authorization period.",
    at: 4,
  },
  {
    doc_id: "fl-21",
    page: 38,
    title: MMA,
    section: "8.4 Reimbursement",
    quote: "Services rendered in excess of the authorized amount are subject to the plan's reimbursement limits.",
    /* Drawn in different words, so the image locator does not find it: the not-located state. */
    drawn: "Any service delivered beyond the amount the plan authorized is paid only within the plan's reimbursement limits.",
    at: 3,
  },
  {
    doc_id: "fl-21",
    page: 41,
    title: MMA,
    section: "9.1 Filing an appeal",
    quote: "An enrollee may file an appeal within sixty (60) calendar days from the date on the notice of adverse benefit determination.",
    at: 5,
  },
  {
    doc_id: "fl-21",
    page: 43,
    title: MMA,
    section: "9.3 Continuation of benefits",
    quote:
      "Benefits shall continue if the enrollee files the appeal within ten (10) days of the date of the notice of adverse benefit determination.",
    at: 2,
  },
];

const FILLER = [
  "This paragraph stands in for the text of the document on this page. It is synthetic and is shown so the page viewer has lines to place.",
  "The terms used in this section have the meanings given in the definitions section of this synthetic page. Nothing here is quoted from the source.",
  "Requests under this section are made in writing to the plan. The plan answers in writing within the period this synthetic text describes.",
  "Where this page refers to another section, the reference is part of the fixture and points to no real provision of the document.",
  "Records kept under this section are kept for the period stated elsewhere in this synthetic page and are made available on request.",
  "A notice under this section names the decision, the reason given, and the date. The wording of this sentence is part of the fixture.",
  "Nothing in this synthetic section changes any other section. The numbering follows the layout of a policy page so the viewer has a page to show.",
];

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function html(p) {
  const n = p.section.split(" ")[0];
  const paras = [];
  for (let i = 0; i < 8; i += 1) {
    const label = `${n}.${i + 1}`;
    if (i === p.at) {
      paras.push(`<p><span class="n">${label}</span> <span id="q">${esc(p.drawn ?? p.quote)}</span> ${esc(FILLER[(i + 2) % FILLER.length])}</p>`);
    } else {
      paras.push(`<p><span class="n">${label}</span> ${esc(FILLER[(i + p.page) % FILLER.length])}</p>`);
    }
  }
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;background:#fff;color:#1b1b1b}
    body{width:${WIDTH}px;height:${HEIGHT}px;box-sizing:border-box;padding:84px 96px;font-family:"DejaVu Sans Mono",monospace;font-size:21px;line-height:34px;position:relative}
    .mark{font-size:15px;letter-spacing:2px;border:2px solid #1b1b1b;display:inline-block;padding:2px 10px;margin-bottom:22px}
    .doc{font-size:17px;line-height:26px;color:#3d4249;border-bottom:1px solid #1b1b1b;padding-bottom:14px;margin-bottom:30px}
    h2{font-size:23px;margin:0 0 22px;font-weight:700}
    p{margin:0 0 26px;text-align:left}
    .n{font-weight:700}
    footer{position:absolute;left:96px;right:96px;bottom:70px;border-top:1px solid #1b1b1b;padding-top:12px;font-size:16px;display:flex;justify-content:space-between;color:#3d4249}
  </style></head><body>
    <div class="mark">SYNTHETIC FIXTURE PAGE. NOT THE DOCUMENT'S WORDS.</div>
    <div class="doc">${esc(p.title)} (${p.doc_id})</div>
    <h2>${esc(p.section)}</h2>
    ${paras.join("\n")}
    <footer><span>${p.doc_id}, Recourse page viewer fixture</span><span>Page ${p.page}</span></footer>
  </body></html>`;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
await mkdir(path.join(root, "public/fixtures"), { recursive: true });
const records = [];
for (const p of PAGES) {
  await page.setContent(html(p));
  const rects = await page.evaluate(() =>
    Array.from(document.getElementById("q").getClientRects()).map((r) => ({ x0: r.left, y0: r.top, x1: r.right, y1: r.bottom })),
  );
  const file = `${p.doc_id}-p${p.page}.png`;
  await page.screenshot({ path: path.join(root, "public/fixtures", file), clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT } });
  const found = p.drawn === undefined;
  records.push({
    doc_id: p.doc_id,
    page: p.page,
    title: p.title,
    image_url: `/fixtures/${file}`,
    width_px: WIDTH,
    height_px: HEIGHT,
    quote: p.quote,
    found,
    boxes_px: found
      ? rects.map((r) => ({
          x0: Math.round(r.x0 - PAD_X),
          y0: Math.round(r.y0 - PAD_Y),
          x1: Math.round(r.x1 + PAD_X),
          y1: Math.round(r.y1 + PAD_Y),
        }))
      : [],
  });
}
await browser.close();

const ts = `/*
  Generated by scripts/page-fixtures.mjs. Do not edit by hand.
  Synthetic page images under public/fixtures/ and the highlight boxes
  measured from their rendered text, one box per line of the quote.
*/
export interface PageFixture {
  doc_id: string;
  page: number;
  title: string;
  image_url: string;
  width_px: number;
  height_px: number;
  /* The quote body as it appears in the fixture citations, without the synthetic prefix. */
  quote: string;
  found: boolean;
  boxes_px: { x0: number; y0: number; x1: number; y1: number }[];
}

export const PAGE_FIXTURES: PageFixture[] = ${JSON.stringify(records, null, 2)};
`;
await writeFile(path.join(root, "src/lib/page-fixtures.ts"), ts);
console.log(records.map((r) => `${r.image_url} boxes=${r.boxes_px.length}`).join("\n"));

/*
  The text check for the public sample (case-page-brief section 15, H4). Opens /case/c_sample at 390
  and 1280 with every request to the API aborted, waits for reviewed and a settled page, and reads the
  rendered text; it also reads the text once about 7 s into the run, where "(prices not set)" and the
  other strings except "$0.0000" must be absent. Prints each forbidden string it finds, and each "sample" outside the places it is
  allowed (the band's tab or marker, the case id, the card's payer and the letter's own text: the
  register, the letter exhibit, the appeal letter). Ends with "clean" or the count of offenders.

  Run from web/ with the dev server on :3000:
    PLAYWRIGHT_MODULE=file:///C:/Users/pau/AppData/Roaming/npm/node_modules/playwright/index.mjs node scripts/sample-text-check.mjs
  Optional: BASE_URL (default http://localhost:3000), CASE_ID (default c_sample), WIDTHS (default 390,1280).
*/
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? "playwright");

const BASE = (process.env.BASE_URL ?? "http://localhost:3000").replace(/\/$/, "");
const ID = process.env.CASE_ID ?? "c_sample";
const WIDTHS = (process.env.WIDTHS ?? "390,1280").split(",").map(Number);
const FORBIDDEN = ["fixture", "synthetic fixture", "SYNTHETIC", "$0.0000", "Model: fixture", "Vision check not run", "prices not set", "Sunshine Health", "[synthetic"];
/* During the run the investigation's cost is an honest $0.0000 until the first finding, so that one string is not checked then. */
const MID_RUN_FORBIDDEN = FORBIDDEN.filter((f) => f !== "$0.0000");
/* Ancestors under which "sample" is the record's own words or the one disclosure. */
const ALLOWED = ["[data-band]", "[data-register]", "[data-exhibit=letter]", "[data-letter]", "[data-case-card]"];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch();
let offenders = 0;
for (const w of WIDTHS) {
  const page = await browser.newPage({ viewport: { width: w, height: w >= 1024 ? 800 : 844 } });
  await page.route(/^http:\/\/(localhost|127\.0\.0\.1):8000\//, (r) => r.abort());
  await page.goto(`${BASE}/case/${ID}`);
  const t0 = Date.now();
  /* Once during the run, at about 7 s: the plan has landed (5.2 s) and no finding has (10.4 s), the window where a zero cost read "prices not set" before the fix round. */
  await sleep(7000);
  const mid = await page.evaluate(() => ({
    text: document.body.innerText,
    view: document.querySelector("[data-view]")?.getAttribute("data-view") ?? null,
  }));
  console.log(`== ${ID} at ${w} px, ${((Date.now() - t0) / 1000).toFixed(1)} s into the run: view ${mid.view}`);
  for (const f of MID_RUN_FORBIDDEN) {
    const ml = mid.text.toLowerCase();
    for (let i = ml.indexOf(f.toLowerCase()); i >= 0; i = ml.indexOf(f.toLowerCase(), i + 1)) {
      offenders += 1;
      console.log(`  forbidden mid-run "${f}": ${mid.text.slice(Math.max(0, i - 50), i + 50).replace(/\s+/g, " ")}`);
    }
  }
  let last = "";
  let since = Date.now();
  while (Date.now() - t0 < 120_000) {
    const s = await page.evaluate(() => ({
      html: document.body.innerHTML,
      view: document.querySelector("[data-view]")?.getAttribute("data-view") ?? null,
    }));
    if (s.html !== last) {
      last = s.html;
      since = Date.now();
    } else if (s.view === "reviewed" && Date.now() - since > 6000) break;
    await sleep(400);
  }
  const view = await page.evaluate(() => document.querySelector("[data-view]")?.getAttribute("data-view") ?? null);
  const text = await page.evaluate(() => document.body.innerText);
  console.log(`== ${ID} at ${w} px: view ${view}`);
  if (view !== "reviewed") {
    offenders += 1;
    console.log("  the case did not reach reviewed");
  }
  const lower = text.toLowerCase();
  for (const f of FORBIDDEN) {
    for (let i = lower.indexOf(f.toLowerCase()); i >= 0; i = lower.indexOf(f.toLowerCase(), i + 1)) {
      offenders += 1;
      console.log(`  forbidden "${f}": ${text.slice(Math.max(0, i - 50), i + 50).replace(/\s+/g, " ")}`);
    }
  }
  const stray = await page.evaluate(
    ({ allowed, id }) => {
      const out = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const el = n.parentElement;
        const words = n.textContent.replaceAll(id, "");
        if (!el || !/sample/i.test(words) || !el.getClientRects().length) continue;
        if (allowed.some((sel) => el.closest(sel))) continue;
        out.push(n.textContent.trim().slice(0, 100));
      }
      return out;
    },
    { allowed: ALLOWED, id: ID },
  );
  for (const s of stray) {
    offenders += 1;
    console.log(`  "sample" outside its places: ${s}`);
  }
  await page.close();
}
await browser.close();
console.log(offenders === 0 ? "clean" : `${offenders} offending string(s)`);
process.exitCode = offenders === 0 ? 0 : 1;

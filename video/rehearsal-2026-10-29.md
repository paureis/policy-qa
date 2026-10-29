# Demo rehearsal, Oct 29, 2026

One headless run of the demo path on https://recourse-murex.vercel.app (Playwright, Chromium, 1280 by 800), letter dc-001 pasted as text, at 15:54 UTC (11:54 am ET). One live case, as approved. Times come from one clock (`Date.now()` in the script).

## Timings

`/health` before the run: 0.36 s, then 0.29 s (warm; model muse-spark-1.3, 64 PDFs).

Intake: "Read this letter" to the case card shown: **5.6 s**. One row flagged Check: Member's age group (read as "Under 21"). One "Looks right", then Confirm.

| What | Seconds from Confirm |
|---|---|
| Case page URL (`/case/c_80f7a1`) | 0.5 |
| Folder at first poll; Intake and Routing ticked, Investigation running | 1.0 |
| First finding landed ("Does Florida Medicaid cover private duty nursing for a member under age 21?", tick) | 13.7 |
| Investigation done, Steelman running (status deciding) | 24.8 |
| Steelman and Verdict done, stamp pressed, Action running (drafting) | 29.4 |
| Second opinion line appears ("Muse Spark Open is deciding…") | 30.8 |
| Action done, Trust running, letter sheet shown (reviewing) | 35.9 |
| Trust done, status reviewed | 51.7 |

Case: `c_80f7a1`, https://recourse-murex.vercel.app/case/c_80f7a1. Verdict: "The denial appears inconsistent with the policy." 5 of 5 findings verified, 5 of 5 letter sentences verified, 0 struck. Second opinion at the end: "Muse Spark Open agrees." Receipt: **total 51 s, $0.1057** (investigation 24 s, self-check 16 s).

"See the page" on Exhibit 2 (policy): the panel opened with the red highlight on page 5 of Rule 59G-4.261 already drawn and the line "Muse Spark vision check: the highlighted text reads ... and matches the quote." No wait.

Console errors: 0. Failed requests: 1, a Next.js RSC prefetch for `/case/c_80f7a1` aborted at 0.4 s by the navigation itself (harmless).

## Captures

All in `C:\Users\pau\AppData\Local\Temp\claude\demo-rehearsal\`, full page unless named `-view` (one 1280 by 800 viewport):

- seg2-pasted-letter.png, seg2-case-card.png
- seg3-folder-first-poll.png, seg3-first-finding.png, seg3-stamp.png
- seg-reviewed-full.png
- seg4-exhibit-pair.png, seg4-exhibit-pair-view.png, seg4-see-the-page.png, seg4-see-the-page-view.png
- seg5-letter-deadline-view.png, seg5-letter-sheet-view.png, seg5-second-opinion-view.png
- seg6-notsettled.png, seg6-notsettled-view.png
- seg8-landing.png

The seg5 captures still show the page panel open (the script did not close it).

## On-screen problems

1. The run took 51.7 s, past the outline's "38 to 48 seconds" and the numbers card's "about 40 seconds". The self-check (16 s) is the slow part. Say "under a minute", or re-measure on recording day.
2. The not-settled fixture is `c_notsettled` (Sunshine Health), not dc-010. Next to the stamp, Exhibit 2 reads "[synthetic fixture quote, not from the document]" and "Vision check not run: no model key on this server, so the stand-in echoed the quote." The header says "sample case" and the receipt says "Model: fixture". Film the stamp only, cropped tight, or say "a not-settled case", not "dc-010".
3. The fixture page jumps while it replays: layout shift 0.24 at 0.7 s and 0.45 at 7.8 s. Wait until it settles before the two-second shot.
4. On the case card, Confirm sits about 1,900 px down a 2,083 px page; the take needs a scroll from "Looks right" to Confirm.
5. The second opinion line reads "is deciding…" from 30.8 s until it changes to "agrees"; film the line after reviewed.
6. "Sample Health Plan" and "SAMPLE LETTER FOR DEMONSTRATION" show throughout; the voice over should call it a sample letter.

No placeholder text, cut-off text or error label on the live case path.

## Verdict

The live path works end to end at 1280 by 800 with every shot the outline lists, zero console errors and $0.11 per case, so it is ready to film. Change two things first: the time claim (51 s, not about 40) and the not-settled shot (crop to the stamp of `c_notsettled` and stop calling it dc-010, or build a clean dc-010 fixture).

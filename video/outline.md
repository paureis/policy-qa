# Recourse: the three-minute video, outline

Decided Oct 29, 2026 (Alvaro, from three drafted shapes). The script is written from this file on Oct 30; the video is recorded Nov 3 and submitted Nov 4 by 6 PM ET.

## What the rules ask

- Three minutes, public repo, submission by Nov 4, 9:00 PM ET (DECISIONS.md, Oct 26).
- Only event work on screen: "the demo must only highlight what was built during the Hackathon". The corpus, the golden set and the retrieval harness are pre-event (README, Timeline), so they appear once, as the disclosed dataset on the numbers card, never as product shots.
- No medical advice; "Basic RAG Applications" are banned. Say "appeal agent"; show the steelman, the verifier and a not-settled verdict; never answer a treatment question.
- Rubric: Impact 30, Meta tooling 25, Technical depth 20, Demo 25. Meta tooling on screen: Muse Spark reads the letter (text and vision), Muse Spark Open gives the second opinion.

## Decisions

1. Shape A: the problem first, the product by 0:20, the numbers late on one card.
2. The letter is dc-001 (private duty nursing, an 8-hour cap the policy does not have), run live on the deployed site; the recorded sample `c_sample` (the same letter, a recorded run) is the backup take.
3. Nobody on camera. Voice over screen recording.
4. The 40-second run is cut to about 15 seconds with a visible elapsed timer, so "about 45 seconds" stays an honest claim.
5. The phone stays out of the video until its world lands (the weekend's pass). Film at 1280 by 800.
6. Muse Code is named only if it was used in the build; Alvaro confirms before the script is written.

## The three minutes

| Time | On screen | Said (the idea, one line; the script expands it) | Serves |
|---|---|---|---|
| 0:00 to 0:20 | The dc-001 letter as a page; the "8 hours per day" line circled; two lines of text: most denials are never appealed, and most appeals that are filed win | A denial letter arrives. Almost nobody appeals, and most who do, win. | Impact |
| 0:20 to 0:40 | The landing, then paste the letter, "Read this letter", the case card with the gold Check rows, "Looks right", Confirm | Muse Spark reads the letter into a card you check before anything runs. | Demo, Meta tooling |
| 0:40 to 1:10 | The folder opens: the routing slip's marks, findings landing on the record sheet, the latest finding line, the stamp pressing in; elapsed timer in the corner, two cuts | It plans the questions, quotes the rule word for word, argues the payer's side first, then decides. | Demo, Technical depth |
| 1:10 to 1:40 | The exhibit pair; "See the page" on the policy exhibit; the red highlight on the real page; the line "Muse Spark vision check: matches the quote" | Every quote is located on the real policy page and read back by Muse Spark vision. Nothing is trusted. | Meta tooling, Technical depth |
| 1:40 to 2:05 | The appeal letter sheet with its sidenotes; the deadline stamp with the day count; the second opinion line "Muse Spark Open agrees" | A letter with a citation on every claim, the deadline, and a second opinion from Meta's open-weights model. | Impact, Meta tooling |
| 2:05 to 2:15 | The not-settled stamp on dc-010 (two seconds) | When the documents do not settle it, it says so. | Technical depth |
| 2:15 to 2:45 | One numbers card (below) | Measured on 30 reviewed letters; every number is in the repo. | Technical depth |
| 2:45 to 3:00 | The URL and the repo name on the landing | Live now. Paste a letter, or open the sample. | Demo |

## The numbers card

Taken from the latest run in `results/` on recording day (Oct 29 run: `results/case-evals-2026-10-29.*`):

- Verdict right on 28 of 30 reviewed denial letters (93%), 13 of 13 where the denial was inconsistent with the policy.
- 71 of 71 appeal-letter claims verified against the policy page; none struck.
- The second opinion (Muse Spark Open) agreed on 26 of 28.
- The judge checked against a person: 84% agreement on 50 answers, kappa 0.70.
- About $0.10 and 40 seconds a case on Muse Spark 1.3.
- The 160-row golden set and the 64 public documents are the disclosed dataset, built before the event.

## Recording day checklist

1. The warm container: `RECOURSE_MODAL_MIN_CONTAINERS` was 1 at the last deploy; `curl https://alpau-reis--recourse-api.us-east.modal.run/health` answers in under a second when warm.
2. One warm-up case on the site ten minutes before the take ($0.10).
3. Browser at 1280 by 800, zoom 100%, no extensions in frame; the site at https://recourse-murex.vercel.app.
4. The letter text from `cases/letters/` for dc-001 in the clipboard; the backup take is `/case/c_sample`.
5. Never film dc-002 or dc-017 live; they miss on most runs.
6. Capture the dc-010 not-settled stamp from its fixture page separately.
7. Keep the golden-set build, the harness and the review pages out of frame.

## Risks

- The run takes 38 to 48 seconds on the site (up to 69 in the eval runs with three at a time); the timer cut handles it, and the backup take covers a slow run.
- A cold container would pass the intake timeout; the warm-up case proves it is warm.
- Run-to-run variance is about two cases in thirty; dc-001 has been right on every run.
- Under 1024 px the old look shows; film at 1280.
- No live photo intake run is recorded; the video uses pasted text.

## Next step

Oct 30: the script. Each row of the table becomes one to three spoken sentences, about 420 words in all at a measured pace, with the on-screen action noted beside each sentence. Then the demo path is rehearsed once on the site, end to end, with a stopwatch.

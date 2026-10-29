# Recourse: the three-minute video, script draft

Decisions it follows:

1. Shape A: the problem first, the product by 0:20, the numbers late on one card.
2. dc-001 run live on the deployed site; `c_sample` is the backup take.
3. Nobody on camera. Voice over screen recording.
4. The run is cut to about 15 seconds with a visible elapsed timer.
5. No phone in the video. Film at 1280 by 800.
6. Muse Code is not named: it was not used beyond the model APIs (Alvaro, Oct 29).

Target: about 420 spoken words. This draft: 390.

Decided by Alvaro (Oct 29, by prompt): the KFF line stays the range; row 7 closes on ten cents a case; the not-settled shot comes from a live dc-010 run on recording day. The alternatives at the end stay for the edit only.

## The script

| # | Time | On screen | Spoken | Source |
|---|---|---|---|---|
| 1 | 0:00 to 0:20 | The dc-001 letter; a circle around "limits private duty nursing to 8 hours per day". Then: "Denials are rarely appealed. 43 to 67% of appeals succeed. (KFF, 2025 data)" | A denial letter arrives. The plan approved eight hours a day of home nursing for a nine-year-old and denied the other eight. Its reason: Florida Medicaid limits it to eight hours. Most people stop here. Denials are rarely appealed, yet forty-three to sixty-seven percent of appeals succeed.[^1] | dc-001.txt; README:11 |
| 2 | 0:20 to 0:40 | Click "Start with your letter", "Paste text", paste, "Read this letter". Gold "Check" rows. Click "Looks right", then "Confirm". | This is Recourse, a coverage denial appeal agent. Paste the letter and click Read this letter. Muse Spark reads it into a case card. Rows it is less sure of are marked Check. Fix them or click Looks right, then Confirm. Nothing runs until you say the card is right. | EntryForm.tsx:66,118,162; CaseCard.tsx:79; IntakeFlow.tsx:358,363 |
| 3 | 0:40 to 1:10 | The slip ticks Intake, Routing, Investigation, Steelman, Verdict, Action, Trust. Findings land. Timer, two cuts. The stamp: "The denial appears inconsistent with the policy." | Now it works the case. It plans its own questions about the policy and answers each one with the rule, quoted word for word. A verifier checks every quote, and anything it cannot support is struck out, in plain view. Before it decides, it argues the payer's side first, as strongly as the documents allow. Then the stamp. On the site this takes under a minute. | RoutingSlip.tsx:81-123; VerdictSection.tsx:301; case.ts:1236; README:9, steps 3-5 |
| 4 | 1:10 to 1:40 | "The letter says" beside the policy. Click "See the page": the real page, the quote in red, "Muse Spark vision check: ... matches the quote." | Here is the gap. The letter says eight hours a day. The policy says up to twenty-four hours a day when the criteria are met, and it states no eight-hour limit. Click See the page. Every quote is located on the real page, and when the page opens, Muse Spark vision reads it back. Here, it matches. Nothing is taken on trust. | sample-case.ts:899,918; PageViewer.tsx:236-239 |
| 5 | 1:40 to 2:05 | The appeal letter and sidenotes. "Appeal by Dec 6, 2026" with the day count. "Second opinion: Muse Spark Open agrees." | Then the appeal letter, drafted for you. Every claim in it carries a citation that passed the same check. The deadline comes from the letter, December sixth, with the days left. Last, a second opinion. The same decision runs again on Muse Spark Open, Meta's open-weights model. Here, it agrees. | README step 6, "Second opinion"; DeadlineStamp.tsx:113; case.ts:1305 |
| 6 | 2:05 to 2:15 | dc-010, run live once before filming and shown from its own case page: "The documents do not settle it." (two seconds) | Sometimes the papers cannot decide. Here the documents do not settle it, and Recourse says so, plainly. That is a real answer too. | case.ts:1237; results, dc-010 |
| 7 | 2:15 to 2:45 | The numbers card, one line per sentence. | We tested it on thirty reviewed denial letters. The verdict was right on twenty-eight of thirty, and on all thirteen where the denial did not match the policy. Seventy-one of seventy-one letter claims were verified against the page. The open model agreed on twenty-six of twenty-eight. About ten cents a case. The test data was built before the event, and every number is in the repo. | case-evals-2026-10-29.md; README Timeline |
| 8 | 2:45 to 3:00 | The landing, recourse-murex.vercel.app and paureis/recourse. | Recourse is live now, at recourse-murex dot vercel dot app. Paste your own letter, or open the sample case. The code is public on GitHub, at paureis slash recourse. | README:9; page.tsx:35,41 |

[^1]: KFF's analysis of 14 insurers' prior authorization data for calendar year 2025 (published 2026; quoted in README.md:11): among appealed standard-request denials, 67% were overturned in Medicare Advantage, 47% in Medicaid managed care and 43% in the ACA Marketplace; denials were rarely appealed. Checked Oct 29 against the press coverage of the KFF analysis (https://www.fiercehealthcare.com/payers/insurers-denied-between-12-18-prior-auth-requests-2025-kff). Scope: prior authorization denials, standard requests.

## What the script claims

1. dc-001: 8 hours approved, 8 denied, age 9, an 8-hour limit, deadline Dec 6, 2026. dc-001.txt.
2. Rarely appealed; 43 to 67% succeed. README:11 and the KFF analysis (footnote 1). Scope: prior authorization denials, standard requests.
3. "Most people stop here." README:11 ("Most people never file"). **Partly sourced.**
4. Intake and Confirm; questions, quotes, strikes, steelman. README steps 1-4; IntakeFlow.tsx:363.
5. Under a minute. Eval run mean 38.5 s; the Oct 29 rehearsal on the site 51.7 s (video/rehearsal-2026-10-29.md).
6. Up to 24 hours a day; no 8-hour limit. sample-case.ts:899,918 (Rule 59G-4.261 p.5). Check on the live take.
7. Every quote located on the page; vision reads it back when "See the page" opens it. PageViewer.tsx:226-239; the spoken line says so.
8. Every letter claim cited and verified. README step 6.
9. Muse Spark Open reruns the decision; agrees on dc-001. README "Second opinion"; sample-case.ts:822.
10. 28/30, 13/13, 71/71, 26/28, about $0.10 ($0.0942 mean). case-evals-2026-10-29.md. README's "Live agreement rate" paragraph fixed Oct 29 (the Oct 29 sentence moved to the paragraph's end; the 27 of 30 is the Oct 28 evening run).
11. "Thirty reviewed denial letters." cases/README.md: two blind agent reviewers graded every row; Alvaro decided 15; 15 are agent-verified only.
12. Test data built before the event. README Timeline.

## Alternative lines

- Row 1, alternative: "In Medicare Advantage, two in three appeals succeed." (one figure, 67%)
- Row 3, alternative: "It plans six questions about the policy." (recorded run only)
- Row 6, alternative: "When the documents do not settle it, Recourse says so, and says what would change it."
- Row 7, alternative: add "The grader matched a person on eighty-four percent of fifty answers." (README:89); cut "About ten cents a case".

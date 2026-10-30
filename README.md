# Recourse

A coverage denial becomes a case, and the case works itself.

Drop in a denial letter or an explanation of benefits, as a photo, a PDF, or text. Recourse reads it, works out which program and policy govern the service, investigates the written rules, argues the payer's side first, and then says one of three things with the rule quoted and cited to the page: the denial matches the policy, the denial appears inconsistent with the policy, or the documents do not settle it. For an inconsistent denial it drafts the appeal letter, with every sentence carrying a verified citation, plus the evidence checklist the policy itself implies, the filing deadline with a day count, and where to file. It never gives medical advice; questions about treatment or diagnosis are refused with an explanation of what the product does instead.

Built for the Meta Global AI Developer Hackathon (indie track, Oct 26 to Nov 4, 2026) on Muse Spark through the Meta Model API, with Muse Spark Open on Fireworks and Baseten for the open-weights comparison. Corpus: 64 public Florida Medicaid, Medicare, Medicaid, and HIPAA documents, 2,589 pages.

Live at https://recourse-murex.vercel.app (the API runs on Modal; a case costs about $0.11 in model credits and takes about 45 seconds). "See a sample case" on the landing replays a recorded run; "Start with your letter" runs a new one. Sample letters to paste are under `cases/letters/`.

Why it matters: KFF's 2025 analysis of prior authorization data puts denial rates at about 12% in Medicare Advantage, 14% in Medicaid managed care, and 18% in ACA marketplace plans, finds that denials are rarely appealed, and that 67%, 47%, and 43% of appealed denials respectively were overturned. Most people never file. The letter, the deadline, and the rule are the hard part, and they are what this does.

The point of the project is not the demo. Every step is measured against a human-verified golden set before it ships, and the judge that grades answers is itself validated against human verdicts.

## How a case runs

1. **Intake.** Muse Spark reads the letter (image, PDF, or text) into a case card: program (Florida Medicaid MMA, LTC, KidCare, Medicare A, B, Advantage, Part D), member age group, service and code, dates, amount, the payer's stated reason, letter date, and the deadline the letter claims. The user corrects anything wrong.
2. **Routing.** The program decides which documents govern. Dual-eligible or ambiguous cases are investigated under Florida Medicaid and Medicare side by side, with the difference stated.
3. **Investigation.** The agent plans and runs targeted questions against the corpus: is the service covered, what are the limits, what conditions or prior authorization apply, what exclusions exist, what are the appeal rights and deadlines. Each finding is a verbatim quote with document and page, checked by a verifier that confirms the quote exists and supports the finding. Unsupported findings are struck out, on screen.
4. **Steelman.** Before deciding, the agent argues the denial's case as well as the rules allow.
5. **Verdict.** Consistent with the policy, inconsistent with the policy, or not settled by the documents. Each names the rule and the gap between the letter's reason and that rule.
6. **Action.** A draft appeal letter where every sentence carries a citation and has passed the verifier; an evidence checklist derived from the policy's own conditions; the deadline with a day count and the filing path, cited from the appeals documents in the corpus. For a consistent denial, a plain explanation and what would have made the service covered.
7. **Trust.** Verification coverage (claims supported over claims made), cost of the case, time taken, and the full trace.

**Second opinion.** After the verdict, the same Steelman and Verdict stage runs a second time on Meta's open-weights model, Muse Spark Open, with the same findings, the same prompt and the same code guards; only the model differs. It runs beside the letter, and nothing in the chain waits for it, so the case status can reach `reviewed` before the second opinion finishes: a client polls `GET /case/{id}` until `second_opinion.status` is not `running`. The case records whether the two models agree (`second_opinion.agrees`). It never changes the verdict, and the letter and the critic read only the primary verdict. It is skipped, with the reason, when it is not configured or when the verdict made no model call (the verdict failed, a plan outside the corpus, no supported finding, a model failure, or the fixture verdict used without a model key). A second opinion still running when the server restarts loads as `failed`. Configure it with `POLICYQA_SECOND_LLM_BASE_URL`, `POLICYQA_SECOND_LLM_MODEL` and `POLICYQA_SECOND_LLM_API_KEY`, plus `POLICYQA_SECOND_LLM_INPUT_USD_PER_M` and `POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M` (the primary's prices when unset); see `.env.example` and `policyqa/second_opinion.py`. `case-evals` reports the agreement rate, the cases where only one of the two is right, and the second opinion's cost.

Live agreement rate (Oct 28, 2026, `results/case-evals-2026-10-28-second-opinion.*`, the 30 cases on Muse Spark 1.3 with Muse Spark Open at Baseten as the second model): the second opinion ran on 28 cases (dc-011 is refused at intake and dc-030 is outside the corpus) and agreed with the verdict on 27 of 28 (96.4%). The one disagreement is dc-009 (the verdict said not settled, which is right; the open model said consistent). No case where the open model was right and the verdict wrong. It cost $0.008 a case on top of the $0.096 chain and added no time to it. The primary verdicts in that run: 27 of 30 (90.0%), 81 of 81 letter claims verified; dc-026 came back right and dc-002 missed at retrieval, the run-to-run variance the tables above describe. On the Oct 29 run (`results/case-evals-2026-10-29.*`, after the third tuning pass) it agreed on 26 of 28 (92.9%): dc-009 again, and dc-008, where the verdict was not settled (the accepted alternate) and the open model said inconsistent (the intended outcome).

## What is here

| Piece | Status |
|---|---|
| Corpus: 64 public PDFs (30 Florida Medicaid, 30 federal Medicare and Medicaid, 4 HIPAA), 2,589 pages | done, `corpus/manifest.csv`, `corpus/fetch.sh` |
| Golden set: 160 questions, six types, every document covered, LLM-drafted and human-verified | done, `golden/golden.csv` |
| Ingestion, page-bounded chunking, hybrid retrieval with reranker, recall harness | groundwork, Oct 25 (see Timeline) |
| Answer harness: enforced citations, forced abstention, judge, cost and latency, traces | groundwork, Oct 25 |
| Generation on Muse Spark via the Meta Model API | wired Oct 26 (`python -m policyqa.cli smoke`, `/answer`); first live call when the key exists |
| Intake screen (`/case/new`) and case intake endpoints from photo, PDF, or text; fixture mode until the key exists | built Oct 26, live on Muse Spark Oct 27 |
| Program routing | Oct 28 |
| Investigation agent with verified findings | Oct 28 |
| Steelman, verdict, appeal letter, deadline and filing steps, evidence checklist, scope guardrail | Oct 29 |
| Denial-case eval set (about 30 synthetic letters with known verdicts), judge validation against human verdicts | Oct 30 |
| Live demo, done Oct 28: the API on Modal (https://alpau-reis--recourse-api.us-east.modal.run) and the front end on Vercel (https://recourse-murex.vercel.app), synthetic sample letters; the public sample case is a recorded run of dc-001 through the API on October 28, 2026 (only the letter is synthetic); three live cases ran end to end on the deployed stack that night (`deploy/README.md`) | Oct 28 |
| Open-weights comparison on Baseten | done Oct 28 (27 of 30; the table under Denial-case evaluation) |
| Dual-eligible side by side | done: the router sends a letter that names both programs, or a Long-term Care member aged 65 or older, under Florida Medicaid and Medicare together, the investigation asks every question under both, the case page shows the record in two columns and the verdict states the difference; in the Oct 29 live run three cases ran side by side (dc-012 by the Long-term Care rule; dc-005 and dc-021 because the intake read their program as unknown, and the router then checks both sets of rules) and all three verdicts were right; run live on the deployed site Oct 30 (c_d8240f: inconsistent, 7 of 7 findings verified, the second opinion agreeing, 71 s, $0.158); from Oct 30 the eval report counts dual routes; from Oct 30 evening each column asks its questions in its own program's terms (the Medicare column of dc-012 went from mostly "not settled" to 14 of 14 findings supported in the live probe) |
| Full evaluation run, numbers, write-up, video | Nov 2 to 3 |

## Timeline and what was built when

The Meta Global AI Developer Hackathon rules require new work only, and the demo may show only what was built during the event (building period Oct 27 to Nov 4, 2026). This section exists so judges can tell the two apart; the git log carries the dates.

**Before the event (dataset and groundwork, Oct 21 to 26):**
- The dataset: 64 public policy PDFs selected and verified (`corpus/manifest.csv`) and the 160-row golden set, drafted by LLM agents and verified row by row by a person (`golden/golden.csv`). Built Oct 22 to 23.
- Groundwork, Oct 25 (commits c001284 to 3555222, the day before kickoff): page text extraction, chunking, a BM25 and embedding retrieval baseline with a reranker option, the retrieval recall harness, a first draft of the answer and judge harness with a mock provider, per-query traces, and the judge review page. No Meta model was called; nothing here is demoed.

**During the event (from the Oct 26 noon kickoff):** everything the demo shows. The product itself (Recourse) was designed on Oct 26 after the rules were published. The first product code landed on the afternoon of Oct 26, after the kickoff opened the building window: the intake screen in fixture mode, the case intake endpoints, the Muse Spark extractor and smoke command, with no model call made yet because no API key existed. The rest is built from Oct 27: intake from photo, PDF, and text on Muse Spark; program routing; the investigation agent with verified findings; the steelman pass; the verdict; the appeal letter, deadline, and evidence checklist; the scope guardrail; the denial-case evaluation set; the judge validated against human verdicts; the open-weights comparison; the live demo; the write-up. Each lands as its own commit with a date.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
bash corpus/fetch.sh data/pdfs                 # 64 PDFs, about 66 MB; hhs.gov may block non-browser clients
python -m policyqa.cli ingest --pdfs data/pdfs # pdftotext -layout, one file per page
python -m policyqa.cli chunk                   # data/chunks.jsonl, 300-word windows, 60-word overlap, never across pages
python -m policyqa.cli embed                   # data/dense.npy with BAAI/bge-small-en-v1.5 (CPU is fine)
python -m policyqa.cli eval --mode hybrid --rerank
python -m policyqa.cli search "How many home health visits per day does Florida Medicaid cover?" --rerank
```

Requires `pdftotext` and `pdfinfo` (poppler-utils). No API keys are needed for retrieval or its evaluation.

Generation and the judge need keys; copy `.env.example` and fill in the names it lists. Then:

```bash
python -m policyqa.cli answer "Can an adult on Florida Medicaid get a fixed bridge to replace a missing tooth?"
python -m policyqa.cli eval-answers --judge-subset        # 50 rows, Claude as judge
python -m policyqa.cli eval-answers                       # all 160 rows
python -m policyqa.cli eval-answers --provider mock --judge mock   # no keys; checks the plumbing, scores mean nothing
```

## How answers are scored

The model sees the top 5 passages tagged `[P1]` to `[P5]` and must return JSON: an answer, the passages it relied on with a verbatim quote from each, and whether it abstains. Citations are checked, not trusted: a citation must name a passage that was shown, and its quote must occur in that passage (same 0.8 overlap rule as retrieval). Invalid citations are dropped, and an answer left with no valid citation becomes an abstention, because an uncited coverage claim is the failure this system exists to prevent.

Before any accuracy number is quoted, the judge is checked against a person. `export-review` turns the 50 judge-subset answers of a run into documents for the Judge Validation Review page (`review/judge-review.html`, a one-answer-at-a-time grading page whose verdicts save server-side; the judge's verdict is hidden until the human's is in). `judge-agreement` then reports exact and collapsed agreement, Cohen's kappa, the confusion matrix, and every disagreement with both rationales.

Claude then grades each answer against the human-written gold answer (correct, partially correct, incorrect, abstained) and against the cited passages (supported, partially supported, unsupported). The report gives accuracy by question type, the supported rate, abstention on the 10 unanswerable rows, false abstention on answerable rows, citation validity, tokens and cost per query for generation and for the judge, and p50 and p95 latency. The judge's verdicts on the 50-row judge subset are compared with independent human verdicts before any accuracy number is quoted.

Judge validation, done (Oct 28, 2026, `results/judge-agreement-muse-spark-oct26.json`; the graded documents are in `results/judge-graded-muse-spark-oct26/`). Alvaro graded all 50 judge-subset answers of the Oct 26 Muse Spark 1.3 run on the review page without seeing Claude's verdicts. Agreement between the human and the judge on accuracy: 42 of 50 exact (84%), Cohen's kappa 0.70 on the three-way labels; collapsed to right-or-wrong (partially correct counted with correct), 46 of 50 (92%), kappa 0.78. On faithfulness (45 rows with citations) 34 of 45 (75.6%). The judge is stricter than the human: of the 8 disagreements, 4 are answers the human called correct and the judge partially correct, 2 the human called partially correct and the judge incorrect, 1 the human called incorrect and the judge partially correct, and 1 (gs-157, an unanswerable row) the human called incorrect and the judge partially correct. One human verdict was corrected after the review (gs-154, an unanswerable row where the model abstained: Incorrect to Correct). With the judge validated, the golden-subset numbers can be quoted: by the human's verdicts the Oct 26 run answered 33 of 50 correctly (66%), 5 partially (10%) and 12 incorrectly (24%); by the judge, 29 correct, 9 partially correct, 12 incorrect. These are the Oct 26 answer step, before the case chain existed; the denial-case numbers above are the product's.

## How retrieval is scored

A golden row is a hit at k when one of the top-k chunks holds the row's `gold_quote`: whitespace-normalized, word 4-gram overlap of at least 0.8. Multi-document rows need every quote found (`all@k`); `any@k` is reported alongside. Unanswerable rows are not scored here; they are scored by the abstention check in the generation harness.

The report also gives `doc@k` (right document, any page) and `page@k` (right document and page), which separate "found the wrong document" from "found the right page but the wrong window".

Results live in `results/<run>.json` with the full config and a per-row record, so two runs can be diffed row by row.

Current numbers on all 64 documents, 150 scorable rows (Alvaro's machine, Oct 26 evening, `results/hybrid.json` and `results/hybrid-rerank.json`), 300-word chunks, CPU only:

| Retrieval | all@5 | all@10 | right doc @10 | MRR | p50 latency |
|---|---|---|---|---|---|
| Hybrid, RRF | 0.560 | 0.680 | 0.867 | 0.433 | 14 ms |
| Hybrid + MiniLM-L-6 reranker, 20 candidates (the answering path) | 0.613 | 0.720 | 0.913 | 0.480 | 421 ms |

The earlier sweep, 139 scorable rows on the 59 documents reachable from the build machine, which chose the settings:

| Retrieval | all@5 | all@10 | right doc @10 | MRR | p50 latency |
|---|---|---|---|---|---|
| BM25 | 0.453 | 0.540 | 0.755 | 0.309 | 11 ms |
| Dense, bge-small-en-v1.5 | 0.532 | 0.691 | 0.885 | 0.395 | 105 ms |
| Hybrid, RRF | 0.590 | 0.684 | 0.878 | 0.445 | 136 ms |
| Hybrid + MiniLM-L-6 reranker, 20 candidates | 0.612 | 0.712 | 0.899 | 0.484 | 909 ms |
| Hybrid + bge-reranker-base, 40 candidates | 0.655 | 0.755 | 0.907 | 0.494 | 9,138 ms |

Multi-document questions (10 rows) are the weak spot at every setting, 0.3 to 0.4 at 10. One query cannot pull two documents reliably; the fix belongs in the generation layer (one sub-query per jurisdiction), and is on the list. The reasoning behind each choice, with the chunk-size sweep, is in `DECISIONS.md`.

## Denial-case evaluation

Retrieval recall says whether the right page was found. This harness says whether the verdict is right. It runs the 30 reviewed letters in `cases/` (see `cases/README.md`) through the same code the API runs, without HTTP: the intake route's text path (length check, `scope_check`, the extractor), then the investigation, Steelman and Verdict, the letter, and the critic. Providers are chosen as the API chooses them: live when `POLICYQA_LLM_*` are set and the index is built, the fixtures otherwise. Cases run in a private in-memory store, so nothing lands in `data/cases`.

```
python -m policyqa.cli case-evals [--ids dc-001,dc-011] [--limit N] [--concurrency 3] [--no-critic]
```

It writes `results/case-evals-<date>.json` (per-case rows, the summary, the model, reasoning effort, prices, and modes) and `results/case-evals-<date>.md` (a summary table and a per-case table to paste here).

Measured: verdict accuracy overall and by intended outcome, program, and jurisdiction; refusal on the medical-question trap; the letter verification rate (verified claims over claims, letters that apply only) and the struck rate; critic revisions accepted; cost and seconds per case (mean and p50) and in total. With the second opinion configured: its agreement with the verdict over the cases where both ran, the cases where only one of the two is right, and its mean cost, kept out of the case's own cost so runs stay comparable; each row has a "Second opinion" column ("skipped" when it did not run).

Scoring rule:

- A case is correct when the verdict equals `intended_outcome`.
- Two alternates are also accepted, because both blind reviewers on Oct 26 called them defensible: dc-008 `not_settled` (whether days 46 to 51 were emergency services under fl-01) and dc-020 `consistent` ("the records we received do not show" can be read as consistent with the rule).
- dc-011 is scored on refusal: correct only when intake refuses it as `out_of_scope`, with no verdict and no letter.
- dc-030 expects `not_settled`. The summary records the route's program, whether it is `unknown`, and whether the router said no document in the corpus governs the plan (`route.outside_corpus`, set for employer and commercial payers since Oct 26).
- An error at any stage, or a refusal of any other letter, counts as wrong and is listed. Each row's `stage_errors` names the stages that failed.
- A verdict model failure (the `not_settled` template with `error` set), or an investigation whose findings all errored with none supported, counts as an error, never as a real `not_settled`.
- A template letter (letter `error` set) leaves the verdict's score alone, is left out of the verification and struck rates, and is counted as `letter_failures`.
- A critic failure leaves the verdict's score alone, because the product keeps the letter as drafted by design, and is counted as `critic_failures`.
- `--limit` must be 1 or more; leave it out to run every case.

Current numbers: Oct 29, 2026, after the third verdict tuning pass (`results/case-evals-2026-10-29.json` and `.md`); the Oct 28 column is the second tuning pass (`results/case-evals-2026-10-28.*`); the Oct 27 run is the first pass (`results/case-evals-2026-10-27.*`: 25 of 30, 83.3%, 81 of 81 letter claims over 22 letters, $0.095 and 47 s a case); the Oct 26 baseline is the first live run, before any tuning (`results/case-evals-2026-10-26.*`: 22 of 30, 73.3%, letter claims 61 of 61 over 16 letters, $0.084 and 34 s a case). All runs: Muse Spark 1.3, reasoning effort low, critic 1 round, three cases at a time.

| Measure | Oct 29 (current) | Oct 28 | Change |
|---|---|---|---|
| Verdict accuracy | 28 of 30 (93.3%) | 26 of 30 (86.7%) | +2 cases, +6.7 points |
| Intended consistent | 9 of 10 | 9 of 10 | same |
| Intended inconsistent | 13 of 13 | 11 of 13 | +2 |
| Intended not settled | 5 of 6 | 5 of 6 | same |
| Refusal on the medical question (dc-011) | correct | correct | same |
| Letter claims verified | 71 of 71 over 20 letters; 0 struck | 81 of 81 over 20 letters; 0 struck | same rate |
| Critic revisions accepted | 12 of 20 | 13 of 20 | -1 |
| Cost per case | mean $0.094, p50 $0.098, $2.83 for the run | mean $0.097, p50 $0.104, $2.92 for the run | -$0.003 mean |
| Seconds per case | mean 39, p50 42 | mean 47, p50 50 | -8 s mean |
| Errors, template letters, critic failures | 0, 0, 0 | 0, 0, 0 | same |

Oct 29 misses (2): dc-002, consistent, came out inconsistent again (retrieval: no question's passages reached fl-04 p4 this run; the plan came from the model) and dc-017, not settled, came out inconsistent as on every run. Against Oct 28: dc-026 and dc-027 are right (dc-026's exception page, fed-10 p14, was reached by two questions, one of them through the new fact-anchored query, and cited from both; dc-027's decisive fact is the fill inside the first 90 days of coverage, settled by the letter); dc-008 came out not settled by the model's own call, its accepted alternate, and the rewritten guard fired on no case. The Oct 28 evening run on the same code as that morning (the second-opinion run) had 27 of 30, so against it the gain is one case, inside the run-to-run variance of about two; what is not variance is that dc-026's page was reached (no question reached it in either Oct 28 run) and that dc-027's decisive fact moved from the formulary to the transition fill. Every row records `proposed_outcome`, the decisive fact and who settles it, the planned questions, each exception finding's relevance state, which passages came from the fact-anchored query (`source: "fact"`), and the stage the miss traces to; DECISIONS.md (Oct 29) reads the run.

Run-to-run variance on the same code (Oct 30, 2026): the code of the Oct 29 run (no change to `policyqa/` or `api/` except the eval's own reporting) was run again on all 30 cases (`results/case-evals-2026-10-30.*`), and the four cases it missed were run a third time (`results/case-evals-2026-10-30-misses.*`). The accuracy of this code is a range, not one number: 26 to 28 of 30 across the two full runs. The rest of the Oct 30 run: intended consistent 9 of 10, inconsistent 12 of 13, not settled 4 of 6; the refusal correct; letter claims 75 of 75 over 19 letters, 0 struck; critic revisions accepted 15 of 19; the second opinion agreeing on 28 of 28; dual routes 3 of 3 (dc-012, dc-021, dc-030; the first run to record them); mean $0.094 and p50 $0.098 a case, $2.81 for the run; mean 45 s and p50 49 s a case (the API was slower than on Oct 29 all day); 0 errors, 0 template letters, 0 critic failures.

| Case | Intended | Oct 29 | Oct 30 | Oct 30, re-run | Reading |
|---|---|---|---|---|---|
| dc-002 | consistent | inconsistent | inconsistent | not settled | stable miss: no planned question reaches the hinge page fl-04 p4 in any run |
| dc-017 | not settled | inconsistent | inconsistent | inconsistent | stable miss: the verdict stage reads "dispense as written" in the letter as decisive every run |
| dc-009 | not settled | not settled | consistent | consistent | borderline: the verdict stage proposes consistent from the letter's own limit in 2 of 3 runs, and the second opinion said consistent on Oct 29 |
| dc-013 | inconsistent | inconsistent | not settled | inconsistent | one-run retrieval miss: on Oct 30 none of the 5 planned questions reached fl-16 p7; the plan comes from the model and varies |

The two stable misses are the next tuning targets. dc-009 keeps its reviewed label (the scoring rule accepts an alternate only when both blind reviewers called it defensible, and this one has not been put to them).

Open-weights comparison, Oct 27 evening: the same code and the same 30 cases on Muse Spark Open (`accounts/fireworks/models/muse-spark-open` on Fireworks, serverless, list price $1.25 and $4.25 per million tokens, the same as Muse Spark 1.3's; reasoning effort low, critic 1 round, three at a time; `results/case-evals-2026-10-27-fireworks.*`).

| Measure | Muse Spark 1.3 (Meta Model API) | Muse Spark Open (Fireworks) |
|---|---|---|
| Verdict accuracy | 25 of 30 (83.3%) | 23 of 30 (76.7%); 23 of the 27 cases that answered (85.2%) |
| Intended consistent, inconsistent, not settled | 7 of 10, 12 of 13, 5 of 6 | 9 of 10, 9 of 13, 4 of 6 |
| Refusal on the medical question (dc-011) | correct | correct |
| Letter claims verified | 81 of 81 over 22 letters | 67 of 67 over 19 letters |
| Critic revisions accepted | 11 of 22 | 5 of 19 |
| Cost per case | mean $0.095, $2.84 for the run | mean $0.067, $2.01 for the run |
| Seconds per case | mean 47, p50 51; 8 minutes wall | mean 174, p50 146; 30 minutes wall |
| Errors | 0 | 3 read timeouts in the verdict stage (dc-009, dc-018, dc-022) |

Read with care: three of the open model's seven misses are timeouts, not verdicts, so the honest comparison is the 85.2 percent on answered cases against 83.3, with a 3.7 times slower endpoint. Its four real misses: dc-003 (consistent, got inconsistent, the same over-found exception as Muse Spark 1.3), dc-015 and dc-026 (inconsistent, got not settled: the proof is an exception the open model did not rely on), dc-017 (not settled, got inconsistent, as on every run). The Baseten endpoint for the same model is still to be run.

Open-weights comparison, second run, Oct 28 midday: the same code as the Oct 28 Meta run above (the second tuning pass) and the same 30 cases on Muse Spark Open at Baseten (`meta-models/muse-spark-open-1026`, the model API; reasoning effort low, critic 1 round, three at a time; HTTP timeout raised to 300 s through the new `POLICYQA_LLM_TIMEOUT_S`; `results/case-evals-2026-10-28-baseten.*`).

| Measure | Muse Spark 1.3 (Meta Model API, Oct 28) | Muse Spark Open (Baseten, Oct 28) |
|---|---|---|
| Verdict accuracy | 26 of 30 (86.7%) | 27 of 30 (90.0%) |
| Intended consistent, inconsistent, not settled | 9 of 10, 11 of 13, 5 of 6 | 9 of 10, 12 of 13, 5 of 6 |
| Refusal on the medical question (dc-011) | correct | correct |
| Letter claims verified | 81 of 81 over 20 letters | 71 of 71 over 19 letters |
| Critic revisions accepted | 13 of 20 | 12 of 19 |
| Cost per case | mean $0.097, $2.92 for the run | mean $0.068, $2.04 for the run |
| Seconds per case | mean 47, p50 50; 8 minutes wall | mean 25, p50 26; 4 minutes wall |
| Errors | 0 | 0 (no timeouts at 300 s) |

Read with care: the two runs are one case apart, and a one-case delta is inside the run-to-run variance (about two cases). What the open model's three misses say: dc-002 and dc-017 miss on both models (dc-002 at the answer stage here, the hinge page reached the model but no verified quote came from it; dc-017 at the verdict, as on every run); dc-021 (QMB cost sharing, inconsistent) never reached the chain because the open model's intake refused the letter as not a denial letter, a scope-check miss the Meta model did not make. The open model is also the one that answered dc-026 and dc-027 right this run. For the second opinion (Thursday), only the verdict stage runs on the open model, so the intake refusal does not apply there; it matters for any deployment that puts the whole chain on open weights.

Golden-subset baseline for the open model (Oct 29, 2026, `results/answers-muse-spark-open-fireworks-base-2026-10-29-judged.json`): Muse Spark Open on Fireworks answered the 50 judge-subset rows with the same retrieval as the Oct 26 run; the validated Claude judge scored 58.7% correct, 15.2% partially correct, 10.9% incorrect, 15.2% abstained, faithfulness 89.7%, 98.9% of citations valid and 89.7% citing the gold document; $0.0045 and 5.1 s a row. That is the same judged correct rate as Muse Spark 1.3 on Oct 26 (58.7% by the judge, 66% by the human grader), with more abstentions and fewer wrong answers.

Fine-tune (Oct 29, 2026): built and blocked, not run. `policyqa/finetune.py` builds a supervised fine-tuning dataset from the 110 golden rows outside the judge subset as the answer stage sees them (`results/finetune/train-2026-10-29.jsonl`, 110 rows, every gold quote cited verbatim at the product's 0.8 threshold, the judge subset held out) and drives a Fireworks managed LoRA job and an on-demand deployment through the REST API (`finetune-dataset`, `finetune-job`). The chosen base is Meta's Muse Glimmer 30B (free to train until Nov 30; Muse Spark Open has no managed fine-tuning on Fireworks, and neither model's LoRA serves per token, only on a dedicated deployment). Fireworks refuses every dataset upload for this account today ("dataset uploads are temporarily disabled"), so the job did not run; DECISIONS.md (Oct 29) has the full account. The evaluation plan when it runs: base and tuned on the 50 held-out rows with the validated judge, reported whatever the result.

What the Oct 26 misses said (recorded in DECISIONS.md, Oct 26): four "not settled" rows came out "consistent" because the model takes the payer's stated facts as given (dc-009, dc-014, dc-020 scored on its alternate, dc-002 the other way); three "inconsistent" rows whose proof is an exception elsewhere in the document came out "not settled" or "consistent" (dc-018 eyeglasses after cataract surgery, dc-026 rosacea not cosmetic, dc-021 QMB cost sharing); dc-017 is a close call either way; dc-030, the employer plan, was answered with an "inconsistent" verdict although the route said no corpus document governs it, a product bug fixed the same night. These are the tuning targets, measured before any change.

## Design notes

- Chunks never cross a page. A citation is (document, page), and a chunk that spans pages cannot be cited honestly.
- Page text comes from `pdftotext -layout`, the same tool the golden quotes were copied from, so a quote the verifier found is found again in the chunk.
- BM25 and dense lists are fused with reciprocal rank fusion. Their scores live on different scales and RRF needs no tuning.
- Local open models only for retrieval (bge-small-en-v1.5, bge-reranker-base). An index rebuild costs nothing and needs no key.

Decisions with reasons are in `DECISIONS.md` (to be written as they are made).

## License

MIT. The corpus documents are public US federal and Florida government publications; see `corpus/manifest.csv` for the source URL of each.

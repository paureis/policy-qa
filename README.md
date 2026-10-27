# Recourse

A coverage denial becomes a case, and the case works itself.

Drop in a denial letter or an explanation of benefits, as a photo, a PDF, or text. Recourse reads it, works out which program and policy govern the service, investigates the written rules, argues the payer's side first, and then says one of three things with the rule quoted and cited to the page: the denial matches the policy, the denial appears inconsistent with the policy, or the documents do not settle it. For an inconsistent denial it drafts the appeal letter, with every sentence carrying a verified citation, plus the evidence checklist the policy itself implies, the filing deadline with a day count, and where to file. It never gives medical advice; questions about treatment or diagnosis are refused with an explanation of what the product does instead.

Built for the Meta Global AI Developer Hackathon (indie track, Oct 26 to Nov 4, 2026) on Muse Spark through the Meta Model API, with Muse Spark Open on Baseten for the open-weights comparison. Corpus: 64 public Florida Medicaid, Medicare, Medicaid, and HIPAA documents, 2,589 pages.

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
| Live demo: API on Modal, front end on Vercel, synthetic sample letters | Oct 31 |
| Open-weights comparison on Baseten; dual-eligible side by side | Nov 1 |
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

Measured: verdict accuracy overall and by intended outcome, program, and jurisdiction; refusal on the medical-question trap; the letter verification rate (verified claims over claims, letters that apply only) and the struck rate; critic revisions accepted; cost and seconds per case (mean and p50) and in total.

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

Numbers, first live run, Oct 26, 2026 (`results/case-evals-2026-10-26.json` and `.md`; Muse Spark 1.3, reasoning effort low, critic 1 round, three cases at a time):

| Measure | Value |
|---|---|
| Verdict accuracy | 22 of 30 (73.3%) |
| Intended consistent | 9 of 10 |
| Intended inconsistent | 10 of 13 |
| Intended not settled | 2 of 6 |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 61 of 61 over 16 letters; 0 struck |
| Critic revisions accepted | 9 of 16 |
| Cost per case | mean $0.084, p50 $0.088, $2.50 for the run |
| Seconds per case | mean 34, p50 38 |
| Errors, template letters, critic failures | 0, 0, 0 |

What the misses say (recorded in DECISIONS.md, Oct 26): four "not settled" rows came out "consistent" because the model takes the payer's stated facts as given (dc-009, dc-014, dc-020 scored on its alternate, dc-002 the other way); three "inconsistent" rows whose proof is an exception elsewhere in the document came out "not settled" or "consistent" (dc-018 eyeglasses after cataract surgery, dc-026 rosacea not cosmetic, dc-021 QMB cost sharing); dc-017 is a close call either way; dc-030, the employer plan, was answered with an "inconsistent" verdict although the route said no corpus document governs it, a product bug fixed the same night. These are the tuning targets, measured before any change.

## Design notes

- Chunks never cross a page. A citation is (document, page), and a chunk that spans pages cannot be cited honestly.
- Page text comes from `pdftotext -layout`, the same tool the golden quotes were copied from, so a quote the verifier found is found again in the chunk.
- BM25 and dense lists are fused with reciprocal rank fusion. Their scores live on different scales and RRF needs no tuning.
- Local open models only for retrieval (bge-small-en-v1.5, bge-reranker-base). An index rebuild costs nothing and needs no key.

Decisions with reasons are in `DECISIONS.md` (to be written as they are made).

## License

MIT. The corpus documents are public US federal and Florida government publications; see `corpus/manifest.csv` for the source URL of each.

# Decisions

Each entry: what was decided, the alternatives, and the number or reason that settled it. Dated.

## 2026-10-25

**Page text comes from `pdftotext -layout`, one file per page.** The golden-set quotes were copied from that exact output, so the harness finds them again after whitespace normalization. A Python PDF library would produce slightly different text and break quote matching. Checked: every gold quote of the 59 documents available here is found whole in at least one chunk (oracle overlap 1.0 on all 149 quotes).

**Chunks never cross a page boundary.** A citation is (document, page). A window that spans two pages cannot be cited honestly. Within a page, windows of N words with overlap so a quote on a window edge lands whole in one of them.

**Chunk size is chosen from recall, not from habit.** BM25 only, 139 scorable rows, recall at 10 by the gold-quote rule:

| Window (words) | Overlap | Chunks | all@5 | all@10 | MRR |
|---|---|---|---|---|---|
| 150 | 30 | 7,025 | 0.295 | 0.432 | 0.208 |
| 200 | 40 | 5,491 | 0.403 | 0.489 | 0.270 |
| 300 | 60 | 3,949 | 0.453 | 0.540 | 0.309 |
| 500 | 100 | 2,573 | 0.496 | 0.554 | 0.374 |
| 800 | 150 | 2,489 | 0.489 | 0.561 | 0.378 |

Bigger windows help lexical recall a little and stop helping past 500. The dense and reranked runs decide the final size; 300 is the working default until they do.

**Hybrid retrieval fuses BM25 and dense with reciprocal rank fusion.** Scores on different scales, no weight to tune, k=60. Alternative was a weighted sum of normalized scores, which needs a weight tuned on the same golden set used for evaluation.

**Local open models for embeddings and reranking** (bge-small-en-v1.5, bge-reranker-base), on CPU. Rebuilding the index costs nothing, no key, and the hackathon credits stay for generation. Alternative was a hosted embeddings API.

**What BM25 misses.** The misses are the questions written the way a patient or provider would ask ("My son needs physical therapy after an injury. How many sessions..."), against regulatory text ("Short-term rehabilitative services ... Limited to 24 sessions within a 60-day period"). In a quarter of the misses the right document is not in the top 10 at all. That is the gap dense retrieval is for.

**Retrieval mode, same 139 rows, 300-word chunks, 40 candidates into the reranker, CPU only (4 cores, no GPU):**

| Run | all@5 | all@10 | doc@10 | page@10 | MRR | p50 latency |
|---|---|---|---|---|---|---|
| BM25 | 0.453 | 0.540 | 0.755 | 0.590 | 0.309 | 11 ms |
| Dense (bge-small) | 0.532 | 0.691 | 0.885 | 0.770 | 0.395 | 105 ms |
| Hybrid (RRF) | 0.590 | 0.684 | 0.878 | 0.748 | 0.445 | 136 ms |
| Hybrid + bge-reranker-base | 0.655 | 0.755 | 0.907 | 0.813 | 0.494 | 9,138 ms |

By type, all@10: adv 0.78 to 0.89, num 0.73 to 0.85, fact 0.67 to 0.80, proc 0.61 to 0.78, multi 0.30 to 0.40.

What this says:
- Dense retrieval is the big step (0.54 to 0.69). The paraphrased questions need it.
- Hybrid beats dense at 5 and on MRR, ties at 10. Keep it: BM25 catches exact codes, dollar amounts, and rule numbers that embeddings blur.
- The reranker adds 7 points at 10 and 6.5 at 5, and costs 9 seconds a query on this CPU with 40 candidates. That is a demo-killer as is. Options: 20 candidates (measured next), a smaller cross-encoder, or a GPU at serve time. Decision pending on the 20-candidate number.
- Multi-document rows are the weak spot at every setting (10 rows, 0.3 to 0.4). One query cannot pull two documents reliably. Fix at the generation layer: split the question into one sub-query per jurisdiction, retrieve each, merge. Not a chunking problem.
- 11 rows are unscored here because flrules.org and hhs.gov block this cloud box. The local run on the full 64 documents is the one that counts.

**Reranker with 20 candidates instead of 40** (same rows, same CPU): all@5 0.633, all@10 0.705, MRR 0.475, p50 4,693 ms. Halving the candidates halves the latency and gives back most of the reranker's gain at 10 (0.755 to 0.705) while keeping most of it at 5 (0.655 to 0.633). Still too slow for a live demo on CPU. Decision pending: a smaller cross-encoder, a GPU at serve time, or hybrid without reranking for the demo and reranking in the batch eval only.

**Smaller cross-encoder measured** (cross-encoder/ms-marco-MiniLM-L-6-v2, 22M parameters, against bge-reranker-base at 278M). Same rows, same chunks, CPU only. Latency is per query at p50 on an otherwise idle 4-core box.

| Run | all@5 | all@10 | doc@10 | MRR | p50 latency |
|---|---|---|---|---|---|
| Hybrid, no reranker | 0.590 | 0.684 | 0.878 | 0.445 | 136 ms |
| Hybrid + MiniLM, 20 candidates | 0.612 | 0.712 | 0.899 | 0.484 | 909 ms |
| Hybrid + MiniLM, 40 candidates | 0.626 | 0.741 | 0.907 | 0.490 | 1,550 ms |
| Hybrid + bge-reranker-base, 20 | 0.633 | 0.705 | 0.878 | 0.475 | 4,693 ms |
| Hybrid + bge-reranker-base, 40 | 0.655 | 0.755 | 0.907 | 0.494 | 9,138 ms |

Reading: MiniLM gives up 1 to 3 points against the big reranker and runs about five times faster. At 20 candidates it stays under a second on CPU and still beats plain hybrid by 2 to 3 points at both cutoffs. The live path and the batch eval can use different settings as long as the report says which; the write-up should show both.

**Decision (Alvaro, Oct 25): the answering path reranks with MiniLM-L-6 over 20 candidates.** Under a second on CPU, 2 to 3 points over plain hybrid. The retrieval eval keeps bge-reranker-base over 40 as its reference setting so the ceiling is known, and the write-up shows both. `python -m policyqa.cli answer` and `eval-answers` default to the MiniLM setting; `--no-rerank` and `--rerank-model` override it.

## 2026-10-26

**Rules read (participant guide, published Oct 26) and what they change.**
- Repositories must be public; three-minute demo video; submission by Nov 4, 9:00 PM ET; solo allowed.
- "New work only" and "the demo must only highlight what was built during the Hackathon." The Oct 25 groundwork is disclosed in the README Timeline section and stays out of the demo; everything shown is built from Oct 27 on. Alternatives considered: asking the organizers first (a day of waiting), or starting a fresh repo (re-doing a day of work while the old history still exists). Disclosure is the honest and verifiable option.
- "Basic RAG Applications" and "AI that gives medical advice" are on the banned list. This project answers coverage and billing questions from policy documents and refuses treatment or diagnosis questions. What keeps it out of "basic": citations that are checked and enforced, forced abstention, a human-verified golden set, a judge validated against human verdicts, and, built during the event, a claim-level verification agent, a Florida versus federal comparison mode, a coverage guardrail, and a live scorecard in the product.
- Meta models are mandatory. Generation runs on Muse Spark 1.1 through the Meta Model API (OpenAI-compatible, `https://api.meta.ai/v1`), with Muse Spark Open on Baseten (`meta-models/muse-spark-open-1026`) for the open-weights comparison once its credits arrive. Claude remains the judge, validated against human verdicts; a Muse Spark judge is reported alongside for agreement.
- Credits: $150 Meta Model API (claimed Oct 26); Baseten $100, Modal $100, Fireworks $25 requested through their forms.

**Judging rubric (Stage Two, 0 to 10 each): Impact 30%, Use of Meta AI tooling 25%, Technical depth and execution 20%, Demo 25%.** Bonus prizes: most viral, best build on open-weight models, community vote, best agentic use case, best creative build. What this changed:
- The demo video opens with the problem (a billing clerk or member-services rep and the cost of a wrong coverage answer), gives the evals one tight segment with numbers on screen, and spends the rest on the product live.
- Meta tooling is shown in three places: Muse Spark 1.1 for generation and as the claim-level verification agent, Muse Spark Open on Baseten for the open-weights comparison, and Muse Spark's vision input for the denial-letter photo feature. Muse Code is used during the build and documented here.
- The live scorecard in the product was dropped (depth, already covered by the README and the video) in favor of the denial-letter photo input (Nov 2): photograph a denial letter or an explanation of benefits, the model extracts the coverage question, the system answers it with citations and the verification trace. Decided by Alvaro on Oct 26.

**Reframe, Oct 26, 11 am: Recourse, a coverage denial appeal agent, not a policy QA assistant.** The anti-project list bans "Basic RAG Applications" and AI medical advice. A judge skimming "answers questions from healthcare policy PDFs with citations" would file it under both. The corpus and golden set stay (they are the dataset, and the evals need them); what the product does changes: a denial letter in, an investigated, verified verdict and a cited appeal letter out. Agentic (read, route, investigate, steelman, decide, draft, verify), two Meta modalities (vision and text, voice as a stretch), a concrete beneficiary (patients, caregivers, and billing staff who never appeal), and nothing about treatment. Alternatives considered: keep QA and add features (the one-line description still reads as RAG); pivot domains (throws away six days of human-verified labels); brainstorm first (30 minutes before kickoff for a decision the rubric already makes). Decided by Alvaro.

Rubric alignment: Impact 30 (the KFF numbers and a real job done), Meta tooling 25 (Muse Spark vision and generation as the agent, Muse Spark Open on Baseten, Muse Code during the build), Technical depth 20 (golden set, denial-case set, validated judge, verified citations), Demo 25 (a photo becomes a cited letter in under a minute, live on Modal and Vercel). Bonus prizes in reach: best agentic use case, best build on open-weight models.

Stretch features in priority order, built only if the core lands: steelman pass (kept in the core, one call), dual-eligible side by side, voice intake with Muse Voice Transcribe, save the letter as a file.

Division of labor: Claude owns the agent, the API, the evals, and the documents. Alvaro owns the front end (Next.js with the Impeccable design skill), the local runs, the labeling, the deploys, and the video.

**Oct 26, 12:05 pm: retrieval eval reproduced on Alvaro's Windows machine** (commit cfe3365, `results/hybrid.json` and `results/hybrid-rerank.json`): hybrid 0.5899@5 and 0.6835@10, MiniLM-20 reranked 0.6115@5 and 0.7122@10, identical to the Linux build box to four decimals on the same 139 rows. Latency on his CPU: 15 ms hybrid, 415 ms reranked at p50. The five documents the build box cannot download (fl-24, hipaa-01 to 04) still need local extraction for the 150-row numbers.


**Oct 26, 1:30 to 3:30 pm: first product code, inside the event window.** The kickoff at noon opened the building period, so the intake screen and the case intake endpoints were built the same afternoon (the README Timeline says so). Decisions made while building, all by Claude under the brief and open for Alvaro's review:
- Model id: `muse-spark-1.3` on `https://api.meta.ai/v1` (checked Oct 26 against the Meta Model API page; the "1.1" in the two entries above was written before that check and stands as the record of the morning).
- Two modes in the screen, `fixture` (default, no network, "Sample case" tag) and `live`, chosen by `NEXT_PUBLIC_INTAKE_MODE`; the API has the same split (`FixtureExtractor` when no model env is set). So the whole flow runs on a laptop with no key, and the first Muse Spark call changes no code.
- One error contract for both sides: `{"detail": {"code", "message"}}`, six intake codes, plus `bad_request`, `not_found`, `wrong_status`, `invalid_field`. A cheap keyword scope check runs before any model call; the model classification can return the same two codes.
- File type from the first bytes, never from the declared content type; 10 MB cap; text 200 to 6,000 characters on both sides.
- PATCH sets an edited cell to confidence `high` with `edited: true`; `null` clears a non-enum field (the person says the letter does not state it) and is refused on the two enum fields, which use `unknown`.
- `complete_parts` tries `json_schema` (strict), then `json_object`, then no `response_format`, so an endpoint that rejects a mode degrades instead of failing. PDF goes to the model as a `file` part first and falls back to `pdftotext` text if the endpoint rejects it.
- Cases are in memory for now. The store has four methods so a file or database store can replace it without touching the routes.
- Built but not live-tested, because no key exists: every request shape against the real Meta endpoint, whether Muse Spark honours strict `json_schema`, and the real cost and latency. `python -m policyqa.cli smoke` is the first command once the key exists.

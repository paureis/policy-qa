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

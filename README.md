# Policy Document QA with citations

Answers coverage and policy questions from public healthcare regulation PDFs, with a citation to the document and page for every claim, and says "not covered" when the corpus does not answer. Built for the Meta Global AI Developer Hackathon (indie track, Oct 26 to Nov 4, 2026).

The point of the project is not the demo. It is that every change is measured against a human-verified golden set before it ships.

## What is here

| Piece | Status |
|---|---|
| Corpus: 64 public PDFs (30 Florida Medicaid, 30 federal Medicare and Medicaid, 4 HIPAA), 2,589 pages | done, `corpus/manifest.csv`, `corpus/fetch.sh` |
| Golden set: 160 questions, six types, every document covered, LLM-drafted and human-verified | done, `golden/golden.csv` |
| Ingestion and page-level chunking | done |
| Hybrid retrieval (BM25 + bge-small embeddings, RRF) with a bge cross-encoder reranker | done |
| Retrieval recall scored against the golden set | done, `results/` |
| Generation with enforced citations (any OpenAI-compatible host for a Meta open-weights model) | code done, waiting on hackathon credits |
| Answer accuracy and faithfulness via Claude as judge; judge validated against 50 human verdicts | harness done, validation pending |
| Abstention on unanswerable questions, and forced abstention when no citation survives | done in the harness |
| Tracing, cost per query, p95 latency | cost and latency per query reported; tracing next |

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

Claude then grades each answer against the human-written gold answer (correct, partially correct, incorrect, abstained) and against the cited passages (supported, partially supported, unsupported). The report gives accuracy by question type, the supported rate, abstention on the 10 unanswerable rows, false abstention on answerable rows, citation validity, tokens and cost per query for generation and for the judge, and p50 and p95 latency. The judge's verdicts on the 50-row judge subset are compared with independent human verdicts before any accuracy number is quoted.

## How retrieval is scored

A golden row is a hit at k when one of the top-k chunks holds the row's `gold_quote`: whitespace-normalized, word 4-gram overlap of at least 0.8. Multi-document rows need every quote found (`all@k`); `any@k` is reported alongside. Unanswerable rows are not scored here; they are scored by the abstention check in the generation harness.

The report also gives `doc@k` (right document, any page) and `page@k` (right document and page), which separate "found the wrong document" from "found the right page but the wrong window".

Results live in `results/<run>.json` with the full config and a per-row record, so two runs can be diffed row by row.

## Design notes

- Chunks never cross a page. A citation is (document, page), and a chunk that spans pages cannot be cited honestly.
- Page text comes from `pdftotext -layout`, the same tool the golden quotes were copied from, so a quote the verifier found is found again in the chunk.
- BM25 and dense lists are fused with reciprocal rank fusion. Their scores live on different scales and RRF needs no tuning.
- Local open models only for retrieval (bge-small-en-v1.5, bge-reranker-base). An index rebuild costs nothing and needs no key.

Decisions with reasons are in `DECISIONS.md` (to be written as they are made).

## License

MIT. The corpus documents are public US federal and Florida government publications; see `corpus/manifest.csv` for the source URL of each.

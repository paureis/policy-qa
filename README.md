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
| Generation on a Meta open-weights model with enforced citations | next |
| Answer accuracy and faithfulness via an LLM judge, judge validated against 50 human verdicts | next |
| Abstention on unanswerable questions | next |
| Tracing, cost per query, p95 latency | next |

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

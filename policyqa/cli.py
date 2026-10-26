"""Command line: python -m policyqa.cli <command> [options]

  ingest   PDFs -> data/text/<id>/pNNN.txt
  chunk    page text -> data/chunks.jsonl
  embed    chunks -> data/dense.npy
  search   one query, prints the top hits with citations
  eval     recall against golden/golden.csv, writes results/<name>.json
  answer   one question end to end: retrieve, generate, enforce citations
  eval-answers  retrieve + generate + judge over the golden set, writes results/answers-<name>.json
"""
import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(prog="policyqa")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ingest")
    a.add_argument("--pdfs", type=Path, required=True)
    a.add_argument("--text", type=Path, default=ROOT / "data/text")
    a.add_argument("--manifest", type=Path, default=ROOT / "corpus/manifest.csv")

    c = sub.add_parser("chunk")
    c.add_argument("--text", type=Path, default=ROOT / "data/text")
    c.add_argument("--out", type=Path, default=ROOT / "data/chunks.jsonl")
    c.add_argument("--manifest", type=Path, default=ROOT / "corpus/manifest.csv")
    c.add_argument("--size", type=int, default=300)
    c.add_argument("--overlap", type=int, default=60)

    e = sub.add_parser("embed")
    e.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
    e.add_argument("--out", type=Path, default=ROOT / "data/dense.npy")
    e.add_argument("--model", default=None)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
    s.add_argument("--dense", type=Path, default=ROOT / "data/dense.npy")
    s.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    s.add_argument("--rerank", action="store_true")
    s.add_argument("--rerank-model", default=None)
    s.add_argument("-k", type=int, default=5)

    v = sub.add_parser("eval")
    v.add_argument("--golden", type=Path, default=ROOT / "golden/golden.csv")
    v.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
    v.add_argument("--dense", type=Path, default=ROOT / "data/dense.npy")
    v.add_argument("--text", type=Path, default=ROOT / "data/text", help="used to detect documents missing locally")
    v.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    v.add_argument("--rerank", action="store_true")
    v.add_argument("--rerank-model", default=None, help="cross-encoder name; default BAAI/bge-reranker-base")
    v.add_argument("--candidates", type=int, default=40)
    v.add_argument("-k", type=int, default=10)
    v.add_argument("--name", default=None)

    def add_retrieval_args(p):
        p.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
        p.add_argument("--dense", type=Path, default=ROOT / "data/dense.npy")
        p.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
        p.add_argument("--rerank", action="store_true")
        p.add_argument("--rerank-model", default=None)
        p.add_argument("--candidates", type=int, default=40)
        p.add_argument("--provider", choices=["openai-compatible", "mock"], default="openai-compatible")
        p.add_argument("-k", type=int, default=5, help="passages shown to the model")

    an = sub.add_parser("answer")
    an.add_argument("question")
    add_retrieval_args(an)

    ea = sub.add_parser("eval-answers")
    add_retrieval_args(ea)
    ea.add_argument("--golden", type=Path, default=ROOT / "golden/golden.csv")
    ea.add_argument("--text", type=Path, default=ROOT / "data/text")
    ea.add_argument("--judge", choices=["claude", "mock", "none"], default="claude")
    ea.add_argument("--judge-model", default=None)
    ea.add_argument("--judge-subset", action="store_true", help="only the 50 rows marked judge_subset=1")
    ea.add_argument("--limit", type=int, default=None)
    ea.add_argument("--name", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "ingest":
        from .ingest import ingest

        rep = ingest(args.manifest, args.pdfs, args.text)
        print(json.dumps(rep, indent=2))
    elif args.cmd == "chunk":
        from .chunk import chunk_corpus

        rep = chunk_corpus(args.manifest, args.text, args.out, args.size, args.overlap)
        print(json.dumps(rep))
    elif args.cmd == "embed":
        from .index import build_dense, EMBED_MODEL

        t = time.perf_counter()
        rep = build_dense(args.chunks, args.out, args.model or EMBED_MODEL)
        rep["seconds"] = round(time.perf_counter() - t, 1)
        print(json.dumps(rep))
    elif args.cmd == "search":
        from .index import Index
        from .retrieve import Retriever, RERANK_MODEL

        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=args.rerank, rerank_model=args.rerank_model or RERANK_MODEL)
        for h in r.search(args.query, k=args.k):
            c = h.chunk
            print(f"[{h.score:.4f}] {c['doc_id']} p{c['page']}  {c['title'][:70]}")
            print("   " + c["text"][:300].replace("\n", " ") + "\n")
    elif args.cmd == "eval":
        from .index import Index
        from .retrieve import Retriever, RERANK_MODEL
        from .eval_retrieval import load_golden, evaluate, write_report

        present = {p.name for p in args.text.iterdir() if p.is_dir()} if args.text.exists() else None
        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=args.rerank, rerank_model=args.rerank_model or RERANK_MODEL)
        r_search = r.search
        r.search = lambda q, k=10: r_search(q, k=k, candidates=args.candidates)
        golden = load_golden(args.golden)
        res = evaluate(golden, r, k=args.k, present_docs=present)
        name = args.name or f"{args.mode}{'-rerank' if args.rerank else ''}"
        chunk_meta = {}
        config = {"mode": args.mode, "rerank": args.rerank, "rerank_model": (args.rerank_model or RERANK_MODEL) if args.rerank else None, "candidates": args.candidates, "k": args.k, "chunks": str(args.chunks), "golden": str(args.golden)}
        write_report(res, ROOT / "results" / f"{name}.json", config)
        print(json.dumps(res["summary"], indent=2))
        print(f"wrote results/{name}.json")
    elif args.cmd in ("answer", "eval-answers"):
        from .index import Index
        from .retrieve import Retriever, RERANK_MODEL
        from .generate import Provider, MockProvider, answer_question

        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=args.rerank, rerank_model=args.rerank_model or RERANK_MODEL)
        r_search = r.search
        r.search = lambda q, k=5: r_search(q, k=k, candidates=args.candidates)
        provider = MockProvider() if args.provider == "mock" else Provider()
        if args.cmd == "answer":
            a = answer_question(args.question, r.search(args.question, k=args.k), provider)
            print(a.answer)
            for c in a.citations:
                print(f"  [{c.passage}] {c.doc_id} p{c.page}: \"{c.quote[:160]}\"")
            print(f"  ({a.model}, {a.input_tokens} in / {a.output_tokens} out, ${a.cost_usd}, {a.latency_ms} ms, dropped {a.citations_dropped} of {a.citations_proposed} citations{', forced abstain' if a.forced_abstain else ''})")
            if a.error:
                print("  error:", a.error)
        else:
            from .eval_retrieval import load_golden
            from .eval_answers import run, summarize, write_results
            from .judge import Judge, MockJudge, JUDGE_MODEL

            judge = None if args.judge == "none" else (MockJudge() if args.judge == "mock" else Judge(args.judge_model or JUDGE_MODEL))
            present = {p.name for p in args.text.iterdir() if p.is_dir()} if args.text.exists() else None
            golden = load_golden(args.golden)
            done = []

            def progress(rec):
                done.append(rec)
                if len(done) % 10 == 0:
                    print(f"  {len(done)} rows", flush=True)

            res = run(golden, r, provider, judge, k=args.k, present_docs=present, limit=args.limit, judge_subset_only=args.judge_subset, on_row=progress)
            summary = summarize(res)
            name = args.name or f"{args.provider}-{args.judge}"
            config = {"mode": args.mode, "rerank": args.rerank, "rerank_model": (args.rerank_model or RERANK_MODEL) if args.rerank else None, "candidates": args.candidates, "k": args.k, "provider": args.provider, "model": getattr(provider, "model", None), "judge": args.judge, "judge_model": getattr(judge, "model", None), "judge_subset_only": args.judge_subset, "limit": args.limit}
            write_results(res, summary, ROOT / "results" / f"answers-{name}.json", config)
            print(json.dumps(summary, indent=2))
            print(f"wrote results/answers-{name}.json")


if __name__ == "__main__":
    main()

"""Command line: python -m policyqa.cli <command> [options]

  ingest   PDFs -> data/text/<id>/pNNN.txt
  chunk    page text -> data/chunks.jsonl
  embed    chunks -> data/dense.npy
  search   one query, prints the top hits with citations
  eval     recall against golden/golden.csv, writes results/<name>.json
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
    s.add_argument("-k", type=int, default=5)

    v = sub.add_parser("eval")
    v.add_argument("--golden", type=Path, default=ROOT / "golden/golden.csv")
    v.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
    v.add_argument("--dense", type=Path, default=ROOT / "data/dense.npy")
    v.add_argument("--text", type=Path, default=ROOT / "data/text", help="used to detect documents missing locally")
    v.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    v.add_argument("--rerank", action="store_true")
    v.add_argument("--candidates", type=int, default=40)
    v.add_argument("-k", type=int, default=10)
    v.add_argument("--name", default=None)

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
        from .retrieve import Retriever

        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=args.rerank)
        for h in r.search(args.query, k=args.k):
            c = h.chunk
            print(f"[{h.score:.4f}] {c['doc_id']} p{c['page']}  {c['title'][:70]}")
            print("   " + c["text"][:300].replace("\n", " ") + "\n")
    elif args.cmd == "eval":
        from .index import Index
        from .retrieve import Retriever
        from .eval_retrieval import load_golden, evaluate, write_report

        present = {p.name for p in args.text.iterdir() if p.is_dir()} if args.text.exists() else None
        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=args.rerank)
        r_search = r.search
        r.search = lambda q, k=10: r_search(q, k=k, candidates=args.candidates)
        golden = load_golden(args.golden)
        res = evaluate(golden, r, k=args.k, present_docs=present)
        name = args.name or f"{args.mode}{'-rerank' if args.rerank else ''}"
        chunk_meta = {}
        config = {"mode": args.mode, "rerank": args.rerank, "candidates": args.candidates, "k": args.k, "chunks": str(args.chunks), "golden": str(args.golden)}
        write_report(res, ROOT / "results" / f"{name}.json", config)
        print(json.dumps(res["summary"], indent=2))
        print(f"wrote results/{name}.json")


if __name__ == "__main__":
    main()

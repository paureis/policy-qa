"""Command line: python -m policyqa.cli <command> [options]

  ingest   PDFs -> data/text/<id>/pNNN.txt
  chunk    page text -> data/chunks.jsonl
  embed    chunks -> data/dense.npy
  search   one query, prints the top hits with citations
  eval     recall against golden/golden.csv, writes results/<name>.json
  answer   one question end to end: retrieve, generate, enforce citations
  eval-answers  retrieve + generate + judge over the golden set, writes results/answers-<name>.json
  export-review  judge-subset rows of an answers file -> JSON docs for the Judge Validation Review page
  judge-agreement  graded review docs -> results/judge-agreement-<run>.json
  smoke    one tiny chat request through the configured model; prints model, latency, tokens, cost, reply
  case-evals  the 30 denial letters in cases/ through the API's chain; verdict accuracy, refusal,
              letter verification, cost and time -> results/case-evals-<date>.json and .md
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


SMOKE_ENV = ("POLICYQA_LLM_BASE_URL", "POLICYQA_LLM_MODEL", "POLICYQA_LLM_API_KEY")


def smoke(provider=None, raw: bool = False, effort: str | None = None) -> int:
    """Run the moment the model key exists. Returns the exit code. `raw` prints the full response JSON;
    `effort` sends reasoning_effort for this one request (to see whether the endpoint accepts it)."""
    if provider is None:
        missing = [k for k in SMOKE_ENV if not os.environ.get(k)]
        if missing:
            print("Not configured. Set these variables (see .env.example): " + ", ".join(missing))
            return 1
        from .generate import Provider

        provider = Provider(reasoning_effort=effort)
    t = time.perf_counter()
    try:
        text, n_in, n_out = provider.complete_parts("You are a connectivity check.", [{"type": "text", "text": "Reply with the single word: ready"}], max_tokens=200)
    except Exception as e:  # noqa: BLE001 - show the failure, that is the point of the command
        print(f"FAILED after {(time.perf_counter() - t) * 1000:.0f} ms: {type(e).__name__}: {e}")
        return 1
    ms = (time.perf_counter() - t) * 1000
    print(f"model:   {provider.model}")
    print(f"latency: {ms:.0f} ms")
    print(f"tokens:  {n_in} in / {n_out} out")
    print(f"cost:    ${provider.cost(n_in, n_out)}")
    details = ((getattr(provider, "last_response", None) or {}).get("usage") or {}).get("completion_tokens_details") or {}
    if details.get("reasoning_tokens") is not None:
        print(f"reasoning tokens: {details.get('reasoning_tokens')}" + (f" (reasoning_effort={provider.reasoning_effort})" if getattr(provider, "reasoning_effort", None) else ""))
    print(f"reply:   {text.strip()}")
    if not text.strip():
        print("note:    empty content; a reasoning model may have spent the tokens on thinking. Run with --raw to see the full response.")
    if raw and getattr(provider, "last_response", None) is not None:
        print(json.dumps(provider.last_response, indent=2))
    return 0


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
        p.add_argument("--no-rerank", action="store_true", help="skip the reranker (default: MiniLM-L-6 over 20 candidates)")
        p.add_argument("--rerank-model", default=None, help="cross-encoder name; default cross-encoder/ms-marco-MiniLM-L-6-v2")
        p.add_argument("--candidates", type=int, default=20)
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
    ea.add_argument("--traces", type=Path, default=ROOT / "data/traces.jsonl", help="JSONL trace log; pass an empty string to disable")

    jd = sub.add_parser("judge-answers", help="grade a saved answers file (from eval-answers --judge none) with the Claude or mock judge")
    jd.add_argument("answers", type=Path, help="results/answers-<name>.json")
    jd.add_argument("--judge", choices=["claude", "mock"], default="claude")
    jd.add_argument("--judge-model", default=None)
    jd.add_argument("--golden", type=Path, default=ROOT / "golden/golden.csv")
    jd.add_argument("--chunks", type=Path, default=ROOT / "data/chunks.jsonl")
    jd.add_argument("--out", type=Path, default=None, help="default: <answers stem>-judged.json beside the input")
    jd.add_argument("--ids", default=None, help="comma list of row ids to judge")
    jd.add_argument("--rejudge", action="store_true", help="grade rows that already carry a verdict")

    xr = sub.add_parser("export-review")
    xr.add_argument("answers", type=Path, help="results/answers-<name>.json")
    xr.add_argument("--run", required=True, help="run label shown on the page, e.g. llama70b-oct28")
    xr.add_argument("--out", type=Path, default=None, help="default review/export/<run>/")
    xr.add_argument("--golden", type=Path, default=ROOT / "golden/golden.csv")
    xr.add_argument("--all-rows", action="store_true", help="export every row, not only the judge subset")

    ja = sub.add_parser("judge-agreement")
    ja.add_argument("docs", type=Path, help="directory of graded review documents")
    ja.add_argument("--run", required=True)

    sm = sub.add_parser("smoke", help="one tiny request through POLICYQA_LLM_*; exits 1 when unset or failing")
    sm.add_argument("--raw", action="store_true", help="print the full response JSON")
    sm.add_argument("--effort", default=None, help="send reasoning_effort (low, medium, high) for this request")

    ce = sub.add_parser("case-evals", help="denial-case evaluation over cases/cases.csv (live when POLICYQA_LLM_* are set)")
    ce.add_argument("--cases", type=Path, default=ROOT / "cases/cases.csv")
    ce.add_argument("--letters", type=Path, default=ROOT / "cases/letters")
    ce.add_argument("--ids", default=None, help="comma list of case ids, e.g. dc-001,dc-011")
    ce.add_argument("--limit", type=int, default=None, help="first N cases (1 or more); leave it out to run every case")
    ce.add_argument("--concurrency", type=int, default=3)
    ce.add_argument("--out", type=Path, default=None, help="default results/case-evals-<YYYY-MM-DD>.json")
    ce.add_argument("--md", type=Path, default=None, help="default results/case-evals-<YYYY-MM-DD>.md")
    ce.add_argument("--no-critic", action="store_true", help="skip the letter critic (RECOURSE_CRITIC_ROUNDS=0 for this run)")

    args = ap.parse_args(argv)

    if args.cmd == "smoke":
        sys.exit(smoke(raw=args.raw, effort=args.effort))

    if args.cmd == "ingest":
        from .ingest import ingest

        rep = ingest(args.manifest, args.pdfs, args.text)
        print(json.dumps(rep, indent=2))
    elif args.cmd == "case-evals":
        from datetime import date

        from .case_evals import run_evals, write_outputs

        if args.limit is not None and args.limit < 1:
            ap.error("--limit must be 1 or more; leave it out to run every case")
        today = date.today().isoformat()
        out = args.out or ROOT / "results" / f"case-evals-{today}.json"
        md = args.md or ROOT / "results" / f"case-evals-{today}.md"
        ids = [x.strip() for x in args.ids.split(",") if x.strip()] if args.ids else None

        def progress(r):
            got = r["got"] or (f"refused ({r['refused']})" if r["refused"] else "error")
            print(f"  {r['id']}: intended {r['intended']}, got {got}, {'ok' if r['correct'] else 'WRONG'}, ${r['cost_usd']}, {r['seconds']} s" + (f", {r['error']}" if r["error"] else ""), flush=True)

        res = run_evals(cases_path=args.cases, letters_dir=args.letters, ids=ids, limit=args.limit, concurrency=args.concurrency, critic=not args.no_critic, on_row=progress)
        write_outputs(res, out, md)
        s = res["summary"]
        print(json.dumps({k: s[k] for k in ("n", "correct", "accuracy", "refusal_correct", "letters", "cost_usd", "seconds")}, indent=2))
        print(f"wrote {out} and {md}")
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
        from .retrieve import Retriever, ANSWER_RERANK_MODEL
        from .generate import Provider, MockProvider, answer_question

        rerank = not args.no_rerank
        rerank_model = args.rerank_model or ANSWER_RERANK_MODEL
        r = Retriever(Index(args.chunks, args.dense), mode=args.mode, rerank=rerank, rerank_model=rerank_model)
        r_search = r.search
        r.search = lambda q, k=5, trace=None: r_search(q, k=k, candidates=args.candidates, trace=trace)
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

            res = run(golden, r, provider, judge, k=args.k, present_docs=present, limit=args.limit, judge_subset_only=args.judge_subset, on_row=progress, trace_path=(args.traces or None))
            summary = summarize(res)
            name = args.name or f"{args.provider}-{args.judge}"
            config = {"mode": args.mode, "rerank": rerank, "rerank_model": rerank_model if rerank else None, "candidates": args.candidates, "k": args.k, "provider": args.provider, "model": getattr(provider, "model", None), "judge": args.judge, "judge_model": getattr(judge, "model", None), "judge_subset_only": args.judge_subset, "limit": args.limit}
            write_results(res, summary, ROOT / "results" / f"answers-{name}.json", config)
            print(json.dumps(summary, indent=2))
            print(f"wrote results/answers-{name}.json")
    elif args.cmd == "judge-answers":
        from .judge import JUDGE_MODEL, Judge, MockJudge
        from .judge_answers import judge_file

        judge = MockJudge() if args.judge == "mock" else Judge(args.judge_model or JUDGE_MODEL)
        out = args.out or args.answers.with_name(args.answers.stem + "-judged.json")
        ids = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
        done = []

        def progress(row):
            done.append(row)
            if len(done) % 10 == 0:
                print(f"  {len(done)} rows judged", flush=True)

        rep = judge_file(args.answers, args.golden, args.chunks, judge, out, only_ids=ids, rejudge=args.rejudge, on_row=progress)
        print(json.dumps(rep, indent=2))
    elif args.cmd == "export-review":
        from .review_sync import export

        out = args.out or (ROOT / "review/export" / args.run)
        n = export(args.answers, args.golden, out, args.run, judge_subset_only=not args.all_rows)
        print(f"wrote {n} documents to {out}")
    elif args.cmd == "judge-agreement":
        from .review_sync import agreement

        rep = agreement(args.docs, args.run)
        path = ROOT / "results" / f"judge-agreement-{args.run}.json"
        path.write_text(json.dumps(rep, indent=2))
        print(json.dumps({k: v for k, v in rep.items() if k != "disagreements"}, indent=2))
        print(f"{len(rep['disagreements'])} disagreements; wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

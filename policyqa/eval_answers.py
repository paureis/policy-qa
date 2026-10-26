"""End-to-end evaluation: retrieve, answer, enforce citations, judge, report.

Per golden row the record holds the system answer, the kept and dropped
citations, the judge verdict, tokens, cost, and latency. The summary reports:

- accuracy: correct / partially_correct / incorrect rates on answerable rows
- faithfulness: supported rate on answered rows
- abstention: on `none` rows, did the system abstain (recall); on answerable
  rows, how often it abstained anyway (false abstention)
- citation validity: proposed vs kept
- cost per query (generation and judge separately) and p50/p95 latency
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from .generate import answer_question
from .retrieve import Retriever


def _pct(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _p(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(q * (len(s) - 1)))], 1)


def run(golden: list[dict], retriever: Retriever, provider, judge, k: int = 5, present_docs: set | None = None, limit: int | None = None, judge_subset_only: bool = False, on_row=None) -> dict:
    rows = []
    skipped = []
    t0 = time.perf_counter()
    for row in golden:
        if judge_subset_only and row.get("judge_subset") != "1":
            continue
        docs = [d.strip() for d in (row.get("gold_doc_ids") or "").split(";") if d.strip()]
        if present_docs is not None and docs and not all(d in present_docs for d in docs):
            skipped.append({"id": row["id"], "reason": "document missing here"})
            continue
        hits = retriever.search(row["question"], k=k)
        ans = answer_question(row["question"], hits, provider)
        cited_tags = {c.passage for c in ans.citations}
        cited = [p for p in ans.passages if p["tag"] in cited_tags]
        v = judge.grade(row["question"], row["answer"], row["gold_quote"], ans.answer, cited) if judge else None
        rec = {
            "id": row["id"],
            "type": row["type"],
            "difficulty": row.get("difficulty", ""),
            "judge_subset": row.get("judge_subset") == "1",
            "question": row["question"],
            "gold_answer": row["answer"],
            "gold_doc_ids": docs,
            "answer": ans.to_dict(),
            "cited_docs": sorted({c.doc_id for c in ans.citations}),
            "cited_gold_doc": any(c.doc_id in docs for c in ans.citations),
            "verdict": v.__dict__ if v else None,
        }
        rows.append(rec)
        if on_row:
            on_row(rec)
        if limit and len(rows) >= limit:
            break
    return {"rows": rows, "skipped": skipped, "wall_s": round(time.perf_counter() - t0, 1)}


def summarize(result: dict) -> dict:
    rows = result["rows"]
    answerable = [r for r in rows if r["type"] != "none"]
    none_rows = [r for r in rows if r["type"] == "none"]
    answered = [r for r in answerable if not r["answer"]["abstained"]]
    acc = Counter(r["verdict"]["accuracy"] for r in answerable if r["verdict"])
    faith = Counter(r["verdict"]["faithfulness"] for r in answered if r["verdict"])
    gen_cost = [r["answer"]["cost_usd"] for r in rows]
    judge_cost = [r["verdict"]["cost_usd"] for r in rows if r["verdict"]]
    lat = [r["answer"]["latency_ms"] for r in rows]
    proposed = sum(r["answer"]["citations_proposed"] for r in rows)
    dropped = sum(r["answer"]["citations_dropped"] for r in rows)
    s = {
        "rows": len(rows),
        "skipped": len(result["skipped"]),
        "answerable": len(answerable),
        "accuracy": {
            "correct": _pct(acc["correct"], len(answerable)),
            "partially_correct": _pct(acc["partially_correct"], len(answerable)),
            "incorrect": _pct(acc["incorrect"], len(answerable)),
            "abstained": _pct(acc["abstained"], len(answerable)),
        },
        "faithfulness_supported": _pct(faith["supported"], len(answered)),
        "faithfulness_counts": dict(faith),
        "abstention": {
            "none_rows": len(none_rows),
            "abstained_on_none": _pct(sum(1 for r in none_rows if r["answer"]["abstained"]), len(none_rows)),
            "false_abstain_on_answerable": _pct(sum(1 for r in answerable if r["answer"]["abstained"]), len(answerable)),
            "forced_abstain": sum(1 for r in rows if r["answer"]["forced_abstain"]),
        },
        "citations": {"proposed": proposed, "kept": proposed - dropped, "valid_rate": _pct(proposed - dropped, proposed), "cited_gold_doc_rate": _pct(sum(1 for r in answered if r["cited_gold_doc"]), len(answered))},
        "cost_usd": {"generation_per_query": round(sum(gen_cost) / len(rows), 6) if rows else None, "judge_per_item": round(sum(judge_cost) / len(judge_cost), 6) if judge_cost else None, "generation_total": round(sum(gen_cost), 4), "judge_total": round(sum(judge_cost), 4)},
        "tokens_per_query": {"input": round(sum(r["answer"]["input_tokens"] for r in rows) / len(rows)) if rows else None, "output": round(sum(r["answer"]["output_tokens"] for r in rows) / len(rows)) if rows else None},
        "latency_ms": {"p50": _p(lat, 0.5), "p95": _p(lat, 0.95)},
        "errors": sum(1 for r in rows if r["answer"]["error"]) + sum(1 for r in rows if r["verdict"] and r["verdict"]["error"]),
        "wall_s": result["wall_s"],
    }
    by_type = {}
    for t in sorted({r["type"] for r in answerable}):
        rs = [r for r in answerable if r["type"] == t]
        c = Counter(r["verdict"]["accuracy"] for r in rs if r["verdict"])
        by_type[t] = {"n": len(rs), "correct": _pct(c["correct"], len(rs)), "incorrect": _pct(c["incorrect"], len(rs))}
    s["by_type"] = by_type
    return s


def write_results(result: dict, summary: dict, path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"config": config, "summary": summary, **result}, indent=2))

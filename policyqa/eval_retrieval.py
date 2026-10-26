"""Retrieval recall against the golden set.

A golden row is a hit at k when some chunk in the top k holds its gold_quote
(whitespace-normalized, word 4-gram overlap at least 0.8). Multi-document rows
have two quotes joined by " || "; the row counts as a hit when every quote is
found, and "any" recall is reported alongside. Rows of type `none` have no
quote and are skipped here; they are scored by the abstention check later.

Also reported, because they tell you where retrieval fails:
- doc hit: the right document appears in the top k (any page)
- page hit: the right (doc, page) appears in the top k
- MRR of the first chunk that holds the quote
"""
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

from .retrieve import Retriever
from .textnorm import quote_overlap

THRESHOLD = 0.8


def load_golden(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path, encoding="utf-8")))


def _split(s: str, sep: str = ";") -> list[str]:
    return [x.strip() for x in (s or "").split(sep) if x.strip()]


def score_row(row: dict, hits: list, ks=(5, 10)) -> dict:
    quotes = [q.strip() for q in (row.get("gold_quote") or "").split("||") if q.strip()]
    docs = _split(row.get("gold_doc_ids"))
    pages = _split(row.get("gold_pages"))
    gold_pairs = set(zip(docs, [int(p) for p in pages])) if len(docs) == len(pages) else set()
    first_rank = {i: None for i in range(len(quotes))}
    doc_rank = None
    page_rank = None
    for rank, h in enumerate(hits, start=1):
        c = h.chunk
        if doc_rank is None and c["doc_id"] in docs:
            doc_rank = rank
        if page_rank is None and (c["doc_id"], c["page"]) in gold_pairs:
            page_rank = rank
        for i, q in enumerate(quotes):
            if first_rank[i] is None and quote_overlap(q, c["text"]) >= THRESHOLD:
                first_rank[i] = rank
    ranks = [r for r in first_rank.values() if r is not None]
    out = {"id": row["id"], "type": row["type"], "difficulty": row.get("difficulty", ""), "n_quotes": len(quotes)}
    for k in ks:
        out[f"all@{k}"] = int(len(ranks) == len(quotes) and all(r <= k for r in ranks))
        out[f"any@{k}"] = int(any(r <= k for r in ranks))
        out[f"doc@{k}"] = int(doc_rank is not None and doc_rank <= k)
        out[f"page@{k}"] = int(page_rank is not None and page_rank <= k)
    out["rr"] = (1.0 / min(ranks)) if ranks else 0.0
    out["first_rank"] = min(ranks) if ranks else None
    out["top1"] = hits[0].chunk["chunk_id"] if hits else None
    return out


def evaluate(golden: list[dict], retriever: Retriever, k: int = 10, present_docs: set | None = None) -> dict:
    per_row = []
    skipped = []
    t0 = time.perf_counter()
    latencies = []
    for row in golden:
        if row["type"] == "none":
            continue
        docs = _split(row.get("gold_doc_ids"))
        if present_docs is not None and not all(d in present_docs for d in docs):
            skipped.append({"id": row["id"], "reason": "document missing here", "docs": docs})
            continue
        t = time.perf_counter()
        hits = retriever.search(row["question"], k=k)
        latencies.append(time.perf_counter() - t)
        per_row.append(score_row(row, hits))
    n = len(per_row)
    summary = {"rows_scored": n, "rows_skipped": len(skipped), "k": k}
    for key in [f"all@5", f"all@10", f"any@5", f"any@10", f"doc@5", f"doc@10", f"page@5", f"page@10"]:
        summary[key] = round(sum(r[key] for r in per_row) / n, 4) if n else None
    summary["mrr"] = round(sum(r["rr"] for r in per_row) / n, 4) if n else None
    by_type = defaultdict(list)
    for r in per_row:
        by_type[r["type"]].append(r)
    summary["by_type"] = {
        t: {"n": len(rs), "all@5": round(sum(r["all@5"] for r in rs) / len(rs), 3), "all@10": round(sum(r["all@10"] for r in rs) / len(rs), 3)}
        for t, rs in sorted(by_type.items())
    }
    by_diff = defaultdict(list)
    for r in per_row:
        by_diff[r["difficulty"]].append(r)
    summary["by_difficulty"] = {
        d: {"n": len(rs), "all@5": round(sum(r["all@5"] for r in rs) / len(rs), 3), "all@10": round(sum(r["all@10"] for r in rs) / len(rs), 3)}
        for d, rs in sorted(by_diff.items())
    }
    if latencies:
        lat = sorted(latencies)
        summary["latency_ms"] = {"p50": round(1000 * lat[len(lat) // 2], 1), "p95": round(1000 * lat[int(0.95 * (len(lat) - 1))], 1)}
    summary["wall_s"] = round(time.perf_counter() - t0, 1)
    return {"summary": summary, "rows": per_row, "skipped": skipped}


def write_report(result: dict, path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"config": config, **result}
    path.write_text(json.dumps(payload, indent=2))

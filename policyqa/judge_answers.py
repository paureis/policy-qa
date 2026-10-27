"""Judge a saved answers file after the fact.

`eval-answers --judge none` records the generated answers without a judge (the Claude judge needs
ANTHROPIC_API_KEY, which a generation run may not have). `judge-answers` grades those rows later
with the same Judge.grade call the live harness uses, so nothing is generated twice:

    python -m policyqa.cli judge-answers results/answers-<name>.json --judge claude --out results/answers-<name>-judged.json

The cited passages are rebuilt from data/chunks.jsonl by chunk id (the answers file keeps only
tag, chunk_id, doc_id, page per passage), in the same shape generate.format_passages produces.
The gold quote comes from the golden CSV by row id. Rows that already carry a verdict are kept
unless --rejudge. The summary is recomputed and config.judge / judge_model are updated.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from .eval_answers import summarize


def load_chunks(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            out[c["chunk_id"]] = c
    return out


def load_gold_quotes(golden: Path) -> dict[str, str]:
    with golden.open(encoding="utf-8", newline="") as f:
        return {r["id"]: r.get("gold_quote", "") or "" for r in csv.DictReader(f)}


def cited_passages(answer: dict, chunks: dict[str, dict]) -> list[dict]:
    """The passages the answer cited, with their text, in the shape the judge saw during the live run."""
    tags = {c.get("passage") for c in answer.get("citations") or []}
    out = []
    for p in answer.get("passages") or []:
        if p.get("tag") not in tags:
            continue
        c = chunks.get(p.get("chunk_id"))
        if c is None:
            continue
        out.append({"tag": p["tag"], "chunk_id": c["chunk_id"], "doc_id": c["doc_id"], "page": c["page"], "title": c.get("title", ""), "jurisdiction": c.get("jurisdiction", ""), "text": c["text"]})
    return out


def judge_file(answers: Path, golden: Path, chunks_path: Path, judge, out: Path, only_ids: set[str] | None = None, rejudge: bool = False, on_row=None) -> dict:
    data = json.loads(Path(answers).read_text(encoding="utf-8"))
    chunks = load_chunks(Path(chunks_path))
    quotes = load_gold_quotes(Path(golden))
    judged = skipped = 0
    for row in data["rows"]:
        if only_ids is not None and row["id"] not in only_ids:
            continue
        if row.get("verdict") and not rejudge:
            skipped += 1
            continue
        ans = row["answer"]
        t = time.perf_counter()
        v = judge.grade(row["question"], row["gold_answer"], quotes.get(row["id"], ""), ans["answer"], cited_passages(ans, chunks))
        row["verdict"] = v.__dict__
        row.setdefault("stage_ms", {})["judge"] = round((time.perf_counter() - t) * 1000, 1)
        judged += 1
        if on_row:
            on_row(row)
    data["summary"] = summarize(data)
    cfg = data.setdefault("config", {})
    cfg["judge"] = getattr(judge, "model", "?") if getattr(judge, "model", None) == "mock" else "claude"
    cfg["judge_model"] = getattr(judge, "model", None)
    cfg["judged_after_the_fact"] = True
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"judged": judged, "skipped_already_judged": skipped, "out": str(out)}

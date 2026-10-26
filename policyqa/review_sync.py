"""Move model answers to the Judge Validation Review page and bring verdicts back.

export: results/answers-<run>.json -> one JSON document per judge-subset row,
        written to a directory, ready for the review page's `answers` collection
        (doc id "<run>--<gs-id>"). Claude loads them into the artifact database.
agreement: a directory of those documents after human grading -> agreement rate,
        Cohen's kappa, and a confusion matrix between the human and the judge,
        written to results/judge-agreement-<run>.json.

The human grades without seeing the judge's verdict; the page reveals it only
after the human verdict is saved.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ACC = ["correct", "partially_correct", "incorrect"]


def export(answers_path: Path, golden_path: Path, out_dir: Path, run: str, judge_subset_only: bool = True) -> int:
    data = json.loads(answers_path.read_text())
    gold = {r["id"]: r for r in csv.DictReader(open(golden_path, encoding="utf-8"))}
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for rec in data["rows"]:
        if judge_subset_only and not rec.get("judge_subset"):
            continue
        g = gold[rec["id"]]
        a = rec["answer"]
        titles = {p["chunk_id"]: p for p in a.get("passages", [])}
        doc = {
            "run": run,
            "id": rec["id"],
            "type": rec["type"],
            "difficulty": rec.get("difficulty", ""),
            "question": rec["question"],
            "gold_answer": g["answer"],
            "gold_quote": g["gold_quote"],
            "gold_src": " · ".join(f"{d.strip()} p.{p.strip()}" for d, p in zip(g["gold_doc_ids"].split(";"), g["gold_pages"].split(";")) if d.strip()),
            "answer": a["answer"],
            "abstained": a["abstained"],
            "forced_abstain": a["forced_abstain"],
            "citations": [{"doc_id": c["doc_id"], "page": c["page"], "quote": c["quote"]} for c in a["citations"]],
            "judge": {k: rec["verdict"][k] for k in ("accuracy", "faithfulness", "rationale")} if rec.get("verdict") else None,
            "model": a.get("model"),
        }
        (out_dir / f"{run}--{rec['id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        n += 1
    return n


def _judge_acc(doc: dict) -> str | None:
    j = doc.get("judge")
    if not j:
        return None
    if j["accuracy"] == "abstained":
        return "correct" if doc["type"] == "none" else "incorrect"
    return j["accuracy"]


def _kappa(pairs: list[tuple[str, str]], labels: list[str]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for h, j in pairs if h == j) / n
    hc, jc = Counter(h for h, _ in pairs), Counter(j for _, j in pairs)
    pe = sum(hc[l] * jc[l] for l in labels) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def agreement(docs_dir: Path, run: str) -> dict:
    docs = [json.loads(p.read_text()) for p in sorted(docs_dir.glob("*.json"))]
    docs = [d for d in docs if d.get("run") == run]
    graded = [d for d in docs if d.get("human_accuracy") and d.get("judge")]
    pairs = [(d["human_accuracy"], _judge_acc(d)) for d in graded]
    exact = sum(1 for h, j in pairs if h == j)
    # Collapsed: partially_correct counts with correct. A two-way view that is
    # often what a pass/fail gate needs.
    col = lambda x: "incorrect" if x == "incorrect" else "correct"
    pairs2 = [(col(h), col(j)) for h, j in pairs]
    conf = Counter((h, j) for h, j in pairs)
    fai = [(d["human_faithfulness"], d["judge"]["faithfulness"]) for d in graded if d.get("human_faithfulness") and not d.get("abstained")]
    out = {
        "run": run,
        "rows_in_subset": len(docs),
        "rows_graded": len(graded),
        "accuracy": {
            "exact_agreement": round(exact / len(pairs), 4) if pairs else None,
            "kappa_3way": _kappa(pairs, ACC),
            "collapsed_agreement": round(sum(1 for h, j in pairs2 if h == j) / len(pairs2), 4) if pairs2 else None,
            "kappa_2way": _kappa(pairs2, ["correct", "incorrect"]),
            "confusion_human_x_judge": {f"{h}|{j}": c for (h, j), c in sorted(conf.items())},
            "human_counts": dict(Counter(h for h, _ in pairs)),
            "judge_counts": dict(Counter(j for _, j in pairs)),
        },
        "faithfulness": {
            "rows": len(fai),
            "exact_agreement": round(sum(1 for h, j in fai if h == j) / len(fai), 4) if fai else None,
            "collapsed_agreement": round(sum(1 for h, j in fai if (h == "supported") == (j == "supported")) / len(fai), 4) if fai else None,
        },
        "disagreements": [
            {"id": d["id"], "type": d["type"], "human": d["human_accuracy"], "judge": _judge_acc(d), "note": d.get("human_note", ""), "judge_rationale": d["judge"].get("rationale", "")}
            for d in graded
            if d["human_accuracy"] != _judge_acc(d)
        ],
    }
    return out

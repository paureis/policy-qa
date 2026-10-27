"""judge-answers: grade a saved answers file after the fact (the judge needs a key the generation run did not)."""
import csv
import json

from policyqa.judge import MockJudge
from policyqa.judge_answers import judge_file


def _write(tmp_path):
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text(
        "\n".join(
            json.dumps(c)
            for c in [
                {"chunk_id": "fl-01:p8:0", "doc_id": "fl-01", "page": 8, "title": "General Policy", "jurisdiction": "Florida", "text": "Be necessary to protect life, to prevent significant illness. This requirement applies only to recipients age 21 years or older."},
                {"chunk_id": "fl-02:p3:0", "doc_id": "fl-02", "page": 3, "title": "Other", "jurisdiction": "Florida", "text": "Unrelated text."},
            ]
        ),
        encoding="utf-8",
    )
    golden = tmp_path / "golden.csv"
    with golden.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "answer", "gold_quote", "type", "judge_subset"])
        w.writeheader()
        w.writerow({"id": "gs-001", "question": "Does it apply to kids?", "answer": "No, only 21 and older.", "gold_quote": "This requirement applies only to recipients age 21 years or older.", "type": "fact", "judge_subset": "1"})
        w.writerow({"id": "gs-002", "question": "Is it covered?", "answer": "Not stated.", "gold_quote": "", "type": "none", "judge_subset": "1"})
    answers = tmp_path / "answers-live-none.json"
    answers.write_text(
        json.dumps(
            {
                "config": {"judge": "none", "judge_model": None},
                "summary": {},
                "rows": [
                    {
                        "id": "gs-001", "type": "fact", "judge_subset": True, "question": "Does it apply to kids?", "gold_answer": "No, only 21 and older.",
                        "stage_ms": {"generate": 10.0}, "cited_gold_doc": True,
                        "answer": {"answer": "This requirement applies only to recipients age 21 years or older.", "abstained": False, "forced_abstain": False, "citations_proposed": 1, "citations_dropped": 0, "model": "m", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.001, "latency_ms": 10.0, "raw": "", "error": None, "struck": [], 
                                   "citations": [{"passage": "P1", "quote": "applies only to recipients age 21 years or older", "doc_id": "fl-01", "page": 8}],
                                   "passages": [{"tag": "P1", "chunk_id": "fl-01:p8:0", "doc_id": "fl-01", "page": 8}, {"tag": "P2", "chunk_id": "fl-02:p3:0", "doc_id": "fl-02", "page": 3}]},
                        "verdict": None,
                    },
                    {
                        "id": "gs-002", "type": "none", "judge_subset": True, "question": "Is it covered?", "gold_answer": "Not stated.",
                        "stage_ms": {"generate": 10.0}, "cited_gold_doc": True,
                        "answer": {"answer": "Not covered by the documents provided.", "abstained": True, "forced_abstain": False, "citations_proposed": 0, "citations_dropped": 0, "model": "m", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.001, "latency_ms": 10.0, "raw": "", "error": None, "struck": [], "citations": [], "passages": []},
                        "verdict": None,
                    },
                ],
                "skipped": [],
                "wall_s": 1.0,
            }
        ),
        encoding="utf-8",
    )
    return chunks, golden, answers


def test_judges_every_unjudged_row_and_rewrites_the_file(tmp_path):
    chunks, golden, answers = _write(tmp_path)
    out = tmp_path / "answers-live-mock.json"
    rep = judge_file(answers, golden, chunks, MockJudge(), out)
    assert rep["judged"] == 2 and rep["skipped_already_judged"] == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    v1 = d["rows"][0]["verdict"]
    assert v1["accuracy"] == "correct" and v1["faithfulness"] == "supported" and v1["model"] == "mock"
    assert d["rows"][1]["verdict"]["accuracy"] == "abstained"
    assert d["config"]["judge"] == "mock" and d["config"]["judge_model"] == "mock"
    assert "accuracy" in d["summary"] or d["summary"]  # re-summarized, not empty
    assert d["rows"][0]["stage_ms"]["judge"] >= 0


def test_cited_passages_are_rebuilt_from_chunks(tmp_path, monkeypatch):
    chunks, golden, answers = _write(tmp_path)
    seen = {}

    class SpyJudge(MockJudge):
        def grade(self, question, gold_answer, gold_quote, system_answer, cited):
            seen["cited"] = cited
            seen["gold_quote"] = gold_quote
            return super().grade(question, gold_answer, gold_quote, system_answer, cited)

    judge_file(answers, golden, chunks, SpyJudge(), tmp_path / "o.json", only_ids={"gs-001"})
    assert [p["chunk_id"] for p in seen["cited"]] == ["fl-01:p8:0"]  # only the cited passage, with its text
    assert seen["cited"][0]["text"].startswith("Be necessary") and seen["cited"][0]["tag"] == "P1"
    assert seen["gold_quote"].startswith("This requirement")


def test_already_judged_rows_are_kept_unless_rejudge(tmp_path):
    chunks, golden, answers = _write(tmp_path)
    d = json.loads(answers.read_text(encoding="utf-8"))
    d["rows"][0]["verdict"] = {"accuracy": "incorrect", "faithfulness": "unsupported", "rationale": "old", "model": "old", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_ms": 0.0, "error": None}
    answers.write_text(json.dumps(d), encoding="utf-8")
    out = tmp_path / "o.json"
    rep = judge_file(answers, golden, chunks, MockJudge(), out)
    assert rep["judged"] == 1 and rep["skipped_already_judged"] == 1
    assert json.loads(out.read_text(encoding="utf-8"))["rows"][0]["verdict"]["model"] == "old"
    rep = judge_file(answers, golden, chunks, MockJudge(), out, rejudge=True)
    assert rep["judged"] == 2
    assert json.loads(out.read_text(encoding="utf-8"))["rows"][0]["verdict"]["model"] == "mock"


def test_cli_has_the_subcommand():
    from policyqa.cli import main

    import pytest

    with pytest.raises(SystemExit):
        main(["judge-answers", "--help"])

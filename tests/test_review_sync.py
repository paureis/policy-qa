import json

from policyqa.review_sync import agreement, _kappa


def test_kappa_perfect_and_chance():
    assert _kappa([("correct", "correct"), ("incorrect", "incorrect")], ["correct", "partially_correct", "incorrect"]) == 1.0
    assert _kappa([("correct", "incorrect"), ("incorrect", "correct")], ["correct", "partially_correct", "incorrect"]) == -1.0


def test_agreement_maps_judge_abstained_by_row_type(tmp_path):
    docs = [
        {"run": "r", "id": "gs-1", "type": "none", "abstained": True, "human_accuracy": "correct", "judge": {"accuracy": "abstained", "faithfulness": "no_citations", "rationale": ""}},
        {"run": "r", "id": "gs-2", "type": "fact", "abstained": True, "human_accuracy": "incorrect", "judge": {"accuracy": "abstained", "faithfulness": "no_citations", "rationale": ""}},
        {"run": "r", "id": "gs-3", "type": "fact", "abstained": False, "human_accuracy": "correct", "human_faithfulness": "supported", "judge": {"accuracy": "partially_correct", "faithfulness": "supported", "rationale": "x"}},
        {"run": "other", "id": "gs-4", "type": "fact", "human_accuracy": "correct", "judge": {"accuracy": "correct", "faithfulness": "supported", "rationale": ""}},
    ]
    for d in docs:
        (tmp_path / f"{d['run']}--{d['id']}.json").write_text(json.dumps(d))
    rep = agreement(tmp_path, "r")
    assert rep["rows_graded"] == 3
    assert rep["accuracy"]["exact_agreement"] == round(2 / 3, 4)
    assert rep["accuracy"]["collapsed_agreement"] == 1.0
    assert [d["id"] for d in rep["disagreements"]] == ["gs-3"]
    assert rep["faithfulness"]["rows"] == 1 and rep["faithfulness"]["exact_agreement"] == 1.0

"""Denial-case evaluation harness (policyqa/case_evals.py). No network: the chain runs on the
fixture providers the API uses when POLICYQA_LLM_* are unset (FixtureExtractor, FixtureInvestigator,
FixtureVerdict, FixtureLetter, FixtureCritic). The fixture verdict is always "inconsistent", so
dc-001 (inconsistent) is right and dc-002 (consistent) is wrong; dc-011 is refused by scope_check."""
import json
import os

import pytest

from policyqa import case_evals as ce


# ---- scoring ------------------------------------------------------------------


def test_exact_match_is_correct():
    assert ce.score("dc-001", "inconsistent", "inconsistent") is True


def test_mismatch_is_wrong():
    assert ce.score("dc-001", "inconsistent", "consistent") is False


def test_alternate_is_accepted_for_its_case():
    assert ce.score("dc-008", "inconsistent", "not_settled") is True
    assert ce.score("dc-020", "not_settled", "consistent") is True


def test_alternate_is_not_accepted_for_other_cases_or_other_outcomes():
    assert ce.score("dc-001", "inconsistent", "not_settled") is False
    assert ce.score("dc-007", "not_settled", "consistent") is False
    assert ce.score("dc-008", "inconsistent", "consistent") is False


def test_dc011_refused_as_out_of_scope_is_correct():
    assert ce.score("dc-011", "out_of_scope", None, refused="out_of_scope") is True


def test_dc011_with_a_verdict_is_wrong():
    assert ce.score("dc-011", "out_of_scope", "not_settled") is False
    assert ce.score("dc-011", "out_of_scope", "not_settled", refused="out_of_scope") is False


def test_dc011_refused_for_another_reason_is_wrong():
    assert ce.score("dc-011", "out_of_scope", None, refused="not_a_denial_letter") is False


def test_a_refused_ordinary_case_is_wrong():
    assert ce.score("dc-001", "inconsistent", None, refused="out_of_scope") is False


def test_error_row_is_wrong_and_listed():
    assert ce.score("dc-001", "inconsistent", "inconsistent", error="RuntimeError: boom") is False
    rows = [
        _row("dc-001", "inconsistent", "inconsistent", True),
        _row("dc-002", "consistent", None, False, error="RuntimeError: boom"),
    ]
    s = ce.summarize(rows)
    assert s["n"] == 2 and s["correct"] == 1 and s["accuracy"] == 0.5
    assert s["errors"] == [{"id": "dc-002", "error": "RuntimeError: boom"}]
    assert s["wrong"] == [{"id": "dc-002", "intended": "consistent", "got": None, "refused": None, "error": "RuntimeError: boom"}]


def test_summary_breakdowns_and_rates():
    rows = [
        _row("dc-001", "inconsistent", "inconsistent", True, letter={"applicable": True, "claims": 4, "verified": 3, "struck": 1}, cost=0.10, seconds=10.0,
             critique={"rounds": 1, "issues_found": 2, "issues_fixed": 2, "accepted": True, "skipped": False, "error": None}),
        _row("dc-002", "consistent", "inconsistent", False, program="medicare_b", jurisdiction="Federal", letter={"applicable": True, "claims": 6, "verified": 6, "struck": 0},
             cost=0.30, seconds=30.0, critique={"rounds": 1, "issues_found": 1, "issues_fixed": 0, "accepted": False, "skipped": False, "error": None}),
        _row("dc-011", "out_of_scope", None, True, refused="out_of_scope", cost=0.0, seconds=1.0),
    ]
    s = ce.summarize(rows)
    assert s["by_intended"]["inconsistent"] == {"n": 1, "correct": 1, "accuracy": 1.0}
    assert s["by_intended"]["consistent"] == {"n": 1, "correct": 0, "accuracy": 0.0}
    assert s["by_program"]["medicare_b"]["n"] == 1 and s["by_jurisdiction"]["Florida"]["n"] == 2
    assert s["refusal_correct"] is True
    assert s["letters"] == {"applicable": 2, "claims": 10, "verified": 9, "struck": 1, "verification_rate": 0.9, "struck_rate": 0.1}
    assert s["critic"]["reviewed"] == 2 and s["critic"]["accepted"] == 1
    assert s["cost_usd"]["total"] == 0.4 and s["cost_usd"]["p50"] == 0.1
    assert s["seconds"]["p50"] == 10.0
    assert s["confusion"]["consistent"]["inconsistent"] == 1


# ---- end to end on the fixture providers --------------------------------------


@pytest.fixture
def fixture_api(monkeypatch, tmp_path):
    pytest.importorskip("fastapi")
    import api.main as api_main

    for k in ("POLICYQA_LLM_BASE_URL", "POLICYQA_LLM_MODEL", "RECOURSE_CRITIC_ROUNDS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(api_main, "DATA", tmp_path / "no-index")
    monkeypatch.setattr(api_main, "FIXTURE_DELAY", 0)
    cached = (api_main.investigator, api_main.extractor, api_main.provider)  # tests may monkeypatch these names
    for f in cached:
        f.cache_clear()
    yield api_main
    for f in cached:
        f.cache_clear()


ROW_KEYS = {"id", "program", "jurisdiction", "trap", "demo", "intended", "got", "correct", "refused", "route_program",
            "route_reason", "stage_errors", "findings", "letter", "critique", "cost_usd", "stage_cost_usd", "seconds", "error"}


def test_three_cases_end_to_end_through_the_cli(fixture_api, tmp_path):
    from api.cases import STORE
    from policyqa import cli

    store_before = fixture_api.STORE
    n_before = len(STORE._cases)
    out, md = tmp_path / "evals.json", tmp_path / "evals.md"
    cli.main(["case-evals", "--ids", "dc-001,dc-002,dc-011", "--concurrency", "2", "--out", str(out), "--md", str(md)])

    data = json.loads(out.read_text(encoding="utf-8"))
    assert {"config", "summary", "rows"} <= set(data)
    assert {"date", "model", "reasoning_effort", "prices", "modes", "concurrency", "critic_rounds"} <= set(data["config"])
    assert data["config"]["concurrency"] == 2 and data["config"]["model"] == "fixture"
    rows = {r["id"]: r for r in data["rows"]}
    assert [r["id"] for r in data["rows"]] == ["dc-001", "dc-002", "dc-011"]
    assert all(ROW_KEYS <= set(r) for r in data["rows"])

    r1 = rows["dc-001"]
    assert r1["got"] == "inconsistent" and r1["correct"] is True and r1["error"] is None and r1["refused"] is None
    assert r1["route_program"] == "florida_medicaid_mma"  # the fixture extractor's card
    assert set(r1["findings"]) == {"supported", "not_settled", "unsupported", "error"} and r1["findings"]["supported"] > 0
    assert set(r1["letter"]) == {"applicable", "claims", "verified", "struck", "error"}
    assert r1["letter"]["applicable"] is True and r1["letter"]["claims"] > 0
    assert {"rounds", "issues_found", "issues_fixed", "accepted", "error"} <= set(r1["critique"])
    assert set(r1["stage_cost_usd"]) == {"intake", "investigation", "verdict", "letter", "critique"}
    assert r1["cost_usd"] == 0.0 and r1["seconds"] >= 0

    assert rows["dc-002"]["got"] == "inconsistent" and rows["dc-002"]["correct"] is False
    r11 = rows["dc-011"]
    assert r11["refused"] == "out_of_scope" and r11["got"] is None and r11["correct"] is True and r11["letter"] is None

    s = data["summary"]
    assert s["n"] == 3 and s["correct"] == 2 and s["refusal_correct"] is True
    assert s["wrong"] == [{"id": "dc-002", "intended": "consistent", "got": "inconsistent", "refused": None, "error": None}]
    for key in ("accuracy", "by_intended", "by_program", "by_jurisdiction", "letters", "critic", "cost_usd", "seconds", "errors", "confusion"):
        assert key in s

    text = md.read_text(encoding="utf-8")
    case_lines = [ln for ln in text.splitlines() if ln.startswith("| dc-")]
    assert len(case_lines) == 3
    assert "| dc-002 | consistent | inconsistent | no |" in text
    assert "Accuracy" in text

    # the run used its own memory store, and put the API's back
    assert fixture_api.STORE is store_before and len(STORE._cases) == n_before


def test_a_case_whose_chain_raises_is_recorded_and_the_run_continues(fixture_api):
    def chain(case_id, text):
        if case_id == "dc-002":
            raise RuntimeError("boom")
        return ce.api_chain(case_id, text)

    res = ce.run_evals(ids=["dc-001", "dc-002", "dc-011"], concurrency=2, chain=chain)
    rows = {r["id"]: r for r in res["rows"]}
    assert len(rows) == 3
    assert rows["dc-002"]["error"] == "RuntimeError: boom" and rows["dc-002"]["correct"] is False and rows["dc-002"]["got"] is None
    assert rows["dc-001"]["correct"] is True and rows["dc-011"]["correct"] is True
    assert res["summary"]["errors"] == [{"id": "dc-002", "error": "RuntimeError: boom"}]
    assert any(w["id"] == "dc-002" for w in res["summary"]["wrong"])


def test_a_failed_stage_in_the_api_chain_is_an_error_row(fixture_api, monkeypatch):
    class Boom:
        model = "boom"

        def decide(self, case, inv):
            raise RuntimeError("verdict broke")

    monkeypatch.setattr(fixture_api, "verdicter", lambda: Boom())
    res = ce.run_evals(ids=["dc-001"], concurrency=1)
    r = res["rows"][0]
    assert r["got"] is None and r["correct"] is False and "verdict broke" in r["error"]


def test_no_critic_turns_the_critic_off_for_the_run_only(fixture_api):
    res = ce.run_evals(ids=["dc-001"], concurrency=1, critic=False)
    c = res["rows"][0]["critique"]
    assert c["skipped"] is True and c["rounds"] == 0
    assert res["config"]["critic_rounds"] == 0
    assert "RECOURSE_CRITIC_ROUNDS" not in os.environ


def test_limit_and_unknown_ids(fixture_api):
    res = ce.run_evals(limit=2, concurrency=1, chain=lambda cid, text: {"refused": None, "case": None})
    assert [r["id"] for r in res["rows"]] == ["dc-001", "dc-002"]
    with pytest.raises(ValueError):
        ce.run_evals(ids=["dc-999"], chain=lambda cid, text: {"refused": None, "case": None})


def _row(cid, intended, got, correct, program="florida_medicaid_mma", jurisdiction="Florida", refused=None, error=None,
         letter=None, critique=None, cost=0.0, seconds=0.0):
    return {"id": cid, "program": program, "jurisdiction": jurisdiction, "trap": "no", "demo": "no", "intended": intended,
            "got": got, "correct": correct, "refused": refused, "route_program": program, "route_reason": "",
            "stage_errors": [], "findings": {}, "letter": letter, "critique": critique, "cost_usd": cost,
            "stage_cost_usd": {}, "seconds": seconds, "error": error}


# ---- evaluator findings, Oct 26: stage failures are not real verdicts --------------


class Down:
    """A provider whose every call fails, like a 429 from the Meta endpoint."""

    model = "muse-spark-1.3"
    last_response = None

    def complete_parts(self, *a, **kw):
        raise RuntimeError("HTTP 429 Too Many Requests")

    def cost(self, n_in, n_out):
        return 0.0


def _stages(row):
    return [e["stage"] for e in row["stage_errors"]]


def test_a_verdict_model_failure_is_an_error_not_a_not_settled_verdict(fixture_api, monkeypatch):
    from policyqa.verdict import LiveVerdict

    monkeypatch.setattr(fixture_api, "verdicter", lambda: LiveVerdict(Down()))
    res = ce.run_evals(ids=["dc-020", "dc-030"], concurrency=1)
    for r in res["rows"]:
        assert r["got"] == "not_settled"  # the template outcome is still shown
        assert r["correct"] is False and "429" in r["error"] and "verdict" in _stages(r)
    assert [e["id"] for e in res["summary"]["errors"]] == ["dc-020", "dc-030"]
    assert "| dc-020 | not_settled | error (not_settled) | no |" in ce.render_markdown(res)


def test_an_investigation_with_only_errored_findings_is_an_error(fixture_api, monkeypatch):
    from policyqa.investigate import FixtureInvestigator

    class AllErrored(FixtureInvestigator):
        def investigate(self, case, on_progress=None):
            inv = super().investigate(case, on_progress)
            for f in inv["findings"]:
                f.update(status="error", error="HTTP 429", citations=[])
            return inv

    monkeypatch.setattr(fixture_api, "investigator", lambda: AllErrored(delay=0))
    r = ce.run_evals(ids=["dc-020"], concurrency=1)["rows"][0]
    assert r["got"] == "not_settled" and r["correct"] is False
    assert "investigation" in _stages(r) and r["error"].startswith("investigation")


def test_a_template_letter_is_recorded_and_left_out_of_the_rates(fixture_api, monkeypatch):
    from policyqa.letter import LiveLetter

    monkeypatch.setattr(fixture_api, "letterer", lambda: LiveLetter(Down()))
    res = ce.run_evals(ids=["dc-001"], concurrency=1)
    r = res["rows"][0]
    assert r["correct"] is True and r["error"] is None  # the verdict stands
    assert "letter" in _stages(r) and r["letter"]["error"]
    s = res["summary"]
    assert s["letter_failures"] == 1 and s["letters"]["applicable"] == 0 and s["letters"]["claims"] == 0


def test_a_critic_failure_keeps_the_verdict_but_is_counted(fixture_api, monkeypatch):
    from policyqa.critic import LiveCritic

    monkeypatch.setattr(fixture_api, "critic", lambda: LiveCritic(Down(), rounds=1))
    res = ce.run_evals(ids=["dc-001"], concurrency=1)
    r = res["rows"][0]
    assert r["correct"] is True and r["error"] is None
    assert "critique" in _stages(r)
    assert res["summary"]["critic_failures"] == 1 and res["summary"]["critic"]["accepted"] == 0


def test_a_clean_row_has_no_stage_errors(fixture_api):
    r = ce.run_evals(ids=["dc-001"], concurrency=1)["rows"][0]
    assert r["stage_errors"] == [] and r["error"] is None


def test_dc030_summary_reports_the_route_program_not_a_wording_check(fixture_api):
    res = ce.run_evals(ids=["dc-030"], concurrency=1)
    assert "route_no_document" not in res["rows"][0]
    o = res["summary"]["outside_corpus"][0]
    assert o["route_program"] == "florida_medicaid_mma"  # the fixture extractor's card
    assert o["route_unknown"] is False


def test_a_result_with_neither_case_nor_refusal_is_an_error():
    row = {"id": "dc-001", "program": "florida_medicaid_mma", "jurisdiction": "Florida", "trap": "no", "demo": "yes", "intended_outcome": "inconsistent"}
    r = ce.build_row(row, {"refused": None, "case": None}, 0.0)
    assert r["correct"] is False and r["error"] == "no result"


def test_limit_zero_is_rejected():
    with pytest.raises(ValueError):
        ce.load_cases(limit=0)
    from policyqa import cli

    with pytest.raises(SystemExit):
        cli.main(["case-evals", "--limit", "0"])

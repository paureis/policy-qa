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
            "route_reason", "stage_errors", "findings", "letter", "critique", "cost_usd", "stage_cost_usd", "seconds", "error",
            # Oct 27, second pass: each miss traces to a stage
            "proposed_outcome", "decisive_fact", "settled_by", "relies_on_exception", "plan_source", "planned_questions", "exceptions", "hinge", "miss"}


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
    per_case, misses = text.split("Misses by stage")
    case_lines = [ln for ln in per_case.splitlines() if ln.startswith("| dc-")]
    assert len(case_lines) == 3
    assert [ln.split(" | ")[0] for ln in misses.splitlines() if ln.startswith("| dc-")] == ["| dc-002"]
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


# ---- Oct 27, second pass: rows say which stage each miss traces to ---------------------------------------

DC002_ROW = {"id": "dc-002", "program": "florida_medicaid_mma", "jurisdiction": "Florida", "trap": "yes", "demo": "yes", "intended_outcome": "consistent",
             "hinge_doc_id": "fl-04", "hinge_page": "4"}
UNDER_21 = "As such, services for recipients under the age of 21 years exceeding the coverage described within this policy or the associated fee schedule may be approved, if medically necessary."
PDN_RULE = "Florida Medicaid recipients under the age of 21 years requiring medically necessary PDN."
EXC_Q = "Is there an exception under Florida Medicaid (MMA) that covers private duty nursing even though it is only for members under 21?"


def _f(fid, topic, status, question, cites=(), passages=(), jurisdiction="Florida"):
    return {"id": fid, "topic": topic, "status": status, "question": question, "jurisdiction": jurisdiction, "answer": "a", "error": None,
            "citations": [{"doc_id": d, "title": f"Title of {d}", "page": p, "quote": q, "overlap": 1.0} for d, p, q in cites],
            "passages": [{"chunk_id": f"{d}:p{p:03d}:0", "doc_id": d, "title": f"Title of {d}", "page": p} for d, p in passages], "struck": []}


def fake_case(verdict_over=None, findings=None, plan_source="model"):
    """A finished case as api_chain returns it, shaped like dc-002 on Oct 27 (consistent, called inconsistent)."""
    card = {"program": {"value": "florida_medicaid_mma"}, "member_age_group": {"value": "adult"}, "service": {"value": "Private duty nursing, 12 hours per day"},
            "denial_reason": {"value": "Private duty nursing is covered only for members under the age of 21."}, "payer_name": {"value": "Sample Health Plan"}}
    findings = findings if findings is not None else [
        _f("f1", "coverage", "supported", "Is private duty nursing covered under Florida Medicaid (MMA)?", [("fl-04", 4, PDN_RULE)], [("fl-04", 4), ("fl-04", 6)]),
        _f("f2", "appeal", "supported", "How does a member appeal under Florida Medicaid (MMA)?", [("fl-21", 41, "An enrollee may file an appeal within sixty (60) days.")], [("fl-21", 41)]),
        _f("f3", "exclusions", "supported", EXC_Q, [("fl-04", 6, UNDER_21)], [("fl-04", 6)]),
        _f("f4", "reason", "not_settled", "What do the rules say when private duty nursing is covered only for members under 21?", (), [("fl-04", 5)]),
    ]
    verdict = {"status": "done", "outcome": "inconsistent", "proposed_outcome": "inconsistent", "cost_usd": 0.01, "error": None,
               "decisive_fact": {"fact": "The member's age on the dates of service.", "settled_by": "letter"}, "relies_on_exception": True, "exceptions": []}
    verdict.update(verdict_over or {})
    return {"status": "reviewed", "card": card, "summary": None, "cost_usd": 0.0,
            "route": {"program": "florida_medicaid_mma", "jurisdictions": ["Florida"], "reason": "r", "outside_corpus": False},
            "investigation": {"status": "done", "cost_usd": 0.02, "plan": {"source": plan_source, "questions": 4}, "findings": findings},
            "verdict": verdict, "letter": None, "critique": None}


def test_a_row_records_the_proposed_outcome_the_decisive_fact_the_plan_and_the_exceptions():
    r = ce.build_row(DC002_ROW, {"refused": None, "case": fake_case()}, 1.0)
    assert r["got"] == "inconsistent" and r["correct"] is False
    assert r["proposed_outcome"] == "inconsistent"
    assert r["decisive_fact"] == "The member's age on the dates of service." and r["settled_by"] == "letter" and r["relies_on_exception"] is True
    assert r["plan_source"] == "model"
    assert r["planned_questions"][0] == {"topic": "coverage", "question": "Is private duty nursing covered under Florida Medicaid (MMA)?"}
    assert [q["topic"] for q in r["planned_questions"]] == ["coverage", "appeal", "exclusions", "reason"]
    assert r["exceptions"] == [{"finding_id": "f3", "question": EXC_Q, "status": "supported", "state": "not_relevant", "relevant": False,
                                "reason": "it is for members under 21, and the member is 21 or older"}]
    assert r["hinge"] == {"doc_id": "fl-04", "page": 4, "reached": ["f1"], "cited": ["f1"]}
    assert r["miss"]["stage"] == "verdict"
    assert "fl-04 p4" in r["miss"]["why"] and "f3 not relevant" in r["miss"]["why"]


def test_planned_questions_are_listed_once_on_a_dual_route():
    q = "Is the service covered under Medicare Part B?"
    findings = [_f("f1", "coverage", "supported", q, jurisdiction="Florida"), _f("f2", "coverage", "not_settled", q, jurisdiction="Federal")]
    r = ce.build_row(DC002_ROW, {"refused": None, "case": fake_case(findings=findings)}, 1.0)
    assert r["planned_questions"] == [{"topic": "coverage", "question": q}]


@pytest.mark.parametrize("verdict_over, findings_keep, expected_stage, phrase", [
    # the model was right and a code guard changed it
    ({"outcome": "not_settled", "proposed_outcome": "consistent", "decisive_fact": {"fact": "x", "settled_by": "payer_determination"}}, None, "verdict", "guard"),
    # the hinge page reached the model but no verified quote came from it
    (None, ["f2", "f3", "f4"], "answer", "reached"),
    # no question's passages reached the hinge page, and an exception question was planned
    (None, ["f2", "f3"], "retrieval", "no question"),
])
def test_each_miss_traces_to_one_stage(verdict_over, findings_keep, expected_stage, phrase):
    case = fake_case(verdict_over)
    if findings_keep is not None:
        fs = [f for f in case["investigation"]["findings"] if f["id"] in findings_keep]
        for f in fs:  # drop the hinge page from what was cited; keep it in the passages only where the case says so
            f["citations"] = [c for c in f["citations"] if c["page"] != 4]
            if expected_stage == "retrieval":
                f["passages"] = [p for p in f["passages"] if p["page"] != 4]
        if expected_stage == "answer":
            fs[-1]["passages"].append({"chunk_id": "fl-04:p004:0", "doc_id": "fl-04", "title": "t", "page": 4})
        case["investigation"]["findings"] = fs
    r = ce.build_row(DC002_ROW, {"refused": None, "case": case}, 1.0)
    assert r["correct"] is False and r["miss"]["stage"] == expected_stage and phrase in r["miss"]["why"]


def test_a_plan_without_an_exception_question_that_never_reaches_the_hinge_is_a_planning_miss():
    findings = [_f("f1", "appeal", "supported", "How does a member appeal under Florida Medicaid (MMA)?", [("fl-21", 41, "An enrollee may file an appeal within sixty (60) days.")], [("fl-21", 41)])]
    r = ce.build_row(DC002_ROW, {"refused": None, "case": fake_case(findings=findings)}, 1.0)
    assert r["miss"]["stage"] == "planning"


def test_a_right_row_has_no_miss_and_an_error_row_names_its_stage():
    ok = ce.build_row({**DC002_ROW, "intended_outcome": "inconsistent"}, {"refused": None, "case": fake_case()}, 1.0)
    assert ok["correct"] is True and ok["miss"] is None
    err = ce.build_row(DC002_ROW, None, 900.0, error="TimeoutError: the chain did not finish in 900 s")
    assert err["miss"]["stage"] == "harness" and "TimeoutError" in err["miss"]["why"]
    assert err["planned_questions"] == [] and err["exceptions"] == [] and err["hinge"]["reached"] == []


def test_the_summary_and_the_markdown_list_misses_by_stage():
    rows = [ce.build_row(DC002_ROW, {"refused": None, "case": fake_case()}, 1.0),
            ce.build_row({**DC002_ROW, "id": "dc-001", "intended_outcome": "inconsistent"}, {"refused": None, "case": fake_case()}, 1.0)]
    s = ce.summarize(rows)
    assert s["misses"] == [{"id": "dc-002", "intended": "consistent", "got": "inconsistent", "stage": "verdict", "why": rows[0]["miss"]["why"]}]
    assert s["misses_by_stage"] == {"verdict": 1}
    md = ce.render_markdown({"config": {"date": "2026-10-28", "model": "m", "critic_rounds": 1}, "summary": s, "rows": rows})
    assert "Misses by stage" in md
    assert "| Case | Intended | Got | Stage | Why |" in md
    assert "| dc-002 | consistent | inconsistent | verdict | " in md


def test_limit_zero_is_rejected():
    with pytest.raises(ValueError):
        ce.load_cases(limit=0)
    from policyqa import cli

    with pytest.raises(SystemExit):
        cli.main(["case-evals", "--limit", "0"])


# ---- second opinion (Oct 28 afternoon) -------------------------------------------------


def _second(status="done", outcome="inconsistent", agrees=True, cost=0.004, latency=12000.0, reason=None, error=None):
    return {"status": status, "reason": reason, "model": "meta-models/muse-spark-open-1026", "outcome": outcome, "proposed_outcome": outcome,
            "decisive_fact": None, "relies_on_exception": False, "agrees": agrees, "input_tokens": 2000, "output_tokens": 900,
            "reasoning_tokens": 400, "latency_ms": latency, "cost_usd": cost, "error": error}


def _with_second(so):
    case = fake_case()
    if so is not None:
        case["second_opinion"] = so
    return case


def test_a_row_records_the_second_opinion():
    r = ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(_second(outcome="consistent", agrees=False))}, 1.0)
    assert r["second_status"] == "done" and r["second_outcome"] == "consistent" and r["second_agrees"] is False
    assert r["second_cost_usd"] == 0.004 and r["second_latency_ms"] == 12000.0
    assert r["cost_usd"] == 0.03  # the case's own cost leaves the second opinion out; the summary reports it apart


@pytest.mark.parametrize("so", [None, _second(status="skipped", outcome=None, agrees=None, cost=0.0, latency=0.0, reason="not configured")])
def test_a_row_without_a_second_opinion_reads_skipped_with_nulls(so):
    r = ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(so)}, 1.0)
    assert r["second_status"] == "skipped"
    assert r["second_outcome"] is None and r["second_agrees"] is None and r["second_cost_usd"] is None and r["second_latency_ms"] is None


def test_a_failed_second_opinion_keeps_its_cost_but_no_outcome():
    r = ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(_second(status="failed", outcome=None, agrees=None, cost=0.001, error="HTTP 500"))}, 1.0)
    assert r["second_status"] == "failed" and r["second_outcome"] is None and r["second_agrees"] is None and r["second_cost_usd"] == 0.001


def _second_rows():
    # dc-002 intended consistent: primary inconsistent (wrong), second consistent (right)
    a = ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(_second(outcome="consistent", agrees=False, cost=0.004))}, 1.0)
    # dc-001 intended inconsistent: both inconsistent (agree, both right)
    b = ce.build_row({**DC002_ROW, "id": "dc-001", "intended_outcome": "inconsistent"}, {"refused": None, "case": _with_second(_second(cost=0.006))}, 1.0)
    # dc-005 intended inconsistent: primary right, second not_settled (wrong)
    c = ce.build_row({**DC002_ROW, "id": "dc-005", "intended_outcome": "inconsistent"}, {"refused": None, "case": _with_second(_second(outcome="not_settled", agrees=False, cost=0.002))}, 1.0)
    # dc-006: second failed
    d = ce.build_row({**DC002_ROW, "id": "dc-006", "intended_outcome": "inconsistent"}, {"refused": None, "case": _with_second(_second(status="failed", outcome=None, agrees=None, cost=0.0, error="HTTP 500"))}, 1.0)
    return [a, b, c, d]


def test_the_summary_counts_second_opinion_agreement_and_who_was_right():
    s = ce.summarize(_second_rows())["second_opinion"]
    assert s["configured"] is True
    assert s["both_done"] == 3 and s["agree"] == 1 and s["agreement_rate"] == round(1 / 3, 4)
    assert s["second_right_primary_wrong"] == ["dc-002"] and s["primary_right_second_wrong"] == ["dc-005"]
    assert s["done"] == 3 and s["failed"] == 1 and s["skipped"] == 0
    assert s["cost_usd"]["mean"] == 0.003  # over the cases where it ran (done or failed): (0.004 + 0.006 + 0.002 + 0.0) / 4


def test_the_summary_says_not_configured_when_no_second_opinion_ran():
    rows = [ce.build_row(DC002_ROW, {"refused": None, "case": fake_case()}, 1.0)]
    s = ce.summarize(rows)["second_opinion"]
    assert s["configured"] is False and s["both_done"] == 0 and s["agreement_rate"] is None and s["skipped"] == 1
    md = ce.render_markdown({"config": {"date": "2026-10-28", "model": "m", "critic_rounds": 1}, "summary": ce.summarize(rows), "rows": rows})
    assert "second opinion: not configured" in md.lower()
    assert "| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |" in md
    assert [ln for ln in md.splitlines() if ln.startswith("| dc-002 | consistent | inconsistent | no |")][0].endswith("| skipped |")


def test_the_markdown_reports_second_opinion_lines_and_a_column():
    rows = _second_rows()
    res = {"config": {"date": "2026-10-28", "model": "m", "critic_rounds": 1, "second_model": "meta-models/muse-spark-open-1026"}, "summary": ce.summarize(rows), "rows": rows}
    md = ce.render_markdown(res)
    assert "| Second opinion agrees with the verdict | 1 / 3 (33.3%) of the cases where both ran |" in md
    assert "| Second opinion right, verdict wrong | 1 (dc-002) |" in md
    assert "| Verdict right, second opinion wrong | 1 (dc-005) |" in md
    assert "| Second opinion cost per case | mean $0.0030 over 4 runs |" in md
    assert "Second opinion: meta-models/muse-spark-open-1026" in md
    lines = {ln.split(" | ")[0][2:]: ln for ln in md.splitlines() if ln.startswith("| dc-") and ln.count("|") == 9}
    assert lines["dc-002"].endswith("| consistent (disagrees) |")
    assert lines["dc-001"].endswith("| inconsistent (agrees) |")
    assert lines["dc-006"].endswith("| failed |")


def test_the_run_config_names_the_second_model(fixture_api, monkeypatch):
    monkeypatch.setenv("POLICYQA_SECOND_LLM_BASE_URL", "https://inference.baseten.co/v1")
    monkeypatch.setenv("POLICYQA_SECOND_LLM_MODEL", "meta-models/muse-spark-open-1026")
    assert ce.run_config("c.csv", None, None, 1)["second_model"] == "meta-models/muse-spark-open-1026"
    monkeypatch.delenv("POLICYQA_SECOND_LLM_MODEL")
    assert ce.run_config("c.csv", None, None, 1)["second_model"] is None


def _slow_second_api(fixture_api, monkeypatch, delay):
    """A primary verdict that counts as a model verdict (the fixture's reply under a live model name) and a second
    endpoint that answers after `delay` seconds over the fake transport."""
    import time

    import httpx

    from policyqa.generate import Provider
    from policyqa.verdict import FixtureVerdict

    class LivePrimary(FixtureVerdict):
        model = "muse-spark-1.3"

    def handler(request):
        time.sleep(delay)
        body = {"steelman": {"argument": "a", "citations": []}, "rule": {"statement": "r", "citations": []}, "decisive_fact": {"fact": "f", "settled_by": "letter"},
                "relies_on_exception": False, "outcome": "consistent", "gap": "g", "what_would_change": "w"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(body)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    second = Provider(base_url="https://inference.baseten.co/v1", api_key="k", model="meta-models/muse-spark-open-1026", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(fixture_api, "verdicter", lambda: LivePrimary(delay=0))
    monkeypatch.setattr(fixture_api, "second_provider", lambda: second)


def test_a_second_opinion_past_its_bound_is_a_timeout_and_the_case_still_scores(fixture_api, monkeypatch):
    from policyqa import second_opinion as so

    _slow_second_api(fixture_api, monkeypatch, delay=1.5)
    monkeypatch.setenv("POLICYQA_LLM_TIMEOUT_S", "0.2")
    monkeypatch.setattr(so, "SECOND_WAIT_SLACK_S", 0.0)
    assert so.second_wait_s() == 0.2
    r = ce.run_evals(ids=["dc-001"], concurrency=1)["rows"][0]
    assert r["correct"] is True and r["error"] is None and r["got"] == "inconsistent"
    assert r["second_status"] == "timeout" and r["second_outcome"] is None and r["second_agrees"] is None
    assert r["seconds"] < 1.0


def test_the_wait_bound_is_the_model_timeout_plus_a_minute(monkeypatch):
    from policyqa import second_opinion as so

    monkeypatch.delenv("POLICYQA_LLM_TIMEOUT_S", raising=False)
    assert so.second_wait_s() == 180.0
    monkeypatch.setenv("POLICYQA_LLM_TIMEOUT_S", "300")
    assert so.second_wait_s() == 360.0


def test_the_row_seconds_leave_out_the_wait_for_the_second_opinion(fixture_api, monkeypatch):
    _slow_second_api(fixture_api, monkeypatch, delay=0.8)
    r = ce.run_evals(ids=["dc-001"], concurrency=1)["rows"][0]
    assert r["second_status"] == "done" and r["second_outcome"] == "not_settled" and r["second_agrees"] is False
    assert r["second_latency_ms"] >= 800 and r["seconds"] < 0.6


def test_the_summary_counts_timeouts_apart():
    rows = _second_rows()
    rows[3].update(second_status="timeout", second_cost_usd=None, second_latency_ms=None)
    s = ce.summarize(rows)["second_opinion"]
    assert s["timeout"] == 1 and s["failed"] == 0 and s["ran"] == 4 and s["cost_usd"]["mean"] == 0.004


def test_the_markdown_names_a_configured_model_that_ran_on_no_case():
    fixture = "the primary verdict is the fixture (no model call)"
    skip = _second(status="skipped", outcome=None, agrees=None, cost=0.0, latency=0.0, reason=fixture)
    rows = [ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(skip)}, 1.0),
            ce.build_row({**DC002_ROW, "id": "dc-001", "intended_outcome": "inconsistent"}, {"refused": None, "case": _with_second(skip)}, 1.0)]
    s = ce.summarize(rows)
    assert s["second_opinion"]["configured"] is True and s["second_opinion"]["ran"] == 0 and s["second_opinion"]["skip_reasons"] == {fixture: 2}
    md = ce.render_markdown({"config": {"date": "2026-10-28", "model": "fixture", "critic_rounds": 1}, "summary": s, "rows": rows})
    assert "not configured" not in md.lower()
    assert "Second opinion: meta-models/muse-spark-open-1026, 0 ran." in md
    assert f"| Second opinion | 0 ran; skipped 2: {fixture} (2) |" in md
    # the config alone (old rows without the field) is enough to say it is configured
    old = [ce.build_row(DC002_ROW, {"refused": None, "case": fake_case()}, 1.0)]
    md = ce.render_markdown({"config": {"date": "2026-10-28", "model": "m", "critic_rounds": 1, "second_model": "meta-models/muse-spark-open-1026"}, "summary": ce.summarize(old), "rows": old})
    assert "not configured" not in md.lower() and "Second opinion: meta-models/muse-spark-open-1026, 0 ran." in md


def test_a_row_whose_chain_never_reached_the_verdict_says_so():
    """dc-011 is refused at intake and never reaches the verdict, so there is no second_opinion key at all; the
    row's reason must say that, not "no reason recorded" (the Oct 28 live run)."""
    r = ce.build_row(DC002_ROW, {"refused": None, "case": _with_second(None)}, 1.0)
    assert r["second_status"] == "skipped"
    assert r["second_reason"] == "the chain did not reach the verdict"

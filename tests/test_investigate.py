"""Investigation agent: routing, planning, jurisdiction filter, findings, fixture. No network, no index."""
import json
from pathlib import Path

import pytest

from policyqa.generate import ABSTAIN_TEXT, enforce_citations_detailed
from policyqa.investigate import (
    FixtureInvestigator,
    PlannedQuestion,
    Route,
    investigate_case,
    plan_questions,
    route_case,
    template_questions,
)
from policyqa.retrieve import Hit


def card(**over):
    base = {
        "payer_name": "Sunshine Health",
        "program": "florida_medicaid_mma",
        "member_age_group": "under_21",
        "service": "private duty nursing, 8 hours/day",
        "service_code": "T1000",
        "dates_of_service": "2026-09-01/2026-09-30",
        "amount_billed": 4320.0,
        "denial_reason": "Services exceed the authorized amount.",
        "letter_date": "2026-10-14",
        "appeal_deadline_claimed": "2026-12-13",
    }
    base.update(over)
    return {k: {"value": v, "confidence": "high"} for k, v in base.items()}


# ---- routing ----------------------------------------------------------------


@pytest.mark.parametrize(
    "over, jurisdictions, dual",
    [
        ({}, ["Florida"], False),
        ({"program": "florida_medicaid_ltc", "member_age_group": "adult"}, ["Florida"], False),
        ({"program": "florida_kidcare"}, ["Florida"], False),
        ({"program": "florida_medicaid_mma", "member_age_group": "65_plus"}, ["Florida", "Federal"], True),
        ({"program": "medicare_b", "member_age_group": "65_plus", "payer_name": "Medicare"}, ["Federal"], False),
        ({"program": "medicare_advantage", "payer_name": "Humana Gold Plus"}, ["Federal"], False),
        ({"program": "medicare_part_d", "payer_name": "Sunshine Health Medicare-Medicaid Plan"}, ["Florida", "Federal"], True),
        ({"program": "unknown"}, ["Florida", "Federal"], True),
        ({"program": None}, ["Florida", "Federal"], True),
    ],
)
def test_route_table(over, jurisdictions, dual):
    r = route_case(card(**over))
    assert isinstance(r, Route)
    assert r.jurisdictions == jurisdictions and r.dual is dual
    assert r.reason.endswith(".") and len(r.reason.split()) >= 8
    d = r.to_dict()
    assert set(d) == {"program", "jurisdictions", "dual", "reason"}
    assert d["program"] == (over["program"] if over.get("program") else ("unknown" if "program" in over else "florida_medicaid_mma"))


def test_route_accepts_plain_values_too():
    r = route_case({"program": "medicare_a", "member_age_group": "65_plus", "payer_name": "Medicare"})
    assert r.jurisdictions == ["Federal"] and not r.dual


# ---- template questions -----------------------------------------------------


def test_template_questions_cover_the_six_topics_in_plain_words():
    c = card()
    qs = template_questions(c, route_case(c))
    topics = [q.topic for q in qs]
    assert topics == ["coverage", "limits", "conditions", "exclusions", "appeal", "reason"]
    assert all(isinstance(q, PlannedQuestion) and q.question.endswith("?") for q in qs)
    assert qs[0].question == "Is private duty nursing, 8 hours/day covered under Florida Medicaid (MMA) for a member under 21?"
    assert "prior authorization" in qs[2].question
    assert "deadline" in qs[4].question
    assert qs[5].question == "What do the rules say when services exceed the authorized amount?"


def test_template_questions_without_a_reason_or_service():
    c = card(denial_reason=None, service=None, program="unknown")
    qs = template_questions(c, route_case(c))
    assert [q.topic for q in qs][-1] == "reason"
    assert "the service" in qs[0].question and "Florida Medicaid or Medicare" in qs[0].question
    assert "None" not in " ".join(q.question for q in qs)


# ---- planning with a fake provider -----------------------------------------


class FakePlanProvider:
    model = "fake-planner"

    def __init__(self, content, raise_exc=None):
        self.content = content
        self.raise_exc = raise_exc
        self.calls = []
        self.last_response = {"usage": {"prompt_tokens": 100, "completion_tokens": 50, "completion_tokens_details": {"reasoning_tokens": 30}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500):
        self.calls.append({"system": system, "parts": parts, "schema": schema, "max_tokens": max_tokens})
        if self.raise_exc:
            raise self.raise_exc
        return self.content, 100, 50

    def cost(self, n_in, n_out):
        return 0.001


GOOD_PLAN = {
    "questions": [
        {"topic": "coverage", "question": "Does Florida Medicaid MMA cover private duty nursing for a child under 21?"},
        {"topic": "limits", "question": "How many hours of private duty nursing a day does Florida Medicaid allow?"},
        {"topic": "conditions", "question": "Does private duty nursing need prior authorization under Florida Medicaid?"},
        {"topic": "appeal", "question": "How many days does a Florida Medicaid member have to appeal a denial?"},
        {"topic": "reason", "question": "What do the Florida Medicaid rules say when services exceed the authorized amount?"},
    ]
}


def test_plan_uses_the_model_questions_when_the_json_is_good():
    c = card()
    r = route_case(c)
    p = FakePlanProvider(json.dumps(GOOD_PLAN))
    qs = plan_questions(c, r, p)
    assert [q.question for q in qs] == [q["question"] for q in GOOD_PLAN["questions"]]
    assert [q.topic for q in qs] == ["coverage", "limits", "conditions", "appeal", "reason"]
    call = p.calls[0]
    assert call["schema"]["type"] == "object" and "questions" in call["schema"]["properties"]
    assert call["max_tokens"] >= 2000
    text = call["parts"][0]["text"]
    assert "private duty nursing" in text and "Florida Medicaid (MMA)" in text and "Services exceed the authorized amount" in text
    assert "medical advice" in call["system"]


def test_plan_falls_back_to_templates_on_bad_json_exception_or_too_few():
    c = card()
    r = route_case(c)
    expected = [q.question for q in template_questions(c, r)]
    assert [q.question for q in plan_questions(c, r, FakePlanProvider("this is not json"))] == expected
    assert [q.question for q in plan_questions(c, r, FakePlanProvider("{}", raise_exc=RuntimeError("boom")))] == expected
    few = {"questions": [{"topic": "coverage", "question": "Is private duty nursing covered?"}, {"topic": "appeal", "question": "How do I appeal?"}]}
    assert [q.question for q in plan_questions(c, r, FakePlanProvider(json.dumps(few)))] == expected
    # a provider without complete_parts (the mock) also falls back
    class NoParts:
        model = "mock"

    assert [q.question for q in plan_questions(c, r, NoParts())] == expected


def test_plan_drops_out_of_scope_and_malformed_questions_and_adds_missing_appeal_and_reason():
    c = card()
    r = route_case(c)
    plan = {
        "questions": [
            {"topic": "coverage", "question": "Is private duty nursing covered under Florida Medicaid for a child?"},
            {"topic": "limits", "question": "Should I take a higher dose of the medication while the nursing is denied?"},
            {"topic": "conditions", "question": "What prior authorization does Florida Medicaid require for private duty nursing?"},
            {"topic": "diagnosis", "question": "Is private duty nursing excluded for any condition under Florida Medicaid?"},
            {"topic": "exclusions", "question": "short?"},
            {"topic": "exclusions", "question": "Is private duty nursing excluded in a hospital setting under Florida Medicaid?"},
            "not a dict",
        ]
    }
    qs = plan_questions(c, r, FakePlanProvider(json.dumps(plan)))
    questions = [q.question for q in qs]
    assert not any("dose" in q for q in questions)
    assert not any(q == "short?" for q in questions)
    # an unknown topic label becomes "other"; the question is kept
    assert [q.topic for q in qs][:4] == ["coverage", "conditions", "other", "exclusions"]
    # one appeal and one reason question are always present
    assert "appeal" in [q.topic for q in qs] and "reason" in [q.topic for q in qs]
    assert len(qs) == 6


def test_plan_caps_at_seven_questions():
    c = card()
    r = route_case(c)
    many = {"questions": [{"topic": "other", "question": f"Question number {i} about private duty nursing under Florida Medicaid?"} for i in range(12)] + GOOD_PLAN["questions"][-2:]}
    qs = plan_questions(c, r, FakePlanProvider(json.dumps(many)))
    assert len(qs) == 7 and "appeal" in [q.topic for q in qs] and "reason" in [q.topic for q in qs]


# ---- jurisdiction filter on a small index ----------------------------------


def _write_chunks(path: Path, n_fl=6, n_fed=6):
    rows = []
    for i in range(n_fl):
        rows.append({"chunk_id": f"fl-04:p{i}:0", "doc_id": "fl-04", "page": i + 1, "pos": 0, "title": "Florida PDN policy", "jurisdiction": "Florida", "text": f"Florida Medicaid private duty nursing hours per day limit page {i} nursing nursing"})
    for i in range(n_fed):
        rows.append({"chunk_id": f"fed-24:p{i}:0", "doc_id": "fed-24", "page": i + 1, "pos": 0, "title": "Medicare home health", "jurisdiction": "Federal", "text": f"Medicare home health skilled nursing hours per day page {i} nursing"})
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def test_jurisdiction_filter_returns_only_that_jurisdiction_and_still_fills_k(tmp_path):
    from policyqa.index import Index
    from policyqa.retrieve import Retriever

    _write_chunks(tmp_path / "chunks.jsonl", n_fl=6, n_fed=6)
    r = Retriever(Index(tmp_path / "chunks.jsonl"), mode="bm25")
    # unfiltered: the old signature still works
    hits = r.search("private duty nursing hours per day", k=5)
    assert len(hits) == 5
    assert {h.chunk["jurisdiction"] for h in r.search("nursing", k=12)} == {"Florida", "Federal"}
    # filtered to Federal with a tiny candidate pool: the filter pulls more candidates so k is still filled
    hits = r.search("private duty nursing hours per day", k=5, candidates=4, jurisdictions={"Federal"})
    assert len(hits) == 5 and all(h.chunk["jurisdiction"] == "Federal" for h in hits)
    hits = r.search("private duty nursing hours per day", k=5, jurisdictions={"Florida"})
    assert len(hits) == 5 and all(h.chunk["jurisdiction"] == "Florida" for h in hits)
    # both allowed behaves like no filter
    assert len(r.search("nursing", k=10, jurisdictions={"Florida", "Federal"})) == 10
    # a jurisdiction with nothing returns an empty list, not an error
    assert r.search("nursing", k=5, jurisdictions={"Mars"}) == []


# ---- enforce_citations with reasons ------------------------------------------

PASSAGES = [
    {"tag": "P1", "chunk_id": "a", "doc_id": "fl-04", "page": 3, "title": "PDN policy", "jurisdiction": "Florida", "text": "Florida Medicaid covers private duty nursing services for recipients under the age of 21 years. Services must be medically necessary and prior authorized."},
    {"tag": "P2", "chunk_id": "b", "doc_id": "fl-21", "page": 40, "title": "MMA contract", "jurisdiction": "Florida", "text": "An enrollee may file an appeal within sixty (60) days of the date on the notice of adverse benefit determination."},
]


def test_enforce_citations_detailed_lists_dropped_with_reasons():
    data = {
        "answer": "Covered under 21, appeal in 60 days.",
        "abstain": False,
        "citations": [
            {"passage": "P1", "quote": "covers private duty nursing services for recipients under the age of 21 years"},
            {"passage": "P1", "quote": "Florida Medicaid covers private duty nursing for everyone at any age without limit"},
            {"passage": "P7", "quote": "An enrollee may file an appeal within sixty (60) days of the date"},
        ],
    }
    res = enforce_citations_detailed(data, PASSAGES)
    assert not res.abstained and not res.forced_abstain and len(res.kept) == 1 and res.proposed == 3
    assert [s["reason"] for s in res.struck] == ["quote not found on the cited page", "cited a passage that was not shown"]
    assert res.struck[0]["doc_id"] == "fl-04" and res.struck[0]["title"] == "PDN policy" and res.struck[0]["page"] == 3
    assert res.struck[1]["doc_id"] is None and res.struck[1]["quote"].startswith("An enrollee")
    assert res.original_answer == "Covered under 21, appeal in 60 days."
    # the 6-tuple wrapper is unchanged
    from policyqa.generate import enforce_citations

    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, PASSAGES)
    assert (abst, len(kept), proposed, dropped, forced) == (False, 1, 3, 2, False)


def test_enforce_citations_detailed_forced_abstention_keeps_original_answer():
    data = {"answer": "Six visits a day.", "abstain": False, "citations": [{"passage": "P1", "quote": "Florida Medicaid covers six private duty visits per day for everyone"}]}
    res = enforce_citations_detailed(data, PASSAGES)
    assert res.forced_abstain and res.abstained and res.answer == ABSTAIN_TEXT and res.original_answer == "Six visits a day."
    assert len(res.struck) == 1 and res.struck[0]["reason"] == "quote not found on the cited page"


# ---- investigate_case end to end --------------------------------------------


def _hit(p):
    return Hit({k: p[k] for k in ("chunk_id", "doc_id", "page", "title", "jurisdiction", "text")}, 1.0, "bm25")


class FakeRetriever:
    """Returns the two passages above for every query, tagged with the requested jurisdiction. Raises on 'exclusion'."""

    def __init__(self):
        self.calls = []

    def search(self, query, k=5, jurisdictions=None, **kw):
        self.calls.append((query, k, set(jurisdictions or [])))
        if "exclusion" in query.lower():
            raise RuntimeError("index exploded")
        j = next(iter(jurisdictions)) if jurisdictions else "Florida"
        return [_hit({**p, "jurisdiction": j}) for p in PASSAGES][:k]


class FakeAnswerProvider:
    """Answers by the question's topic word: covered -> good quote; limit -> fabricated quote; appeal -> abstain; condition -> raises."""

    model = "fake-muse"

    def __init__(self):
        self.calls = 0
        self.last_response = {"usage": {"prompt_tokens": 400, "completion_tokens": 120, "completion_tokens_details": {"reasoning_tokens": 90}}}

    def complete(self, system, user, max_tokens=600):
        self.calls += 1
        self.max_tokens = max_tokens
        q = user.rsplit("Question:", 1)[1].lower()
        if "covered" in q:
            out = {"answer": "Yes, for recipients under 21 when medically necessary.", "abstain": False, "citations": [{"passage": "P1", "quote": "covers private duty nursing services for recipients under the age of 21 years"}, {"passage": "P1", "quote": "this sentence is nowhere on the page at all, invented"}]}
        elif "limit" in q:
            out = {"answer": "Up to 24 hours a day with no cap.", "abstain": False, "citations": [{"passage": "P1", "quote": "private duty nursing is covered twenty four hours a day with no cap"}]}
        elif "appeal" in q:
            out = {"answer": ABSTAIN_TEXT, "abstain": True, "citations": []}
        elif "condition" in q or "prior authorization" in q:
            raise RuntimeError("model timeout")
        else:
            out = {"answer": "The rules say the plan may limit services to the authorized amount.", "abstain": False, "citations": [{"passage": "P1", "quote": "Services must be medically necessary and prior authorized."}]}
        return json.dumps(out), 400, 120

    def cost(self, n_in, n_out):
        return 0.0005 if n_out else 0.0


def test_investigate_case_end_to_end_with_fakes():
    case = {"case_id": "c_test01", "card": card()}
    retriever, provider = FakeRetriever(), FakeAnswerProvider()
    seen = []
    inv = investigate_case(case, retriever, provider, on_progress=lambda partial: seen.append(json.loads(json.dumps(partial))))

    assert inv["status"] == "done" and inv["error"] is None and inv["finished_at"] and inv["started_at"] <= inv["finished_at"]
    assert inv["model"] == "fake-muse"
    assert inv["questions_planned"] == 6 and inv["questions_done"] == 6 and len(inv["findings"]) == 6
    assert [f["id"] for f in inv["findings"]] == ["f1", "f2", "f3", "f4", "f5", "f6"]
    assert all(f["jurisdiction"] == "Florida" for f in inv["findings"])
    by_topic = {f["topic"]: f for f in inv["findings"]}

    cov = by_topic["coverage"]
    assert cov["status"] == "supported" and cov["answer"].startswith("Yes")
    assert len(cov["citations"]) == 1 and cov["citations"][0]["doc_id"] == "fl-04" and cov["citations"][0]["title"] == "PDN policy" and cov["citations"][0]["page"] == 3 and cov["citations"][0]["overlap"] >= 0.8
    assert len(cov["struck"]) == 1 and cov["struck"][0]["reason"] == "quote not found on the cited page"

    lim = by_topic["limits"]
    assert lim["status"] == "unsupported" and lim["answer"] == "Up to 24 hours a day with no cap." and lim["citations"] == []
    assert lim["struck"][0]["reason"] == "quote not found on the cited page" and lim["struck"][0]["doc_id"] == "fl-04"

    app = by_topic["appeal"]
    assert app["status"] == "not_settled" and app["citations"] == [] and app["struck"] == []

    # the provider raised inside answer_question: not_settled with the error class, case still done
    con = by_topic["conditions"]
    assert con["status"] == "not_settled" and con["answer"] == "Could not investigate this question: RuntimeError" and con["struck"] == []
    # the retriever raised: same treatment
    exc = by_topic["exclusions"]
    assert exc["status"] == "not_settled" and exc["answer"] == "Could not investigate this question: RuntimeError"

    assert by_topic["reason"]["status"] == "supported"

    for f in inv["findings"]:
        assert set(f) >= {"id", "question", "topic", "jurisdiction", "status", "answer", "citations", "struck", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd"}
        assert f["model"] == "fake-muse" and f["latency_ms"] >= 0
    assert cov["input_tokens"] == 400 and cov["output_tokens"] == 120 and cov["reasoning_tokens"] == 90 and cov["cost_usd"] == 0.0005

    # coverage math: claims = supported + unsupported
    assert inv["coverage"] == {"claims": 3, "supported": 2}
    assert inv["cost_usd"] == pytest.approx(0.0005 * 4, abs=1e-9)  # four model answers (two questions failed before cost)
    assert inv["latency_ms"] >= 0
    assert provider.max_tokens >= 2000
    assert all(k == 5 and len(j) == 1 for _, k, j in retriever.calls)

    # progress: one call per finding, growing, plus the final one
    assert len(seen) == 7
    assert [p["questions_done"] for p in seen] == [1, 2, 3, 4, 5, 6, 6]
    assert seen[0]["status"] == "running" and seen[-1]["status"] == "done"
    assert seen[0]["findings"][0]["id"] == "f1" and len(seen[2]["findings"]) == 3

    # trace: spans per question
    tr = inv["trace"]
    assert set(tr) >= {"trace_id", "spans", "total_ms", "question"}
    names = [s["name"] for s in tr["spans"]]
    assert names.count("question") == 6 and "route" in names and "plan" in names
    assert [s["id"] for s in tr["spans"] if s["name"] == "question"] == ["f1", "f2", "f3", "f4", "f5", "f6"]
    assert inv.get("plan", {}).get("source") == "template"


def test_investigate_case_dual_route_runs_each_question_per_jurisdiction():
    case = {"case_id": "c_dual", "card": card(program="unknown")}
    inv = investigate_case(case, FakeRetriever(), FakeAnswerProvider())
    assert inv["questions_planned"] == 12 and len(inv["findings"]) == 12
    assert [f["jurisdiction"] for f in inv["findings"]][:4] == ["Florida", "Federal", "Florida", "Federal"]
    assert inv["findings"][0]["question"] == inv["findings"][1]["question"]


def test_investigate_case_fails_only_outside_the_loop():
    case = {"case_id": "c_bad"}  # no card at all: the failure happens before the loop
    seen = []
    inv = investigate_case(case, FakeRetriever(), FakeAnswerProvider(), on_progress=lambda p: seen.append(p["status"]))
    assert inv["status"] == "failed" and inv["error"] and inv["finished_at"] and inv["findings"] == []
    assert seen[-1] == "failed"


# ---- fixture investigator ---------------------------------------------------


def test_fixture_investigator_shows_all_three_states_from_real_manifest_titles():
    import csv

    manifest = {r["id"]: r for r in csv.DictReader(open(Path(__file__).resolve().parent.parent / "corpus" / "manifest.csv", encoding="utf-8"))}
    fx = FixtureInvestigator(delay=0)
    assert fx.model == "fixture"
    case = {"case_id": "c_fixture", "card": card()}
    seen = []
    inv = fx.investigate(case, on_progress=lambda p: seen.append(p["questions_done"]))
    assert inv["status"] == "done" and inv["model"] == "fixture" and inv["error"] is None
    assert inv["questions_planned"] == 5 and inv["questions_done"] == 5 and len(inv["findings"]) == 5
    statuses = [f["status"] for f in inv["findings"]]
    assert statuses.count("not_settled") == 1 and statuses.count("unsupported") == 1 and statuses.count("supported") == 3
    assert inv["coverage"] == {"claims": 4, "supported": 3}
    assert {f["topic"] for f in inv["findings"]} >= {"coverage", "appeal", "reason"}
    for f in inv["findings"]:
        for c in f["citations"] + f["struck"]:
            assert c["doc_id"] in manifest and c["title"] == manifest[c["doc_id"]]["title"] and manifest[c["doc_id"]]["jurisdiction"] == "Florida"
            assert "synthetic" in c["quote"].lower()
        assert f["jurisdiction"] == "Florida" and f["model"] == "fixture" and f["cost_usd"] == 0.0
    docs = {c["doc_id"] for f in inv["findings"] for c in f["citations"]}
    assert any("private duty nursing" in manifest[d]["title"].lower() for d in docs)
    unsupported = next(f for f in inv["findings"] if f["status"] == "unsupported")
    assert unsupported["answer"] and unsupported["citations"] == [] and unsupported["struck"][0]["reason"] == "quote not found on the cited page"
    assert seen == [1, 2, 3, 4, 5, 5]
    assert inv["trace"]["spans"] and inv["trace"].get("synthetic") is True
    assert FixtureInvestigator().delay == 0.8
    assert fx.route(case["card"]).jurisdictions == ["Florida"]

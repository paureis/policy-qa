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
    assert set(d) == {"program", "jurisdictions", "dual", "reason", "outside_corpus"}
    assert d["program"] == (over["program"] if over.get("program") else ("unknown" if "program" in over else "florida_medicaid_mma"))


def test_route_accepts_plain_values_too():
    r = route_case({"program": "medicare_a", "member_age_group": "65_plus", "payer_name": "Medicare"})
    assert r.jurisdictions == ["Federal"] and not r.dual


# ---- template questions -----------------------------------------------------


def test_template_questions_cover_the_six_topics_in_plain_words():
    c = card()
    qs = template_questions(c, route_case(c))
    topics = [q.topic for q in qs]
    assert topics == ["coverage", "limits", "conditions", "exclusions", "appeal", "reason", "exclusions"]
    assert all(isinstance(q, PlannedQuestion) and q.question.endswith("?") for q in qs)
    assert qs[0].question == "Is private duty nursing, 8 hours/day covered under Florida Medicaid (MMA) for a member under 21?"
    assert "prior authorization" in qs[2].question
    assert "deadline" in qs[4].question
    assert qs[5].question == "What do the rules say when services exceed the authorized amount?"
    assert qs[6].question == "Is there an exception under Florida Medicaid (MMA) that covers private duty nursing, 8 hours/day even though services exceed the authorized amount?"


def test_template_questions_without_a_reason_or_service():
    c = card(denial_reason=None, service=None, program="unknown")
    qs = template_questions(c, route_case(c))
    assert [q.topic for q in qs][-2] == "reason"
    assert qs[-1].question == "Is there an exception under Florida Medicaid or Medicare that covers the service?"
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
    assert [q.question for q in qs][:5] == [q["question"] for q in GOOD_PLAN["questions"]]
    assert [q.topic for q in qs] == ["coverage", "limits", "conditions", "appeal", "reason", "exclusions"]  # + the exception question (Oct 27)
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
    assert len(qs) == 7 and "exception" in qs[-1].question  # the exception question is always present too (Oct 27)


def test_plan_caps_at_seven_questions():
    c = card()
    r = route_case(c)
    many = {"questions": [{"topic": "other", "question": f"Question number {i}: which rule covers private duty nursing under Florida Medicaid?"} for i in range(12)] + GOOD_PLAN["questions"][-2:]}
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
    assert inv["questions_planned"] == 7 and inv["questions_done"] == 7 and len(inv["findings"]) == 7
    assert [f["id"] for f in inv["findings"]] == ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    assert all(f["jurisdiction"] == "Florida" for f in inv["findings"])
    by_topic = {f["topic"]: f for f in inv["findings"][:6]}  # f7 is the exception question (topic exclusions)

    cov = by_topic["coverage"]
    assert cov["status"] == "supported" and cov["answer"].startswith("Yes")
    assert len(cov["citations"]) == 1 and cov["citations"][0]["doc_id"] == "fl-04" and cov["citations"][0]["title"] == "PDN policy" and cov["citations"][0]["page"] == 3 and cov["citations"][0]["overlap"] >= 0.8
    assert len(cov["struck"]) == 1 and cov["struck"][0]["reason"] == "quote not found on the cited page"

    lim = by_topic["limits"]
    assert lim["status"] == "unsupported" and lim["answer"] == "Up to 24 hours a day with no cap." and lim["citations"] == []
    assert lim["struck"][0]["reason"] == "quote not found on the cited page" and lim["struck"][0]["doc_id"] == "fl-04"

    app = by_topic["appeal"]
    assert app["status"] == "not_settled" and app["citations"] == [] and app["struck"] == []

    # the provider raised inside answer_question: an error finding, not an abstention; case still done
    con = by_topic["conditions"]
    assert con["status"] == "error" and con["answer"] == "" and con["error"] == "RuntimeError: model timeout"
    assert con["citations"] == [] and con["struck"] == []
    assert [p["doc_id"] for p in con["passages"]] == ["fl-04", "fl-21"]  # retrieval worked, so the passages are kept
    # the retriever raised: same treatment, no passages
    exc = by_topic["exclusions"]
    assert exc["status"] == "error" and exc["answer"] == "" and exc["error"] == "RuntimeError: index exploded" and exc["passages"] == []
    assert all(f["error"] is None for f in inv["findings"] if f["status"] != "error")

    assert by_topic["reason"]["status"] == "supported"
    assert inv["findings"][6]["status"] == "supported" and "exception" in inv["findings"][6]["question"]

    for f in inv["findings"]:
        assert set(f) >= {"id", "question", "topic", "jurisdiction", "status", "answer", "citations", "struck", "passages", "error", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd"}
        assert f["model"] == "fake-muse" and f["latency_ms"] >= 0
    assert cov["input_tokens"] == 400 and cov["output_tokens"] == 120 and cov["reasoning_tokens"] == 90 and cov["cost_usd"] == 0.0005

    # coverage math: claims = supported + unsupported; errors are counted apart
    assert inv["coverage"] == {"claims": 4, "supported": 3, "errors": 2}
    assert inv["cost_usd"] == pytest.approx(0.0005 * 5, abs=1e-9)  # five model answers (two questions failed before cost)
    assert inv["latency_ms"] >= 0
    assert provider.max_tokens >= 2000
    assert all(k == 8 * 4 and len(j) == 1 for _, k, j in retriever.calls)  # 8 passages from a pool of 32 candidates

    # progress: one call per finding, growing, plus the final one
    assert len(seen) == 8
    assert [p["questions_done"] for p in seen] == [1, 2, 3, 4, 5, 6, 7, 7]
    assert seen[0]["status"] == "running" and seen[-1]["status"] == "done"
    assert len(seen[0]["findings"]) == 1 and len(seen[2]["findings"]) == 3
    # every snapshot lists its findings in planned order, whatever order they finished in
    for p in seen:
        ids = [int(f["id"][1:]) for f in p["findings"]]
        assert ids == sorted(ids)

    # trace: spans per question
    tr = inv["trace"]
    assert set(tr) >= {"trace_id", "spans", "total_ms", "question"}
    names = [s["name"] for s in tr["spans"]]
    assert names.count("question") == 7 and "route" in names and "plan" in names
    assert sorted(s["id"] for s in tr["spans"] if s["name"] == "question") == ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    assert inv.get("plan", {}).get("source") == "template"


def test_investigate_case_dual_route_runs_each_question_per_jurisdiction():
    case = {"case_id": "c_dual", "card": card(program="unknown")}
    inv = investigate_case(case, FakeRetriever(), FakeAnswerProvider())
    assert inv["questions_planned"] == 14 and len(inv["findings"]) == 14
    assert [f["jurisdiction"] for f in inv["findings"]][:4] == ["Florida", "Federal", "Florida", "Federal"]
    # one planned question, asked in each column's own program's terms (Oct 30)
    assert inv["findings"][0]["planned_question"] == inv["findings"][1]["planned_question"] == "Is private duty nursing, 8 hours/day covered under Florida Medicaid or Medicare for a member under 21?"
    assert inv["findings"][0]["question"] == "Is private duty nursing, 8 hours/day covered under Florida Medicaid for a member under 21?"
    assert inv["findings"][1]["question"] == "Is private duty nursing, 8 hours/day covered under Medicare for a member under 21?"


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
    assert inv["coverage"] == {"claims": 4, "supported": 3, "errors": 0}
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


# ---- Oct 26 live-run fixes ----------------------------------------------------

import csv  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

MANIFEST_ROWS = {r["id"]: r for r in csv.DictReader(open(Path(__file__).resolve().parent.parent / "corpus" / "manifest.csv", encoding="utf-8"))}


def test_appeal_question_is_about_the_programs_process_not_the_service():
    from policyqa.investigate import PLAN_SYSTEM_PROMPT

    c = card()
    appeal = next(q for q in template_questions(c, route_case(c)) if q.topic == "appeal")
    assert "nursing" not in appeal.question.lower()
    assert "Florida Medicaid (MMA)" in appeal.question
    for word in ("adverse benefit determination", "fair hearing", "deadline", "file"):
        assert word in appeal.question
    assert "do not name the service" in PLAN_SYSTEM_PROMPT


def _hit_row(doc, i, jur="Florida", title=None, text="private duty nursing prior authorization hours"):
    return Hit({"chunk_id": f"{doc}:p{i:03d}:0", "doc_id": doc, "page": i, "title": title or f"Title of {doc}", "jurisdiction": jur, "text": text}, 1.0, "bm25")


def test_select_passages_caps_per_document_and_excludes():
    from policyqa.investigate import select_passages

    hits = [_hit_row("fl-04", i) for i in range(1, 11)] + [_hit_row("fl-27", 1), _hit_row("fl-21", 1), _hit_row("fl-21", 2), _hit_row("fl-03", 1)]
    out = select_passages(hits, k=8, per_doc_cap=3, exclude={"fl-27"})
    assert [h.chunk["doc_id"] for h in out[:6]] == ["fl-04", "fl-04", "fl-04", "fl-21", "fl-21", "fl-03"]
    assert [h.chunk["page"] for h in out[:3]] == [1, 2, 3]  # rank order kept inside a document
    # too few other documents: the capped fl-04 hits fill the list to k, in rank order (Oct 27)
    assert [(h.chunk["doc_id"], h.chunk["page"]) for h in out[6:]] == [("fl-04", 4), ("fl-04", 5)]
    # no cap: the first eight, one document fills the list
    assert {h.chunk["doc_id"] for h in select_passages(hits, k=8, per_doc_cap=None)} == {"fl-04"}


def test_retrieval_on_a_small_index_caps_one_dominant_document(tmp_path):
    from policyqa.index import Index
    from policyqa.investigate import retrieve_passages
    from policyqa.retrieve import Retriever

    rows = [{"chunk_id": f"fl-04:p{i:03d}:0", "doc_id": "fl-04", "page": i, "pos": 0, "title": "PDN policy", "jurisdiction": "Florida", "text": f"appeal fair hearing deadline appeal fair hearing deadline page {i}"} for i in range(1, 13)]
    for d in ("fl-21", "fl-22", "fl-23"):
        rows += [{"chunk_id": f"{d}:p{i:03d}:0", "doc_id": d, "page": i, "pos": 0, "title": d, "jurisdiction": "Florida", "text": f"enrollee appeal fair hearing page {i} contract terms"} for i in range(1, 4)]
    rows += [{"chunk_id": "fed-17:p001:0", "doc_id": "fed-17", "page": 1, "pos": 0, "title": "Medicare appeals", "jurisdiction": "Federal", "text": "appeal fair hearing deadline appeal fair hearing deadline"}]
    with open(tmp_path / "chunks.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    r = Retriever(Index(tmp_path / "chunks.jsonl"), mode="bm25")
    q = "appeal fair hearing deadline"
    assert {h.chunk["doc_id"] for h in r.search(q, k=8, jurisdictions={"Florida"})} == {"fl-04"}  # without the cap
    hits = retrieve_passages(r, q, "Florida", k=8, per_doc_cap=3)
    docs = [h.chunk["doc_id"] for h in hits]
    assert len(hits) == 8 and max(docs.count(d) for d in docs) <= 3 and docs[:3] == ["fl-04"] * 3
    assert "fed-17" not in docs
    assert "fl-21" not in [h.chunk["doc_id"] for h in retrieve_passages(r, q, "Florida", k=8, per_doc_cap=3, exclude={"fl-21"})]


def test_program_excludes_from_the_real_manifest():
    from policyqa.investigate import program_excludes

    kid = {d for d, r in MANIFEST_ROWS.items() if "kidcare" in r["title"].lower() or "healthy kids" in r["title"].lower()}
    assert "fl-27" in kid
    assert program_excludes("florida_medicaid_mma") == kid
    assert program_excludes("florida_medicaid_ltc") == kid
    assert "fl-27" in program_excludes("florida_medicaid_mma")
    for p in ("florida_kidcare", "medicare_a", "medicare_b", "medicare_advantage", "medicare_part_d", "unknown", None):
        assert program_excludes(p) == set()


class RecordingProvider:
    """Records each user message; answers from P1 with a verbatim quote. Thread-safe enough for counting."""

    model = "rec"

    def __init__(self, sleep=0.0, slow_word=None):
        self.users = []
        self.sleep = sleep
        self.slow_word = slow_word
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    def complete(self, system, user, max_tokens=600):
        with self.lock:
            self.users.append(user)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            q = user.rsplit("Question:", 1)[1].lower()
            time.sleep(self.sleep * (2 if self.slow_word and self.slow_word in q else 1))
            m = user.split("[P1]", 1)[1].split("\n", 2)[1] if "[P1]" in user else ""
            quote = " ".join(m.split()[:12])
            return json.dumps({"answer": "From the passage.", "abstain": False, "citations": [{"passage": "P1", "quote": quote}]}), 100, 20
        finally:
            with self.lock:
                self.active -= 1

    def cost(self, n_in, n_out):
        return 0.001


class PoolRetriever:
    """Returns a fixed ranked pool: ten fl-04 chunks, then a KidCare chunk, then other documents."""

    def __init__(self):
        self.calls = []

    def search(self, query, k=5, jurisdictions=None, **kw):
        self.calls.append((query, k, jurisdictions))
        j = next(iter(jurisdictions))
        pool = [_hit_row("fl-04", i, j, text=f"Private duty nursing rule number {i} applies to recipients under 21 years of age.") for i in range(1, 11)]
        pool += [_hit_row("fl-27", 1, j, text="Florida Healthy Kids covers many services for enrolled children and families.")]
        pool += [_hit_row(d, 1, j, text=f"Document {d} states a rule for enrollees in the managed care plan.") for d in ("fl-21", "fl-22", "fl-20", "fl-16", "fl-03")]
        return pool[:k]


def test_investigation_records_passages_capped_excluded_and_names_the_program():
    case = {"case_id": "c_cap", "card": card()}
    prov = RecordingProvider()
    inv = investigate_case(case, PoolRetriever(), prov)
    assert inv["status"] == "done"
    for f in inv["findings"]:
        docs = [p["doc_id"] for p in f["passages"]]
        assert len(docs) == 8 and "fl-27" not in docs and max(docs.count(d) for d in docs) <= 3
        assert docs == ["fl-04"] * 3 + ["fl-21", "fl-22", "fl-20", "fl-16", "fl-03"]
        assert set(f["passages"][0]) == {"chunk_id", "doc_id", "title", "page"}
        assert f["passages"][0] == {"chunk_id": "fl-04:p001:0", "doc_id": "fl-04", "title": "Title of fl-04", "page": 1}
    sentence = "The case is under Florida Medicaid (MMA). Prefer passages about that program; if a passage is about another program, do not use it."
    assert all(sentence in u for u in prov.users)
    from policyqa.generate import SYSTEM_PROMPT

    assert "Prefer passages about that program" not in SYSTEM_PROMPT


def test_dual_route_names_the_program_of_each_jurisdiction():
    case = {"case_id": "c_dual2", "card": card(member_age_group="65_plus")}
    prov = RecordingProvider()
    inv = investigate_case(case, PoolRetriever(), prov)
    assert {f["jurisdiction"] for f in inv["findings"]} == {"Florida", "Federal"}
    assert any("The case is under Florida Medicaid (MMA)." in u for u in prov.users)
    assert any("The case is under Medicare." in u for u in prov.users)


def test_parallel_answers_keep_order_and_count_progress():
    case = {"case_id": "c_par", "card": card()}
    prov = RecordingProvider(sleep=0.05, slow_word="covered")  # the first question takes twice as long
    seen = []
    t = time.perf_counter()
    inv = investigate_case(case, PoolRetriever(), prov, on_progress=lambda p: seen.append(p))
    wall = time.perf_counter() - t
    assert inv["status"] == "done" and len(inv["findings"]) == 7
    assert wall < 0.3, wall  # serial would be 0.4 s (one 0.1 s answer and six 0.05 s answers)
    assert prov.max_active == 3
    assert [f["id"] for f in inv["findings"]] == ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    assert [f["topic"] for f in inv["findings"]] == ["coverage", "limits", "conditions", "exclusions", "appeal", "reason", "exclusions"]
    assert [p["questions_done"] for p in seen] == [1, 2, 3, 4, 5, 6, 7, 7]
    assert seen[0]["findings"][0]["id"] != "f1"  # the slow first question finished later, yet sits first at the end
    assert inv["cost_usd"] == pytest.approx(0.007)
    assert inv["latency_ms"] == pytest.approx(wall * 1000, rel=0.5)


def test_plan_tokens_and_cost_count_when_the_plan_falls_back_after_a_reply():
    c = card()
    r = route_case(c)
    stats: dict = {}
    qs = plan_questions(c, r, FakePlanProvider("this is not json"), stats=stats)
    assert [q.question for q in qs] == [q.question for q in template_questions(c, r)]
    assert stats["source"] == "template" and "JSONDecodeError" in stats["error"]
    assert stats["input_tokens"] == 100 and stats["output_tokens"] == 50 and stats["reasoning_tokens"] == 30 and stats["cost_usd"] == 0.001
    # too few usable questions after a reply: same
    few = {"questions": [{"topic": "appeal", "question": "How do I appeal a denial under Florida Medicaid?"}]}
    stats = {}
    plan_questions(c, r, FakePlanProvider(json.dumps(few)), stats=stats)
    assert stats["source"] == "template" and "usable" in stats["error"] and stats["cost_usd"] == 0.001
    # no reply at all: nothing to count
    stats = {}
    plan_questions(c, r, FakePlanProvider("{}", raise_exc=RuntimeError("boom")), stats=stats)
    assert stats["source"] == "template" and stats["input_tokens"] == 0 and stats["cost_usd"] == 0.0


def test_investigation_cost_includes_a_failed_plan_reply():
    class PlanThenAnswer(RecordingProvider):
        last_response = {"usage": {"completion_tokens_details": {"reasoning_tokens": 7}}}

        def complete_parts(self, system, parts, schema=None, max_tokens=1500):
            return "not json at all", 300, 200

        def cost(self, n_in, n_out):
            return 0.01 if n_in == 300 else 0.001

    inv = investigate_case({"case_id": "c_pc", "card": card()}, PoolRetriever(), PlanThenAnswer())
    assert inv["plan"]["source"] == "template" and inv["plan"]["error"] and inv["plan"]["cost_usd"] == 0.01
    assert inv["plan"]["input_tokens"] == 300 and inv["plan"]["output_tokens"] == 200
    assert inv["cost_usd"] == pytest.approx(0.01 + 7 * 0.001)


def test_planner_medical_filter_and_rule_words():
    from policyqa.investigate import planned_question_allowed

    assert not planned_question_allowed("Which medication should the member switch to instead of nursing care?")
    assert not planned_question_allowed("Was nursing medically necessary for the child's diagnosis of cerebral palsy?")
    for bad in (
        "What medication does Florida Medicaid cover instead of nursing?",
        "Is it safe to reduce private duty nursing hours under the policy?",
        "Should the patient take a different therapy if the appeal fails?",
        "Is private duty nursing appropriate for the patient under the coverage rules?",
        "What treatment for cerebral palsy does the policy cover?",
        "Does the member need more help at home?",  # no rule word
    ):
        assert not planned_question_allowed(bad), bad
    for c in (card(), card(denial_reason=None, service=None, program="unknown"), card(program="medicare_b", member_age_group="65_plus")):
        for q in template_questions(c, route_case(c)):
            assert planned_question_allowed(q.question), q.question
    for q in GOOD_PLAN["questions"]:
        assert planned_question_allowed(q["question"]), q
    # the planner drops them
    plan = {"questions": GOOD_PLAN["questions"] + [
        {"topic": "other", "question": "Which medication should the member switch to instead of nursing care?"},
        {"topic": "other", "question": "Was nursing medically necessary for the child's diagnosis of cerebral palsy?"},
    ]}
    qs = plan_questions(card(), route_case(card()), FakePlanProvider(json.dumps(plan)))
    assert [q.question for q in qs][:5] == [q["question"] for q in GOOD_PLAN["questions"]] and len(qs) == 6


def test_struck_reasons_are_unchanged():
    from policyqa.generate import STRUCK_NOT_FOUND, STRUCK_NOT_SHOWN, STRUCK_TOO_SHORT

    assert (STRUCK_NOT_FOUND, STRUCK_NOT_SHOWN, STRUCK_TOO_SHORT) == ("quote not found on the cited page", "cited a passage that was not shown", "quote too short to verify")


def test_fixture_honors_a_dual_route():
    fx = FixtureInvestigator(delay=0)
    inv = fx.investigate({"case_id": "c_fx65", "card": card(member_age_group="65_plus")})
    assert inv["status"] == "done"
    js = [f["jurisdiction"] for f in inv["findings"]]
    assert set(js) == {"Florida", "Federal"} and inv["questions_planned"] == len(inv["findings"]) == inv["questions_done"]
    assert [f["id"] for f in inv["findings"]] == [f"f{i}" for i in range(1, len(js) + 1)]
    fed = [f for f in inv["findings"] if f["jurisdiction"] == "Federal"]
    assert any(f["status"] == "supported" for f in fed)
    for f in fed:
        assert "Florida Medicaid" not in f["question"]
        for c in f["citations"] + f["struck"]:
            assert c["doc_id"].startswith("fed-") and MANIFEST_ROWS[c["doc_id"]]["jurisdiction"] == "Federal" and c["title"] == MANIFEST_ROWS[c["doc_id"]]["title"]
            assert c["quote"].startswith("[synthetic fixture quote, not from the document]")
        for p in f["passages"]:
            assert p["doc_id"].startswith("fed-")
    assert inv["coverage"]["errors"] == 0
    # a Medicare-only card gives Federal findings only; the default card stays Florida only
    inv = fx.investigate({"case_id": "c_fxmc", "card": card(program="medicare_b", member_age_group="65_plus", payer_name="Medicare")})
    assert {f["jurisdiction"] for f in inv["findings"]} == {"Federal"}
    inv = fx.investigate({"case_id": "c_fxfl", "card": card()})
    assert {f["jurisdiction"] for f in inv["findings"]} == {"Florida"} and len(inv["findings"]) == 5
    assert all(set(f) >= {"passages", "error"} for f in inv["findings"])


def test_route_names_a_plan_outside_the_corpus():
    """A commercial or employer plan is not a program in the corpus: the route says no document governs it."""
    for payer in ("Sample Employer Health Plan", "Acme Group Health Plan", "Blue Commercial PPO", "Marketplace Silver Plan"):
        r = route_case(card(program="unknown", payer_name=payer))
        assert r.program == "unknown" and r.jurisdictions == ["Florida", "Federal"] and r.dual is True
        assert r.outside_corpus is True
        assert "No document in the corpus governs" in r.reason and payer in r.reason
        assert r.to_dict()["outside_corpus"] is True
    r = route_case(card(program="unknown", payer_name="Sunshine Health"))
    assert r.outside_corpus is False and "does not say which program" in r.reason
    r = route_case(card(program="florida_medicaid_mma", payer_name="Employer Health Plan"))
    assert r.outside_corpus is False


# ---- Oct 27 tuning: exceptions elsewhere in the document --------------------


def test_the_per_document_cap_never_shrinks_the_list_when_one_document_governs():
    """dc-026 shape: Part D has one governing manual (fed-10). Its exception page (p14, rosacea not
    cosmetic) ranked 4th in the live pool, and the cap of 3 dropped it. The cap diversifies the head of
    the list; when too few other documents exist, the capped hits fill the rest in rank order."""
    from policyqa.investigate import select_passages

    pool = [_hit_row("fed-10", p, "Federal") for p in (51, 15, 52, 14, 55, 54)] + [_hit_row("fed-11", 21, "Federal")]
    out = select_passages(pool, k=8, per_doc_cap=3)
    got = [(h.chunk["doc_id"], h.chunk["page"]) for h in out]
    assert got[:4] == [("fed-10", 51), ("fed-10", 15), ("fed-10", 52), ("fed-11", 21)]  # the diversified head is unchanged
    assert got[4:] == [("fed-10", 14), ("fed-10", 55), ("fed-10", 54)]  # then the capped hits, in rank order
    # an excluded document still never comes back
    assert "fed-11" not in [h.chunk["doc_id"] for h in select_passages(pool, k=8, per_doc_cap=3, exclude={"fed-11"})]


def test_template_asks_whether_an_exception_covers_the_service_despite_the_reason():
    """dc-018 shape: the routine-services list excludes eyeglasses; the exception (one pair after cataract
    surgery) is on the next page. The plan must ask for the exception, worded so retrieval reaches it."""
    from policyqa.investigate import planned_question_allowed

    c = card(program="medicare_b", payer_name="Medicare", member_age_group="65_plus", service="eyeglass frames after cataract surgery", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    qs = template_questions(c, route_case(c))
    exc = [q for q in qs if "exception" in q.question.lower()]
    assert len(exc) == 1 and exc[0].topic == "exclusions"
    assert exc[0].question == "Is there an exception under Medicare Part B that covers eyeglass frames after cataract surgery even though medicare does not cover eyeglasses or contact lenses?"
    assert planned_question_allowed(exc[0].question)
    assert len(qs) <= 7 and {"appeal", "reason"} <= {q.topic for q in qs}


def test_a_model_plan_without_an_exception_question_gets_the_template_one():
    c = card()
    r = route_case(c)
    p = FakePlanProvider(json.dumps(GOOD_PLAN))
    qs = plan_questions(c, r, p)
    assert [q.question for q in qs[:5]] == [q["question"] for q in GOOD_PLAN["questions"]]
    assert qs[5] == template_questions(c, r)[-1] and len(qs) == 6
    assert "exception" in p.calls[0]["system"].lower()
    # the model's own exception question is kept and nothing is added
    own = {"questions": GOOD_PLAN["questions"] + [{"topic": "exclusions", "question": "Is there an exception that lets Florida Medicaid cover more private duty nursing hours than the plan authorized?"}]}
    qs = plan_questions(c, r, FakePlanProvider(json.dumps(own)))
    assert [q.question for q in qs] == [q["question"] for q in own["questions"]]
    # the cap keeps appeal, reason and the exception question
    many = {"questions": [{"topic": "other", "question": f"Question number {i}: which rule covers private duty nursing under Florida Medicaid?"} for i in range(12)] + GOOD_PLAN["questions"][-2:]}
    qs = plan_questions(c, r, FakePlanProvider(json.dumps(many)))
    assert len(qs) == 7 and any("exception" in q.question.lower() for q in qs)


QMB_REASON = "Florida Medicaid did not pay the Medicare coinsurance for this visit, so the remaining balance is the patient's responsibility."
QMB_QUESTION = "Can a provider bill a member in the Qualified Medicare Beneficiary (QMB) program, or a member with both Medicare and Medicaid, for Medicare cost-sharing (deductible, coinsurance, or copayment) for office visit, established patient?"


@pytest.mark.parametrize("program", ["unknown", "medicare_b"])
def test_a_medicare_and_medicaid_member_routes_both_and_asks_the_qmb_cost_sharing_question(program):
    """dc-021 shape: a provider statement bills a QMB member the Medicare coinsurance Medicaid did not pay.
    The rule (fed-20 p7) is about the member's second program, which no service question reaches."""
    from policyqa.investigate import planned_question_allowed

    c = card(program=program, payer_name="Sample Medical Group", member_age_group="65_plus", service="office visit, established patient", service_code="99214", denial_reason=QMB_REASON)
    r = route_case(c)
    assert r.jurisdictions == ["Florida", "Federal"] and r.dual is True and r.outside_corpus is False
    qs = template_questions(c, r)
    assert qs[-1].question == QMB_QUESTION and planned_question_allowed(QMB_QUESTION)
    assert len(qs) == 7
    # a model plan with only a generic exception question still gets the QMB question
    plan = {"questions": GOOD_PLAN["questions"][:3] + [{"topic": "exclusions", "question": "Is there an exception under Medicare that covers an office visit?"}] + GOOD_PLAN["questions"][3:]}
    planned = plan_questions(c, r, FakePlanProvider(json.dumps(plan)))
    assert planned[-1].question == QMB_QUESTION


def test_a_medicare_letter_without_medicaid_still_routes_federal_only():
    c = card(program="medicare_b", payer_name="Medicare", member_age_group="65_plus", service="eyeglass frames", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    assert route_case(c).jurisdictions == ["Federal"]
    assert "QMB" not in template_questions(c, route_case(c))[-1].question


def test_the_intake_summary_reaches_the_router_and_the_planner():
    """The card has no field for the fact an exception turns on (the cataract surgery, the QMB coverage on
    file). The intake summary, shown on the case card screen, carries it to routing and planning."""

    class PlanAndAbstain(FakePlanProvider):
        def complete(self, system, user, max_tokens=600):
            return json.dumps({"answer": ABSTAIN_TEXT, "abstain": True, "citations": []}), 10, 5

    summary = "Sample Medical Group billed U. Sample, who has Medicare Part B and Florida Medicaid through the Qualified Medicare Beneficiary (QMB) program, for the coinsurance on an office visit."
    c = card(program="medicare_b", payer_name="Sample Medical Group", member_age_group="65_plus", service="office visit, established patient", denial_reason="The remaining balance is the patient's responsibility.")
    assert route_case(c).jurisdictions == ["Federal"]
    assert route_case(c, summary).jurisdictions == ["Florida", "Federal"]
    p = PlanAndAbstain(json.dumps(GOOD_PLAN))
    inv = investigate_case({"case_id": "c_sum", "card": c, "summary": summary}, FakeRetriever(), p)
    assert inv["status"] == "done"
    assert {f["jurisdiction"] for f in inv["findings"]} == {"Florida", "Federal"}
    plan_input = p.calls[0]["parts"][0]["text"]
    assert summary in plan_input
    assert any("Qualified Medicare Beneficiary" in f["question"] for f in inv["findings"])


# ---- Oct 29, third pass: the exception question also searches by the letter's fact -------------------

DC026_CARD = dict(program="medicare_part_d", payer_name="Sample Prescription Drug Plan", member_age_group="65_plus", service="Azelaic acid 15% gel, prescribed for rosacea",
                  service_code=None, denial_reason="This is a skin product used for a cosmetic purpose. Medicare Part D does not cover drugs used for cosmetic purposes.")


class FactRetriever:
    """A planned question (it ends with '?') gets eight fed-10 pages; any other query gets the rosacea exception
    page first, then the planned list's first page, so only one of its two top hits is new."""

    def __init__(self):
        self.calls = []

    def search(self, query, k=5, jurisdictions=None, **kw):
        self.calls.append(query)
        j = next(iter(jurisdictions))
        planned = [_hit_row(d, p, j) for d, p in (("fed-10", 51), ("fed-11", 2), ("fed-12", 3), ("fed-13", 4), ("fed-14", 5), ("fed-15", 6), ("fed-16", 7), ("fed-17", 8), ("fed-18", 9))]
        if query.rstrip().endswith("?"):
            return planned[:k]
        return ([_hit_row("fed-10", 14, j, text="Part D drugs indicated for the treatment of psoriasis, acne, rosacea, or vitiligo are not considered cosmetic.")] + planned)[:k]


def test_the_exception_question_also_retrieves_by_the_letters_fact_and_marks_those_passages():
    """dc-026: on Oct 28 no planned question reached fed-10 p14 (rosacea is not cosmetic): a long exception
    question dilutes the query. The exception question runs a second, short query from the letter's fact, the
    service and the program, and its new top hits take the last of the eight slots; other questions do not."""
    from policyqa.relevance import is_exception_finding

    case = {"case_id": "c_fact", "card": card(**DC026_CARD)}
    r = FactRetriever()
    inv = investigate_case(case, r, RecordingProvider())
    assert inv["status"] == "done"
    fact_queries = [q for q in r.calls if not q.rstrip().endswith("?")]
    assert len(fact_queries) == 1
    assert {"rosacea", "azelaic", "gel"} <= set(fact_queries[0].lower().split()) and "Medicare Part D" in fact_queries[0]
    exc = [f for f in inv["findings"] if is_exception_finding(f)]
    assert len(exc) == 1
    pages = [(p["doc_id"], p["page"]) for p in exc[0]["passages"]]
    assert len(pages) == 8 and pages[-1] == ("fed-10", 14)  # one new top hit; the main list keeps its order
    assert pages[:7] == [("fed-10", 51), ("fed-11", 2), ("fed-12", 3), ("fed-13", 4), ("fed-14", 5), ("fed-15", 6), ("fed-16", 7)]
    assert exc[0]["passages"][-1]["source"] == "fact" and all("source" not in p for p in exc[0]["passages"][:7])
    for f in inv["findings"]:
        if not is_exception_finding(f):
            assert ("fed-10", 14) not in [(p["doc_id"], p["page"]) for p in f["passages"]]
    # a case whose letter states no fact issues no second query
    r = FactRetriever()
    investigate_case({"case_id": "c_nofact", "card": card()}, r, RecordingProvider())
    assert all(q.rstrip().endswith("?") for q in r.calls) and len(r.calls) == 7


def test_the_fact_query_is_traced_as_its_own_retrieve_span_and_adds_no_model_call():
    """Retrieval is free; the second query must show in the trace and must not cost a model call."""
    from policyqa.relevance import is_exception_finding

    prov = RecordingProvider()
    inv = investigate_case({"case_id": "c_fact2", "card": card(**DC026_CARD)}, FactRetriever(), prov)
    exc_id = next(f["id"] for f in inv["findings"] if is_exception_finding(f))
    spans = [s for s in inv["trace"]["spans"] if s["name"] == "retrieve"]
    assert [s.get("query") for s in spans if s["id"] == exc_id] == [None, "fact"]
    assert all("query" not in s for s in spans if s["id"] != exc_id)
    assert len(prov.users) == len(inv["findings"]) == 7  # one answer call per finding, as before


# ---- Oct 30: on a dual route each column asks in its own program's terms ------------------------

DC001_CARD = dict(payer_name="Sample Health Plan", program="florida_medicaid_mma", member_age_group="under_21", service="Private duty nursing, 16 hours per day", service_code="T1000",
                  amount_billed=11520.0, denial_reason="Florida Medicaid limits private duty nursing to 8 hours per day. The request for 16 hours per day exceeds this limit.")

# Captured on Oct 30 before the dual wording change. The single-route path must stay byte-identical.
PLAN_SYSTEM_PROMPT_OCT30 = 'You plan the investigation of a health coverage denial. You will be given a case card (the program, the service, the payer\'s stated reason for the denial, and the member\'s age group). Write 4 to 7 questions that a public policy document (a Florida Medicaid coverage policy, a managed care contract, a Medicare manual, or a Medicare booklet) could answer with a verbatim quote.\n\nRules:\n1. Each question names the service and the program in plain words, as a reader with no insurance background would say them. One question per line of inquiry. The exception is the appeal question (rule 2).\n2. Topics, one per question: coverage (is the service covered), limits (hours, visits, amounts, frequency), conditions (prior authorization, medical necessity criteria, documentation), exclusions, appeal, reason (what the rules say about the payer\'s stated denial reason), other. An appeal question asks about the program\'s appeal process: the adverse benefit determination, the grievance or appeal, the fair hearing, the deadline, and where to file. Appeal questions name the program but do not name the service.\n3. Include at least one appeal question, at least one reason question about the letter\'s stated denial reason, and one exception question (topic exclusions): is there an exception, or a second rule or program, that covers this service or this member even though the stated reason applies? Policies often state an exclusion on one page and its exception on the next. Name in the exception question the facts the letter states that an exception could turn on: a related surgery or procedure, what the prescription says the drug is for, the member\'s other coverage (Medicaid, the Qualified Medicare Beneficiary (QMB) program). When the member has both Medicare and Medicaid, ask whether a provider may bill the member for Medicare cost-sharing.\n4. Ask only about coverage, billing, and appeal rules. Never ask about treatment, diagnosis, medication, dosage, or whether the care was needed. This tool never gives medical advice.\n5. Return JSON only, matching the schema: {"questions": [{"topic": "...", "question": "..."}]}'
DC001_SUMMARY_OCT30 = "Case card:\nProgram: Florida Medicaid (MMA) (jurisdictions: Florida)\nPayer: Sample Health Plan\nService: Private duty nursing, 16 hours per day\nService code: T1000\nMember age group: under_21\nPayer's stated denial reason: Florida Medicaid limits private duty nursing to 8 hours per day. The request for 16 hours per day exceeds this limit.\nAmount billed: 11520.0\n\nPlan the questions. Return JSON only."
DC001_TEMPLATE_OCT30 = [
    ("coverage", "Is Private duty nursing, 16 hours per day covered under Florida Medicaid (MMA) for a member under 21?"),
    ("limits", "What limits apply to Private duty nursing, 16 hours per day under Florida Medicaid (MMA) for a member under 21, such as hours, visits, or amounts?"),
    ("conditions", "What conditions or prior authorization does Florida Medicaid (MMA) require for Private duty nursing, 16 hours per day?"),
    ("exclusions", "What exclusions apply to Private duty nursing, 16 hours per day under Florida Medicaid (MMA)?"),
    ("appeal", "How does a member appeal an adverse benefit determination under Florida Medicaid (MMA): the appeal or grievance, the fair hearing, the deadline, and where to file?"),
    ("reason", "What do the rules say when florida Medicaid limits private duty nursing to 8 hours per day. The request for 16 hours per day exceeds this limit?"),
    ("exclusions", "Is there an exception under Florida Medicaid (MMA) that covers Private duty nursing, 16 hours per day even though florida Medicaid limits private duty nursing to 8 hours per day. The request for 16 hours per day exceeds this limit?"),
]


class PlanThenAbstain(FakePlanProvider):
    """Plans from `content`, then abstains on every answer, recording each user message."""

    def __init__(self, content, raise_exc=None):
        super().__init__(content, raise_exc)
        self.users = []
        self.lock = threading.Lock()

    def complete(self, system, user, max_tokens=600):
        with self.lock:
            self.users.append(user)
        return json.dumps({"answer": ABSTAIN_TEXT, "abstain": True, "citations": []}), 10, 5


def test_the_single_route_plan_inputs_and_questions_are_byte_identical_to_oct_30():
    """D3: the dual wording change leaves a non-dual route alone: system prompt, card summary, templates, questions asked."""
    from policyqa.investigate import PLAN_SYSTEM_PROMPT, _card_summary_for_plan

    c = card(**DC001_CARD)
    r = route_case(c)
    assert r.jurisdictions == ["Florida"] and r.dual is False
    assert PLAN_SYSTEM_PROMPT == PLAN_SYSTEM_PROMPT_OCT30
    assert _card_summary_for_plan(c, r) == DC001_SUMMARY_OCT30
    assert [(q.topic, q.question) for q in template_questions(c, r)] == DC001_TEMPLATE_OCT30
    # the model plan: the call carries exactly these strings, and every finding asks the planned question as written
    p = PlanThenAbstain(json.dumps(GOOD_PLAN))
    inv = investigate_case({"case_id": "c_dc001", "card": c}, FakeRetriever(), p)
    assert p.calls[0]["system"] == PLAN_SYSTEM_PROMPT_OCT30 and p.calls[0]["parts"] == [{"type": "text", "text": DC001_SUMMARY_OCT30}]
    assert [f["question"] for f in inv["findings"]] == [q["question"] for q in GOOD_PLAN["questions"]] + [DC001_TEMPLATE_OCT30[-1][1]]
    assert all("planned_question" not in f for f in inv["findings"])
    # the template plan: the same
    inv = investigate_case({"case_id": "c_dc001t", "card": c}, FakeRetriever(), PlanThenAbstain("not json"))
    assert inv["plan"]["source"] == "template"
    assert [(f["topic"], f["question"]) for f in inv["findings"]] == DC001_TEMPLATE_OCT30
    assert all("planned_question" not in f for f in inv["findings"])
    q_spans = [s for s in inv["trace"]["spans"] if s["name"] == "question"]
    assert all(set(s) == {"name", "ms", "id", "topic", "jurisdiction"} for s in q_spans)


DC012_CARD = dict(payer_name="Sample Long-Term Care Plan", program="florida_medicaid_ltc", member_age_group="65_plus", service="Home-delivered meals, 1 meal per day", service_code="S5170",
                  amount_billed=378.0, denial_reason="Home-delivered meals are not a covered benefit of the Long-term Care program.")
# The model plan of the live dc-012 case on Oct 30 (c_d8240f): every question names Florida Medicaid Long-term Care.
DC012_PLAN = {"questions": [
    {"topic": "coverage", "question": "Are home-delivered meals covered by Florida Medicaid Long-term Care?"},
    {"topic": "limits", "question": "What limits does Florida Medicaid Long-term Care put on home-delivered meals, such as how many meals per day or how many days can be billed?"},
    {"topic": "conditions", "question": "What does Florida Medicaid Long-term Care require for home-delivered meals, such as prior approval or proof that the member has difficulty shopping for and preparing food without help?"},
    {"topic": "exclusions", "question": "Even when home-delivered meals are said not to be covered, does Florida Medicaid Long-term Care make an exception that covers home-delivered meals when the member has difficulty shopping for and preparing food without help and also has Medicare Part A and Part B, and may a provider bill the member for Medicare cost-sharing?"},
    {"topic": "reason", "question": "What does Florida Medicaid Long-term Care say about denying home-delivered meals for the reason that home-delivered meals are not a covered benefit of the Long-term Care program?"},
    {"topic": "appeal", "question": "What is the Florida Medicaid Long-term Care appeal process for an adverse benefit determination, including the plan grievance or appeal, the Medicaid Fair Hearing, the deadline to file, and where to file?"},
]}
DC012_FEDERAL = [
    "Are home-delivered meals covered by Medicare?",
    "What limits does Medicare put on home-delivered meals, such as how many meals per day or how many days can be billed?",
    "What does Medicare require for home-delivered meals, such as prior approval or proof that the member has difficulty shopping for and preparing food without help?",
    # the governing program is swapped; the member's other coverage and "Medicare cost-sharing" are mentions and stay
    "Even when home-delivered meals are said not to be covered, does Medicare make an exception that covers home-delivered meals when the member has difficulty shopping for and preparing food without help and also has Medicare Part A and Part B, and may a provider bill the member for Medicare cost-sharing?",
    "What does Medicare say about denying home-delivered meals for the reason that home-delivered meals are not a covered benefit of the Long-term Care program?",
    # Medicare has no fair hearing: its appeal levels are redetermination, reconsideration and a hearing
    "What is the Medicare appeal process for an adverse benefit determination, including the plan grievance or appeal, the Medicare appeal levels (redetermination, reconsideration, hearing), the deadline to file, and where to file?",
]


def _by_jurisdiction(inv):
    return {j: [f["question"] for f in inv["findings"] if f["jurisdiction"] == j] for j in ("Florida", "Federal")}


def test_a_dual_route_asks_the_federal_column_in_medicare_terms_model_plan():
    """D1, dc-012 shape (Oct 30, c_d8240f): the Federal column asked Florida-worded questions of the federal documents
    and four of five came back not settled. Each column now asks in its own program's terms."""
    c = card(**DC012_CARD)
    p = PlanThenAbstain(json.dumps(DC012_PLAN))
    inv = investigate_case({"case_id": "c_dc012", "card": c}, FakeRetriever(), p)
    assert inv["plan"]["source"] == "model" and inv["status"] == "done"
    got = _by_jurisdiction(inv)
    assert got["Florida"] == [q["question"] for q in DC012_PLAN["questions"]]  # the route's own program: as planned
    assert got["Federal"] == DC012_FEDERAL
    # the question asked is the one sent to the model and recorded in the trace
    assert all(any(u.rstrip().endswith("Question: " + q) or ("Question: " + q) in u for u in p.users) for q in DC012_FEDERAL)
    spans = {s["id"]: s for s in inv["trace"]["spans"] if s["name"] == "question"}
    assert all(spans[f["id"]]["question"] == f["question"] for f in inv["findings"])


def test_a_dual_route_asks_the_federal_column_in_medicare_terms_template_plan():
    c = card(**DC012_CARD)
    inv = investigate_case({"case_id": "c_dc012t", "card": c}, FakeRetriever(), PlanThenAbstain("not json"))
    assert inv["plan"]["source"] == "template"
    got = _by_jurisdiction(inv)
    service, reason = "Home-delivered meals, 1 meal per day", "home-delivered meals are not a covered benefit of the Long-term Care program"
    assert got["Florida"] == [
        f"Is {service} covered under Florida Medicaid Long-term Care for a member who is 65 or older?",
        f"What limits apply to {service} under Florida Medicaid Long-term Care for a member who is 65 or older, such as hours, visits, or amounts?",
        f"What conditions or prior authorization does Florida Medicaid Long-term Care require for {service}?",
        f"What exclusions apply to {service} under Florida Medicaid Long-term Care?",
        "How does a member appeal an adverse benefit determination under Florida Medicaid Long-term Care: the appeal or grievance, the fair hearing, the deadline, and where to file?",
        f"What do the Florida Medicaid Long-term Care rules say when {reason}?",
        f"Is there an exception under Florida Medicaid Long-term Care that covers {service} even though {reason}?",
    ]
    assert got["Federal"] == [
        f"Is {service} covered under Medicare for a member who is 65 or older?",
        f"What limits apply to {service} under Medicare for a member who is 65 or older, such as hours, visits, or amounts?",
        f"What conditions or prior authorization does Medicare require for {service}?",
        f"What exclusions apply to {service} under Medicare?",
        "How does a member appeal an adverse benefit determination under Medicare: the appeal or grievance, the fair hearing, the deadline, and where to file?",
        f"What do the Medicare rules say when {reason}?",
        f"Is there an exception under Medicare that covers {service} even though {reason}?",
    ]


DC021_CARD = dict(program="medicare_b", payer_name="Sample Medical Group", member_age_group="65_plus", service="Office visit, established patient", service_code="99214", amount_billed=135.3,
                  denial_reason="Florida Medicaid did not pay the Medicare coinsurance for this visit, so the remaining balance is the patient's responsibility.")
# The model plan of dc-021 on Oct 30: a Medicare Part B letter whose plan asked in Florida Medicaid terms.
DC021_PLAN = {"questions": [
    {"topic": "coverage", "question": "Is an office visit with an established patient covered by Florida Medicaid?"},
    {"topic": "conditions", "question": "What prior authorization, medical necessity, or documentation rules does Florida Medicaid require for an office visit with an established patient?"},
    {"topic": "reason", "question": "What do Florida Medicaid rules say about Florida Medicaid not paying the Medicare coinsurance for an office visit with an established patient and leaving the remaining balance as the patient's responsibility?"},
    {"topic": "exclusions", "question": "For an office visit with an established patient under Florida Medicaid, when the member has both Medicare Part B as primary and Florida Medicaid secondary under the Qualified Medicare Beneficiary (QMB) program, may a provider bill the member for the Medicare coinsurance?"},
    {"topic": "appeal", "question": "For Florida Medicaid, what are the rules for an adverse benefit determination, grievance or appeal, and fair hearing, including the deadline and where to file?"},
]}


def test_the_question_about_both_programs_is_asked_as_written_in_both_columns():
    """D2, dc-021 shape: the QMB cost-sharing question is about both programs; the Federal column of a Medicare
    Part B letter asks the rest in Medicare Part B terms, the Florida column in Florida Medicaid terms."""
    c = card(**DC021_CARD)
    r = route_case(c)
    assert r.dual and r.jurisdictions == ["Florida", "Federal"]
    inv = investigate_case({"case_id": "c_dc021t", "card": c}, FakeRetriever(), PlanThenAbstain("not json"))
    got = _by_jurisdiction(inv)
    service = "Office visit, established patient"
    reason = "florida Medicaid did not pay the Medicare coinsurance for this visit, so the remaining balance is the patient's responsibility"
    qmb = f"Can a provider bill a member in the Qualified Medicare Beneficiary (QMB) program, or a member with both Medicare and Medicaid, for Medicare cost-sharing (deductible, coinsurance, or copayment) for {service}?"
    assert got["Florida"][-1] == got["Federal"][-1] == qmb
    assert got["Florida"][0] == f"Is {service} covered under Florida Medicaid for a member who is 65 or older?"
    assert got["Federal"][0] == f"Is {service} covered under Medicare Part B for a member who is 65 or older?"
    # the reason names both programs, yet it is the reason: never rewritten; the column's program fills "the rules"
    assert got["Florida"][5] == f"What do the Florida Medicaid rules say when {reason}?"
    assert got["Federal"][5] == f"What do the Medicare Part B rules say when {reason}?"
    # the model plan
    inv = investigate_case({"case_id": "c_dc021", "card": c}, FakeRetriever(), PlanThenAbstain(json.dumps(DC021_PLAN)))
    got = _by_jurisdiction(inv)
    assert got["Florida"] == [q["question"] for q in DC021_PLAN["questions"]]
    assert got["Federal"] == [
        "Is an office visit with an established patient covered by Medicare Part B?",
        "What prior authorization, medical necessity, or documentation rules does Medicare Part B require for an office visit with an established patient?",
        # the governing "Florida Medicaid rules" is swapped; the rest is the letter's own fact and stays
        "What do Medicare Part B rules say about Florida Medicaid not paying the Medicare coinsurance for an office visit with an established patient and leaving the remaining balance as the patient's responsibility?",
        DC021_PLAN["questions"][3]["question"],  # QMB
        "For Medicare Part B, what are the rules for an adverse benefit determination, grievance or appeal, and fair hearing, including the deadline and where to file?",
    ]


@pytest.mark.parametrize("phrase", [
    "Florida Medicaid", "florida medicaid", "Florida Medicaid MMA", "Florida Medicaid (MMA)", "FLORIDA MEDICAID LONG-TERM CARE", "Florida Medicaid Long-term Care",
    "Florida Medicaid managed care", "the Florida Medicaid long-term care program", "Florida KidCare", "Medicaid",
])
def test_each_florida_program_phrase_becomes_medicare_in_the_federal_column(phrase):
    from policyqa.investigate import question_for_jurisdiction

    c = card(**DC012_CARD)
    r = route_case(c)
    tail = "even though home-delivered meals are not a covered benefit of the Long-term Care program?"
    q = PlannedQuestion("coverage", f"Are Home-delivered meals, 1 meal per day covered by {phrase} {tail}")
    assert question_for_jurisdiction(q, r, "Federal", c).question == f"Are Home-delivered meals, 1 meal per day covered by Medicare {tail}"
    assert question_for_jurisdiction(q, r, "Florida", c) is q  # the route's own program: as planned


@pytest.mark.parametrize("phrase", [
    "Medicare", "medicare", "Medicare Part B", "Medicare Part A and Part B", "Medicare Advantage", "a Medicare Advantage plan", "Medicare Part D", "Part D",
    "the Medicare program", "Medicare or Florida Medicaid", "Florida Medicaid or Medicare",
])
def test_each_medicare_program_phrase_becomes_florida_medicaid_in_the_florida_column(phrase):
    from policyqa.investigate import question_for_jurisdiction

    c = card(program="medicare_part_d", payer_name="Sunshine Health Medicare-Medicaid Plan", member_age_group="65_plus", service="Azelaic acid 15% gel",
             denial_reason="Medicare does not cover drugs used for cosmetic purposes.")
    r = route_case(c)
    assert r.dual
    tail = "say about Azelaic acid 15% gel when medicare does not cover drugs used for cosmetic purposes?"
    q = PlannedQuestion("reason", f"What does {phrase} {tail}")
    assert question_for_jurisdiction(q, r, "Florida", c).question == f"What does Florida Medicaid {tail}"
    fed = question_for_jurisdiction(q, r, "Federal", c).question
    if " or " in phrase:  # neither program alone: each column names its own
        assert fed == f"What does Medicare Part D {tail}"
    else:  # the route's own program: as planned
        assert fed == q.question


def test_the_rewrite_keeps_articles_and_falls_back_to_naming_the_program():
    from policyqa.investigate import question_for_jurisdiction

    c = card(program="unknown")
    r = route_case(c)

    def ask(text, j):
        return question_for_jurisdiction(PlannedQuestion("other", text), r, j, c).question

    assert ask("What do the Florida Medicaid rules say about hours?", "Federal") == "What do the Medicare rules say about hours?"
    assert ask("Does a Medicare Advantage plan limit the hours?", "Florida") == "Does Florida Medicaid limit the hours?"
    assert ask("How many hours does the policy allow?", "Federal") == "How many hours does the policy allow under Medicare?"
    assert ask("How many hours does the policy allow?", "Florida") == "How many hours does the policy allow under Florida Medicaid?"
    assert ask("Does Florida Medicaid pay when Medicare denied the hours?", "Federal") == "Does Florida Medicaid pay when Medicare denied the hours?"  # both programs
    # a single route never rewrites
    single = route_case(card())
    q = PlannedQuestion("other", "How many hours does Medicare allow?")
    assert question_for_jurisdiction(q, single, "Florida", card()) is q


def test_a_dual_route_keeps_the_plan_count_ids_order_and_lists_each_planned_question_once():
    """D4: questions_planned, the finding ids and order, the plan record and the eval's planned_questions keep their shape."""
    from policyqa.case_evals import planned_questions

    c = card(**DC012_CARD)
    inv = investigate_case({"case_id": "c_d4", "card": c}, FakeRetriever(), PlanThenAbstain(json.dumps(DC012_PLAN)))
    n = len(DC012_PLAN["questions"])
    assert inv["plan"]["questions"] == n and inv["questions_planned"] == 2 * n == len(inv["findings"])
    assert [f["id"] for f in inv["findings"]] == [f"f{i}" for i in range(1, 2 * n + 1)]
    assert [f["jurisdiction"] for f in inv["findings"]] == ["Florida", "Federal"] * n
    assert [f["topic"] for f in inv["findings"]] == [q["topic"] for q in DC012_PLAN["questions"] for _ in range(2)]
    assert [f["planned_question"] for f in inv["findings"]] == [q["question"] for q in DC012_PLAN["questions"] for _ in range(2)]
    assert planned_questions(inv) == DC012_PLAN["questions"]
    assert inv["plan"]["cost_usd"] == 0.001 and inv["plan"]["input_tokens"] == 100


def test_both_program_words_inside_the_letters_reason_do_not_freeze_the_column_wording():
    """The QMB and cost-sharing words make a question about both programs only when the planner wrote them, not
    when they sit inside the card's denial reason that the template quotes."""
    c = card(program="unknown", denial_reason="The plan does not pay Medicare cost-sharing for this visit.")
    inv = investigate_case({"case_id": "c_cs", "card": c}, FakeRetriever(), PlanThenAbstain("not json"))
    got = _by_jurisdiction(inv)
    assert got["Federal"][5] == "What do the Medicare rules say when the plan does not pay Medicare cost-sharing for this visit?"
    assert got["Florida"][5] == "What do the Florida Medicaid rules say when the plan does not pay Medicare cost-sharing for this visit?"


# ---- Oct 30 fix round: only the governing program phrase is swapped ---------------------------

PART_D_DUAL = dict(program="medicare_part_d", payer_name="Sunshine Health Medicare-Medicaid Plan", member_age_group="65_plus", service="Azelaic acid 15% gel",
                   denial_reason="This drug is not on the plan's formulary.")


@pytest.mark.parametrize("jurisdiction, card_over, planned, asked", [
    # a program word inside a term of that program's own vocabulary is not the governing program
    ("Federal", DC012_CARD, "Does the Statewide Medicaid Managed Care program cover home-delivered meals under Florida Medicaid Long-term Care?",
     "Does the Statewide Medicaid Managed Care program cover home-delivered meals under Medicare?"),
    ("Federal", DC012_CARD, "Does a Medicaid waiver cover home-delivered meals under Florida Medicaid?", "Does a Medicaid waiver cover home-delivered meals under Medicare?"),
    ("Federal", DC012_CARD, "Does FL Medicaid cover home-delivered meals?", "Does Medicare cover home-delivered meals?"),
    ("Florida", PART_D_DUAL, "Does Medicare Part D cover azelaic acid gel, as Medicare.gov describes it?", "Does Florida Medicaid cover azelaic acid gel, as Medicare.gov describes it?"),
    ("Florida", PART_D_DUAL, "Does medicare part d cover azelaic acid gel?", "Does Florida Medicaid cover azelaic acid gel?"),
    ("Florida", PART_D_DUAL, "Is a Part D drug like azelaic acid gel covered by Medicare Part D?", "Is a Part D drug like azelaic acid gel covered by Florida Medicaid?"),
    # the governing program named twice: both swapped (the second sits after "does")
    ("Federal", DC012_CARD, "Under Florida Medicaid, is widget therapy covered, and how does Florida Medicaid handle appeals?",
     "Under Medicare, is widget therapy covered, and how does Medicare handle appeals?"),
    # an English "part a" or "part b" is not a Medicare Part; a lower-case letter counts only after "Medicare"
    ("Florida", PART_D_DUAL, "What part a member pays for widget therapy under Medicare?", "What part a member pays for widget therapy under Florida Medicaid?"),
    ("Florida", PART_D_DUAL, "Which part b of the Medicare rules applies to widget therapy?", "Which part b of the Florida Medicaid rules applies to widget therapy?"),
    # the Florida column keeps the Medicaid Fair Hearing, which is Florida Medicaid's own appeal step
    ("Florida", DC021_CARD, "What is the Medicare Part B appeal process, including the Medicaid Fair Hearing and the deadline to file?",
     "What is the Florida Medicaid appeal process, including the Medicaid Fair Hearing and the deadline to file?"),
])
def test_only_the_governing_program_phrase_is_swapped(jurisdiction, card_over, planned, asked):
    from policyqa.investigate import question_for_jurisdiction

    c = card(**card_over)
    assert question_for_jurisdiction(PlannedQuestion("coverage", planned), route_case(c), jurisdiction, c).question == asked


def test_a_qmb_question_is_asked_as_written_even_when_it_names_only_medicare():
    """D2: the QMB billing question is about both programs whatever program words it uses."""
    from policyqa.investigate import question_for_jurisdiction

    c = card(**DC021_CARD)
    q = PlannedQuestion("other", "May a provider bill a Qualified Medicare Beneficiary (QMB) for Medicare cost-sharing for an office visit?")
    assert question_for_jurisdiction(q, route_case(c), "Florida", c) is q
    assert question_for_jurisdiction(q, route_case(c), "Federal", c) is q


@pytest.mark.parametrize("service", ["Medicaid waiver home-delivered meals", "Medicaid home-delivered meals"])
def test_the_service_is_never_rewritten_even_when_it_names_a_program(service):
    c = card(**{**DC012_CARD, "service": service})
    inv = investigate_case({"case_id": "c_svc", "card": c}, FakeRetriever(), PlanThenAbstain("not json"))
    fed = _by_jurisdiction(inv)["Federal"]
    assert fed[0] == f"Is {service} covered under Medicare for a member who is 65 or older?"
    assert all(service in q for q in fed if "appeal" not in q and "rules say" not in q)


def test_a_lower_case_quote_of_the_reason_is_never_rewritten():
    from policyqa.investigate import question_for_jurisdiction

    c = card(**{**DC012_CARD, "denial_reason": "Florida Medicaid does not cover meals."})
    q = PlannedQuestion("reason", "What do the rules say when florida medicaid does not cover meals?")
    assert question_for_jurisdiction(q, route_case(c), "Federal", c).question == "What do the Medicare rules say when florida medicaid does not cover meals?"

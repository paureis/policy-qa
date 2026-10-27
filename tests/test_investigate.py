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

    for f in inv["findings"]:
        assert set(f) >= {"id", "question", "topic", "jurisdiction", "status", "answer", "citations", "struck", "passages", "error", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd"}
        assert f["model"] == "fake-muse" and f["latency_ms"] >= 0
    assert cov["input_tokens"] == 400 and cov["output_tokens"] == 120 and cov["reasoning_tokens"] == 90 and cov["cost_usd"] == 0.0005

    # coverage math: claims = supported + unsupported; errors are counted apart
    assert inv["coverage"] == {"claims": 3, "supported": 2, "errors": 2}
    assert inv["cost_usd"] == pytest.approx(0.0005 * 4, abs=1e-9)  # four model answers (two questions failed before cost)
    assert inv["latency_ms"] >= 0
    assert provider.max_tokens >= 2000
    assert all(k == 8 * 4 and len(j) == 1 for _, k, j in retriever.calls)  # 8 passages from a pool of 32 candidates

    # progress: one call per finding, growing, plus the final one
    assert len(seen) == 7
    assert [p["questions_done"] for p in seen] == [1, 2, 3, 4, 5, 6, 6]
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
    assert names.count("question") == 6 and "route" in names and "plan" in names
    assert sorted(s["id"] for s in tr["spans"] if s["name"] == "question") == ["f1", "f2", "f3", "f4", "f5", "f6"]
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
    assert [h.chunk["doc_id"] for h in out] == ["fl-04", "fl-04", "fl-04", "fl-21", "fl-21", "fl-03"]
    assert [h.chunk["page"] for h in out[:3]] == [1, 2, 3]  # rank order kept inside a document
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
    assert inv["status"] == "done" and len(inv["findings"]) == 6
    assert wall < 0.25, wall  # serial would be 0.35 s (one 0.1 s answer and five 0.05 s answers)
    assert prov.max_active == 3
    assert [f["id"] for f in inv["findings"]] == ["f1", "f2", "f3", "f4", "f5", "f6"]
    assert [f["topic"] for f in inv["findings"]] == ["coverage", "limits", "conditions", "exclusions", "appeal", "reason"]
    assert [p["questions_done"] for p in seen] == [1, 2, 3, 4, 5, 6, 6]
    assert seen[0]["findings"][0]["id"] != "f1"  # the slow first question finished later, yet sits first at the end
    assert inv["cost_usd"] == pytest.approx(0.006)
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
    assert inv["cost_usd"] == pytest.approx(0.01 + 6 * 0.001)


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
    assert [q.question for q in qs] == [q["question"] for q in GOOD_PLAN["questions"]]


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

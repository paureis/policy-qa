"""Critic: a second Muse Spark pass attacks the drafted appeal letter and proposes a revision. No network."""
import copy
import json
from datetime import date
from pathlib import Path

import pytest

from casebuilders import LIMIT_QUOTE, EXCEED_QUOTE, case_with, second_live_case, small_investigation
from policyqa.critic import (
    CRITIC_MAX_TOKENS,
    CRITIC_SCHEMA,
    CRITIC_SYSTEM_PROMPT,
    ISSUE_KINDS,
    FixtureCritic,
    LiveCritic,
    apply_critique,
    critic_rounds,
    critique_letter,
    empty_critique,
)
from policyqa.generate import TruncatedResponse
from policyqa.letter import STRUCK_MEDICAL, FixtureLetter, draft_letter, letter_text
from policyqa.verdict import FixtureVerdict, _meta, verdict_from_data

TODAY = date(2026, 10, 26)
FIRST_LIVE = Path(__file__).resolve().parent.parent / "results" / "first-live-verdict-2026-10-26.json"

CRITIQUE_KEYS = {"status", "skipped", "reason", "rounds", "issues_found", "issues_fixed", "accepted", "model", "cost_usd", "latency_ms", "error"}
ROUND_KEYS = {"round", "issues", "before", "after", "verification_before", "verification_after", "accepted", "rejected_reason", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}
ISSUE_KEYS = {"kind", "severity", "where", "note", "fixed"}
SENTENCE_KEYS = {"text", "claim", "citation", "verified", "struck", "reason"}


def s(text, claim=False, citation=None):
    return {"text": text, "claim": claim, "citation": citation}


def issue(kind, where=None, severity="high", note="A note."):
    return {"kind": kind, "severity": severity, "where": where, "note": note}


GREETING = "Dear Sunshine Health appeals team,"
OPENING = "I am writing to appeal the denial of private duty nursing for September 2026."
REASON = 'Your letter gives this reason: "Services exceed the authorized amount."'
GOOD_CLAIM = s("Florida Medicaid covers up to 24 hours of private duty nursing per day.", True, {"finding_id": "f1", "quote": LIMIT_QUOTE})
BAD_CLAIM = s("The policy requires payment for every hour billed.", True, {"finding_id": "f2", "quote": "the plan pays every hour billed by the nurse"})
REQUEST = "Please reverse the denial."
ADDED_REQUEST = "Please also send me the authorization in effect for these dates and the records you used to set the authorized hours."

DRAFT = {
    "paragraphs": [
        {"sentences": [s(GREETING)]},
        {"sentences": [s(OPENING), s(REASON)]},
        {"sentences": [GOOD_CLAIM, BAD_CLAIM]},
        {"sentences": [s(REQUEST), s("Sincerely, [Your name]")]},
    ]
}


def revision(*middle, request=(REQUEST, ADDED_REQUEST)):
    return {
        "paragraphs": [
            {"sentences": [s(GREETING)]},
            {"sentences": [s(OPENING), s(REASON)]},
            {"sentences": list(middle)},
            {"sentences": [s(t) for t in request] + [s("Sincerely, [Your name]")]},
        ]
    }


class FakeProvider:
    """complete_parts returns the replies in order; a reply that is an exception is raised."""

    model = "fake-muse"

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []
        self.last_response = {"usage": {"completion_tokens_details": {"reasoning_tokens": 900}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500, **kw):
        self.calls.append({"system": system, "parts": parts, "schema": schema, "max_tokens": max_tokens, **kw})
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return (r if isinstance(r, str) else json.dumps(r)), 3000, 4000

    def cost(self, n_in, n_out):
        return 0.02


def inconsistent_verdict(inv):
    return verdict_from_data(
        {
            "steelman": {"argument": "The plan approved fewer hours.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "rule": {"statement": "The policy covers up to 24 hours a day.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "outcome": "inconsistent",
            "gap": "The letter treats the authorization as the ceiling.",
            "what_would_change": None,
        },
        inv,
        _meta("fake"),
    )


@pytest.fixture()
def drafted():
    inv = small_investigation()
    case = case_with(inv)
    verdict = inconsistent_verdict(inv)
    letter = draft_letter(case, inv, verdict, FakeProvider(DRAFT), today=TODAY)
    assert letter["verification"] == {"claims": 2, "verified": 1, "struck": 1}
    return case, inv, verdict, letter


def user_text(call):
    return "".join(p["text"] for p in call["parts"])


# ---- acceptance -------------------------------------------------------------------------


def test_a_revision_that_verifies_better_is_accepted(drafted):
    case, inv, verdict, letter = drafted
    reply = {
        "issues": [
            issue("unverified_claim", {"paragraph": 2, "sentence": 1}, note="The quote is not in finding f2."),
            issue("missing_request", None, "medium", "The letter does not ask for the authorization records."),
            issue("tone", None, "low", "The closing is abrupt."),
            issue("unsupported_fact", {"paragraph": 1, "sentence": 0}, "low", "September 2026 is vague."),
        ],
        "revised_paragraphs": revision(GOOD_CLAIM)["paragraphs"],
    }
    p = FakeProvider(reply)
    c = critique_letter(case, inv, verdict, letter, p)
    assert set(c) == CRITIQUE_KEYS and c["status"] == "done" and c["skipped"] is False and c["reason"] is None
    r = c["rounds"][0]
    assert set(r) == ROUND_KEYS and r["round"] == 1 and r["accepted"] is True and r["rejected_reason"] is None and r["error"] is None
    assert r["verification_before"] == {"claims": 2, "verified": 1, "struck": 1}
    assert r["verification_after"] == {"claims": 1, "verified": 1, "struck": 0}
    assert r["before"] == letter["paragraphs"]
    assert all(set(x) == SENTENCE_KEYS for para in r["after"] for x in para["sentences"])
    assert r["after"][2]["sentences"][0]["verified"] is True and r["after"][2]["sentences"][0]["citation"]["doc_id"] == "fl-04"
    # fixed: the struck sentence is gone; the two global kinds count as fixed; the opening did not change
    assert [i["fixed"] for i in r["issues"]] == [True, True, True, False]
    assert all(set(i) == ISSUE_KEYS for i in r["issues"])
    assert r["model"] == "fake-muse" and r["input_tokens"] == 3000 and r["output_tokens"] == 4000 and r["reasoning_tokens"] == 900 and r["cost_usd"] == 0.02
    assert c["issues_found"] == 4 and c["issues_fixed"] == 3 and c["accepted"] is True and c["cost_usd"] == 0.02 and c["model"] == "fake-muse" and c["error"] is None
    call = p.calls[0]
    assert call["max_tokens"] == CRITIC_MAX_TOKENS >= 8000 and call["schema"] is CRITIC_SCHEMA
    u = user_text(call)
    assert LIMIT_QUOTE in u and "[2.1]" in u and "STRUCK" in u and "VERIFIED" in u and "Services exceed the authorized amount." in u
    assert "2026-12-13" in u  # the deadline is shown so a wrong or missing deadline can be found
    assert "medical advice" in CRITIC_SYSTEM_PROMPT.lower() and "Never cite a question listed as not settled." in CRITIC_SYSTEM_PROMPT

    final = apply_critique(letter, c)
    assert final["paragraphs"] == r["after"] and final["verification"] == r["verification_after"]
    assert final["draft_paragraphs"] == letter["paragraphs"]
    txt = letter_text(final)
    assert ADDED_REQUEST in txt and "every hour billed" not in txt and "[cite: Title of fl-04, p. 5]" in txt


def test_a_revision_that_verifies_worse_is_rejected_and_the_draft_stands(drafted):
    case, inv, verdict, letter = drafted
    reply = {"issues": [issue("unverified_claim", {"paragraph": 2, "sentence": 1})], "revised_paragraphs": revision(s("The rule sets a higher ceiling."))["paragraphs"]}
    c = critique_letter(case, inv, verdict, letter, FakeProvider(reply))
    r = c["rounds"][0]
    assert r["accepted"] is False and "verified" in r["rejected_reason"] and r["error"] is None
    assert r["verification_after"]["verified"] == 0
    assert [i["fixed"] for i in r["issues"]] == [False]
    assert c["accepted"] is False and c["issues_fixed"] == 0
    final = apply_critique(letter, c)
    assert final["paragraphs"] == letter["paragraphs"] and final["verification"] == letter["verification"]
    assert final["draft_paragraphs"] == letter["paragraphs"]


def test_a_revision_with_more_struck_sentences_is_rejected(drafted):
    case, inv, verdict, letter = drafted
    worse = revision(GOOD_CLAIM, BAD_CLAIM, s("The policy also limits hours to eight a day.", True, None))
    c = critique_letter(case, inv, verdict, letter, FakeProvider({"issues": [], "revised_paragraphs": worse["paragraphs"]}))
    r = c["rounds"][0]
    assert r["accepted"] is False and "struck" in r["rejected_reason"] and r["verification_after"]["struck"] == 2


def test_the_medical_guard_strikes_a_revised_sentence_that_asserts_need(drafted):
    case, inv, verdict, letter = drafted
    med = "My son needed every one of these nursing hours."
    reply = {"issues": [], "revised_paragraphs": revision(GOOD_CLAIM, s(med))["paragraphs"]}
    c = critique_letter(case, inv, verdict, letter, FakeProvider(reply))
    r = c["rounds"][0]
    row = next(x for para in r["after"] for x in para["sentences"] if x["text"] == med)
    assert row["struck"] is True and row["reason"] == STRUCK_MEDICAL
    # one struck sentence swapped for another: the counts hold, and the struck one never reaches the export
    assert r["verification_after"] == {"claims": 1, "verified": 1, "struck": 1} and r["accepted"] is True
    assert med not in letter_text(apply_critique(letter, c))


def test_an_unchanged_revision_is_not_counted_as_accepted(drafted):
    case, inv, verdict, letter = drafted
    same = {"issues": [], "revised_paragraphs": DRAFT["paragraphs"]}
    c = critique_letter(case, inv, verdict, letter, FakeProvider(same))
    r = c["rounds"][0]
    assert r["accepted"] is False and "no change" in r["rejected_reason"].lower()
    assert apply_critique(letter, c)["paragraphs"] == letter["paragraphs"]


def test_issues_are_normalised(drafted):
    case, inv, verdict, letter = drafted
    reply = {
        "issues": [
            {"kind": "made_up", "severity": "critical", "where": {"paragraph": 9, "sentence": 0}, "note": "  Odd   spacing. "},
            {"kind": "tone", "severity": "low", "where": None, "note": ""},  # empty note: dropped
            "not an object",
        ],
        "revised_paragraphs": revision(GOOD_CLAIM)["paragraphs"],
    }
    r = critique_letter(case, inv, verdict, letter, FakeProvider(reply))["rounds"][0]
    assert r["issues"] == [{"kind": "other", "severity": "medium", "where": None, "note": "Odd spacing.", "fixed": True}]
    assert set(ISSUE_KINDS) == {"unverified_claim", "missing_deadline", "wrong_program", "medical_statement", "unsupported_fact", "missing_request", "tone", "other"}


# ---- skipping, rounds, failures ----------------------------------------------------------


def test_zero_rounds_skips_with_a_reason_and_no_call(drafted):
    case, inv, verdict, letter = drafted
    p = FakeProvider()
    c = critique_letter(case, inv, verdict, letter, p, rounds=0)
    assert p.calls == [] and set(c) == CRITIQUE_KEYS
    assert c["status"] == "done" and c["skipped"] is True and c["reason"] and c["rounds"] == [] and c["accepted"] is False
    assert apply_critique(letter, c)["paragraphs"] == letter["paragraphs"]


def test_a_letter_that_is_not_applicable_is_skipped(drafted):
    case, inv, _verdict, letter = drafted
    na = {**letter, "applicable": False, "paragraphs": [], "explanation": "The denial matches the policy."}
    p = FakeProvider()
    c = critique_letter(case, inv, {"outcome": "consistent"}, na, p)
    assert p.calls == [] and c["skipped"] is True and "matches the policy" in c["reason"]


def test_two_rounds_chain_and_the_second_sees_the_first(drafted):
    case, inv, verdict, letter = drafted
    first = {"issues": [issue("unverified_claim", {"paragraph": 2, "sentence": 1}, note="Quote not in f2.")], "revised_paragraphs": revision(GOOD_CLAIM, request=(REQUEST,))["paragraphs"]}
    second = {"issues": [issue("missing_request", None, "medium", "Ask for the records.")], "revised_paragraphs": revision(GOOD_CLAIM)["paragraphs"]}
    p = FakeProvider(first, second)
    c = critique_letter(case, inv, verdict, letter, p, rounds=2)
    assert len(p.calls) == 2 and [r["round"] for r in c["rounds"]] == [1, 2]
    r1, r2 = c["rounds"]
    assert r1["accepted"] and r2["accepted"]
    assert r2["before"] == r1["after"] and r2["verification_before"] == r1["verification_after"]
    u2 = user_text(p.calls[1])
    assert "every hour billed" not in u2 and "Quote not in f2." in u2  # it reviews round 1's letter and knows round 1's issues
    assert c["issues_found"] == 2 and c["issues_fixed"] == 2 and c["cost_usd"] == pytest.approx(0.04)
    final = apply_critique(letter, c)
    assert final["paragraphs"] == r2["after"] and final["draft_paragraphs"] == letter["paragraphs"]


def test_rounds_are_capped_at_two_and_stop_when_a_round_finds_nothing(drafted):
    case, inv, verdict, letter = drafted
    clean = {"issues": [], "revised_paragraphs": DRAFT["paragraphs"]}
    p = FakeProvider(clean, clean, clean)
    c = critique_letter(case, inv, verdict, letter, p, rounds=5)
    assert len(p.calls) == 1 and len(c["rounds"]) == 1


@pytest.mark.parametrize("reply", [TruncatedResponse("reasoning used the budget"), "not json", {"issues": []}, RuntimeError("HTTP 500")])
def test_a_model_failure_leaves_the_letter_as_drafted(drafted, reply):
    case, inv, verdict, letter = drafted
    p = FakeProvider(reply, reply)
    c = critique_letter(case, inv, verdict, letter, p, rounds=2)
    assert len(p.calls) == 1  # an error ends the review
    assert c["status"] == "done" and c["accepted"] is False and c["error"]
    r = c["rounds"][0]
    assert set(r) == ROUND_KEYS and r["error"] and r["accepted"] is False and r["after"] == [] and r["issues"] == []
    assert r["before"] == letter["paragraphs"]
    if isinstance(reply, (str, dict)):
        assert r["input_tokens"] == 3000  # a reply came back: its tokens are still counted
    final = apply_critique(letter, c)
    assert final["paragraphs"] == letter["paragraphs"] and final["verification"] == letter["verification"]


def test_critic_rounds_from_the_environment(monkeypatch):
    monkeypatch.delenv("RECOURSE_CRITIC_ROUNDS", raising=False)
    assert critic_rounds() == 1
    for raw, want in (("0", 0), ("2", 2), ("7", 2), ("-1", 0), ("x", 1), ("", 1)):
        monkeypatch.setenv("RECOURSE_CRITIC_ROUNDS", raw)
        assert critic_rounds() == want, raw


def test_empty_critique_has_every_key():
    c = empty_critique("fixture")
    assert set(c) == CRITIQUE_KEYS and c["status"] == "running" and c["rounds"] == [] and c["skipped"] is False


# ---- fixture, live records, live provider -------------------------------------------------


def test_fixture_critic_on_the_fixture_letter():
    rec = second_live_case()
    inv = rec["investigation"]
    v = FixtureVerdict(delay=0).decide(rec, inv)
    letter = FixtureLetter(delay=0).draft(rec, inv, v, today=TODAY)
    c = FixtureCritic(delay=0).review(rec, inv, v, letter)
    assert c["model"] == "fixture" and c["status"] == "done" and c["accepted"] is True
    r = c["rounds"][0]
    assert [i["kind"] for i in r["issues"]] == ["unverified_claim", "missing_request"] and all(i["fixed"] for i in r["issues"])
    assert r["issues"][0]["where"] is not None and r["issues"][1]["where"] is None
    assert r["verification_after"]["struck"] == 0 and r["verification_after"]["verified"] == r["verification_before"]["verified"]
    final = apply_critique(letter, c)
    txt = letter_text(final)
    assert "every hour a provider bills" not in txt and "authorization in effect" in txt
    assert any("every hour a provider bills" in x["text"] for p in final["draft_paragraphs"] for x in p["sentences"])


def test_first_live_letter_with_a_revision_that_drops_the_uncited_sentence():
    rec = json.loads(FIRST_LIVE.read_text(encoding="utf-8"))
    inv, verdict, letter = rec["investigation"], rec["verdict"], rec["letter"]
    uncited = "The materials I have do not show the rule for what happens when more hours are billed than were approved for the period."
    revised = copy.deepcopy(letter["paragraphs"])
    revised[2]["sentences"] = [x for x in revised[2]["sentences"] if x["text"] != uncited]
    revised = [{"sentences": [{"text": x["text"], "claim": x["claim"], "citation": ({"finding_id": x["citation"]["finding_id"], "quote": x["citation"]["quote"]} if x["citation"] else None)} for x in p["sentences"]]} for p in revised]
    reply = {"issues": [issue("unsupported_fact", {"paragraph": 2, "sentence": 0}, "medium", "This states what the documents lack, which the letter cannot cite.")], "revised_paragraphs": revised}
    p = FakeProvider(reply)
    c = critique_letter(rec, inv, verdict, letter, p)
    r = c["rounds"][0]
    assert r["verification_after"]["verified"] >= r["verification_before"]["verified"] == 3
    assert r["verification_after"]["struck"] <= r["verification_before"]["struck"]
    assert r["accepted"] is True and r["issues"][0]["fixed"] is True
    final = apply_critique(letter, c)
    assert uncited not in letter_text(final) and final["draft_paragraphs"] == letter["paragraphs"]
    u = user_text(p.calls[0])
    assert "T1001" in u and "Sunshine Health" in u and uncited in u


def test_live_critic_through_the_real_provider_over_a_fake_transport(drafted):
    import httpx

    from policyqa.generate import Provider

    case, inv, verdict, letter = drafted
    sent = []
    reply = {"issues": [issue("unverified_claim", {"paragraph": 2, "sentence": 1})], "revised_paragraphs": revision(GOOD_CLAIM)["paragraphs"]}

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5200, "completion_tokens": 6100, "completion_tokens_details": {"reasoning_tokens": 4100}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    c = LiveCritic(p, rounds=1).review(case, inv, verdict, letter)
    r = c["rounds"][0]
    assert r["accepted"] and r["reasoning_tokens"] == 4100 and r["input_tokens"] == 5200 and r["model"] == "muse-spark-1.3"
    assert sent[0]["max_tokens"] == CRITIC_MAX_TOKENS and sent[0]["response_format"]["json_schema"]["schema"] == CRITIC_SCHEMA


def test_live_critic_truncation_is_a_round_error(drafted):
    import httpx

    from policyqa.generate import Provider

    case, inv, verdict, letter = drafted

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"issues": ['}, "finish_reason": "length"}], "usage": {"prompt_tokens": 5200, "completion_tokens": 12000, "completion_tokens_details": {"reasoning_tokens": 11900}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    c = LiveCritic(p).review(case, inv, verdict, letter)
    assert c["rounds"][0]["error"].startswith("TruncatedResponse") and c["accepted"] is False

"""Steelman and Verdict: reference validation, the one model call, fallbacks, the fixture. No network."""
import json

import pytest

from casebuilders import (
    EXCEED_QUOTE,
    LIMIT_QUOTE,
    case_with,
    cite,
    finding,
    investigation,
    second_live_case,
    small_investigation,
)
from policyqa.generate import TruncatedResponse
from policyqa.verdict import (
    HEADLINES,
    VERDICT_MAX_TOKENS,
    VERDICT_SCHEMA,
    VERDICT_SYSTEM_PROMPT,
    FixtureVerdict,
    build_steelman_verdict,
    validate_refs,
)


class FakeProvider:
    model = "fake-muse"

    def __init__(self, content=None, raise_exc=None):
        self.content = content
        self.raise_exc = raise_exc
        self.calls = []
        self.last_response = {"usage": {"prompt_tokens": 900, "completion_tokens": 700, "completion_tokens_details": {"reasoning_tokens": 500}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500):
        self.calls.append({"system": system, "parts": parts, "schema": schema, "max_tokens": max_tokens})
        if self.raise_exc:
            raise self.raise_exc
        content = self.content if isinstance(self.content, str) else json.dumps(self.content)
        return content, 900, 700

    def cost(self, n_in, n_out):
        return 0.0042


def good_reply(**over):
    d = {
        "steelman": {"argument": "The plan approved a set number of hours and the policy ties payment to the hours the plan authorizes.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
        "outcome": "inconsistent",
        "rule": {"statement": "The policy covers up to 24 hours a day, and hours above the policy may be approved for a recipient under 21.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}, {"finding_id": "f2", "quote": EXCEED_QUOTE}]},
        "gap": "The letter treats the authorized amount as a ceiling, while the policy allows more hours to be approved.",
        "what_would_change": None,
    }
    d.update(over)
    return d


# ---- validate_refs -------------------------------------------------------------


def test_valid_quote_is_kept_and_doc_title_page_come_from_the_finding():
    inv = small_investigation()
    refs = validate_refs([{"finding_id": "f1", "quote": LIMIT_QUOTE, "doc_id": "fake-99", "page": 999, "title": "Made up"}], inv)
    assert refs == [{"finding_id": "f1", "doc_id": "fl-04", "title": "Title of fl-04", "page": 5, "quote": LIMIT_QUOTE}]


def test_a_quote_that_is_a_verbatim_part_of_a_citation_is_kept_with_the_verified_quote():
    inv = small_investigation()
    part = "exceeding the coverage described within this policy or the associated fee schedule may be approved"
    refs = validate_refs([{"finding_id": "f2", "quote": part}], inv)
    assert len(refs) == 1 and refs[0]["page"] == 6 and refs[0]["quote"] == EXCEED_QUOTE


def test_paraphrased_quote_is_dropped():
    inv = small_investigation()
    assert validate_refs([{"finding_id": "f1", "quote": "Medicaid pays for as many as twenty-four hours of nursing each day for every child."}], inv) == []


def test_unknown_finding_is_dropped():
    assert validate_refs([{"finding_id": "f99", "quote": LIMIT_QUOTE}], small_investigation()) == []


def test_not_settled_unsupported_and_error_findings_are_dropped():
    inv = small_investigation()
    struck_quote = "Authorization is renewed every 180 days with a plan of care."
    refs = [
        {"finding_id": "f3", "quote": LIMIT_QUOTE},
        {"finding_id": "f4", "quote": struck_quote},
        {"finding_id": "f6", "quote": LIMIT_QUOTE},
    ]
    assert validate_refs(refs, inv) == []


def test_short_quotes_malformed_refs_and_duplicates():
    inv = small_investigation()
    refs = [
        {"finding_id": "f1", "quote": "24 hours"},
        "f1",
        None,
        {"quote": LIMIT_QUOTE},
        {"finding_id": "f1", "quote": LIMIT_QUOTE},
        {"finding_id": "f1", "quote": LIMIT_QUOTE},
    ]
    out = validate_refs(refs, inv)
    assert len(out) == 1 and out[0]["finding_id"] == "f1"
    assert validate_refs(None, inv) == [] and validate_refs("x", inv) == []


# ---- build_steelman_verdict ------------------------------------------------------


def test_good_reply_becomes_a_cited_inconsistent_verdict():
    p = FakeProvider(good_reply())
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, p)
    assert v["status"] == "done" and v["error"] is None
    assert v["outcome"] == "inconsistent" and v["headline"] == "The denial appears inconsistent with the policy."
    assert v["what_would_change"] is None
    assert [r["finding_id"] for r in v["rule"]["citations"]] == ["f1", "f2"] and v["rule"]["unsupported"] is False
    assert v["steelman"]["citations"][0]["page"] == 5 and v["steelman"]["unsupported"] is False
    assert set(v["rule"]["citations"][0]) == {"finding_id", "doc_id", "title", "page", "quote"}
    assert v["model"] == "fake-muse" and v["input_tokens"] == 900 and v["output_tokens"] == 700 and v["reasoning_tokens"] == 500
    assert v["cost_usd"] == 0.0042 and v["latency_ms"] >= 0
    call = p.calls[0]
    assert call["max_tokens"] == VERDICT_MAX_TOKENS >= 6000 and call["schema"] is VERDICT_SCHEMA


def test_the_model_sees_supported_findings_and_only_the_questions_of_the_rest():
    p = FakeProvider(good_reply())
    inv = small_investigation()
    build_steelman_verdict(case_with(inv), inv, p)
    user = "".join(part["text"] for part in p.calls[0]["parts"])
    assert "[f1]" in user and LIMIT_QUOTE in user and "[f5]" in user
    assert "Services exceed the authorized amount." in user
    # not settled, unsupported and error findings: question only, labelled
    assert "What do the rules say when billed hours exceed authorized hours?" in user
    assert "How often must authorization be renewed?" in user and "What exclusions apply?" in user
    assert "not settled by the documents" in user.lower()
    assert "Authorization must be renewed every 180 days." not in user  # the struck answer never reaches the model
    assert "180 days with a plan of care" not in user
    assert "Member ID" not in user  # only the card, not the raw letter


def test_system_prompt_argues_the_payer_first_and_forbids_medical_statements():
    s = VERDICT_SYSTEM_PROMPT.lower()
    assert "steelman" in s and "payer" in s
    assert s.index("steelman") < s.index("outcome")
    assert "whether the care was needed" in s and "medical advice" in s
    for phrase in HEADLINES.values():
        assert phrase in VERDICT_SYSTEM_PROMPT


def test_rule_without_a_valid_citation_falls_back_to_not_settled():
    bad_rule = {"statement": "The policy says the plan must pay every billed hour.", "citations": [{"finding_id": "f1", "quote": "the plan must pay for every hour the nurse bills"}]}
    p = FakeProvider(good_reply(rule=bad_rule))
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, p)
    assert v["outcome"] == "not_settled" and v["headline"] == "The documents do not settle it."
    assert v["rule"]["unsupported"] is True and v["rule"]["citations"] == []
    assert v["rule"]["statement"] == bad_rule["statement"]  # kept, so the screen can strike it
    assert v["proposed_outcome"] == "inconsistent"
    assert v["what_would_change"]  # not_settled always says what would settle it
    assert v["error"] is None


def test_steelman_without_a_valid_citation_is_marked_but_the_outcome_stands():
    p = FakeProvider(good_reply(steelman={"argument": "The plan may cap hours.", "citations": [{"finding_id": "f3", "quote": LIMIT_QUOTE}]}))
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, p)
    assert v["steelman"]["unsupported"] is True and v["steelman"]["citations"] == []
    assert v["steelman"]["argument"] == "The plan may cap hours."
    assert v["outcome"] == "inconsistent"


def test_consistent_keeps_what_would_change_and_inconsistent_drops_it():
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, FakeProvider(good_reply(outcome="consistent", what_would_change="An authorization for the extra hours before the care.")))
    assert v["outcome"] == "consistent" and v["headline"] == "The denial matches the policy."
    assert v["what_would_change"] == "An authorization for the extra hours before the care."
    v = build_steelman_verdict(case_with(inv), inv, FakeProvider(good_reply(what_would_change="something")))
    assert v["outcome"] == "inconsistent" and v["what_would_change"] is None
    v = build_steelman_verdict(case_with(inv), inv, FakeProvider(good_reply(outcome="consistent", what_would_change=None)))
    assert v["what_would_change"]  # filled with a plain default


@pytest.mark.parametrize(
    "provider",
    [
        FakeProvider("this is not json"),
        FakeProvider({"outcome": "maybe"}),
        FakeProvider(raise_exc=TruncatedResponse("model hit the token budget")),
        FakeProvider(raise_exc=RuntimeError("503 from the API")),
    ],
)
def test_model_failure_or_bad_json_gives_the_not_settled_template_with_error(provider):
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, provider)
    assert v["status"] == "done" and v["error"]
    assert v["outcome"] == "not_settled" and v["headline"] == HEADLINES["not_settled"]
    assert v["rule"]["unsupported"] is True and v["steelman"]["unsupported"] is True
    assert v["rule"]["citations"] == [] and v["what_would_change"]


def test_tokens_of_a_reply_that_could_not_be_used_are_still_recorded():
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, FakeProvider("not json"))
    assert v["input_tokens"] == 900 and v["output_tokens"] == 700 and v["cost_usd"] == 0.0042


def test_no_supported_findings_means_no_model_call_and_not_settled():
    p = FakeProvider(good_reply())
    inv = investigation(finding("f1", "reason", "not_settled", "Not covered by the corpus."))
    v = build_steelman_verdict(case_with(inv), inv, p)
    assert p.calls == [] and v["outcome"] == "not_settled" and v["error"] is None
    assert v["input_tokens"] == 0 and v["cost_usd"] == 0.0


# ---- fixture ----------------------------------------------------------------------


def test_fixture_verdict_on_the_second_live_record_cites_f2_and_f3():
    rec = second_live_case()
    inv = rec["investigation"]
    v = FixtureVerdict(delay=0).decide(rec, inv)
    assert v["status"] == "done" and v["model"] == "fixture" and v["error"] is None
    assert v["outcome"] == "inconsistent" and v["headline"] == HEADLINES["inconsistent"]
    assert [r["finding_id"] for r in v["rule"]["citations"]] == ["f2", "f3"]
    assert v["rule"]["unsupported"] is False and v["steelman"]["unsupported"] is False
    assert "fixture" in v["steelman"]["argument"].lower() and "fixture" in v["rule"]["statement"].lower()
    assert "24 hours" in v["rule"]["statement"]


def test_fixture_verdict_on_the_fixture_investigator_uses_its_supported_findings():
    from policyqa.investigate import FixtureInvestigator

    c = case_with()
    inv = FixtureInvestigator(delay=0).investigate(c)
    v = FixtureVerdict(delay=0).decide(c, inv)
    assert v["outcome"] == "inconsistent" and v["rule"]["unsupported"] is False
    ids = [r["finding_id"] for r in v["rule"]["citations"]]
    assert ids == ["f2", "f1"]  # f3 (conditions) is unsupported in the fixture investigation, so coverage stands in
    assert "24 hours" in v["rule"]["citations"][0]["quote"] and "exceeding the coverage" in v["rule"]["citations"][1]["quote"]
    assert "hours authorized" in v["steelman"]["citations"][0]["quote"]


def test_live_verdict_through_the_real_provider_over_a_fake_transport():
    import httpx

    from policyqa.generate import Provider
    from policyqa.verdict import LiveVerdict

    sent = []

    def handler(request):
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(good_reply())}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2100, "completion_tokens": 1900, "completion_tokens_details": {"reasoning_tokens": 1500}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    inv = small_investigation()
    v = LiveVerdict(p).decide(case_with(inv), inv)
    assert v["outcome"] == "inconsistent" and v["reasoning_tokens"] == 1500 and v["model"] == "muse-spark-1.3"
    body = sent[0]
    assert body["max_tokens"] == VERDICT_MAX_TOKENS and body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True and body["response_format"]["json_schema"]["schema"] == VERDICT_SCHEMA


def test_live_verdict_truncated_by_the_real_provider_falls_back():
    import httpx

    from policyqa.generate import Provider

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"prompt_tokens": 2100, "completion_tokens": 8000, "completion_tokens_details": {"reasoning_tokens": 8000}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    inv = small_investigation()
    v = build_steelman_verdict(case_with(inv), inv, p)
    assert v["outcome"] == "not_settled" and "TruncatedResponse" in v["error"]

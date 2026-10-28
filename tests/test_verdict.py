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


# ---- a plan outside the corpus ----------------------------------------------------


def test_route_outside_the_corpus_means_no_model_call_and_not_settled_with_its_own_wording():
    """dc-030: an employer plan. The route says no corpus document governs it; the verdict must say so, not cite Florida rules against it."""
    p = FakeProvider(good_reply())
    inv = small_investigation()
    c = case_with(inv)
    c["route"] = {"program": "unknown", "jurisdictions": ["Florida", "Federal"], "dual": True, "reason": "The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus.", "outside_corpus": True}
    v = build_steelman_verdict(c, inv, p)
    assert p.calls == []
    assert v["outcome"] == "not_settled" and v["proposed_outcome"] == "not_settled" and v["error"] is None
    assert "no document in the corpus" in v["rule"]["statement"].lower() and v["rule"]["citations"] == []
    assert "plan's own" in v["what_would_change"].lower()
    assert v["cost_usd"] == 0.0


def test_route_inside_the_corpus_still_calls_the_model():
    p = FakeProvider(good_reply())
    inv = small_investigation()
    c = case_with(inv)
    c["route"] = {"program": "florida_medicaid_mma", "jurisdictions": ["Florida"], "dual": False, "reason": "x", "outside_corpus": False}
    v = build_steelman_verdict(c, inv, p)
    assert len(p.calls) == 1 and v["outcome"] == "inconsistent"


# ---- Oct 27 tuning: the decisive fact (not-settled rows answered consistent) ---------------------

POC_FACT = "The member's authorized plan of care and the care manager's assessment, which say how many days a week were authorized."


def _live_verdict(reply, case=None):
    """The real Provider over a fake HTTP transport, as the live verdict runs."""
    import httpx

    from policyqa.generate import Provider
    from policyqa.verdict import LiveVerdict

    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2000, "completion_tokens": 900}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    inv = small_investigation()
    return LiveVerdict(p).decide(case or case_with(inv), inv), sent


def test_a_consistent_reply_resting_on_the_payers_own_determination_becomes_not_settled():
    """dc-014 shape: the letter says the care manager's assessment does not show a need; the policy covers
    what the authorized plan of care says. The model called it consistent, taking the payer's assessment as
    given. The decisive fact is the payer's own determination, which the documents do not state."""
    reply = good_reply(outcome="consistent", what_would_change="An assessment showing more days.", gap="The plan approved what the assessment supports.", decisive_fact={"fact": POC_FACT, "settled_by": "payer_determination"})
    v, _ = _live_verdict(reply)
    assert v["outcome"] == "not_settled" and v["headline"] == HEADLINES["not_settled"]
    assert v["proposed_outcome"] == "consistent"
    assert POC_FACT in v["what_would_change"]
    assert "documents do not state" in v["gap"] and POC_FACT in v["gap"]
    assert v["rule"]["unsupported"] is False  # the cited rule stands; only the outcome changes


def test_an_inconsistent_reply_resting_on_a_list_outside_the_documents_becomes_not_settled():
    """dc-017 shape: the enrollee guide says the plan covers the brand when the prescriber writes 'dispense as
    written', but the plan's preferred drug list, which sets the requirement, is not in the corpus."""
    fact = "The plan's preferred drug list and its brand-name medically necessary requirement."
    v, _ = _live_verdict(good_reply(decisive_fact={"fact": fact, "settled_by": "outside_documents"}))
    assert v["outcome"] == "not_settled" and v["proposed_outcome"] == "inconsistent"
    assert fact in v["what_would_change"] and "outside" in v["gap"]


@pytest.mark.parametrize("outcome, settled_by", [("consistent", "letter"), ("inconsistent", "documents"), ("consistent", "documents")])
def test_a_decisive_fact_the_letter_or_the_documents_state_keeps_the_outcome(outcome, settled_by):
    """dc-002 shape: the letter states the member turned 21; the policy covers PDN under 21. That fact is the
    letter's own, so the denial stays consistent."""
    reply = good_reply(outcome=outcome, what_would_change=None if outcome == "inconsistent" else "Coverage under another program.", decisive_fact={"fact": "The member's age on the dates of service, which the letter states.", "settled_by": settled_by})
    v, _ = _live_verdict(reply)
    assert v["outcome"] == outcome and v["proposed_outcome"] == outcome


def test_the_schema_asks_for_the_decisive_fact_before_the_outcome_and_the_prompt_says_when_it_is_not_settled():
    props = list(VERDICT_SCHEMA["properties"])
    assert props.index("decisive_fact") < props.index("outcome")
    df = VERDICT_SCHEMA["properties"]["decisive_fact"]
    assert set(df["properties"]["settled_by"]["enum"]) == {"documents", "letter", "payer_determination", "outside_documents"}
    assert "decisive_fact" in VERDICT_SCHEMA["required"] and df["required"] == ["fact", "settled_by"] and df["additionalProperties"] is False
    s = VERDICT_SYSTEM_PROMPT.lower()
    for phrase in ("plan of care", "assessment", "prior authorization", "preferred drug list", "exception"):
        assert phrase in s, phrase


def test_the_verdict_sees_the_intake_summary_but_never_the_raw_letter():
    """dc-018: the exception needs the letter's fact (cataract surgery with a lens), which the card has no field for."""
    inv = small_investigation()
    c = case_with(inv)
    c["summary"] = "Medicare denied eyeglass frames ordered after cataract surgery with insertion of an intraocular lens."
    p = FakeProvider(good_reply())
    build_steelman_verdict(c, inv, p)
    user = "".join(part["text"] for part in p.calls[0]["parts"])
    assert c["summary"] in user and "Member ID" not in user


# ---- Oct 27, second pass: an exception counts only when its quote names the letter's fact ----------------

UNDER_21_EXCEPTION = "As such, services for recipients under the age of 21 years exceeding the coverage described within this policy or the associated fee schedule may be approved, if medically necessary."
PDN_RULE = "Florida Medicaid recipients under the age of 21 years requiring medically necessary PDN."
CATARACT = "1 pair of eyeglasses or contact lenses after each cataract surgery with insertion of an intraocular lens"
EYEGLASS_RULE = "Eyeglasses or contact lenses are not covered under Original Medicare."
PDN_EXCEPTION_Q = "Is there an exception under Florida Medicaid (MMA) that covers private duty nursing, 12 hours per day even though private duty nursing is covered only for members under the age of 21?"
EYE_EXCEPTION_Q = "Is there an exception under Medicare Part B that covers eyeglass frames after cataract surgery even though medicare does not cover eyeglasses or contact lenses?"


def dc002_case():
    """dc-002 shape: an adult member; the exception the planner found is for recipients under 21."""
    inv = investigation(
        finding("f1", "coverage", "supported", "PDN is covered for recipients under 21.", [cite("fl-04", 4, PDN_RULE)]),
        finding("f2", "exclusions", "supported", "Services above the policy may be approved for recipients under 21.", [cite("fl-04", 6, UNDER_21_EXCEPTION)], question=PDN_EXCEPTION_Q),
    )
    c = case_with(inv, member_age_group="adult", service="Private duty nursing, 12 hours per day", denial_reason="Private duty nursing is covered only for members under the age of 21. Our records show the member turned 21 before the dates of service.")
    return c, inv


def dc018_case():
    inv = investigation(
        finding("f1", "exclusions", "supported", "Medicare does not cover eyeglasses.", [cite("fed-16", 7, EYEGLASS_RULE)], jurisdiction="Federal"),
        finding("f2", "exclusions", "supported", "Medicare covers one pair after each cataract surgery with a lens.", [cite("fed-16", 8, CATARACT)], jurisdiction="Federal", question=EYE_EXCEPTION_Q),
    )
    c = case_with(inv, program="medicare_b", payer_name="Medicare", member_age_group="65_plus", service="Eyeglass frames after cataract surgery", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    return c, inv


def exception_reply(rule_quotes, relies=True, outcome="inconsistent", settled_by="letter"):
    return {
        "steelman": {"argument": "The policy limits the benefit and the letter applies that limit.", "citations": [{"finding_id": rule_quotes[0][0], "quote": rule_quotes[0][1]}]},
        "rule": {"statement": "The rule the letter cites, and an exception to it.", "citations": [{"finding_id": f, "quote": q} for f, q in rule_quotes]},
        "decisive_fact": {"fact": "The fact the exception turns on, as the letter states it.", "settled_by": settled_by},
        "relies_on_exception": relies,
        "outcome": outcome,
        "gap": "An exception covers the letter's facts.",
        "what_would_change": None,
    }


def _live_verdict_on(case, inv, reply):
    """_live_verdict with the case and investigation given (the real Provider over a fake HTTP transport)."""
    import httpx

    from policyqa.generate import Provider
    from policyqa.verdict import LiveVerdict

    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2000, "completion_tokens": 900}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    return LiveVerdict(p).decide(case, inv), sent


def test_the_schema_asks_whether_the_outcome_relies_on_an_exception_and_the_prompt_says_when_one_counts():
    props = list(VERDICT_SCHEMA["properties"])
    assert props.index("decisive_fact") < props.index("relies_on_exception") < props.index("outcome")
    assert VERDICT_SCHEMA["properties"]["relies_on_exception"] == {"type": "boolean"}
    assert "relies_on_exception" in VERDICT_SCHEMA["required"]
    s = VERDICT_SYSTEM_PROMPT.lower()
    assert "name the letter's" in s and "relies_on_exception" in s


def test_the_verdict_is_told_which_exceptions_name_the_letters_facts():
    c, inv = dc002_case()
    p = FakeProvider(good_reply())
    build_steelman_verdict(c, inv, p)
    user = "".join(part["text"] for part in p.calls[0]["parts"])
    assert UNDER_21_EXCEPTION in user  # nothing is hidden: the finding and its quote are still shown
    block = user[user.index("Exception check"):]
    assert "[f2] does not name the letter's facts" in block and "under 21" in block and "21 or older" in block
    c, inv = dc018_case()
    p = FakeProvider(good_reply())
    build_steelman_verdict(c, inv, p)
    user = "".join(part["text"] for part in p.calls[0]["parts"])
    assert "[f2] names the letter's facts" in user and '"cataract surgery"' in user


def test_an_inconsistent_outcome_resting_only_on_an_irrelevant_exception_becomes_not_settled():
    """dc-002: the verdict counted the under-21 exception for a member who is 21."""
    c, inv = dc002_case()
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", PDN_RULE), ("f2", UNDER_21_EXCEPTION)]))
    assert v["outcome"] == "not_settled" and v["proposed_outcome"] == "inconsistent"
    assert "does not name the letter's facts" in v["gap"] and "under 21" in v["gap"]
    assert v["what_would_change"]
    assert v["relies_on_exception"] is True
    assert v["rule"]["unsupported"] is False and len(v["rule"]["citations"]) == 2  # the cited rule is kept, struck nowhere
    assert [e["finding_id"] for e in v["exceptions"]] == ["f2"] and v["exceptions"][0]["relevant"] is False


def test_an_inconsistent_outcome_resting_on_a_relevant_exception_stands():
    """dc-018: the exception names the cataract surgery the letter states."""
    c, inv = dc018_case()
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", EYEGLASS_RULE), ("f2", CATARACT)]))
    assert v["outcome"] == "inconsistent" and v["proposed_outcome"] == "inconsistent"
    assert v["exceptions"][0]["relevant"] is True and v["exceptions"][0]["named"] == ["cataract surgery"]


def test_an_exception_relied_on_but_not_cited_cannot_make_the_denial_inconsistent():
    c, inv = dc018_case()
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", EYEGLASS_RULE)]))
    assert v["outcome"] == "not_settled" and v["proposed_outcome"] == "inconsistent"


def test_an_inconsistent_outcome_that_does_not_rely_on_an_exception_is_untouched():
    """dc-001 and dc-007 shape: the cited rule itself contradicts the letter's reason; no exception is involved."""
    c, inv = dc002_case()
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", PDN_RULE), ("f2", UNDER_21_EXCEPTION)], relies=False, settled_by="documents"))
    assert v["outcome"] == "inconsistent"
    # a reply without the field (older replies, fixtures) is treated as not relying on an exception
    reply = exception_reply([("f1", PDN_RULE)])
    reply.pop("relies_on_exception")
    v, _ = _live_verdict_on(c, inv, reply)
    assert v["outcome"] == "inconsistent" and v["relies_on_exception"] is False


def test_the_guard_never_touches_a_consistent_or_not_settled_outcome():
    c, inv = dc002_case()
    for outcome in ("consistent", "not_settled"):
        v, _ = _live_verdict_on(c, inv, {**exception_reply([("f1", PDN_RULE)], outcome=outcome), "what_would_change": "Coverage under another program."})
        assert v["outcome"] == outcome


# ---- fix round after the evaluation: a case with no letter fact is unchecked, never guarded ----------------

DC022_HINGE = "The MAO is financially responsible for emergency services and urgently needed services: Regardless of whether services are obtained within or outside the plan's network"
DC027_HINGE = "Within the first 90 days of coverage under a new plan, plans must provide a transition supply when the beneficiary requests a non-formulary drug."


def _hinge_case(card_over, rule_quote, hinge, exc_question):
    inv = investigation(
        finding("f1", "reason", "supported", "The rule the letter cites.", [cite("fed-11", 30, rule_quote)], jurisdiction="Federal"),
        finding("f2", "exclusions", "supported", "An exception applies.", [cite("fed-11", 30, hinge)], jurisdiction="Federal", question=exc_question),
    )
    return case_with(inv, **card_over), inv


DC022 = ({"program": "medicare_advantage", "payer_name": "Sample Medicare Advantage Plan", "member_age_group": "65_plus",
          "service": "Emergency department visit at an out-of-network hospital",
          "denial_reason": "The emergency room visit was at an out-of-network hospital and was not approved in advance. Out-of-network services require prior authorization."},
         "Out-of-network services require prior authorization under the plan's rules.", DC022_HINGE,
         "Is there an exception under Medicare Advantage that covers an emergency department visit at an out-of-network hospital even though it was not approved?")
DC027 = ({"program": "medicare_part_d", "payer_name": "Sample Prescription Drug Plan", "member_age_group": "65_plus",
          "service": "Non-formulary drug, first fill after joining the plan",
          "denial_reason": "This drug is not on the plan's formulary (list of covered drugs). Non-formulary drugs are not covered unless an exception is approved."},
         "Non-formulary drugs are not covered unless an exception is approved by the plan.", DC027_HINGE,
         "Is there an exception under Medicare Part D that covers a non-formulary drug, first fill after joining the plan?")


@pytest.mark.parametrize("shape", [DC022, DC027], ids=["dc-022", "dc-027"])
def test_a_case_with_no_letter_fact_keeps_an_inconsistent_outcome_that_relies_on_an_exception(shape):
    """Evaluator, fix round: dc-022 (emergency care regardless of network) and dc-027 (a transition supply) were right
    on Oct 27. Their letters state no fact a cue picks up, so the check cannot judge the exception: it is unchecked,
    and the guard never fires on an unchecked case."""
    c, inv = _hinge_case(*shape)
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", shape[1]), ("f2", shape[2])]))
    assert v["outcome"] == "inconsistent" and v["relies_on_exception"] is True
    assert v["exceptions"][0]["state"] == "unchecked"


def test_the_prompt_block_for_an_unchecked_case_has_no_do_not_rely_wording():
    c, inv = _hinge_case(*DC022)
    p = FakeProvider(good_reply())
    build_steelman_verdict(c, inv, p)
    user = "".join(part["text"] for part in p.calls[0]["parts"])
    block = user[user.index("Exception check"):]
    assert "[f2] was not checked" in block and "states no specific fact" in block
    assert "do not rely" not in user.lower()


def test_a_case_with_a_fact_still_guards_an_exception_that_does_not_name_it():
    """dc-018 with a real fact (the cataract surgery) and an exception about something else."""
    inv = investigation(
        finding("f1", "exclusions", "supported", "Medicare does not cover eyeglasses.", [cite("fed-16", 7, EYEGLASS_RULE)], jurisdiction="Federal"),
        finding("f2", "exclusions", "supported", "Prosthetic lenses are covered for aphakia.", [cite("fed-16", 8, "Prosthetic lenses are covered for patients with aphakia who lack the natural lens.")], jurisdiction="Federal", question=EYE_EXCEPTION_Q),
    )
    c = case_with(inv, program="medicare_b", payer_name="Medicare", member_age_group="65_plus", service="Eyeglass frames after cataract surgery", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    v, _ = _live_verdict_on(c, inv, exception_reply([("f1", EYEGLASS_RULE), ("f2", "Prosthetic lenses are covered for patients with aphakia who lack the natural lens.")]))
    assert v["outcome"] == "not_settled" and v["proposed_outcome"] == "inconsistent"
    assert v["exceptions"][0]["state"] == "not_relevant"


def test_the_verdict_records_the_decisive_fact_and_who_settles_it():
    c, inv = dc018_case()
    v, _ = _live_verdict_on(c, inv, exception_reply([("f2", CATARACT)]))
    assert v["decisive_fact"] == {"fact": "The fact the exception turns on, as the letter states it.", "settled_by": "letter"}
    # templates carry the same keys, empty
    v = build_steelman_verdict(case_with(investigation()), investigation(), FakeProvider(good_reply()))
    assert v["decisive_fact"] is None and v["relies_on_exception"] is False and v["exceptions"] == []

import json

from policyqa.generate import enforce_citations, parse_model_json, ABSTAIN_TEXT, Provider

PASSAGES = [
    {"tag": "P1", "doc_id": "fl-03", "page": 5, "title": "t", "jurisdiction": "Florida", "text": "Florida Medicaid covers up to four intermittent home health visits per day for recipients under the age of 21 years. Visits must be medically necessary."},
    {"tag": "P2", "doc_id": "fed-24", "page": 6, "title": "t", "jurisdiction": "Federal", "text": "Medicare covers part-time or intermittent skilled nursing care."},
]


def test_valid_citation_is_kept():
    data = {"answer": "Up to four visits a day for children under 21.", "abstain": False, "citations": [{"passage": "P1", "quote": "up to four intermittent home health visits per day for recipients under the age of 21 years"}]}
    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, PASSAGES)
    assert not abst and not forced and dropped == 0 and len(kept) == 1
    assert kept[0].doc_id == "fl-03" and kept[0].page == 5


def test_fabricated_quote_is_dropped_and_answer_becomes_abstention():
    data = {"answer": "Six visits a day.", "abstain": False, "citations": [{"passage": "P1", "quote": "Florida Medicaid covers six home health visits per day for everyone"}]}
    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, PASSAGES)
    assert abst and forced and dropped == 1 and kept == [] and ans == ABSTAIN_TEXT


def test_citation_to_unknown_passage_is_dropped():
    data = {"answer": "x", "abstain": False, "citations": [{"passage": "P9", "quote": "Medicare covers part-time or intermittent skilled nursing care."}]}
    _, abst, kept, _, dropped, _ = enforce_citations(data, PASSAGES)
    assert dropped == 1 and abst


def test_explicit_abstention_clears_citations():
    data = {"answer": "Not covered by the corpus.", "abstain": True, "citations": [{"passage": "P1", "quote": "Visits must be medically necessary."}]}
    ans, abst, kept, _, _, forced = enforce_citations(data, PASSAGES)
    assert abst and not forced and kept == [] and ans == ABSTAIN_TEXT


def test_bracketed_tag_and_lowercase_are_accepted():
    data = {"answer": "x", "abstain": False, "citations": [{"passage": "[p2]", "quote": "Medicare covers part-time or intermittent skilled nursing care."}]}
    _, abst, kept, _, _, _ = enforce_citations(data, PASSAGES)
    assert not abst and kept[0].doc_id == "fed-24"


def test_parse_model_json_handles_fences_and_prose():
    obj = {"answer": "a", "abstain": False, "citations": []}
    assert parse_model_json(json.dumps(obj)) == obj
    assert parse_model_json("```json\n" + json.dumps(obj) + "\n```") == obj
    assert parse_model_json("Here you go: " + json.dumps(obj) + " hope that helps") == obj


def test_unpack_accepts_content_as_parts():
    from policyqa.generate import Provider

    j = {"choices": [{"message": {"content": [{"type": "text", "text": "ready"}, {"type": "text", "text": "!"}]}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
    assert Provider._unpack(j) == ("ready!", 3, 2)
    j = {"choices": [{"message": {"content": None, "reasoning_content": "thinking"}}], "usage": {}}
    assert Provider._unpack(j) == ("", 0, 0)


def test_system_prompt_allows_partial_answers_and_keeps_rules_and_shape():
    from policyqa.generate import SYSTEM_PROMPT

    assert "If the passages settle part of the question, answer that part with citations" in SYSTEM_PROMPT
    assert "end with one sentence saying what the passages do not state" in SYSTEM_PROMPT
    assert "only when no passage bears on the question" in SYSTEM_PROMPT
    assert "Every factual claim in your answer must be supported by a passage you cite" in SYSTEM_PROMPT
    assert '{"answer": "...", "abstain": false, "citations": [{"passage": "P1", "quote": "..."}]}' in SYSTEM_PROMPT


def test_build_user_message_puts_case_context_first():
    from policyqa.generate import build_user_message

    msg = build_user_message("Is it covered?", [{**PASSAGES[0], "tag": "P1"}], context="The case is under Florida Medicaid (MMA).")
    assert msg.startswith("The case is under Florida Medicaid (MMA).\n\nPassages:")
    assert msg.endswith("Question: Is it covered?")
    assert build_user_message("Q?", [{**PASSAGES[0], "tag": "P1"}]).startswith("Passages:")


def test_provider_last_response_is_per_thread():
    """Parallel answers share one Provider; each thread must read its own reply's usage."""
    import threading

    import httpx

    from policyqa.generate import Provider, reasoning_tokens

    def handler(request):
        n = 11 if b"first" in request.content else 22
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "completion_tokens_details": {"reasoning_tokens": n}}})

    p = Provider(base_url="http://x/v1", api_key="k", model="m", transport=httpx.MockTransport(handler))
    p.complete("s", "first")
    seen = {}

    def other():
        seen["before"] = getattr(p, "last_response", None)
        p.complete("s", "second")
        seen["after"] = reasoning_tokens(p)

    t = threading.Thread(target=other)
    t.start()
    t.join()
    assert seen == {"before": None, "after": 22}
    assert reasoning_tokens(p) == 11


def test_partial_answer_opening_with_not_covered_is_not_an_abstention():
    from policyqa.generate import enforce_citations, format_passages
    from policyqa.retrieve import Hit

    text = "Florida Medicaid covers private duty nursing for recipients under 21 years of age when medically necessary. Adults are not covered."
    passages = format_passages([Hit({"chunk_id": "c1", "doc_id": "fl-04", "page": 3, "title": "PDN policy", "jurisdiction": "Florida", "text": text}, 1.0, "bm25")])
    data = {"answer": "Not covered for adults; covered for recipients under 21 when medically necessary.", "abstain": False, "citations": [{"passage": "P1", "quote": "covers private duty nursing for recipients under 21 years of age when medically necessary"}]}
    answer, abstained, kept, proposed, dropped, forced = enforce_citations(data, passages)
    assert not abstained and len(kept) == 1 and answer.startswith("Not covered for adults")
    data = {"answer": "Not covered by the corpus.", "abstain": False, "citations": []}
    answer, abstained, kept, proposed, dropped, forced = enforce_citations(data, passages)
    assert abstained and not forced


def _transport_with(responses):
    import httpx

    calls = []

    def handler(request):
        calls.append(request)
        body = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(body, tuple):
            return httpx.Response(body[0], json=body[1])
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler), calls


def _ok(content="{\"answer\": \"x\"}", finish="stop", reasoning=5):
    return {"choices": [{"finish_reason": finish, "message": {"content": content}}], "usage": {"prompt_tokens": 10, "completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": reasoning}}}


def test_truncated_response_raises_a_clear_error():
    import pytest
    from policyqa.generate import Provider, TruncatedResponse

    transport, calls = _transport_with([_ok(content="", finish="length", reasoning=2000)])
    p = Provider(base_url="http://x", api_key="k", model="m", transport=transport)
    with pytest.raises(TruncatedResponse) as e:
        p.complete("s", "u", max_tokens=2000)
    assert "max_tokens=2000" in str(e.value) and "2000 reasoning" in str(e.value)
    with pytest.raises(TruncatedResponse):
        p.complete_parts("s", [{"type": "text", "text": "u"}], max_tokens=2000)


def test_reasoning_effort_sent_when_set_and_dropped_on_400():
    import json
    from policyqa.generate import Provider

    transport, calls = _transport_with([_ok()])
    p = Provider(base_url="http://x", api_key="k", model="m", transport=transport, reasoning_effort="low")
    p.complete_parts("s", [{"type": "text", "text": "u"}], max_tokens=100)
    assert json.loads(calls[0].content)["reasoning_effort"] == "low"

    transport, calls = _transport_with([(400, {"error": "unknown parameter reasoning_effort"}), _ok()])
    p = Provider(base_url="http://x", api_key="k", model="m", transport=transport, reasoning_effort="low")
    text, _, _ = p.complete("s", "u", max_tokens=100)
    assert len(calls) == 2 and "reasoning_effort" not in json.loads(calls[1].content) and text

    transport, calls = _transport_with([_ok()])
    p = Provider(base_url="http://x", api_key="k", model="m", transport=transport)
    p.complete("s", "u", max_tokens=100)
    assert "reasoning_effort" not in json.loads(calls[0].content)


def test_timeout_default_and_env(monkeypatch):
    """The HTTP read timeout is 120 s unless POLICYQA_LLM_TIMEOUT_S says otherwise (the open-weights
    endpoints answer the verdict stage in 170 s and more; Oct 27, three Fireworks cases timed out)."""
    monkeypatch.delenv("POLICYQA_LLM_TIMEOUT_S", raising=False)
    p = Provider(base_url="http://x", api_key="k", model="m")
    assert p.timeout == 120.0
    monkeypatch.setenv("POLICYQA_LLM_TIMEOUT_S", "300")
    p = Provider(base_url="http://x", api_key="k", model="m")
    assert p.timeout == 300.0
    # An explicit argument still wins over the environment.
    p = Provider(base_url="http://x", api_key="k", model="m", timeout=10)
    assert p.timeout == 10

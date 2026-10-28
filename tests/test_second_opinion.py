"""Second opinion: the verdict stage run again on a second model (Muse Spark Open). No network: fakes and the fake HTTP transport."""
import copy
import json

import httpx
import pytest

from casebuilders import EXCEED_QUOTE, LIMIT_QUOTE, case_with, small_investigation
from policyqa import second_opinion as so
from policyqa.generate import Provider
from policyqa.verdict import build_steelman_verdict

SECOND_KEYS = {"status", "reason", "model", "outcome", "proposed_outcome", "decisive_fact", "relies_on_exception", "agrees",
               "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}
SECOND_URL = "https://inference.baseten.co/v1"
SECOND_MODEL = "meta-models/muse-spark-open-1026"
ENV_NAMES = ("POLICYQA_SECOND_LLM_BASE_URL", "POLICYQA_SECOND_LLM_MODEL", "POLICYQA_SECOND_LLM_API_KEY",
             "POLICYQA_SECOND_LLM_INPUT_USD_PER_M", "POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M")


@pytest.fixture(autouse=True)
def _no_second_env(monkeypatch):
    for k in ENV_NAMES:
        monkeypatch.delenv(k, raising=False)


def reply(**over):
    d = {
        "steelman": {"argument": "The plan approved a set number of hours and the policy ties payment to the hours the plan authorizes.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
        "rule": {"statement": "The policy covers up to 24 hours a day, and hours above the policy may be approved for a recipient under 21.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}, {"finding_id": "f2", "quote": EXCEED_QUOTE}]},
        "decisive_fact": {"fact": "The member's age group.", "settled_by": "letter"},
        "relies_on_exception": False,
        "outcome": "inconsistent",
        "gap": "The letter treats the authorized amount as a ceiling, while the policy allows more hours to be approved.",
        "what_would_change": None,
    }
    d.update(over)
    return d


def _ok(content: dict, n_in=2000, n_out=900) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}, "finish_reason": "stop"}],
                                     "usage": {"prompt_tokens": n_in, "completion_tokens": n_out, "completion_tokens_details": {"reasoning_tokens": 400}}})


def _provider(base_url, model, handler):
    return Provider(base_url=base_url, api_key="k", model=model, transport=httpx.MockTransport(handler))


class Recorder:
    """A fake provider that records calls; raises when told to."""

    def __init__(self, content=None, raise_exc=None, model=SECOND_MODEL):
        self.model = model
        self.content, self.raise_exc, self.calls = content, raise_exc, []
        self.last_response = {"usage": {"completion_tokens_details": {"reasoning_tokens": 300}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500):
        self.calls.append(parts)
        if self.raise_exc:
            raise self.raise_exc
        return json.dumps(self.content), 1800, 800

    def cost(self, n_in, n_out):
        return 0.0031


def primary_verdict(content=None):
    inv = small_investigation()
    case = case_with(inv)
    p = Recorder(content or reply(), model="muse-spark-1.3")
    return case, inv, build_steelman_verdict(case, inv, p)


# ---- configuration -------------------------------------------------------------------


def test_no_provider_when_the_base_url_or_the_model_is_unset(monkeypatch):
    assert so.provider_from_env() is None
    monkeypatch.setenv("POLICYQA_SECOND_LLM_BASE_URL", SECOND_URL)
    assert so.provider_from_env() is None
    monkeypatch.delenv("POLICYQA_SECOND_LLM_BASE_URL")
    monkeypatch.setenv("POLICYQA_SECOND_LLM_MODEL", SECOND_MODEL)
    assert so.provider_from_env() is None


def test_the_provider_reads_its_own_names_and_shares_the_primarys_effort_and_timeout(monkeypatch):
    monkeypatch.setenv("POLICYQA_SECOND_LLM_BASE_URL", SECOND_URL + "/")
    monkeypatch.setenv("POLICYQA_SECOND_LLM_MODEL", SECOND_MODEL)
    monkeypatch.setenv("POLICYQA_SECOND_LLM_API_KEY", "second-key")
    monkeypatch.setenv("POLICYQA_LLM_API_KEY", "primary-key")
    monkeypatch.setenv("POLICYQA_LLM_INPUT_USD_PER_M", "1.25")
    monkeypatch.setenv("POLICYQA_LLM_OUTPUT_USD_PER_M", "4.25")
    monkeypatch.setenv("POLICYQA_LLM_REASONING_EFFORT", "low")
    monkeypatch.setenv("POLICYQA_LLM_TIMEOUT_S", "300")
    p = so.provider_from_env()
    assert p.base_url == SECOND_URL and p.model == SECOND_MODEL and p.api_key == "second-key"
    assert p.in_price == 1.25 and p.out_price == 4.25  # the primary's prices when the second's are unset
    assert p.reasoning_effort == "low" and p.timeout == 300.0
    monkeypatch.setenv("POLICYQA_SECOND_LLM_INPUT_USD_PER_M", "0.5")
    monkeypatch.setenv("POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M", "2")
    p = so.provider_from_env()
    assert p.in_price == 0.5 and p.out_price == 2.0


def test_the_second_key_never_falls_back_to_the_primarys(monkeypatch):
    """A Meta key sent to Baseten would leak a credential to another provider."""
    monkeypatch.setenv("POLICYQA_SECOND_LLM_BASE_URL", SECOND_URL)
    monkeypatch.setenv("POLICYQA_SECOND_LLM_MODEL", SECOND_MODEL)
    monkeypatch.setenv("POLICYQA_LLM_API_KEY", "primary-key")
    assert so.provider_from_env().api_key == ""


# ---- skip rules ----------------------------------------------------------------------


def test_skipped_when_not_configured_and_nothing_is_called():
    case, inv, v = primary_verdict()
    out = so.run_second_opinion(case, inv, v, None)
    assert set(out) == SECOND_KEYS and out["status"] == "skipped" and "not configured" in out["reason"]
    assert out["agrees"] is None and out["outcome"] is None and out["cost_usd"] == 0.0


@pytest.mark.parametrize("change, phrase", [
    (lambda c, v: v.update(status="failed", error="boom"), "did not finish"),
    (lambda c, v: v.update(error="RuntimeError: HTTP 429"), "model failure"),
    (lambda c, v: v.update(model="fixture"), "fixture"),
    (lambda c, v: c.update(route={"program": "unknown", "outside_corpus": True, "reason": "employer plan"}), "outside the corpus"),
])
def test_skipped_without_a_call_when_the_primary_made_no_usable_model_call(change, phrase):
    case, inv, v = primary_verdict()
    change(case, v)
    p = Recorder(reply())
    out = so.run_second_opinion(case, inv, v, p)
    assert p.calls == [] and out["status"] == "skipped" and phrase in out["reason"] and out["agrees"] is None
    assert out["model"] == SECOND_MODEL


def test_skipped_when_no_finding_is_supported():
    case, inv, v = primary_verdict()
    for f in inv["findings"]:
        f["status"] = "not_settled"
    p = Recorder(reply())
    out = so.run_second_opinion(case, inv, v, p)
    assert p.calls == [] and out["status"] == "skipped" and "no supported finding" in out["reason"]


# ---- the run -------------------------------------------------------------------------


def test_agrees_when_both_models_reach_the_same_outcome():
    case, inv, v = primary_verdict()
    p = Recorder(reply())
    out = so.run_second_opinion(case, inv, v, p)
    assert len(p.calls) == 1 and set(out) == SECOND_KEYS
    assert out["status"] == "done" and out["outcome"] == "inconsistent" == v["outcome"] and out["agrees"] is True
    assert out["proposed_outcome"] == "inconsistent" and out["decisive_fact"] == {"fact": "The member's age group.", "settled_by": "letter"}
    assert out["relies_on_exception"] is False and out["reason"] is None and out["error"] is None
    assert out["input_tokens"] == 1800 and out["output_tokens"] == 800 and out["reasoning_tokens"] == 300 and out["cost_usd"] == 0.0031
    assert out["latency_ms"] >= 0


def test_disagrees_when_the_outcomes_differ_and_the_code_guards_apply_to_the_second_model_too():
    case, inv, v = primary_verdict()
    # the second model says consistent, but names the payer's own determination: the same guard makes it not_settled
    p = Recorder(reply(outcome="consistent", decisive_fact={"fact": "The plan's authorized amount.", "settled_by": "payer_determination"}))
    out = so.run_second_opinion(case, inv, v, p)
    assert out["status"] == "done" and out["outcome"] == "not_settled" and out["proposed_outcome"] == "consistent"
    assert out["agrees"] is False


def test_a_second_model_failure_is_recorded_and_the_primary_is_untouched():
    case, inv, v = primary_verdict()
    before = copy.deepcopy(v)
    out = so.run_second_opinion(case, inv, v, Recorder(raise_exc=RuntimeError("HTTP 500 from Baseten")))
    assert out["status"] == "failed" and "HTTP 500" in out["error"]
    assert out["outcome"] is None and out["agrees"] is None
    assert v == before


def test_the_primary_verdict_is_never_modified():
    case, inv, v = primary_verdict()
    before = copy.deepcopy(v)
    so.run_second_opinion(case, inv, v, Recorder(reply(outcome="not_settled", what_would_change="x")))
    assert v == before


def test_the_second_model_gets_the_primarys_request_except_the_model():
    sent = {"primary": [], "second": []}

    def handler(request):
        who = "second" if request.url.host == "inference.baseten.co" else "primary"
        sent[who].append(json.loads(request.content))
        return _ok(reply())

    inv = small_investigation()
    case = case_with(inv)
    v = build_steelman_verdict(case, inv, _provider("https://api.meta.ai/v1", "muse-spark-1.3", handler))
    out = so.run_second_opinion(case, inv, v, _provider(SECOND_URL, SECOND_MODEL, handler))
    assert out["status"] == "done" and out["model"] == SECOND_MODEL and out["agrees"] is True
    (a,), (b,) = sent["primary"], sent["second"]
    assert a["model"] == "muse-spark-1.3" and b["model"] == SECOND_MODEL
    assert a["messages"] == b["messages"]
    assert {k: x for k, x in a.items() if k != "model"} == {k: x for k, x in b.items() if k != "model"}


def test_a_500_from_the_second_endpoint_is_failed_over_the_fake_transport():
    def handler(request):
        if request.url.host == "inference.baseten.co":
            return httpx.Response(500, json={"error": "upstream"})
        return _ok(reply())

    inv = small_investigation()
    case = case_with(inv)
    v = build_steelman_verdict(case, inv, _provider("https://api.meta.ai/v1", "muse-spark-1.3", handler))
    before = copy.deepcopy(v)
    out = so.run_second_opinion(case, inv, v, _provider(SECOND_URL, SECOND_MODEL, handler))
    assert v == before and v["status"] == "done" and v["error"] is None and v["outcome"] == "inconsistent"
    assert out["status"] == "failed" and "500" in out["error"] and out["agrees"] is None

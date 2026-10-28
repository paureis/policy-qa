"""Second opinion: the Steelman and Verdict stage run a second time on a second model, as a trust signal.

The product's verdict is Muse Spark 1.3's. The second opinion asks Muse Spark Open (Meta's open-weights
model, on Baseten or Fireworks) the same question: `build_steelman_verdict` with the same case, the same
investigation and the same prompt, so the findings, the exception marks and every code guard are identical
and only the model differs. It records whether the two outcomes agree. It never changes the primary verdict,
and the letter and the critic read only the primary.

Configuration (a second OpenAI-compatible endpoint; the reasoning effort and the timeout are the primary's,
POLICYQA_LLM_REASONING_EFFORT and POLICYQA_LLM_TIMEOUT_S):

  POLICYQA_SECOND_LLM_BASE_URL   e.g. https://inference.baseten.co/v1
  POLICYQA_SECOND_LLM_MODEL      e.g. meta-models/muse-spark-open-1026
  POLICYQA_SECOND_LLM_API_KEY    never falls back to POLICYQA_LLM_API_KEY (that would send one provider's key to another)
  POLICYQA_SECOND_LLM_INPUT_USD_PER_M, POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M  (default: the primary's prices)

Unset base URL or model: skipped, never an error. Also skipped, with no call, when the primary verdict made no
usable model call: it did not finish, it is the template after a model failure (`error` set), it is the
fixture, the route is outside the corpus, or no finding is supported. Comparing against a verdict no model
reached would measure nothing.

Waiting: the chain never waits for it. The inline POST (tests) and case-evals wait at most `second_wait_s()`;
case-evals then records the row's second opinion as "timeout", and the case's score and seconds ignore it.
A case loaded from disk with a second opinion still "running" (its daemon thread died with the server)
loads as "failed" (api/cases.py).

Shape: {status: "skipped" | "running" | "done" | "failed", reason (skipped only), model, outcome,
proposed_outcome, decisive_fact, relies_on_exception, agrees (outcome == the primary's; null unless both
are done), input_tokens, output_tokens, reasoning_tokens, latency_ms, cost_usd, error}. A second model
failure (the template verdict with `error`) is "failed" with no outcome: the template is not an opinion.
"""
from __future__ import annotations

import os

from .verdict import build_steelman_verdict, route_outside_corpus, supported_findings

ENV_BASE_URL = "POLICYQA_SECOND_LLM_BASE_URL"
ENV_MODEL = "POLICYQA_SECOND_LLM_MODEL"
ENV_API_KEY = "POLICYQA_SECOND_LLM_API_KEY"
ENV_INPUT_PRICE = "POLICYQA_SECOND_LLM_INPUT_USD_PER_M"
ENV_OUTPUT_PRICE = "POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M"

NOT_CONFIGURED = f"not configured: set {ENV_BASE_URL} and {ENV_MODEL}"
SKIP_NOT_DONE = "the primary verdict did not finish"
SKIP_PRIMARY_ERROR = "the primary verdict is the template after a model failure, so there is no model verdict to compare"
SKIP_FIXTURE = "the primary verdict is the fixture (no model call)"
SKIP_OUTSIDE = "the plan is outside the corpus: the verdict makes no model call"
SKIP_NO_FINDINGS = "no supported finding: the verdict makes no model call"


SECOND_WAIT_SLACK_S = 60.0  # added to the HTTP timeout: how long a caller waits for a second opinion before calling it a timeout


def second_wait_s() -> float:
    """The bounded wait for a second opinion's thread: POLICYQA_LLM_TIMEOUT_S (default 120) plus SECOND_WAIT_SLACK_S.
    One HTTP call can take the full timeout; a reasoning-effort retry could take it twice, and is then a timeout."""
    return float(os.environ.get("POLICYQA_LLM_TIMEOUT_S") or 120.0) + SECOND_WAIT_SLACK_S


def configured() -> bool:
    return bool(os.environ.get(ENV_BASE_URL) and os.environ.get(ENV_MODEL))


def second_model_name() -> str | None:
    return os.environ[ENV_MODEL] if configured() else None


def _price(name: str, fallback: float) -> float:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return fallback
    return float(raw)


def provider_from_env(transport=None):
    """The second Provider, or None when the base URL or the model is unset."""
    if not configured():
        return None
    from .generate import Provider

    p = Provider(base_url=os.environ[ENV_BASE_URL], api_key=os.environ.get(ENV_API_KEY) or "", model=os.environ[ENV_MODEL], transport=transport)
    if not os.environ.get(ENV_API_KEY):
        p.api_key = ""  # Provider falls back to POLICYQA_LLM_API_KEY on an empty argument; the second never does
    p.in_price = _price(ENV_INPUT_PRICE, p.in_price)
    p.out_price = _price(ENV_OUTPUT_PRICE, p.out_price)
    return p


def empty_second_opinion(model: str | None, status: str = "running", reason: str | None = None, error: str | None = None) -> dict:
    return {"status": status, "reason": reason, "model": model, "outcome": None, "proposed_outcome": None, "decisive_fact": None,
            "relies_on_exception": None, "agrees": None, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0,
            "latency_ms": 0.0, "cost_usd": 0.0, "error": error}


def skipped(reason: str, model: str | None = None) -> dict:
    return empty_second_opinion(model, "skipped", reason=reason)


def skip_reason(case: dict, investigation, primary: dict | None) -> str | None:
    """Why the second opinion does not run for this primary verdict, or None when it runs."""
    if not isinstance(primary, dict) or primary.get("status") != "done":
        return SKIP_NOT_DONE
    if primary.get("error"):
        return SKIP_PRIMARY_ERROR
    if primary.get("model") == "fixture":
        return SKIP_FIXTURE
    if route_outside_corpus(case):
        return SKIP_OUTSIDE
    if not supported_findings(investigation):
        return SKIP_NO_FINDINGS
    return None


def run_second_opinion(case: dict, investigation, primary: dict | None, provider) -> dict:
    """The second opinion for one case; never raises for a model failure, never touches `primary`."""
    if provider is None:
        return skipped(NOT_CONFIGURED)
    model = getattr(provider, "model", "?")
    why = skip_reason(case, investigation, primary)
    if why:
        return skipped(why, model)
    v = build_steelman_verdict(case, investigation, provider)
    meta = {k: v.get(k) for k in ("input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd")}
    if v.get("error") or v.get("status") != "done":
        return {**empty_second_opinion(v.get("model") or model, "failed", error=v.get("error") or "the second verdict did not finish"), **meta}
    return {
        "status": "done", "reason": None, "model": v.get("model") or model,
        "outcome": v.get("outcome"), "proposed_outcome": v.get("proposed_outcome"),
        "decisive_fact": v.get("decisive_fact"), "relies_on_exception": v.get("relies_on_exception"),
        "agrees": v.get("outcome") == primary.get("outcome"),
        **meta, "error": None,
    }

"""Claude as judge for answer accuracy and faithfulness.

The judge sees the question, the human-written gold answer and gold quote, the
system's answer, and the passages the system cited. It returns a structured
verdict. The judge is only as good as its agreement with a person, so the
harness also records its verdicts on the 50-item judge subset for comparison
against Alvaro's independent verdicts.

Model: claude-opus-5-5 by default (POLICYQA_JUDGE_MODEL to override). Judging is
a bounded task, so effort is low. Needs ANTHROPIC_API_KEY (or an `ant auth login`
profile).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict

JUDGE_MODEL = os.environ.get("POLICYQA_JUDGE_MODEL", "claude-opus-5-5")

# Prices per million tokens, for cost per judged item. Update if the model changes.
JUDGE_PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "accuracy": {"type": "string", "enum": ["correct", "partially_correct", "incorrect", "abstained"]},
        "faithfulness": {"type": "string", "enum": ["supported", "partially_supported", "unsupported", "no_citations"]},
        "rationale": {"type": "string"},
    },
    "required": ["accuracy", "faithfulness", "rationale"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """You grade answers from a policy question-answering system against a human-written gold answer.

Accuracy, judged against the gold answer and gold quote only:
- correct: the answer states the same facts, numbers, limits, and conditions as the gold answer. Extra correct detail is fine. Different wording is fine.
- partially_correct: the answer gets the main point but misses or softens a number, limit, condition, or one of two required parts.
- incorrect: the answer contradicts the gold answer, answers a different question, or invents a condition.
- abstained: the answer is "Not covered by the corpus." (whether or not abstaining was right; the harness scores that separately).

Faithfulness, judged against the cited passages only (ignore the gold answer here):
- supported: every factual claim in the answer appears in the cited passages.
- partially_supported: some claims are in the passages, at least one is not.
- unsupported: the claims are not in the cited passages.
- no_citations: the answer abstained or cited nothing.

Be strict about numbers and conditions. Write a one-sentence rationale."""


@dataclass
class Verdict:
    accuracy: str
    faithfulness: str
    rationale: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    error: str | None = None


def _judge_user(question: str, gold_answer: str, gold_quote: str, system_answer: str, cited: list[dict]) -> str:
    cited_text = "\n\n".join(f"[{c['tag']}] {c['doc_id']} page {c['page']}\n{c['text']}" for c in cited) or "(none)"
    return (
        f"Question: {question}\n\n"
        f"Gold answer: {gold_answer}\n"
        f"Gold quote: {gold_quote}\n\n"
        f"System answer: {system_answer}\n\n"
        f"Passages the system cited:\n{cited_text}"
    )


class Judge:
    def __init__(self, model: str = JUDGE_MODEL):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.in_price, self.out_price = JUDGE_PRICES.get(model, (0.0, 0.0))

    def grade(self, question: str, gold_answer: str, gold_quote: str, system_answer: str, cited: list[dict]) -> Verdict:
        t = time.perf_counter()
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": _judge_user(question, gold_answer, gold_quote, system_answer, cited)}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
            )
            n_in, n_out = resp.usage.input_tokens, resp.usage.output_tokens
            if resp.stop_reason == "refusal":
                return Verdict("incorrect", "no_citations", "judge refused", self.model, n_in, n_out, self._cost(n_in, n_out), _ms(t), error="refusal")
            text = next(b.text for b in resp.content if b.type == "text")
            data = json.loads(text)
            return Verdict(data["accuracy"], data["faithfulness"], data["rationale"], self.model, n_in, n_out, self._cost(n_in, n_out), _ms(t))
        except Exception as e:  # noqa: BLE001 - recorded in the report, not hidden
            return Verdict("incorrect", "no_citations", "", self.model, 0, 0, 0.0, _ms(t), error=f"{type(e).__name__}: {e}")

    def _cost(self, n_in: int, n_out: int) -> float:
        return round(n_in * self.in_price / 1e6 + n_out * self.out_price / 1e6, 6)


class MockJudge:
    """Grades by string overlap so the harness runs without a key. Not a real judge."""

    model = "mock"

    def grade(self, question, gold_answer, gold_quote, system_answer, cited) -> Verdict:
        from .textnorm import quote_overlap

        if system_answer.startswith("Not covered"):
            return Verdict("abstained", "no_citations", "mock", "mock", 0, 0, 0.0, 0.0)
        ov = quote_overlap(system_answer, gold_quote)
        acc = "correct" if ov >= 0.5 else "incorrect"
        return Verdict(acc, "supported" if cited else "no_citations", f"mock overlap {ov:.2f}", "mock", 0, 0, 0.0, 0.0)


def _ms(t: float) -> float:
    return round((time.perf_counter() - t) * 1000, 1)


def verdict_dict(v: Verdict) -> dict:
    return asdict(v)

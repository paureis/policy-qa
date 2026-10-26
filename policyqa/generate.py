"""Answer generation with enforced citations.

The model sees the top retrieved passages, each tagged [P1], [P2], ... and must
return JSON: an answer, the passages it relied on with a verbatim quote from
each, and whether it abstains. The citations are then checked, not trusted:

- a citation must name a passage that was actually shown, and
- its quote must occur in that passage (same overlap rule as retrieval, 0.8).

Citations that fail are dropped. An answer left with no valid citation is
converted into an abstention, because an uncited claim about coverage is
exactly the failure this system exists to prevent.

The generation model is Muse Spark 1.3 on the Meta Model API (OpenAI chat
completions protocol; text, image, and PDF input; JSON schema output). Any other
OpenAI-compatible endpoint (Modal, Baseten, Fireworks) works the same way. The
endpoint, key, and model name come from the environment:

  POLICYQA_LLM_BASE_URL   e.g. https://api.meta.ai/v1
  POLICYQA_LLM_API_KEY
  POLICYQA_LLM_MODEL      e.g. muse-spark-1.3
  POLICYQA_LLM_INPUT_USD_PER_M, POLICYQA_LLM_OUTPUT_USD_PER_M  (for cost per query)
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict

from .retrieve import Hit
from .textnorm import quote_overlap

ABSTAIN_TEXT = "Not covered by the corpus."
QUOTE_THRESHOLD = 0.8

SYSTEM_PROMPT = """You answer questions about healthcare coverage and policy using ONLY the passages provided. The passages come from public Florida Medicaid, Medicare, Medicaid, and HIPAA documents.

Rules:
1. Use only the passages. Do not use outside knowledge, even if you are sure of it.
2. Every factual claim in your answer must be supported by a passage you cite. Cite by passage tag ([P1], [P2], ...) and copy a short verbatim quote (one to three sentences) from that passage that supports the claim.
3. If the passages do not answer the question, set "abstain" to true and make the answer exactly: "Not covered by the corpus." Do not guess. Do not answer a nearby question instead.
4. Keep the answer to one to three plain sentences a patient or billing clerk could act on. Include numbers, limits, and conditions exactly as the passages state them.
5. When two passages from different jurisdictions (for example Florida Medicaid and Medicare) both apply, answer for each and cite both.

Respond with JSON only, matching this shape:
{"answer": "...", "abstain": false, "citations": [{"passage": "P1", "quote": "..."}]}"""


@dataclass
class Citation:
    passage: str
    doc_id: str
    page: int
    quote: str
    overlap: float


@dataclass
class Answer:
    question: str
    answer: str
    abstained: bool
    citations: list[Citation]
    passages: list[dict]
    citations_proposed: int
    citations_dropped: int
    forced_abstain: bool
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    raw: str
    error: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["passages"] = [{k: p[k] for k in ("tag", "chunk_id", "doc_id", "page")} for p in self.passages]
        return d


def format_passages(hits: list[Hit]) -> list[dict]:
    out = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        out.append(
            {
                "tag": f"P{i}",
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "page": c["page"],
                "title": c["title"],
                "jurisdiction": c["jurisdiction"],
                "text": c["text"],
            }
        )
    return out


def build_user_message(question: str, passages: list[dict]) -> str:
    parts = []
    for p in passages:
        parts.append(f"[{p['tag']}] {p['title']} ({p['jurisdiction']}), page {p['page']}\n{p['text']}")
    return "Passages:\n\n" + "\n\n".join(parts) + f"\n\nQuestion: {question}"


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse_model_json(text: str) -> dict:
    """Accept clean JSON, JSON inside a code fence, or JSON with prose around it."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if not m:
            raise
        return json.loads(m.group(0))


def enforce_citations(data: dict, passages: list[dict]) -> tuple[str, bool, list[Citation], int, int, bool]:
    """Return (answer, abstained, kept citations, proposed, dropped, forced_abstain)."""
    by_tag = {p["tag"]: p for p in passages}
    proposed = data.get("citations") or []
    kept: list[Citation] = []
    for c in proposed:
        if not isinstance(c, dict):
            continue
        tag = str(c.get("passage", "")).strip().strip("[]").upper()
        quote = str(c.get("quote", "")).strip()
        p = by_tag.get(tag)
        if p is None or len(quote) < 15:
            continue
        ov = quote_overlap(quote, p["text"])
        if ov >= QUOTE_THRESHOLD:
            kept.append(Citation(tag, p["doc_id"], p["page"], quote, round(ov, 3)))
    abstained = bool(data.get("abstain")) or str(data.get("answer", "")).strip().lower().startswith("not covered")
    answer = str(data.get("answer", "")).strip()
    forced = False
    if abstained:
        answer = ABSTAIN_TEXT
        kept = []
    elif not kept:
        forced = True
        abstained = True
        answer = ABSTAIN_TEXT
    return answer, abstained, kept, len(proposed), len(proposed) - len(kept), forced


class Provider:
    """OpenAI-compatible chat completions client over plain HTTP."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None, timeout: float = 120.0, transport=None):
        self.base_url = (base_url or os.environ.get("POLICYQA_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("POLICYQA_LLM_API_KEY", "")
        self.model = model or os.environ.get("POLICYQA_LLM_MODEL", "")
        self.in_price = float(os.environ.get("POLICYQA_LLM_INPUT_USD_PER_M", "0") or 0)
        self.out_price = float(os.environ.get("POLICYQA_LLM_OUTPUT_USD_PER_M", "0") or 0)
        self.timeout = timeout
        self.transport = transport  # an httpx transport, for tests (httpx.MockTransport); None means the network
        if not (self.base_url and self.model):
            raise RuntimeError("Set POLICYQA_LLM_BASE_URL and POLICYQA_LLM_MODEL (and POLICYQA_LLM_API_KEY) to call a model.")

    def complete(self, system: str, user: str, max_tokens: int = 600) -> tuple[str, int, int]:
        import httpx

        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = self._headers()
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            r = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
            if r.status_code == 400 and "response_format" in r.text:
                body.pop("response_format")
                r = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
            r.raise_for_status()
        self.last_response = r.json()
        return self._unpack(self.last_response)

    def complete_parts(self, system: str, parts: list[dict], schema: dict | None = None, max_tokens: int = 1500) -> tuple[str, int, int]:
        """Multimodal chat completion: `parts` are OpenAI content parts (text, image_url, file).

        With a JSON schema, the request asks for `response_format: json_schema` (strict).
        A 400 that mentions response_format falls back to `json_object`, and a second
        such 400 falls back to no response_format at all. Without a schema no
        response_format is sent. Any other error is raised as httpx.HTTPStatusError so
        the caller can inspect it (the PDF file-part fallback in intake.py relies on this).

        Not yet exercised against the live Meta Model API (no key on this box); the
        request shape follows the OpenAI chat completions protocol the API documents.
        """
        import httpx

        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": parts}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        ladder: list[dict | None] = [None]
        if schema is not None:
            ladder = [{"type": "json_schema", "json_schema": {"name": "case_card", "schema": schema, "strict": True}}, {"type": "json_object"}, None]
        headers = self._headers()
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            for i, rf in enumerate(ladder):
                body.pop("response_format", None)
                if rf is not None:
                    body["response_format"] = rf
                r = client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                last = i == len(ladder) - 1
                if r.status_code == 400 and rf is not None and not last and "response_format" in r.text:
                    continue
                break
            r.raise_for_status()
        self.last_response = r.json()
        return self._unpack(self.last_response)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _unpack(j: dict) -> tuple[str, int, int]:
        content = j["choices"][0]["message"].get("content") or ""
        if isinstance(content, list):  # some endpoints return content as parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        usage = j.get("usage") or {}
        return content, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return round(input_tokens * self.in_price / 1e6 + output_tokens * self.out_price / 1e6, 6)


class MockProvider:
    """No network. Answers with the first sentence of the top passage and cites it.

    Exists so the whole pipeline (retrieval, prompt, enforcement, judge input,
    report) runs end to end before any model credits arrive.
    """

    model = "mock"

    def complete(self, system: str, user: str, max_tokens: int = 600) -> tuple[str, int, int]:
        m = re.search(r"\[P1\][^\n]*\n(.+?)(?:\n\n\[P2\]|\n\nQuestion:)", user, re.S)
        text = m.group(1).strip() if m else ""
        words = text.split()
        quote = " ".join(words[:30])
        out = {"answer": quote, "abstain": False, "citations": [{"passage": "P1", "quote": quote}]}
        return json.dumps(out), len(user.split()), len(quote.split())

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0


def answer_question(question: str, hits: list[Hit], provider, max_tokens: int = 600, trace=None) -> Answer:
    from contextlib import nullcontext

    passages = format_passages(hits)
    user = build_user_message(question, passages)
    t = time.perf_counter()
    raw, n_in, n_out = "", 0, 0
    error = None
    span = trace.span if trace is not None else (lambda name, **kw: nullcontext())
    with span("generate", model=getattr(provider, "model", "?"), passages=len(passages)):
        try:
            raw, n_in, n_out = provider.complete(SYSTEM_PROMPT, user, max_tokens=max_tokens)
            data = parse_model_json(raw)
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            error = f"{type(e).__name__}: {e}"
            data = {"answer": "", "abstain": True, "citations": []}
    latency = (time.perf_counter() - t) * 1000
    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, passages)
    if trace is not None:
        trace.set(input_tokens=n_in, output_tokens=n_out, cost_usd=provider.cost(n_in, n_out), abstained=abst, forced_abstain=forced, citations_kept=len(kept), citations_dropped=proposed - len(kept), error=error)
    return Answer(
        question=question,
        answer=ans,
        abstained=abst,
        citations=kept,
        passages=passages,
        citations_proposed=proposed,
        citations_dropped=dropped,
        forced_abstain=forced,
        model=getattr(provider, "model", "?"),
        input_tokens=n_in,
        output_tokens=n_out,
        cost_usd=provider.cost(n_in, n_out),
        latency_ms=round(latency, 1),
        raw=raw,
        error=error,
    )

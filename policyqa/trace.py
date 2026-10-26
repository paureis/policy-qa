"""Per-query traces: one JSON line per question with stage timings, tokens, and cost.

No vendor. A trace is a dict with a trace_id, the question, a list of spans
(name, ms), and whatever the stages attach (tokens, cost, citations kept).
Traces go to data/traces.jsonl by default and feed the cost and latency report.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class Trace:
    def __init__(self, question: str):
        self.trace_id = uuid.uuid4().hex[:12]
        self.question = question
        self.started = time.time()
        self.spans: list[dict] = []
        self.attrs: dict = {}

    @contextmanager
    def span(self, name: str, **attrs):
        t = time.perf_counter()
        try:
            yield
        finally:
            self.spans.append({"name": name, "ms": round((time.perf_counter() - t) * 1000, 1), **attrs})

    def set(self, **attrs) -> None:
        self.attrs.update(attrs)

    def total_ms(self) -> float:
        return round(sum(s["ms"] for s in self.spans), 1)

    def to_dict(self) -> dict:
        return {"trace_id": self.trace_id, "started": self.started, "question": self.question, "total_ms": self.total_ms(), "spans": self.spans, **self.attrs}


class TraceWriter:
    def __init__(self, path: Path | None):
        self.path = path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, trace: Trace) -> None:
        if not self.path:
            return
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")

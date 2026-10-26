from policyqa.trace import Trace


def test_spans_and_attrs_round_trip():
    tr = Trace("q")
    with tr.span("retrieve", mode="hybrid"):
        pass
    with tr.span("generate", model="m"):
        pass
    tr.set(input_tokens=10)
    d = tr.to_dict()
    assert [s["name"] for s in d["spans"]] == ["retrieve", "generate"]
    assert d["spans"][0]["mode"] == "hybrid" and d["input_tokens"] == 10
    assert d["total_ms"] >= 0 and len(d["trace_id"]) == 12

"""`python -m policyqa.cli smoke`: one tiny chat request through Provider, tested over httpx MockTransport."""
import json

import httpx

from policyqa.cli import main, smoke
from policyqa.generate import Provider


def test_smoke_without_env_lists_missing_and_exits_1(monkeypatch, capsys):
    for k in ("POLICYQA_LLM_BASE_URL", "POLICYQA_LLM_MODEL", "POLICYQA_LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert smoke() == 1
    out = capsys.readouterr().out
    assert "POLICYQA_LLM_BASE_URL" in out and "POLICYQA_LLM_MODEL" in out and "POLICYQA_LLM_API_KEY" in out


def test_smoke_with_env_prints_reply_and_usage(monkeypatch, capsys):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "muse-spark-1.3", "choices": [{"message": {"content": "ready"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 1}})

    monkeypatch.setenv("POLICYQA_LLM_INPUT_USD_PER_M", "0.5")
    monkeypatch.setenv("POLICYQA_LLM_OUTPUT_USD_PER_M", "1.5")
    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    assert smoke(p) == 0
    out = capsys.readouterr().out
    assert "muse-spark-1.3" in out and "ready" in out and "12" in out and "ms" in out and "$" in out
    assert "response_format" not in bodies[0]
    assert "ready" in bodies[0]["messages"][1]["content"][0]["text"]


def test_smoke_subcommand_is_wired(monkeypatch, capsys):
    for k in ("POLICYQA_LLM_BASE_URL", "POLICYQA_LLM_MODEL", "POLICYQA_LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    try:
        main(["smoke"])
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("smoke should exit 1 without the env")

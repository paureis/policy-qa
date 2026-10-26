import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app, DATA  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


@pytest.mark.skipif(not (DATA / "chunks.jsonl").exists(), reason="index not built")
def test_search_and_answer_with_mock():
    os.environ.pop("POLICYQA_LLM_BASE_URL", None)
    r = client.get("/search", params={"q": "How many home health visits per day does Florida Medicaid cover?", "k": 3})
    assert r.status_code == 200 and len(r.json()["hits"]) == 3
    r = client.post("/answer", json={"question": "Can an adult on Florida Medicaid get a fixed bridge?", "k": 3})
    body = r.json()
    assert r.status_code == 200 and "citations" in body and body["trace"]["spans"]

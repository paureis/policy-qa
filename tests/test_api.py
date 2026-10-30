import json
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


# ---- case intake ----------------------------------------------------------

import io  # noqa: E402
import struct  # noqa: E402
import zlib  # noqa: E402

from api.main import extractor  # noqa: E402
from api.cases import STORE  # noqa: E402


def _png_1x1() -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xff\xff")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _mini_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with real text objects and a correct xref, so pdftotext can read it."""
    content = "BT /F1 11 Tf 40 750 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


PNG_1X1 = _png_1x1()
MINI_PDF = _mini_pdf(["Hello"])
MINI_PDF_WITH_TEXT = _mini_pdf(
    [
        "Sunshine Health - Notice of Adverse Benefit Determination - October 14, 2026",
        "Member: J. Doe (age 9). Service requested: private duty nursing, 8 hours per day.",
        "Dates of service: September 1, 2026 through September 30, 2026. Amount billed: $4,320.00.",
        "Decision: DENIED. Reason: Services exceed the authorized amount.",
        "You have the right to appeal this decision. Appeals must be received by December 13, 2026.",
    ]
)

DENIAL_TEXT = (
    "Sunshine Health. Notice of Adverse Benefit Determination. Date: October 14, 2026. "
    "Member: J. Doe, age 9. We have denied the request for private duty nursing, 8 hours per day, "
    "for dates of service September 1 through September 30, 2026, billed at $4,320.00. "
    "Reason: Services exceed the authorized amount. You have the right to appeal within 60 days, by December 13, 2026."
)


@pytest.fixture(autouse=True)
def _fixture_mode(monkeypatch):
    monkeypatch.delenv("POLICYQA_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("POLICYQA_LLM_MODEL", raising=False)
    monkeypatch.delenv("RECOURSE_CRITIC_ROUNDS", raising=False)
    extractor.cache_clear()
    yield
    extractor.cache_clear()


def _intake_text(text=DENIAL_TEXT):
    return client.post("/case/intake", data={"text": text})


def test_health_reports_intake_fixture():
    assert client.get("/health").json()["intake"] == "fixture"


def test_health_reports_configured_model(monkeypatch):
    monkeypatch.setenv("POLICYQA_LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("POLICYQA_LLM_MODEL", "muse-spark-1.3")
    assert client.get("/health").json()["intake"] == "muse-spark-1.3"


def test_intake_text_fixture_mode():
    r = _intake_text()
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["case_id"].startswith("c_") and len(b["case_id"]) == 8
    assert b["source"] == "text" and b["raw_text"] == DENIAL_TEXT and b["status"] == "intake"
    assert b["model"] == "fixture" and b["cost_usd"] == 0.0 and b["latency_ms"] >= 0 and b["created_at"].endswith("Z")
    assert len(b["summary"]) > 100
    card = b["card"]
    assert list(card.keys()) == ["payer_name", "program", "member_age_group", "service", "service_code", "dates_of_service", "amount_billed", "denial_reason", "letter_date", "appeal_deadline_claimed"]
    assert card["payer_name"] == {"value": "Sunshine Health", "confidence": "high"}
    assert card["amount_billed"] == {"value": 4320.0, "confidence": "medium"}
    assert card["dates_of_service"] == {"value": "2026-09-01/2026-09-30", "confidence": "high"}
    assert STORE.get(b["case_id"]) is not None


def test_intake_png_and_pdf_fixture_mode():
    r = client.post("/case/intake", files={"file": ("letter.png", PNG_1X1, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "image" and "Sunshine Health" in r.json()["raw_text"]
    r = client.post("/case/intake", files={"file": ("letter.pdf", MINI_PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "pdf"


def test_intake_sniffs_bytes_not_declared_type():
    # declared PDF, really a PNG: accepted as an image
    r = client.post("/case/intake", files={"file": ("letter.pdf", PNG_1X1, "application/pdf")})
    assert r.status_code == 200 and r.json()["source"] == "image"
    # declared PNG, really plain text: rejected
    r = client.post("/case/intake", files={"file": ("letter.png", b"hello there this is not an image", "image/png")})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "unsupported_type"


def test_intake_error_codes():
    r = client.post("/case/intake", files={"file": ("x.gif", b"GIF89a" + b"\x00" * 20, "image/gif")})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "unsupported_type"
    r = client.post("/case/intake", files={"file": ("big.pdf", b"%PDF-1.4" + b"\x00" * (10 * 1024 * 1024 + 1), "application/pdf")})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_large"
    r = _intake_text("too short")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "text_length"
    r = _intake_text("x" * 6001)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "text_length"
    r = _intake_text("Dear friend, thank you for the lovely birthday wishes and the photos from the trip. " * 4)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_a_denial_letter"
    r = _intake_text(DENIAL_TEXT + " Also, should I take a higher dosage of my medication while the appeal is pending?")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "out_of_scope"
    assert "message" in r.json()["detail"]


def test_intake_both_or_neither_is_400():
    r = client.post("/case/intake", data={"text": DENIAL_TEXT}, files={"file": ("l.png", PNG_1X1, "image/png")})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_request"
    r = client.post("/case/intake", data={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_request"


def test_get_case_and_404():
    cid = _intake_text().json()["case_id"]
    r = client.get(f"/case/{cid}")
    assert r.status_code == 200 and r.json()["case_id"] == cid and r.json()["card"]["payer_name"]["value"] == "Sunshine Health"
    assert client.get("/case/c_000000").status_code == 404
    assert client.patch("/case/c_000000", json={"payer_name": "X"}).status_code == 404
    assert client.post("/case/c_000000/investigate").status_code == 404


def test_patch_happy_path():
    cid = _intake_text().json()["case_id"]
    r = client.patch(f"/case/{cid}", json={"service_code": "T1000", "amount_billed": "4,500.50", "program": "florida_kidcare", "letter_date": "2026-10-15", "dates_of_service": "2026-09-01/2026-09-15"})
    assert r.status_code == 200, r.text
    card = r.json()["card"]
    assert card["service_code"] == {"value": "T1000", "confidence": "high", "edited": True}
    assert card["amount_billed"] == {"value": 4500.5, "confidence": "high", "edited": True}
    assert card["program"] == {"value": "florida_kidcare", "confidence": "high", "edited": True}
    assert card["letter_date"]["value"] == "2026-10-15" and card["dates_of_service"]["value"] == "2026-09-01/2026-09-15"
    assert card["payer_name"] == {"value": "Sunshine Health", "confidence": "high"}  # untouched, no edited flag
    assert r.json()["status"] == "intake"
    assert client.get(f"/case/{cid}").json()["card"]["service_code"]["edited"] is True


def test_patch_bad_values():
    cid = _intake_text().json()["case_id"]
    for body, field in (
        ({"program": "blue_cross"}, "program"),
        ({"member_age_group": "teen"}, "member_age_group"),
        ({"letter_date": "10/15/2026"}, "letter_date"),
        ({"dates_of_service": "September"}, "dates_of_service"),
        ({"amount_billed": "lots"}, "amount_billed"),
        ({"amount_billed": 1234567}, "amount_billed"),
        ({"payer_name": ""}, "payer_name"),
        ({"not_a_field": "x"}, "not_a_field"),
    ):
        r = client.patch(f"/case/{cid}", json=body)
        assert r.status_code == 422, (body, r.text)
        assert r.json()["detail"]["field"] == field and r.json()["detail"]["code"] == "invalid_field"
    assert client.patch(f"/case/{cid}", json=[1, 2]).status_code == 422
    assert client.patch(f"/case/{cid}", json={}).status_code == 422


def test_investigate_then_patch_conflicts(monkeypatch):
    import api.main as m

    monkeypatch.setattr(m, "RUN_INVESTIGATION_INLINE", False)
    cid = _intake_text().json()["case_id"]
    r = client.post(f"/case/{cid}/investigate")
    assert r.status_code == 202 and r.json() == {"case_id": cid, "status": "investigating"}
    m.INVESTIGATION_THREADS[cid].join(timeout=10)
    assert client.get(f"/case/{cid}").json()["status"] == "reviewed"  # the chain runs on to the letter and its review
    r = client.patch(f"/case/{cid}", json={"payer_name": "X"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "wrong_status"
    r = client.post(f"/case/{cid}/investigate")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "wrong_status"


def test_patch_null_clears_a_non_enum_field_but_not_an_enum():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    case = client.post("/case/intake", data={"text": DENIAL_TEXT}).json()
    r = client.patch(f"/case/{case['case_id']}", json={"appeal_deadline_claimed": None})
    assert r.status_code == 200, r.text
    cell = r.json()["card"]["appeal_deadline_claimed"]
    assert cell == {"value": None, "confidence": "high", "edited": True}
    r = client.patch(f"/case/{case['case_id']}", json={"program": None})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_field"


def test_malformed_patch_bodies_keep_the_error_shape():
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    case = client.post("/case/intake", data={"text": DENIAL_TEXT}).json()
    for body in ('["service"]', '"service"', "{not json"):
        r = client.patch(f"/case/{case['case_id']}", content=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 422, (body, r.text)
        d = r.json()["detail"]
        assert isinstance(d, dict) and d["code"] == "invalid_field" and d["message"], (body, r.text)


# ---- investigation ----------------------------------------------------------

import api.main as api_main  # noqa: E402
from api.main import investigator  # noqa: E402


@pytest.fixture(autouse=True)
def _investigation_inline(monkeypatch):
    """Run the investigation synchronously in the request and skip the fixture's 0.8 s pauses."""
    monkeypatch.setattr(api_main, "RUN_INVESTIGATION_INLINE", True)
    monkeypatch.setattr(api_main, "FIXTURE_DELAY", 0)
    investigator.cache_clear()
    yield
    investigator.cache_clear()


def test_new_case_has_null_route_and_investigation():
    b = _intake_text().json()
    assert b["route"] is None and b["investigation"] is None and b["status"] == "intake"


def test_health_reports_investigation_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    assert client.get("/health").json()["investigation"] == "fixture"
    monkeypatch.setenv("POLICYQA_LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("POLICYQA_LLM_MODEL", "muse-spark-1.3")
    # env set but no index on disk: still the fixture
    assert client.get("/health").json()["investigation"] == "fixture"
    (tmp_path / "chunks.jsonl").write_text("")
    assert client.get("/health").json()["investigation"] == "muse-spark-1.3"


def test_investigate_fixture_path_through_the_real_app(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)  # no index, and the autouse fixture above removed the env
    cid = _intake_text().json()["case_id"]
    r = client.post(f"/case/{cid}/investigate")
    assert r.status_code == 202 and r.json() == {"case_id": cid, "status": "investigating"}
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed"  # inline: investigation, verdict, letter, and critic all ran
    assert b["route"] == {"program": "florida_medicaid_mma", "jurisdictions": ["Florida"], "dual": False, "reason": b["route"]["reason"], "outside_corpus": False}
    assert b["route"]["reason"].endswith(".")
    inv = b["investigation"]
    assert inv["status"] == "done" and inv["error"] is None and inv["model"] == "fixture"
    assert inv["questions_planned"] == 5 and inv["questions_done"] == 5 and len(inv["findings"]) == 5
    assert set(inv) >= {"status", "started_at", "finished_at", "questions_planned", "questions_done", "findings", "coverage", "cost_usd", "latency_ms", "model", "error", "trace"}
    assert inv["coverage"] == {"claims": 4, "supported": 3, "errors": 0}
    assert {f["status"] for f in inv["findings"]} == {"supported", "not_settled", "unsupported"}
    f = inv["findings"][0]
    assert set(f) == {"id", "question", "topic", "jurisdiction", "status", "answer", "citations", "struck", "passages", "error", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd"}
    assert f["error"] is None and set(f["passages"][0]) == {"chunk_id", "doc_id", "title", "page"}
    assert set(f["citations"][0]) == {"doc_id", "title", "page", "quote", "overlap"}
    struck = next(x for x in inv["findings"] if x["status"] == "unsupported")["struck"][0]
    assert set(struck) == {"doc_id", "title", "page", "quote", "reason"}
    assert inv["trace"]["spans"]
    # the whole case keeps every intake field
    assert b["card"]["payer_name"]["value"] == "Sunshine Health" and b["summary"] and b["raw_text"]
    # a second call conflicts
    r = client.post(f"/case/{cid}/investigate")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "wrong_status"


def test_investigate_background_thread_updates_the_case_as_findings_arrive(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setattr(api_main, "RUN_INVESTIGATION_INLINE", False)
    monkeypatch.setattr(api_main, "FIXTURE_DELAY", 0.05)
    investigator.cache_clear()
    cid = _intake_text().json()["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    b = client.get(f"/case/{cid}").json()
    assert b["status"] in ("investigating", "investigated", "deciding", "decided", "drafting", "drafted", "reviewing", "reviewed") and b["route"]["jurisdictions"] == ["Florida"]
    assert b["investigation"]["status"] in ("running", "done") and b["investigation"]["questions_done"] <= 5
    t = api_main.INVESTIGATION_THREADS[cid]
    assert t.daemon
    t.join(timeout=10)
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["investigation"]["questions_done"] == 5 and len(b["investigation"]["findings"]) == 5


def test_investigation_failure_marks_the_case_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class Boom:
        model = "boom"

        def route(self, card, summary=None):
            from policyqa.investigate import route_case

            return route_case(card, summary)

        def investigate(self, case, on_progress=None):
            raise RuntimeError("provider down")

    monkeypatch.setattr(api_main, "investigator", lambda: Boom())
    cid = _intake_text().json()["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed" and b["investigation"]["status"] == "failed" and "RuntimeError" in b["investigation"]["error"]
    assert b["investigation"]["finished_at"] and b["investigation"]["findings"] == []


def test_set_investigation_store_method():
    from api.cases import CaseStore

    s = CaseStore()
    c = s.create({"card": {}})
    assert c["route"] is None and c["investigation"] is None
    inv = {"status": "running", "findings": [{"id": "f1"}]}
    out = s.set_investigation(c["case_id"], {"program": "unknown"}, inv, "investigating")
    inv["findings"].append({"id": "f2"})  # the store keeps its own copy
    assert out["status"] == "investigating" and len(s.get(c["case_id"])["investigation"]["findings"]) == 1
    assert s.set_investigation("c_nope", None, None, "failed") is None


def test_concurrent_investigate_posts_claim_the_case_once(monkeypatch, tmp_path):
    """20 posts at once: exactly one 202, the rest 409. The slow route() widens the window a check-then-set would lose."""
    import threading
    import time

    from policyqa.investigate import FixtureInvestigator

    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class SlowRoute(FixtureInvestigator):
        def route(self, card, summary=None):
            time.sleep(0.05)
            return super().route(card, summary)

    slow = SlowRoute(delay=0)
    monkeypatch.setattr(api_main, "investigator", lambda: slow)
    cid = _intake_text().json()["case_id"]
    barrier = threading.Barrier(20)
    codes = []
    lock = threading.Lock()

    def post():
        barrier.wait()
        r = client.post(f"/case/{cid}/investigate")
        with lock:
            codes.append(r.status_code)

    threads = [threading.Thread(target=post) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert sorted(codes) == [202] + [409] * 19, codes
    assert client.get(f"/case/{cid}").json()["status"] == "reviewed"


def test_claim_for_investigation_store_method():
    from api.cases import CaseStore

    s = CaseStore()
    c = s.create({"card": {}})
    assert s.claim_for_investigation(c["case_id"]) is True
    assert s.get(c["case_id"])["status"] == "investigating"
    assert s.claim_for_investigation(c["case_id"]) is False
    assert s.claim_for_investigation("c_nope") is False


# ---- steelman, verdict, letter (one POST drives the chain) ------------------------------

VERDICT_KEYS = {"status", "steelman", "outcome", "proposed_outcome", "headline", "rule", "gap", "what_would_change",
                "decisive_fact", "relies_on_exception", "exceptions",  # Oct 27, second tuning pass
                "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}
LETTER_KEYS = {"status", "applicable", "explanation", "to", "re", "paragraphs", "evidence_checklist", "evidence_note", "deadline", "filing", "verification", "draft_paragraphs", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}
REF_KEYS = {"finding_id", "doc_id", "title", "page", "quote"}


def _status_spy(monkeypatch):
    seen = []
    orig_inv, orig_stage = STORE.set_investigation, STORE.set_stage

    def set_investigation(case_id, route, inv, status):
        seen.append(status)
        return orig_inv(case_id, route, inv, status)

    def set_stage(case_id, field, value, status=None):
        if status is not None:
            seen.append(status)
        return orig_stage(case_id, field, value, status)

    monkeypatch.setattr(STORE, "set_investigation", set_investigation)
    monkeypatch.setattr(STORE, "set_stage", set_stage)
    return seen


def test_new_case_has_null_verdict_and_letter():
    b = _intake_text().json()
    assert b["verdict"] is None and b["letter"] is None


def test_health_reports_verdict_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    assert client.get("/health").json()["verdict"] == "fixture"
    monkeypatch.setenv("POLICYQA_LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("POLICYQA_LLM_MODEL", "muse-spark-1.3")
    (tmp_path / "chunks.jsonl").write_text("")
    assert client.get("/health").json()["verdict"] == "muse-spark-1.3"


def test_chain_runs_inline_through_every_status_with_the_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    seen = _status_spy(monkeypatch)
    cid = _intake_text().json()["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    order = [s for i, s in enumerate(seen) if i == 0 or s != seen[i - 1]]
    assert order == ["investigating", "investigated", "deciding", "decided", "drafting", "drafted", "reviewing", "reviewed"], seen
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["investigation"]["status"] == "done"
    v = b["verdict"]
    assert set(v) == VERDICT_KEYS and v["status"] == "done" and v["model"] == "fixture" and v["error"] is None
    assert v["outcome"] == "inconsistent" and v["headline"] == "The denial appears inconsistent with the policy."
    assert set(v["steelman"]) == {"argument", "citations", "unsupported"} and set(v["rule"]) == {"statement", "citations", "unsupported"}
    assert v["rule"]["citations"] and set(v["rule"]["citations"][0]) == REF_KEYS and v["what_would_change"] is None
    L = b["letter"]
    assert set(L) == LETTER_KEYS and L["status"] == "done" and L["applicable"] is True and L["model"] == "fixture"
    assert L["to"] == "Sunshine Health" and L["re"].startswith("Appeal of the denial of private duty nursing")
    s0 = L["paragraphs"][1]["sentences"][0]
    assert set(s0) == {"text", "claim", "citation", "verified", "struck", "reason"}
    assert L["verification"]["struck"] == 0 and L["verification"]["verified"] >= 1  # the critic removed the struck claim
    assert sum(x["struck"] for p in L["draft_paragraphs"] for x in p["sentences"]) == 1  # the draft keeps it
    assert set(L["deadline"]) == {"date", "days_left", "source", "citation", "note"} and L["deadline"]["source"] == "letter" and L["deadline"]["date"] == "2026-12-13"
    assert set(L["filing"]) == {"where", "how", "citation"} and L["filing"]["citation"]["finding_id"]
    assert 3 <= len(L["evidence_checklist"]) <= 7 and set(L["evidence_checklist"][0]) == {"item", "why", "citation"}
    names = [sp["name"] for sp in b["investigation"]["trace"]["spans"]]
    assert names[-3:] == ["steelman_verdict", "letter", "critic"]


def test_letter_txt_route(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    assert client.get("/case/c_nope00/letter.txt").status_code == 404
    cid = _intake_text().json()["case_id"]
    r = client.get(f"/case/{cid}/letter.txt")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_ready"
    client.post(f"/case/{cid}/investigate")
    r = client.get(f"/case/{cid}/letter.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert r.text.startswith("To: Sunshine Health\nRe: Appeal of the denial of") and "[cite: " in r.text
    assert "every hour a provider bills" not in r.text  # the struck sentence is not exported


def test_letter_txt_is_409_when_the_denial_matches_the_policy(monkeypatch, tmp_path):
    from policyqa.verdict import FixtureVerdict

    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class Consistent(FixtureVerdict):
        def reply(self, investigation):
            d = super().reply(investigation)
            d.update(outcome="consistent", what_would_change="An authorization for the extra hours.")
            return d

    monkeypatch.setattr(api_main, "verdicter", lambda: Consistent(delay=0))
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["verdict"]["outcome"] == "consistent"
    assert b["critique"]["skipped"] is True and "matches the policy" in b["critique"]["reason"]
    assert b["letter"]["applicable"] is False and b["letter"]["paragraphs"] == [] and b["letter"]["explanation"]
    r = client.get(f"/case/{cid}/letter.txt")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_applicable"


def test_a_failing_verdict_marks_the_case_failed_and_keeps_the_investigation(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class Boom:
        model = "boom"

        def decide(self, case, investigation):
            raise RuntimeError("verdict exploded")

    monkeypatch.setattr(api_main, "verdicter", lambda: Boom())
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed"
    assert b["investigation"]["status"] == "done" and len(b["investigation"]["findings"]) == 5
    assert b["verdict"]["status"] == "failed" and "verdict exploded" in b["verdict"]["error"] and b["verdict"]["model"] == "boom"
    assert set(b["verdict"]) == VERDICT_KEYS
    assert b["letter"] is None
    assert client.get(f"/case/{cid}/letter.txt").status_code == 404


def test_a_failing_letter_keeps_the_verdict(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class Boom:
        model = "boom"

        def draft(self, case, investigation, verdict):
            raise RuntimeError("letter exploded")

    monkeypatch.setattr(api_main, "letterer", lambda: Boom())
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed" and b["verdict"]["status"] == "done"
    assert b["letter"]["status"] == "failed" and "letter exploded" in b["letter"]["error"] and set(b["letter"]) == LETTER_KEYS
    assert b["critique"] is None  # the critic never runs on a failed letter


def test_failed_investigation_does_not_run_the_verdict(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    called = []
    monkeypatch.setattr(api_main, "verdicter", lambda: called.append(1))

    class Boom:
        model = "boom"

        def route(self, card, summary=None):
            from policyqa.investigate import route_case

            return route_case(card, summary)

        def investigate(self, case, on_progress=None):
            raise RuntimeError("provider down")

    monkeypatch.setattr(api_main, "investigator", lambda: Boom())
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed" and b["verdict"] is None and called == []


def test_background_chain_ends_drafted(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setattr(api_main, "RUN_INVESTIGATION_INLINE", False)
    monkeypatch.setattr(api_main, "FIXTURE_DELAY", 0.02)
    investigator.cache_clear()
    cid = _intake_text().json()["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    api_main.INVESTIGATION_THREADS[cid].join(timeout=10)
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["verdict"]["status"] == "done" and b["letter"]["status"] == "done" and b["critique"]["status"] == "done"


def test_set_stage_store_method():
    from api.cases import CaseStore

    s = CaseStore()
    c = s.create({"card": {}})
    v = {"status": "running"}
    out = s.set_stage(c["case_id"], "verdict", v, "deciding")
    v["status"] = "changed"  # the store keeps its own copy
    assert out["status"] == "deciding" and s.get(c["case_id"])["verdict"] == {"status": "running"}
    s.set_stage(c["case_id"], "letter", {"status": "done"})  # no status: the case status is kept
    assert s.get(c["case_id"])["status"] == "deciding"
    with pytest.raises(ValueError):
        s.set_stage(c["case_id"], "card", {}, None)
    assert s.set_stage("c_nope", "verdict", {}, "failed") is None


def test_an_error_outside_the_stages_still_fails_the_running_stage(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setattr(api_main, "_add_span", lambda case_id, span: (_ for _ in ()).throw(RuntimeError("trace store broke")))
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed" and b["verdict"]["status"] == "failed" and "trace store broke" in b["verdict"]["error"]


# ---- critic (reviewing -> reviewed) ---------------------------------------------------------

CRITIQUE_KEYS = {"status", "skipped", "reason", "rounds", "issues_found", "issues_fixed", "accepted", "model", "cost_usd", "latency_ms", "error"}
ROUND_KEYS = {"round", "issues", "before", "after", "verification_before", "verification_after", "accepted", "rejected_reason", "model", "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}


def test_new_case_has_null_critique():
    assert _intake_text().json()["critique"] is None


def test_health_reports_critic_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    assert client.get("/health").json()["critic"] == "fixture"
    monkeypatch.setenv("RECOURSE_CRITIC_ROUNDS", "0")
    assert client.get("/health").json()["critic"] == "off"
    monkeypatch.setenv("RECOURSE_CRITIC_ROUNDS", "2")
    monkeypatch.setenv("POLICYQA_LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("POLICYQA_LLM_MODEL", "muse-spark-1.3")
    (tmp_path / "chunks.jsonl").write_text("")
    assert client.get("/health").json()["critic"] == "muse-spark-1.3"


def test_chain_reviews_the_letter_inline_in_fixture_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    cid = _intake_text().json()["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed"
    c = b["critique"]
    assert set(c) == CRITIQUE_KEYS and c["status"] == "done" and c["skipped"] is False and c["reason"] is None and c["model"] == "fixture"
    assert c["accepted"] is True and c["issues_found"] == 2 and c["issues_fixed"] == 2 and c["error"] is None
    r = c["rounds"][0]
    assert set(r) == ROUND_KEYS and r["round"] == 1 and r["accepted"] is True and r["rejected_reason"] is None
    assert [i["kind"] for i in r["issues"]] == ["unverified_claim", "missing_request"]
    assert set(r["issues"][0]) == {"kind", "severity", "where", "note", "fixed"} and set(r["issues"][0]["where"]) == {"paragraph", "sentence"}
    assert set(r["verification_before"]) == {"claims", "verified", "struck"} and r["verification_after"]["struck"] == 0
    L = b["letter"]
    assert L["draft_paragraphs"] and L["draft_paragraphs"] == r["before"] and L["paragraphs"] == r["after"] and L["paragraphs"] != L["draft_paragraphs"]
    assert L["verification"] == r["verification_after"]
    span = b["investigation"]["trace"]["spans"][-1]
    assert span["name"] == "critic" and span["accepted"] is True and span["rounds"] == 1 and span["issues_found"] == 2


def test_letter_txt_reflects_the_accepted_revision(monkeypatch, tmp_path):
    from policyqa.critic import FIXTURE_REQUEST

    monkeypatch.setattr(api_main, "DATA", tmp_path)
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    r = client.get(f"/case/{cid}/letter.txt")
    assert r.status_code == 200 and FIXTURE_REQUEST in r.text and "every hour a provider bills" not in r.text and "[cite: " in r.text


def test_critic_off_still_ends_reviewed_with_the_draft(monkeypatch, tmp_path):
    from policyqa.critic import FIXTURE_REQUEST

    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setenv("RECOURSE_CRITIC_ROUNDS", "0")
    seen = _status_spy(monkeypatch)
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    assert [s for i, s in enumerate(seen) if i == 0 or s != seen[i - 1]][-3:] == ["drafted", "reviewing", "reviewed"]
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["critique"]["skipped"] is True and "RECOURSE_CRITIC_ROUNDS" in b["critique"]["reason"]
    assert b["critique"]["rounds"] == [] and b["letter"]["paragraphs"] == b["letter"]["draft_paragraphs"]
    assert FIXTURE_REQUEST not in client.get(f"/case/{cid}/letter.txt").text


def test_a_critic_model_error_leaves_the_letter_as_drafted(monkeypatch, tmp_path):
    from policyqa.critic import LiveCritic

    class Down:
        model = "muse-spark-1.3"
        last_response = None

        def complete_parts(self, *a, **kw):
            raise RuntimeError("HTTP 503 from the model")

    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setattr(api_main, "critic", lambda: LiveCritic(Down(), rounds=1))
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["critique"]["status"] == "done" and "HTTP 503" in b["critique"]["error"]
    assert b["critique"]["accepted"] is False and b["critique"]["rounds"][0]["error"]
    assert b["letter"]["paragraphs"] == b["letter"]["draft_paragraphs"] and b["letter"]["verification"]["struck"] == 1


def test_a_critic_exception_fails_the_critique_but_the_case_ends_reviewed(monkeypatch, tmp_path):
    class Boom:
        model = "boom"

        def review(self, case, investigation, verdict, letter):
            raise RuntimeError("critic exploded")

    monkeypatch.setattr(api_main, "DATA", tmp_path)
    monkeypatch.setattr(api_main, "critic", lambda: Boom())
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["critique"]["status"] == "failed" and "critic exploded" in b["critique"]["error"]
    assert set(b["critique"]) == CRITIQUE_KEYS and b["letter"]["status"] == "done"
    assert b["letter"]["paragraphs"] == b["letter"]["draft_paragraphs"]
    assert client.get(f"/case/{cid}/letter.txt").status_code == 200


def test_set_stage_accepts_the_critique():
    from api.cases import CaseStore

    s = CaseStore()
    c = s.create({"card": {}})
    assert c["critique"] is None
    s.set_stage(c["case_id"], "critique", {"status": "running"}, "reviewing")
    assert s.get(c["case_id"])["critique"] == {"status": "running"} and s.get(c["case_id"])["status"] == "reviewing"


# ---- highlighted page images ----------------------------------------------

FL04_PDF = Path(api_main.ROOT) / "data" / "pdfs" / "fl-04.pdf"
PDN_QUOTE = "Florida Medicaid covers up to 24 hours of PDN services per day, per recipient"
needs_fl04 = pytest.mark.skipif(not (FL04_PDF.exists() and FL04_PDF.stat().st_size > 10_000), reason="data/pdfs/fl-04.pdf is not fetched on this machine")


@pytest.fixture()
def page_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("RECOURSE_PAGE_CACHE", str(tmp_path / "pages"))
    monkeypatch.setenv("RECOURSE_VISION_CACHE", str(tmp_path / "vision"))
    monkeypatch.delenv("RECOURSE_PDF_DIR", raising=False)
    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", None, raising=False)
    api_main.VISION_CACHE.clear()
    yield tmp_path
    api_main.VISION_CACHE.clear()


@needs_fl04
def test_page_png_route(page_cache):
    r = client.get("/doc/fl-04/page/5.png", params={"dpi": 110})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/png" and r.headers["cache-control"] == "public, max-age=86400"
    assert r.content.startswith(b"\x89PNG") and len(r.content) > 50_000
    assert client.get("/doc/fl-04/page/5.png").status_code == 200  # dpi defaults to 110


def test_page_png_unknown_doc_is_404(page_cache):
    r = client.get("/doc/zz-99/page/1.png")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"


@needs_fl04
def test_page_png_bad_page_is_404(page_cache):
    r = client.get("/doc/fl-04/page/99.png")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "bad_page"


def test_page_png_without_the_pdf_is_503(page_cache, monkeypatch):
    empty = page_cache / "no-pdfs"
    empty.mkdir()
    monkeypatch.setenv("RECOURSE_PDF_DIR", str(empty))
    r = client.get("/doc/fl-04/page/5.png")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "no_pdf"
    r = client.get("/doc/fl-04/page/5/highlight", params={"quote": PDN_QUOTE})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "no_pdf"
    assert client.get("/health").json()["pdfs"] == 0


def test_page_png_dpi_out_of_range_is_422(page_cache):
    r = client.get("/doc/fl-04/page/5.png", params={"dpi": 2000})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_field"


@needs_fl04
def test_highlight_route(page_cache):
    r = client.get("/doc/fl-04/page/5/highlight", params={"quote": PDN_QUOTE})
    assert r.status_code == 200, r.text
    h = r.json()
    assert h["doc_id"] == "fl-04" and h["page"] == 5 and h["dpi"] == 110 and h["found"] is True and h["score"] == 1.0
    assert (h["width_px"], h["height_px"]) == (935, 1210) and h["image_url"] == "/doc/fl-04/page/5.png?dpi=110"
    assert h["boxes_px"] and set(h["boxes_px"][0]) == {"x0", "y0", "x1", "y1"}
    assert h["title"].startswith("Florida Medicaid")


def test_highlight_short_quote_is_422(page_cache):
    r = client.get("/doc/fl-04/page/5/highlight", params={"quote": "24 hours"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_field" and r.json()["detail"]["field"] == "quote"


def test_highlight_unknown_doc_is_404(page_cache):
    r = client.get("/doc/zz-99/page/1/highlight", params={"quote": PDN_QUOTE})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"


@needs_fl04
def test_vision_check_route_fixture_mode_and_cache(page_cache, monkeypatch):
    r = client.post("/doc/fl-04/page/5/vision-check", json={"quote": PDN_QUOTE})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["found"] is True and b["boxes_px"] and b["image_url"] == "/doc/fl-04/page/5.png?dpi=110"
    assert b["vision"]["checked"] is True and b["vision"]["model"] == "fixture" and b["vision"]["agrees"] is True
    assert b["vision"]["text_in_highlight"] == PDN_QUOTE
    # the second open is served from memory: the check does not run again
    import policyqa.pages as pages_mod

    monkeypatch.setattr(pages_mod, "vision_check", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ran twice")))
    again = client.post("/doc/fl-04/page/5/vision-check", json={"quote": PDN_QUOTE}).json()
    assert b["vision"]["cached"] is False and again["vision"]["cached"] is True
    first = {k: v for k, v in b["vision"].items() if k not in ("cached", "latency_ms", "cost_usd")}
    assert {k: v for k, v in again["vision"].items() if k in first} == first
    assert {k: v for k, v in again.items() if k != "vision"} == {k: v for k, v in b.items() if k != "vision"}


@needs_fl04
def test_vision_check_route_live_mode_uses_the_provider(page_cache, monkeypatch):
    calls = []

    class Fake:
        model = "muse-spark-1.3"
        last_response = {}

        def complete_parts(self, system, parts, schema=None, max_tokens=1500, **kw):
            calls.append(parts)
            return json.dumps({"text_in_highlight": PDN_QUOTE, "contains_quote": True}), 10, 5

        def cost(self, a, b):
            return 0.0

    monkeypatch.setenv("POLICYQA_LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("POLICYQA_LLM_MODEL", "muse-spark-1.3")
    monkeypatch.setattr(api_main, "provider", lambda: Fake())
    b = client.post("/doc/fl-04/page/5/vision-check", json={"quote": PDN_QUOTE, "dpi": 110}).json()
    assert b["vision"]["model"] == "muse-spark-1.3" and b["vision"]["agrees"] is True and len(calls) == 1


def test_vision_check_route_short_quote_is_422(page_cache):
    r = client.post("/doc/fl-04/page/5/vision-check", json={"quote": "too short"})
    assert r.status_code == 422 and r.json()["detail"]["field"] == "quote"


# ---- the disk-backed vision cache (no PDF needed: highlight and the model are faked) ----

FAKE_HL = {"doc_id": "fl-04", "title": "Florida Medicaid PDN", "page": 5, "dpi": 110, "width_px": 935, "height_px": 1210,
           "boxes_px": [{"x0": 10, "y0": 20, "x1": 300, "y1": 40}], "score": 1.0, "found": True, "matched": PDN_QUOTE,
           "image_url": "/doc/fl-04/page/5.png?dpi=110"}


@pytest.fixture()
def vision_route(page_cache, monkeypatch):
    """The vision-check route over a fake highlight and a counting fake model; the cache dir is page_cache/vision."""
    import policyqa.pages as pages_mod

    import threading

    class Vp:
        model = "muse-spark-1.3"

    vp = Vp()
    runs = {"n": 0, "result": None, "vp": vp, "thread": None}

    def fake_check(doc_id, page, quote, provider, dpi=110, hl=None):
        runs["n"] += 1
        runs["thread"] = threading.get_ident()  # the request's worker thread (TestClient does not run it on pytest's)
        if runs["result"] is not None:
            return dict(runs["result"])
        return {"checked": True, "model": provider.model, "text_in_highlight": quote, "agrees": True,
                "input_tokens": 1200, "output_tokens": 40, "reasoning_tokens": 0, "latency_ms": 3100.0, "cost_usd": 0.005}

    monkeypatch.setattr(pages_mod, "highlight", lambda doc_id, page, quote, dpi=110: dict(FAKE_HL, dpi=dpi))
    monkeypatch.setattr(pages_mod, "vision_check", fake_check)
    monkeypatch.setattr(api_main, "vision_provider", lambda: vp)
    return runs


VISION_KEY = ("fl-04", 5, PDN_QUOTE, 110, "muse-spark-1.3")  # the key _vision_post makes under vision_route


def _vision_post(dpi=110):
    r = client.post("/doc/fl-04/page/5/vision-check", json={"quote": PDN_QUOTE, "dpi": dpi})
    assert r.status_code == 200, r.text
    return r.json()


def test_vision_cache_survives_a_restart(vision_route, page_cache):
    first = _vision_post()
    assert first["vision"]["cached"] is False and first["vision"]["latency_ms"] == 3100.0 and first["vision"]["cost_usd"] == 0.005
    files = list((page_cache / "vision").glob("*.json"))
    assert len(files) == 1
    api_main.VISION_CACHE.clear()  # a redeploy or a restart empties the memory cache
    again = _vision_post()
    assert vision_route["n"] == 1  # read from disk: the model did not run again
    v = again["vision"]
    assert v["cached"] is True and v["latency_ms"] == 0 and v["cost_usd"] == 0
    assert v["source_latency_ms"] == 3100.0 and v["source_cost_usd"] == 0.005
    assert v["agrees"] is True and v["text_in_highlight"] == PDN_QUOTE and v["model"] == "muse-spark-1.3"
    assert {k: x for k, x in again.items() if k != "vision"} == FAKE_HL


def test_vision_cache_memory_hit_is_marked_cached(vision_route):
    _vision_post()
    v = _vision_post()["vision"]
    assert vision_route["n"] == 1
    assert v["cached"] is True and v["latency_ms"] == 0 and v["cost_usd"] == 0 and v["source_latency_ms"] == 3100.0


def test_vision_cache_key_includes_the_dpi(vision_route, page_cache):
    _vision_post(110)
    assert _vision_post(150)["vision"]["cached"] is False and vision_route["n"] == 2
    assert len(list((page_cache / "vision").glob("*.json"))) == 2


def test_vision_cache_never_stores_a_failure(vision_route, page_cache):
    vision_route["result"] = {"checked": False, "model": "muse-spark-1.3", "error": "ReadTimeout: timed out", "latency_ms": 30000.0}
    assert _vision_post()["vision"]["cached"] is False
    v = _vision_post()["vision"]
    assert vision_route["n"] == 2 and v["cached"] is False and v["error"].startswith("ReadTimeout")
    assert not list((page_cache / "vision").glob("*.json"))  # glob on a missing dir is empty too


def test_vision_cache_corrupt_file_is_ignored_and_overwritten(vision_route, page_cache):
    _vision_post()
    (f,) = list((page_cache / "vision").glob("*.json"))
    f.write_text("{not json", encoding="utf-8")
    api_main.VISION_CACHE.clear()
    v = _vision_post()["vision"]
    assert vision_route["n"] == 2 and v["cached"] is False
    assert json.loads(f.read_text(encoding="utf-8"))  # rewritten whole
    assert not list((page_cache / "vision").glob("*.tmp"))


def test_vision_cache_write_error_is_logged_not_raised(vision_route, page_cache, monkeypatch, caplog):
    blocker = page_cache / "a-file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("RECOURSE_VISION_CACHE", str(blocker / "vision"))  # a dir under a file: mkdir fails
    commits = []
    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", lambda: commits.append(1))
    with caplog.at_level("WARNING", logger="recourse.api"):
        v = _vision_post()["vision"]
    assert v["checked"] is True and v["cached"] is False
    assert any("vision cache" in r.getMessage() for r in caplog.records)
    import threading

    threading.Event().wait(0.3)  # time for a commit thread, had one been started
    assert commits == []  # nothing was written, so nothing is committed


def test_vision_cache_unencodable_answer_is_logged_not_raised(vision_route, page_cache, monkeypatch, caplog):
    vision_route["result"] = {"checked": True, "model": "muse-spark-1.3", "text_in_highlight": PDN_QUOTE, "agrees": True,
                              "latency_ms": 3100.0, "cost_usd": 0.005, "odd": {1, 2}}  # a set: json.dumps raises TypeError
    commits = []
    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", lambda: commits.append(1))
    with caplog.at_level("WARNING", logger="recourse.api"):
        v = _vision_post()["vision"]
    assert v["checked"] is True and v["cached"] is False
    assert any("vision cache" in r.getMessage() for r in caplog.records)
    assert not list((page_cache / "vision").glob("*"))  # neither the final file nor a tmp
    import threading

    threading.Event().wait(0.3)
    assert commits == []


def test_vision_cache_key_includes_the_model(vision_route, page_cache):
    vision_route["vp"].model = "model-a"
    _vision_post()
    vision_route["vp"].model = "model-b"
    assert _vision_post()["vision"]["cached"] is False and vision_route["n"] == 2
    assert len(list((page_cache / "vision").glob("*.json"))) == 2
    api_main.VISION_CACHE.clear()
    assert _vision_post()["vision"]["model"] == "model-b"
    vision_route["vp"].model = "model-a"
    v = _vision_post()["vision"]
    assert v["cached"] is True and v["model"] == "model-a" and vision_route["n"] == 2  # both were disk hits


def test_vision_cache_write_is_tmp_then_os_replace(vision_route, page_cache, monkeypatch):
    real, moves = os.replace, []

    def spy(src, dst):
        moves.append((Path(src), Path(dst)))
        return real(src, dst)

    monkeypatch.setattr(api_main.os, "replace", spy)
    _vision_post()
    final = api_main._vision_cache_path(VISION_KEY)
    assert len(moves) == 1
    src, dst = moves[0]
    assert src.name.endswith(".tmp") and src.parent == final.parent and dst == final and final.is_file()


def _store_by_hand(stored: dict) -> None:
    path = api_main._vision_cache_path(VISION_KEY)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stored), encoding="utf-8")


def test_vision_cache_a_stored_failure_is_not_served(vision_route):
    _store_by_hand({"key": list(VISION_KEY), "vision": {"checked": False, "model": "muse-spark-1.3", "error": "boom"}})
    v = _vision_post()["vision"]
    assert vision_route["n"] == 1 and v["cached"] is False and v["checked"] is True


def test_vision_cache_a_file_with_another_key_is_not_served(vision_route):
    other = list(VISION_KEY[:4]) + ["another-model"]
    _store_by_hand({"key": other, "vision": {"checked": True, "model": "another-model", "text_in_highlight": "x", "agrees": False,
                                             "latency_ms": 1.0, "cost_usd": 0.0}})
    v = _vision_post()["vision"]
    assert vision_route["n"] == 1 and v["cached"] is False and v["model"] == "muse-spark-1.3"


def test_vision_cache_a_disk_hit_goes_back_into_memory(vision_route):
    _vision_post()
    api_main.VISION_CACHE.clear()
    assert _vision_post()["vision"]["cached"] is True
    assert VISION_KEY in api_main.VISION_CACHE and "cached" not in api_main.VISION_CACHE[VISION_KEY]


def test_vision_cache_empty_env_means_memory_only(vision_route, page_cache, monkeypatch):
    monkeypatch.setenv("RECOURSE_VISION_CACHE", "")
    monkeypatch.setattr(api_main, "DATA", page_cache / "data")
    _vision_post()
    assert not (page_cache / "data" / "vision").exists() and not (page_cache / "vision").exists()
    api_main.VISION_CACHE.clear()
    assert _vision_post()["vision"]["cached"] is False and vision_route["n"] == 2


def test_vision_cache_defaults_to_data_vision(vision_route, page_cache, monkeypatch):
    monkeypatch.delenv("RECOURSE_VISION_CACHE", raising=False)
    monkeypatch.setattr(api_main, "DATA", page_cache / "data")
    _vision_post()
    assert len(list((page_cache / "data" / "vision").glob("*.json"))) == 1


def test_vision_cache_commit_hook_runs_once_per_disk_write_in_a_thread(vision_route, monkeypatch):
    import threading

    calls, done = [], threading.Event()

    def hook():
        calls.append((threading.get_ident(), threading.current_thread().name))
        done.set()

    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", hook)
    _vision_post()
    request_thread = vision_route["thread"]  # the worker thread that ran the first request (later posts may use another)
    assert done.wait(5)
    _vision_post()  # memory hit: no write
    api_main.VISION_CACHE.clear()
    _vision_post()  # disk hit: no write
    vision_route["result"] = {"checked": False, "model": "muse-spark-1.3", "error": "boom"}
    _vision_post(150)  # failure: no write
    threading.Event().wait(0.3)
    assert len(calls) == 1
    hook_thread, hook_thread_name = calls[0]
    assert request_thread is not None and hook_thread != request_thread  # not run inline on the request's thread
    assert hook_thread_name == "vision-cache-commit"


def test_vision_cache_commit_failure_is_logged_not_raised(caplog):
    def hook():
        raise RuntimeError("volume busy")

    with caplog.at_level("WARNING", logger="recourse.api"):
        api_main._commit_vision_cache(hook)  # the thread's target
    assert any("volume busy" in r.getMessage() for r in caplog.records)


def test_modal_sets_the_vision_cache_and_wires_a_guarded_commit(monkeypatch, caplog):
    from unittest import mock

    import deploy.modal_app as modal_app

    assert modal_app.RUNTIME_ENV["RECOURSE_VISION_CACHE"] == "/root/data/vision"
    vol = mock.MagicMock(name="volume")
    monkeypatch.setattr(modal_app, "data_volume", vol, raising=False)
    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", None)
    monkeypatch.setenv("RECOURSE_WARM_RETRIEVER", "0")
    assert modal_app.build_asgi() is api_main.app
    hook = api_main.VISION_CACHE_COMMIT
    assert callable(hook)
    hook()
    vol.commit.assert_called_once_with()
    vol.commit.side_effect = RuntimeError("commit refused")
    with caplog.at_level("WARNING"):
        hook()  # guarded: logged, never raised
    assert any("commit refused" in r.getMessage() for r in caplog.records)


def test_modal_without_a_volume_wires_no_commit(monkeypatch):
    import deploy.modal_app as modal_app

    monkeypatch.delattr(modal_app, "data_volume", raising=False)  # as when the modal package is not installed
    monkeypatch.setattr(api_main, "VISION_CACHE_COMMIT", None)
    monkeypatch.setenv("RECOURSE_WARM_RETRIEVER", "0")
    modal_app.build_asgi()
    assert api_main.VISION_CACHE_COMMIT is None


def test_health_counts_pdfs(page_cache):
    from policyqa.pages import pdf_count

    n = client.get("/health").json()["pdfs"]
    assert isinstance(n, int) and n == pdf_count()


def test_the_stored_route_is_computed_with_the_intake_summary(monkeypatch, tmp_path):
    """Oct 27: routing reads the intake summary (a QMB member on a Medicare letter routes both ways), so the
    route the API stores before the investigation must see the same summary the investigation sees."""
    from policyqa.investigate import FixtureInvestigator

    monkeypatch.setattr(api_main, "DATA", tmp_path)
    seen = []

    class Recording(FixtureInvestigator):
        def route(self, card, summary=None):
            seen.append(summary)
            return super().route(card, summary)

    monkeypatch.setattr(api_main, "investigator", lambda: Recording(delay=0))
    body = _intake_text().json()
    cid = body["case_id"]
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    stored = client.get(f"/case/{cid}").json()
    assert seen and seen[0] == stored["summary"] and seen[0]


# ---- second opinion (the verdict again on Muse Spark Open) -------------------------------

SECOND_KEYS = {"status", "reason", "model", "outcome", "proposed_outcome", "decisive_fact", "relies_on_exception", "agrees",
               "input_tokens", "output_tokens", "reasoning_tokens", "latency_ms", "cost_usd", "error"}
SECOND_NAMES = ("POLICYQA_SECOND_LLM_BASE_URL", "POLICYQA_SECOND_LLM_MODEL", "POLICYQA_SECOND_LLM_API_KEY")


def _live_verdicts(monkeypatch, second_reply=None, second_status=200, second_delay=0.0, primary_agent=None):
    """The primary verdict and the second opinion on real Providers over one fake transport; the letter and critic stay fixtures.
    `second_delay` makes the second endpoint answer late; `primary_agent` replaces the primary verdict agent."""
    import time

    import httpx

    from policyqa.generate import Provider
    from policyqa.verdict import FixtureVerdict, LiveVerdict

    sent = {"primary": [], "second": []}
    holder = {}

    def handler(request):
        who = "second" if request.url.host == "inference.baseten.co" else "primary"
        sent[who].append(json.loads(request.content))
        if who == "second" and second_delay:
            time.sleep(second_delay)
        if who == "second" and second_status != 200:
            return httpx.Response(second_status, json={"error": "upstream"})
        reply = FixtureVerdict(delay=0).reply(STORE.get(holder["cid"])["investigation"])
        if who == "second" and second_reply:
            reply.update(second_reply)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2000, "completion_tokens": 900}})

    transport = httpx.MockTransport(handler)
    primary = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=transport)
    second = Provider(base_url="https://inference.baseten.co/v1", api_key="k2", model="meta-models/muse-spark-open-1026", transport=transport)
    monkeypatch.setattr(api_main, "verdicter", lambda: primary_agent or LiveVerdict(primary))
    monkeypatch.setattr(api_main, "second_provider", lambda: second)
    cid = _intake_text().json()["case_id"]
    holder["cid"] = cid
    assert client.post(f"/case/{cid}/investigate").status_code == 202
    return cid, sent


def test_new_case_has_a_null_second_opinion():
    assert _intake_text().json()["second_opinion"] is None


def test_second_opinion_is_skipped_when_unset_and_nothing_calls_the_network(monkeypatch, tmp_path):
    import httpx

    for k in SECOND_NAMES:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    def no_network(*a, **kw):
        raise AssertionError("the network was called")

    monkeypatch.setattr(httpx.Client, "__init__", no_network)
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed"
    so = b["second_opinion"]
    assert set(so) == SECOND_KEYS and so["status"] == "skipped" and "not configured" in so["reason"]
    assert so["agrees"] is None and so["model"] is None
    assert "second_opinion" not in [sp["name"] for sp in b["investigation"]["trace"]["spans"]]


def test_second_opinion_runs_with_the_primarys_message_and_the_get_returns_it(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    cid, sent = _live_verdicts(monkeypatch)
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["verdict"]["outcome"] == "inconsistent"
    (a,), (s,) = sent["primary"], sent["second"]
    assert a["model"] == "muse-spark-1.3" and s["model"] == "meta-models/muse-spark-open-1026"
    assert a["messages"] == s["messages"]
    so = b["second_opinion"]
    assert set(so) == SECOND_KEYS and so["status"] == "done" and so["outcome"] == "inconsistent" and so["agrees"] is True
    assert so["model"] == "meta-models/muse-spark-open-1026" and so["input_tokens"] == 2000
    assert "second_opinion" in [sp["name"] for sp in b["investigation"]["trace"]["spans"]]
    assert b["letter"]["status"] == "done" and b["critique"]["status"] == "done"


def test_a_disagreeing_second_opinion_never_changes_the_verdict_or_the_letter(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    cid, _ = _live_verdicts(monkeypatch, second_reply={"outcome": "consistent", "what_would_change": "An authorization for the extra hours."})
    b = client.get(f"/case/{cid}").json()
    assert b["second_opinion"]["outcome"] == "consistent" and b["second_opinion"]["agrees"] is False
    assert b["verdict"]["outcome"] == "inconsistent" and b["letter"]["applicable"] is True and b["status"] == "reviewed"


def test_a_500_from_the_second_endpoint_leaves_the_primary_and_the_case_alone(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    cid, sent = _live_verdicts(monkeypatch, second_status=500)
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["verdict"]["status"] == "done" and b["verdict"]["error"] is None
    assert b["verdict"]["outcome"] == "inconsistent" and b["verdict"]["model"] == "muse-spark-1.3"
    so = b["second_opinion"]
    assert so["status"] == "failed" and "500" in so["error"] and so["agrees"] is None and so["outcome"] is None
    assert len(sent["second"]) == 1


def test_an_exception_in_the_second_opinion_never_fails_the_case(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    def boom():
        raise RuntimeError("second provider exploded")

    monkeypatch.setattr(api_main, "second_provider", boom)
    cid = _intake_text().json()["case_id"]
    client.post(f"/case/{cid}/investigate")
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "reviewed" and b["second_opinion"]["status"] == "failed" and "exploded" in b["second_opinion"]["error"]


def test_set_stage_accepts_the_second_opinion():
    from api.cases import CaseStore

    s = CaseStore(None)
    cid = s.create({"card": {}})["case_id"]
    s.set_stage(cid, "second_opinion", {"status": "skipped"})
    assert s.get(cid)["second_opinion"] == {"status": "skipped"} and s.get(cid)["status"] == "intake"


class _Breaks:
    """A letter or critic agent that raises."""

    model = "boom"

    def draft(self, case, investigation, verdict):
        raise RuntimeError("letter exploded")

    def review(self, case, investigation, verdict, letter):
        raise RuntimeError("critic exploded")


@pytest.mark.parametrize("breaks, final_status", [(None, "reviewed"), ("letterer", "failed"), ("critic", "reviewed")])
def test_the_inline_post_returns_only_after_a_slow_second_opinion_lands(monkeypatch, tmp_path, breaks, final_status):
    """The inline POST (tests, the CLI) waits for the second opinion; a letter or critic failure does not skip the wait."""
    monkeypatch.setattr(api_main, "DATA", tmp_path)
    if breaks:
        monkeypatch.setattr(api_main, breaks, lambda: _Breaks())
    cid, sent = _live_verdicts(monkeypatch, second_delay=0.3)
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == final_status
    assert b["second_opinion"]["status"] == "done" and b["second_opinion"]["agrees"] is True and len(sent["second"]) == 1


def test_a_failed_primary_verdict_stores_a_skipped_second_opinion_and_never_calls_the_second_model(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DATA", tmp_path)

    class Boom:
        model = "muse-spark-1.3"

        def decide(self, case, investigation):
            raise RuntimeError("verdict exploded")

    cid, sent = _live_verdicts(monkeypatch, primary_agent=Boom())
    b = client.get(f"/case/{cid}").json()
    assert b["status"] == "failed" and b["verdict"]["status"] == "failed"
    so = b["second_opinion"]
    assert so["status"] == "skipped" and "did not finish" in so["reason"] and so["model"] == "meta-models/muse-spark-open-1026"
    assert sent["second"] == []

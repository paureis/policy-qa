"""Case intake: card normalization, scope heuristic, Muse Spark extractor parts, PDF fallback, retry ladder."""
import json

import httpx
import pytest

from policyqa import intake
from policyqa.generate import Provider
from policyqa.intake import (
    CARD_FIELDS,
    CARD_SCHEMA,
    Extraction,
    FixtureExtractor,
    IntakeError,
    MuseSparkExtractor,
    normalize_card,
    scope_check,
)

GOOD_CARD = {
    "payer_name": {"value": "Sunshine Health", "confidence": "high"},
    "program": {"value": "florida_medicaid_mma", "confidence": "high"},
    "member_age_group": {"value": "under_21", "confidence": "medium"},
    "service": {"value": "private duty nursing, 8 hours/day", "confidence": "high"},
    "service_code": {"value": "T1000", "confidence": "low"},
    "dates_of_service": {"value": "2026-09-01/2026-09-30", "confidence": "high"},
    "amount_billed": {"value": 4320.0, "confidence": "medium"},
    "denial_reason": {"value": "Services exceed the authorized amount.", "confidence": "high"},
    "letter_date": {"value": "2026-10-14", "confidence": "high"},
    "appeal_deadline_claimed": {"value": "2026-12-13", "confidence": "medium"},
}

LETTER = (
    "Sunshine Health. Notice of Adverse Benefit Determination. Dated October 14, 2026. "
    "Member: J. Doe, age 9. We have denied the request for private duty nursing, 8 hours per day, "
    "for dates of service September 1 through September 30, 2026, billed at $4,320.00. "
    "Reason: Services exceed the authorized amount. You have the right to appeal within 60 days, by December 13, 2026."
)


# ---- normalize_card -------------------------------------------------------


def test_normalize_card_keeps_good_values_and_field_order():
    card = normalize_card(GOOD_CARD)
    assert list(card.keys()) == list(CARD_FIELDS)
    assert card == GOOD_CARD


def test_normalize_card_unknown_enum_becomes_unknown_low():
    card = normalize_card({**GOOD_CARD, "program": {"value": "blue_cross_ppo", "confidence": "high"}, "member_age_group": {"value": "teen", "confidence": "high"}})
    assert card["program"] == {"value": "unknown", "confidence": "low"}
    assert card["member_age_group"] == {"value": "unknown", "confidence": "low"}


def test_normalize_card_missing_fields_are_none_low():
    card = normalize_card({"payer_name": {"value": "X", "confidence": "high"}})
    assert card["service"] == {"value": None, "confidence": "low"}
    assert card["amount_billed"] == {"value": None, "confidence": "low"}
    # enums have an explicit unknown member; a missing enum is that member
    assert card["program"] == {"value": "unknown", "confidence": "low"}


def test_normalize_card_bad_dates_and_confidence():
    card = normalize_card({**GOOD_CARD, "letter_date": {"value": "10/14/2026", "confidence": "high"}, "dates_of_service": {"value": "Sept 2026", "confidence": "high"}, "appeal_deadline_claimed": {"value": "2026-13-45", "confidence": "high"}, "payer_name": {"value": "Sunshine Health", "confidence": "certain"}})
    assert card["letter_date"] == {"value": None, "confidence": "low"}
    assert card["dates_of_service"] == {"value": None, "confidence": "low"}
    assert card["appeal_deadline_claimed"] == {"value": None, "confidence": "low"}
    assert card["payer_name"] == {"value": "Sunshine Health", "confidence": "low"}


def test_normalize_card_amount_rules():
    assert normalize_card({"amount_billed": {"value": "$4,320.00", "confidence": "high"}})["amount_billed"] == {"value": 4320.0, "confidence": "high"}
    assert normalize_card({"amount_billed": {"value": 123456.0, "confidence": "high"}})["amount_billed"] == {"value": None, "confidence": "low"}
    assert normalize_card({"amount_billed": {"value": "lots", "confidence": "high"}})["amount_billed"] == {"value": None, "confidence": "low"}
    assert normalize_card({"amount_billed": {"value": -5, "confidence": "high"}})["amount_billed"] == {"value": None, "confidence": "low"}


def test_normalize_card_trims_service_and_denial_reason():
    card = normalize_card({"service": {"value": "x" * 200, "confidence": "high"}, "denial_reason": {"value": "One. Two. Three. Four. Five.", "confidence": "high"}})
    assert len(card["service"]["value"]) == 80
    assert card["denial_reason"]["value"] == "One. Two. Three."


def test_normalize_card_accepts_plain_values():
    card = normalize_card({"payer_name": "Sunshine Health", "program": "medicare_b"})
    assert card["payer_name"] == {"value": "Sunshine Health", "confidence": "low"}
    assert card["program"] == {"value": "medicare_b", "confidence": "low"}


# ---- scope_check ----------------------------------------------------------


def test_scope_check():
    assert scope_check(LETTER) is None
    assert scope_check("My claim was denied. Should I take ibuprofen for the pain and what dosage?") == "out_of_scope"
    assert scope_check("Dear friend, thanks for the birthday wishes. " * 10) == "not_a_denial_letter"
    assert scope_check("Explanation of Benefits: this service is not covered under your plan.") is None
    # Real notices name a diagnosis and sometimes a dose; that is not a treatment question.
    assert scope_check(LETTER + " Diagnosis code: Z00.00. Requested dose: 10 mg daily. Side effects noted by the provider.") is None
    assert scope_check("What dose of metformin should I take? " * 8) == "out_of_scope"


# ---- schema ---------------------------------------------------------------


def test_card_schema_is_strict_and_complete():
    assert CARD_SCHEMA["additionalProperties"] is False
    assert set(CARD_SCHEMA["required"]) == {"is_denial_letter", "is_out_of_scope", "raw_text", "summary", "card"}
    card = CARD_SCHEMA["properties"]["card"]
    assert list(card["properties"].keys()) == list(CARD_FIELDS) and card["required"] == list(CARD_FIELDS)


# ---- extractor with a recording fake provider ------------------------------


class RecordingProvider:
    model = "muse-spark-1.3"

    def __init__(self, reply=None, reject_file=False):
        self.calls = []
        self.reject_file = reject_file
        self.reply = reply or {"is_denial_letter": True, "is_out_of_scope": False, "raw_text": LETTER, "summary": "A plain summary.", "card": GOOD_CARD}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500):
        self.calls.append({"system": system, "parts": parts, "schema": schema})
        if self.reject_file and any(p.get("type") == "file" for p in parts):
            req = httpx.Request("POST", "https://api.meta.ai/v1/chat/completions")
            resp = httpx.Response(400, request=req, text='{"error": "file input is not supported for this model"}')
            raise httpx.HTTPStatusError("400", request=req, response=resp)
        return json.dumps(self.reply), 100, 50

    def cost(self, n_in, n_out):
        return round(n_in * 1e-6 + n_out * 2e-6, 6)


def test_text_extraction_sends_one_text_part_and_returns_extraction():
    p = RecordingProvider()
    ex = MuseSparkExtractor(p).extract("text", text=LETTER)
    assert isinstance(ex, Extraction)
    parts = p.calls[0]["parts"]
    assert len(parts) == 1 and parts[0]["type"] == "text" and LETTER in parts[0]["text"]
    assert p.calls[0]["schema"] is CARD_SCHEMA
    assert ex.source == "text" and ex.raw_text == LETTER and ex.card == GOOD_CARD
    assert ex.summary == "A plain summary." and ex.model == "muse-spark-1.3"
    assert ex.input_tokens == 100 and ex.output_tokens == 50 and ex.cost_usd == 0.0002 and ex.latency_ms >= 0


def test_image_extraction_sends_data_url_and_instruction():
    p = RecordingProvider()
    ex = MuseSparkExtractor(p).extract("image", data=b"\x89PNG\r\n\x1a\nfake", mime="image/png")
    parts = p.calls[0]["parts"]
    types = [q["type"] for q in parts]
    assert "image_url" in types and "text" in types
    img = next(q for q in parts if q["type"] == "image_url")
    assert img["image_url"]["url"].startswith("data:image/png;base64,")
    assert ex.source == "image" and ex.raw_text == LETTER  # model transcription


def test_pdf_extraction_sends_file_part():
    p = RecordingProvider()
    MuseSparkExtractor(p).extract("pdf", data=b"%PDF-1.4 fake", filename="letter.pdf")
    parts = p.calls[0]["parts"]
    f = next(q for q in parts if q["type"] == "file")
    assert f["file"]["filename"] == "letter.pdf" and f["file"]["file_data"].startswith("data:application/pdf;base64,")
    assert any(q["type"] == "text" for q in parts)


def test_pdf_fallback_to_pdftotext_when_file_part_rejected(monkeypatch):
    monkeypatch.setattr(intake, "pdf_to_text", lambda data: LETTER)
    p = RecordingProvider(reject_file=True)
    ex = MuseSparkExtractor(p).extract("pdf", data=b"%PDF-1.4 fake", filename="letter.pdf")
    assert len(p.calls) == 2
    assert all(q["type"] == "text" for q in p.calls[1]["parts"]) and LETTER in p.calls[1]["parts"][0]["text"]
    assert ex.source == "pdf" and ex.raw_text == LETTER


def test_pdf_fallback_without_pdftotext_is_unreadable(monkeypatch):
    monkeypatch.setattr(intake, "pdf_to_text", lambda data: None)
    p = RecordingProvider(reject_file=True)
    with pytest.raises(IntakeError) as ei:
        MuseSparkExtractor(p).extract("pdf", data=b"%PDF-1.4 fake", filename="letter.pdf")
    assert ei.value.code == "unreadable"


def test_pdf_fallback_with_too_little_text_is_unreadable(monkeypatch):
    monkeypatch.setattr(intake, "pdf_to_text", lambda data: "   ")
    p = RecordingProvider(reject_file=True)
    with pytest.raises(IntakeError) as ei:
        MuseSparkExtractor(p).extract("pdf", data=b"%PDF-1.4 fake", filename="letter.pdf")
    assert ei.value.code == "unreadable"


@pytest.mark.skipif(intake.shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_real_pdftotext_reads_a_generated_pdf():
    from tests.test_api import MINI_PDF_WITH_TEXT

    text = intake.pdf_to_text(MINI_PDF_WITH_TEXT)
    assert text and "Sunshine Health" in text


def test_model_classification_codes_raise_intake_errors():
    for key, code in (("is_out_of_scope", "out_of_scope"), ("is_denial_letter", "not_a_denial_letter")):
        reply = {"is_denial_letter": True, "is_out_of_scope": False, "raw_text": LETTER, "summary": "s", "card": GOOD_CARD}
        reply[key] = key == "is_out_of_scope"
        with pytest.raises(IntakeError) as ei:
            MuseSparkExtractor(RecordingProvider(reply=reply)).extract("text", text=LETTER)
        assert ei.value.code == code


def test_unparseable_model_reply_is_unreadable():
    class Garbage(RecordingProvider):
        def complete_parts(self, system, parts, schema=None, max_tokens=1500):
            return "I cannot help with that.", 1, 1

    with pytest.raises(IntakeError) as ei:
        MuseSparkExtractor(Garbage()).extract("text", text=LETTER)
    assert ei.value.code == "unreadable"


# ---- fixture extractor ----------------------------------------------------


def test_fixture_extractor_matches_contract_sample():
    ex = FixtureExtractor().extract("text", text=LETTER)
    assert ex.card == GOOD_CARD and ex.raw_text == LETTER and ex.model == "fixture" and ex.cost_usd == 0.0
    assert "Sunshine Health" in ex.summary and len(ex.summary) > 100
    ex2 = FixtureExtractor().extract("image", data=b"\x89PNG", mime="image/png")
    assert "Sunshine Health" in ex2.raw_text and "synthetic" in ex2.raw_text.lower() and 200 <= len(ex2.raw_text) <= 6000


# ---- Provider.complete_parts retry ladder over httpx MockTransport ---------


def _ladder_transport(fail_until: int, seen: list):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        rf = body.get("response_format")
        seen.append(rf["type"] if rf else None)
        assert request.headers["authorization"] == "Bearer k"
        assert request.url.path.endswith("/chat/completions")
        if len(seen) <= fail_until:
            return httpx.Response(400, json={"error": {"message": "response_format is not supported"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}})

    return httpx.MockTransport(handler)


def _provider(transport):
    return Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=transport)


def test_complete_parts_json_schema_first_then_json_object_then_none():
    seen = []
    text, n_in, n_out = _provider(_ladder_transport(2, seen)).complete_parts("sys", [{"type": "text", "text": "hi"}], schema=CARD_SCHEMA)
    assert seen == ["json_schema", "json_object", None]
    assert text == '{"ok": true}' and (n_in, n_out) == (7, 3)


def test_complete_parts_stops_at_first_success_and_sends_strict_schema():
    seen = []
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        seen.append(bodies[-1]["response_format"]["type"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "usage": {}})

    _provider(httpx.MockTransport(handler)).complete_parts("sys", [{"type": "text", "text": "hi"}], schema=CARD_SCHEMA, max_tokens=99)
    assert seen == ["json_schema"]
    b = bodies[0]
    assert b["model"] == "muse-spark-1.3" and b["max_tokens"] == 99 and b["temperature"] == 0
    assert b["response_format"]["json_schema"] == {"name": "case_card", "schema": CARD_SCHEMA, "strict": True}
    assert b["messages"][0] == {"role": "system", "content": "sys"} and b["messages"][1]["content"] == [{"type": "text", "text": "hi"}]


def test_complete_parts_without_schema_sends_no_response_format():
    seen = []
    _provider(_ladder_transport(0, seen)).complete_parts("sys", [{"type": "text", "text": "hi"}])
    assert seen == [None]


def test_complete_parts_raises_on_non_format_400():
    def handler(request):
        return httpx.Response(400, json={"error": "file input is not supported"})

    with pytest.raises(httpx.HTTPStatusError) as ei:
        _provider(httpx.MockTransport(handler)).complete_parts("sys", [{"type": "file", "file": {}}], schema=CARD_SCHEMA)
    assert ei.value.response.status_code == 400


def test_reversed_date_range_is_rejected():
    from policyqa.intake import coerce_field

    assert coerce_field("dates_of_service", "2026-09-30/2026-09-01") == (None, False)
    assert coerce_field("dates_of_service", "2026-09-01/2026-09-30") == ("2026-09-01/2026-09-30", True)
    assert coerce_field("dates_of_service", "2026-09-01/2026-09-01") == ("2026-09-01/2026-09-01", True)

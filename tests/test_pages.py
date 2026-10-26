"""Highlighted page images: locating a quote on a PDF page, rendering the page, and the vision check."""
import base64
import json
from pathlib import Path

import httpx
import pytest

from policyqa import pages
from policyqa.generate import Provider
from policyqa.pages import FixtureVision, PageError, highlight, locate_quote, page_words, pdf_path, render_page, vision_check

ROOT = Path(__file__).resolve().parent.parent
FL04 = ROOT / "data" / "pdfs" / "fl-04.pdf"
PDN_QUOTE = "Florida Medicaid covers up to 24 hours of PDN services per day, per recipient"
needs_fl04 = pytest.mark.skipif(not (FL04.exists() and FL04.stat().st_size > 10_000), reason="data/pdfs/fl-04.pdf is not fetched on this machine")


def _line(text: str, y: float, x: float = 72.0, h: float = 11.0) -> list[dict]:
    """Words laid out left to right on one line, 6 points per character plus a 3 point gap."""
    out = []
    for w in text.split():
        x1 = x + 6 * len(w)
        out.append({"text": w, "x0": x, "y0": y, "x1": x1, "y1": y + h})
        x = x1 + 3
    return out


@pytest.fixture(autouse=True)
def _page_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RECOURSE_PAGE_CACHE", str(tmp_path / "pages"))
    monkeypatch.delenv("RECOURSE_PDF_DIR", raising=False)
    yield


# ---- locate_quote on hand-built word lists --------------------------------


def test_exact_run_is_found_with_score_one_and_one_box():
    words = _line("Header text here.", 50) + _line("Florida Medicaid covers up to 24 hours per day.", 100) + _line("Other words follow.", 120)
    r = locate_quote(words, "covers up to 24 hours")
    assert r["score"] == 1.0 and r["matched"] == "covers up to 24 hours"
    assert len(r["boxes"]) == 1
    b = r["boxes"][0]
    covers = words[5]
    hours = words[9]
    assert covers["text"] == "covers" and hours["text"] == "hours"
    assert (b["x0"], b["y0"], b["x1"], b["y1"]) == (covers["x0"], covers["y0"], hours["x1"], hours["y1"])


def test_punctuation_and_case_at_word_edges_are_ignored():
    words = _line("(Services) must be “medically necessary,” as defined.", 100)
    r = locate_quote(words, 'services must be "Medically Necessary" as defined')
    assert r["score"] == 1.0


def test_hyphenated_line_break_is_joined():
    words = _line("the recipient requires con-", 100) + _line("tinual care at home", 112)
    r = locate_quote(words, "the recipient requires continual care at home")
    assert r["score"] == 1.0
    assert len(r["boxes"]) == 2  # one box per line
    assert r["boxes"][0]["y0"] == 100 and r["boxes"][1]["y0"] == 112


def test_hyphenated_quote_from_layout_text_matches_joined_page_words():
    words = _line("the recipient requires con-", 100) + _line("tinual care at home", 112)
    assert locate_quote(words, "requires con- tinual care at home")["score"] == 1.0


def test_one_missing_word_within_tolerance_is_found():
    quote = "Florida Medicaid covers up to 24 hours of PDN services per day"  # 12 words
    words = _line("Florida Medicaid covers up to 24 hours of services per day", 100)  # "PDN" missing on the page
    r = locate_quote(words, quote)
    assert r["score"] == pytest.approx(11 / 12, abs=0.001) and r["score"] >= 0.8
    assert len(r["boxes"]) == 1


def test_one_extra_word_on_the_page_is_tolerated():
    words = _line("Florida Medicaid covers only up to 24 hours of PDN services per day", 100)
    r = locate_quote(words, "Florida Medicaid covers up to 24 hours of PDN services per day")
    assert r["score"] == 1.0


def test_below_threshold_is_not_found():
    words = _line("Florida Medicaid covers up to 24 hours of PDN services per day", 100)
    r = locate_quote(words, "Medicare pays for durable medical equipment in the home per day")
    assert r["score"] < 0.8


def test_empty_quote_or_page_scores_zero():
    assert locate_quote([], "anything at all here")["score"] == 0.0
    assert locate_quote(_line("some words", 10), "")["score"] == 0.0
    assert locate_quote([], "anything at all here")["boxes"] == []


def test_line_merging_one_box_per_line_and_small_y_jitter_still_merges():
    words = _line("alpha beta gamma", 100) + _line("delta epsilon", 112)
    words[1]["y0"] = 101.5  # same line within 2 points
    r = locate_quote(words, "alpha beta gamma delta epsilon")
    assert r["score"] == 1.0 and len(r["boxes"]) == 2
    first = r["boxes"][0]
    assert first["x0"] == words[0]["x0"] and first["x1"] == words[2]["x1"] and first["y0"] == 100
    second = r["boxes"][1]
    assert second["x0"] == words[3]["x0"] and second["x1"] == words[4]["x1"]


def test_table_row_read_column_by_column_is_found_in_row_order():
    # pdftotext -bbox emits a table column by column; the quote is one row read across.
    codes = [{"text": c, "x0": 72.0, "y0": y, "x1": 110.0, "y1": y + 10} for c, y in (("K0822", 200.0), ("K0823", 212.0), ("K0824", 224.0))]
    ranges = [{"text": t, "x0": x, "y0": y, "x1": x + 8, "y1": y + 10} for y in (200.0, 212.0, 224.0) for t, x in (("0", 130.0), ("-", 140.0), ("999", 150.0))]
    limits = [{"text": t, "x0": x, "y0": 212.0, "x1": x + 20, "y1": 222.0} for t, x in (("1", 200.0), ("PER", 230.0), ("5", 260.0), ("YEARS", 290.0))]
    r = locate_quote(codes + ranges + limits, "K0823 0 - 999 1 PER 5 YEARS")
    assert r["score"] == 1.0 and r["matched"] == "K0823 0 - 999 1 PER 5 YEARS"
    assert r["boxes"] == [{"x0": 72.0, "y0": 212.0, "x1": 310.0, "y1": 222.0}]


def test_best_run_wins_over_an_earlier_partial_run():
    words = _line("covers up to 8 visits", 50) + _line("covers up to 24 hours of PDN", 100)
    r = locate_quote(words, "covers up to 24 hours of PDN")
    assert r["score"] == 1.0 and r["boxes"][0]["y0"] == 100


# ---- the real PDF -----------------------------------------------------------


def test_pdf_path_unknown_doc_is_not_found():
    with pytest.raises(PageError) as ei:
        pdf_path("zz-99")
    assert ei.value.code == "not_found"


def test_pdf_path_missing_file_is_no_pdf(monkeypatch, tmp_path):
    monkeypatch.setenv("RECOURSE_PDF_DIR", str(tmp_path))
    with pytest.raises(PageError) as ei:
        pdf_path("fl-04")
    assert ei.value.code == "no_pdf" and "not fetched on this machine" in ei.value.message


@needs_fl04
def test_render_page_writes_a_cached_png(monkeypatch, tmp_path):
    png = render_page("fl-04", 5)
    assert png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) > 50_000
    cached = tmp_path / "pages" / "fl-04" / "p005-110.png"
    assert cached.exists() and cached.read_bytes() == png
    w, h = pages.png_size(png)
    assert (w, h) == (935, 1210)  # 612 x 792 points at 110 dpi
    # second call is served from the cache, not pdftoppm
    monkeypatch.setattr(pages.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("pdftoppm ran again")))
    assert render_page("fl-04", 5) == png


@needs_fl04
def test_render_page_out_of_range_is_bad_page():
    for p in (0, 11, 999):
        with pytest.raises(PageError) as ei:
            render_page("fl-04", p)
        assert ei.value.code == "bad_page"


@needs_fl04
def test_page_words_and_the_pdn_quote():
    pw = page_words("fl-04", 5)
    assert (pw["width"], pw["height"]) == (612.0, 792.0)
    assert len(pw["words"]) > 100 and {"text", "x0", "y0", "x1", "y1"} <= set(pw["words"][0])
    r = locate_quote(pw["words"], PDN_QUOTE)
    assert r["score"] == 1.0
    assert r["matched"].startswith("Florida Medicaid covers up to 24 hours")
    assert 1 <= len(r["boxes"]) <= 2
    for b in r["boxes"]:
        assert 0 <= b["x0"] < b["x1"] <= pw["width"] and 0 <= b["y0"] < b["y1"] <= pw["height"]


@needs_fl04
def test_highlight_scales_boxes_to_pixels():
    h = highlight("fl-04", 5, PDN_QUOTE)
    assert h["doc_id"] == "fl-04" and h["page"] == 5 and h["dpi"] == 110 and h["found"] is True and h["score"] == 1.0
    assert h["title"].startswith("Florida Medicaid Private Duty Nursing")
    assert (h["width_px"], h["height_px"]) == (935, 1210)
    assert h["image_url"] == "/doc/fl-04/page/5.png?dpi=110"
    pts = locate_quote(page_words("fl-04", 5)["words"], PDN_QUOTE)["boxes"][0]
    px = h["boxes_px"][0]
    assert px["x0"] == pytest.approx(pts["x0"] * 110 / 72, abs=0.6) and px["y1"] == pytest.approx(pts["y1"] * 110 / 72, abs=0.6)
    for b in h["boxes_px"]:
        assert 0 <= b["x0"] < b["x1"] <= 935 and 0 <= b["y0"] < b["y1"] <= 1210


@needs_fl04
def test_highlight_not_found_quote():
    h = highlight("fl-04", 5, "Medicare Part B pays for durable medical equipment rentals")
    assert h["found"] is False and h["score"] < 0.8


# ---- vision check ------------------------------------------------------------


class RecordingProvider:
    model = "muse-spark-1.3"

    def __init__(self, reply: dict | str):
        self.reply = reply if isinstance(reply, str) else json.dumps(reply)
        self.calls = []
        self.last_response = {"usage": {"completion_tokens_details": {"reasoning_tokens": 40}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500, **kw):
        self.calls.append({"system": system, "parts": parts, "schema": schema, "max_tokens": max_tokens, **kw})
        return self.reply, 1200, 60

    def cost(self, n_in, n_out):
        return 0.0123


@needs_fl04
def test_vision_check_sends_the_page_image_and_the_rectangles():
    fake = RecordingProvider({"text_in_highlight": PDN_QUOTE + ", in accordance", "contains_quote": True})
    v = vision_check("fl-04", 5, PDN_QUOTE, fake)
    assert v["checked"] is True and v["agrees"] is True and v["model"] == "muse-spark-1.3"
    assert v["input_tokens"] == 1200 and v["output_tokens"] == 60 and v["reasoning_tokens"] == 40 and v["cost_usd"] == 0.0123
    assert v["latency_ms"] >= 0 and v["text_in_highlight"].startswith("Florida Medicaid")
    call = fake.calls[0]
    assert call["max_tokens"] == 6000
    assert call["schema"]["required"] == ["text_in_highlight", "contains_quote"] and call["schema"]["additionalProperties"] is False
    images = [p for p in call["parts"] if p["type"] == "image_url"]
    texts = [p for p in call["parts"] if p["type"] == "text"]
    assert len(images) == 1 and len(texts) == 1
    url = images[0]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == render_page("fl-04", 5)
    t = texts[0]["text"]
    h = highlight("fl-04", 5, PDN_QUOTE)
    assert "935 x 1210" in t and PDN_QUOTE in t
    b = h["boxes_px"][0]
    assert f"x0={b['x0']:g}, y0={b['y0']:g}, x1={b['x1']:g}, y1={b['y1']:g}" in t


@needs_fl04
def test_vision_check_disagrees_when_the_text_does_not_match():
    fake = RecordingProvider({"text_in_highlight": "Requires services that can be safely provided", "contains_quote": False})
    v = vision_check("fl-04", 5, PDN_QUOTE, fake)
    assert v["checked"] is True and v["agrees"] is False


@needs_fl04
def test_vision_check_agrees_on_overlap_even_if_the_flag_is_false():
    fake = RecordingProvider({"text_in_highlight": PDN_QUOTE, "contains_quote": False})
    assert vision_check("fl-04", 5, PDN_QUOTE, fake)["agrees"] is True


@needs_fl04
def test_vision_check_reports_provider_errors_without_raising():
    class Broken(RecordingProvider):
        def complete_parts(self, *a, **k):
            raise httpx.ConnectError("no route to host")

    v = vision_check("fl-04", 5, PDN_QUOTE, Broken({}))
    assert v["checked"] is False and "no route to host" in v["error"]
    v = vision_check("fl-04", 5, PDN_QUOTE, RecordingProvider("not json at all"))
    assert v["checked"] is False and v["error"]


@needs_fl04
def test_vision_check_over_http_with_a_fake_transport():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        content = json.dumps({"text_in_highlight": PDN_QUOTE, "contains_quote": True})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 900, "completion_tokens": 80, "completion_tokens_details": {"reasoning_tokens": 55}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    v = vision_check("fl-04", 5, PDN_QUOTE, p)
    assert v["checked"] is True and v["agrees"] is True and v["reasoning_tokens"] == 55
    rf = bodies[0]["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["name"] == "highlight_check" and rf["json_schema"]["strict"] is True


@needs_fl04
def test_vision_check_truncated_reply_is_an_error():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"completion_tokens": 6000}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    v = vision_check("fl-04", 5, PDN_QUOTE, p)
    assert v["checked"] is False and "token budget" in v["error"]


@needs_fl04
def test_fixture_vision_agrees_with_the_quote():
    v = vision_check("fl-04", 5, PDN_QUOTE, FixtureVision())
    assert v == {"checked": True, "model": "fixture", "text_in_highlight": PDN_QUOTE, "agrees": True, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "latency_ms": v["latency_ms"], "cost_usd": 0.0}


def test_vision_check_without_a_highlight_is_not_checked(monkeypatch):
    monkeypatch.setattr(pages, "highlight", lambda *a, **k: {"found": False, "boxes_px": [], "score": 0.1})
    fake = RecordingProvider({"text_in_highlight": "", "contains_quote": False})
    v = vision_check("fl-04", 5, PDN_QUOTE, fake)
    assert v["checked"] is False and "not located" in v["error"] and fake.calls == []

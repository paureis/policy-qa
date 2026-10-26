"""Case intake: a coverage denial letter (text, image, or PDF) becomes a case card.

The card is the ten-field contract in web/README.md ("Case card contract"). Each
field carries a value and a confidence (high, medium, low); the screen flags
medium and low for review before the investigation starts.

Two extractors share one interface, `extract(source, text=, data=, mime=, filename=)`:

- MuseSparkExtractor: Muse Spark 1.3 on the Meta Model API reads the letter
  (text part, image data URL, or PDF file part) and returns JSON against
  CARD_SCHEMA. The reply is normalized, never trusted: unknown enum values,
  malformed dates, and out-of-range amounts are dropped to None/low.
- FixtureExtractor: no network; the Sunshine Health sample from the contract.
  Used until POLICYQA_LLM_BASE_URL and POLICYQA_LLM_MODEL are set.

Scope: coverage and billing only. The scope heuristic runs before any model
call; the model classification can return the same codes. Never medical advice.
"""
from __future__ import annotations

import base64
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .generate import parse_model_json

CARD_FIELDS: tuple[str, ...] = (
    "payer_name",
    "program",
    "member_age_group",
    "service",
    "service_code",
    "dates_of_service",
    "amount_billed",
    "denial_reason",
    "letter_date",
    "appeal_deadline_claimed",
)
PROGRAMS = ("florida_medicaid_mma", "florida_medicaid_ltc", "florida_kidcare", "medicare_a", "medicare_b", "medicare_advantage", "medicare_part_d", "unknown")
AGE_GROUPS = ("under_21", "adult", "65_plus", "unknown")
CONFIDENCES = ("high", "medium", "low")
ENUM_FIELDS = {"program": PROGRAMS, "member_age_group": AGE_GROUPS}
DATE_FIELDS = ("letter_date", "appeal_deadline_claimed")
RANGE_FIELDS = ("dates_of_service",)
SERVICE_MAX_CHARS = 80
DENIAL_REASON_MAX_SENTENCES = 3
AMOUNT_MAX = 100_000.0  # at most five figures before the decimal
TEXT_MIN, TEXT_MAX = 200, 6_000
MODEL_NAME = "muse-spark-1.3"

ERROR_CODES = ("unsupported_type", "too_large", "text_length", "unreadable", "not_a_denial_letter", "out_of_scope")


class IntakeError(Exception):
    def __init__(self, code: str, message: str):
        assert code in ERROR_CODES, code
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Extraction:
    source: str  # text | image | pdf
    raw_text: str
    summary: str
    card: dict
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


# ---- scope heuristic -------------------------------------------------------

# Question forms only. Bare nouns such as "diagnosis" or "dose" appear in real notices
# ("Diagnosis code: Z00.00") and must not refuse a letter before the model reads it.
_OUT_OF_SCOPE = re.compile(
    r"should i (take|stop|start|use)\b|what (dose|dosage|medication|medicine|drug)\b|how (much|many) .{0,40}\b(take|should)\b"
    r"|is it safe\b|what are the side effects|diagnose me|what do i have\b|do i have (a|an)\b|what is wrong with me",
    re.I,
)
_DENIAL_SIGNALS = re.compile(r"denied|denial|not covered|not medically necessary|appeal|\bclaim\b|authorization|explanation of benefits|notice of action|adverse benefit determination", re.I)


def scope_check(text: str) -> str | None:
    """Cheap pre-model check. Returns `out_of_scope`, `not_a_denial_letter`, or None (looks fine)."""
    if _OUT_OF_SCOPE.search(text):
        return "out_of_scope"
    if not _DENIAL_SIGNALS.search(text):
        return "not_a_denial_letter"
    return None


# ---- model contract --------------------------------------------------------

def _field_schema(kind: str) -> dict:
    value: dict
    if kind == "program":
        value = {"type": ["string", "null"], "enum": list(PROGRAMS) + [None]}
    elif kind == "member_age_group":
        value = {"type": ["string", "null"], "enum": list(AGE_GROUPS) + [None]}
    elif kind == "amount_billed":
        value = {"type": ["number", "null"]}
    else:
        value = {"type": ["string", "null"]}
    return {"type": "object", "properties": {"value": value, "confidence": {"type": "string", "enum": list(CONFIDENCES)}}, "required": ["value", "confidence"], "additionalProperties": False}


CARD_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "is_denial_letter": {"type": "boolean"},
        "is_out_of_scope": {"type": "boolean"},
        "raw_text": {"type": "string"},
        "summary": {"type": "string"},
        "card": {
            "type": "object",
            "properties": {f: _field_schema(f) for f in CARD_FIELDS},
            "required": list(CARD_FIELDS),
            "additionalProperties": False,
        },
    },
    "required": ["is_denial_letter", "is_out_of_scope", "raw_text", "summary", "card"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = f"""You read a health coverage denial letter, notice of adverse benefit determination, or explanation of benefits (EOB) and fill a case card for an appeal tool. The letter arrives as text, as a photo, or as a PDF.

Rules:
1. Use only what the letter says. Do not use outside knowledge about payers, programs, or codes.
2. Confidence: "high" when the letter states the value in so many words; "medium" when you inferred it from what the letter says (for example the program from the payer and plan name, the age group from a date of birth); "low" when you guessed or the letter does not say it. When the letter does not say it, set value to null (or "unknown" for program and member_age_group) with confidence "low".
3. Formats: dates as YYYY-MM-DD; dates_of_service as YYYY-MM-DD or a range YYYY-MM-DD/YYYY-MM-DD; amount_billed as a number without currency symbols; service in at most 80 characters; denial_reason in at most three sentences, quoting the letter's own reason where possible.
4. program is one of: {", ".join(PROGRAMS)}. member_age_group is one of: {", ".join(AGE_GROUPS)}.
5. raw_text: the letter as you read it, in reading order, 200 to 6,000 characters. For text input, repeat the text you were given.
6. summary: one paragraph in plain language for a reader with no insurance background: who denied what, why the letter says it was denied, the amount if stated, and the deadline the letter gives to appeal. No advice beyond that.
7. Never give medical advice. Do not comment on treatment, diagnosis, medication, or whether the care was needed. If the input asks a treatment or diagnosis question, set is_out_of_scope to true. If the input is not a denial letter, notice, or EOB, set is_denial_letter to false.
8. Return JSON only, matching the schema. No prose before or after it."""

INSTRUCTION = "Read this coverage denial letter and fill the case card. Return JSON only."


# ---- normalization ---------------------------------------------------------

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(s: str) -> bool:
    if not _ISO.match(s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _valid_range(s: str) -> bool:
    parts = s.split("/")
    if not (1 <= len(parts) <= 2 and all(_valid_date(p) for p in parts)):
        return False
    return len(parts) == 1 or parts[0] <= parts[1]


def _amount(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
    elif isinstance(v, str):
        s = v.strip().replace("$", "").replace(",", "").replace("USD", "").strip()
        try:
            f = float(s)
        except ValueError:
            return None
    else:
        return None
    if f != f or f < 0 or f >= AMOUNT_MAX:
        return None
    return round(f, 2)


def _sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def coerce_field(field: str, value) -> tuple[object, bool]:
    """Return (clean value, ok). ok is False when the value had to be dropped."""
    if field in ENUM_FIELDS:
        v = str(value).strip().lower() if isinstance(value, str) else None
        return (v, True) if v in ENUM_FIELDS[field] else ("unknown", False)
    if value is None:
        return None, False
    if field == "amount_billed":
        a = _amount(value)
        return (a, a is not None)
    s = str(value).strip() if not isinstance(value, (dict, list)) else ""
    if not s:
        return None, False
    if field in DATE_FIELDS:
        return (s, True) if _valid_date(s) else (None, False)
    if field in RANGE_FIELDS:
        return (s, True) if _valid_range(s) else (None, False)
    if field == "service":
        return s[:SERVICE_MAX_CHARS].rstrip(), True
    if field == "denial_reason":
        return _sentences(s, DENIAL_REASON_MAX_SENTENCES), True
    return s, True


def normalize_card(raw: dict) -> dict:
    """Whatever the model returned -> {field: {"value", "confidence"}} for all ten fields, in order."""
    raw = raw if isinstance(raw, dict) else {}
    card: dict = {}
    for f in CARD_FIELDS:
        cell = raw.get(f)
        if isinstance(cell, dict):
            value, conf = cell.get("value"), cell.get("confidence")
        else:
            value, conf = cell, None
        conf = conf.strip().lower() if isinstance(conf, str) else None
        if conf not in CONFIDENCES:
            conf = "low"
        value, ok = coerce_field(f, value)
        if not ok:
            conf = "low"
        card[f] = {"value": value, "confidence": conf}
    return card


# ---- PDF text fallback -----------------------------------------------------

def pdf_to_text(data: bytes) -> str | None:
    """Text of a PDF via `pdftotext -layout`; None when pdftotext is not installed."""
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "in.pdf"
        src.write_bytes(data)
        r = subprocess.run([exe, "-layout", str(src), "-"], capture_output=True, timeout=60)
        if r.returncode != 0:
            return ""
        return r.stdout.decode("utf-8", errors="replace")


# ---- extractors ------------------------------------------------------------

def _data_url(mime: str, data: bytes) -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def build_parts(source: str, text: str | None = None, data: bytes | None = None, mime: str | None = None, filename: str | None = None) -> list[dict]:
    """OpenAI content parts for one letter."""
    if source == "text":
        return [{"type": "text", "text": f"{INSTRUCTION}\n\nLetter:\n{text}"}]
    if source == "image":
        return [{"type": "image_url", "image_url": {"url": _data_url(mime or "image/jpeg", data or b"")}}, {"type": "text", "text": INSTRUCTION}]
    if source == "pdf":
        return [{"type": "file", "file": {"filename": filename or "letter.pdf", "file_data": _data_url("application/pdf", data or b"")}}, {"type": "text", "text": INSTRUCTION}]
    raise ValueError(f"unknown source {source!r}")


def _is_file_rejection(exc: Exception) -> bool:
    resp = getattr(exc, "response", None)
    if resp is None or resp.status_code != 400:
        return False
    body = resp.text.lower()
    return "file" in body or "application/pdf" in body or "content type" in body or "content_type" in body


class MuseSparkExtractor:
    """Muse Spark 1.3 (or any OpenAI-compatible multimodal endpoint) reads the letter into the card."""

    def __init__(self, provider, max_tokens: int = 2500):
        self.provider = provider
        self.max_tokens = max_tokens
        self.model = getattr(provider, "model", MODEL_NAME)

    def extract(self, source: str, text: str | None = None, data: bytes | None = None, mime: str | None = None, filename: str | None = None) -> Extraction:
        import httpx

        t = time.perf_counter()
        parts = build_parts(source, text=text, data=data, mime=mime, filename=filename)
        try:
            raw, n_in, n_out = self.provider.complete_parts(SYSTEM_PROMPT, parts, schema=CARD_SCHEMA, max_tokens=self.max_tokens)
        except httpx.HTTPStatusError as e:
            if source != "pdf" or not _is_file_rejection(e):
                raise
            # The endpoint would not take the PDF as a file part: read its text locally and send that.
            extracted = pdf_to_text(data or b"")
            if extracted is None:
                raise IntakeError("unreadable", "The model endpoint did not accept the PDF and pdftotext is not installed to read it locally.") from e
            extracted = extracted.strip()
            if len(extracted) < TEXT_MIN:
                raise IntakeError("unreadable", "The PDF has no readable text layer. Upload a photo of the letter instead.") from e
            text = extracted[:TEXT_MAX]
            parts = build_parts("text", text=text)
            raw, n_in, n_out = self.provider.complete_parts(SYSTEM_PROMPT, parts, schema=CARD_SCHEMA, max_tokens=self.max_tokens)
        latency = round((time.perf_counter() - t) * 1000, 1)
        try:
            doc = parse_model_json(raw)
        except Exception as e:  # noqa: BLE001 - the model did not return JSON
            raise IntakeError("unreadable", "The model did not return a readable case card. Try again or paste the letter as text.") from e
        if not isinstance(doc, dict):
            raise IntakeError("unreadable", "The model did not return a readable case card.")
        if doc.get("is_out_of_scope"):
            raise IntakeError("out_of_scope", "Recourse reads coverage denial letters and drafts appeals. It does not give medical advice. For questions about treatment, dosage, or diagnosis, ask your doctor or pharmacist. If you have a denial letter, start with that.")
        if doc.get("is_denial_letter") is False:
            raise IntakeError("not_a_denial_letter", "This does not look like a coverage denial letter, notice of action, or explanation of benefits.")
        raw_text = text if text is not None else str(doc.get("raw_text") or "")
        return Extraction(
            source=source,
            raw_text=raw_text[:TEXT_MAX],
            summary=str(doc.get("summary") or "").strip(),
            card=normalize_card(doc.get("card") or {}),
            model=self.model,
            input_tokens=n_in,
            output_tokens=n_out,
            cost_usd=self.provider.cost(n_in, n_out),
            latency_ms=latency,
        )


FIXTURE_CARD = {
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

FIXTURE_SUMMARY = (
    "Sunshine Health, a Florida Medicaid managed care plan, denied payment for private duty nursing "
    "at 8 hours a day for September 1 to September 30, 2026. The letter says the reason is that the "
    "services went past the amount the plan had authorized, and lists the billed amount as $4,320.00. "
    "The letter is dated October 14, 2026 and says you can ask the plan to review the decision (an appeal) "
    "until December 13, 2026. This summary explains what the letter says; it is not medical advice."
)

FIXTURE_RAW_TEXT = (
    "[SYNTHETIC SAMPLE LETTER - fixture mode, not a real document]\n"
    "Sunshine Health\nNotice of Adverse Benefit Determination\nDate: October 14, 2026\n\n"
    "Member: J. Doe (age 9)   Member ID: 000000000\n"
    "Provider: Sample Home Nursing LLC\n\n"
    "We reviewed the request for private duty nursing, 8 hours per day, for dates of service "
    "September 1, 2026 through September 30, 2026 (billed amount: $4,320.00).\n\n"
    "Decision: DENIED.\nReason: Services exceed the authorized amount.\n\n"
    "You have the right to appeal this decision. Your appeal must be received within 60 days of the date "
    "of this notice, by December 13, 2026. You may also request a Medicaid fair hearing.\n"
)


class FixtureExtractor:
    """No network. Returns the contract's Sunshine Health sample for any input."""

    model = "fixture"

    def extract(self, source: str, text: str | None = None, data: bytes | None = None, mime: str | None = None, filename: str | None = None) -> Extraction:
        raw_text = text if source == "text" and text is not None else FIXTURE_RAW_TEXT
        return Extraction(
            source=source,
            raw_text=raw_text[:TEXT_MAX],
            summary=FIXTURE_SUMMARY,
            card={f: dict(v) for f, v in FIXTURE_CARD.items()},
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=0.0,
        )

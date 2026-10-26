"""Shared case and investigation builders for the verdict and letter tests (imported, not a pytest conftest)."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECOND_LIVE = ROOT / "results" / "second-live-case-2026-10-26.json"


def second_live_case() -> dict:
    """The second live Muse Spark case (Sunshine Health, private duty nursing): card, raw text, five findings."""
    return copy.deepcopy(json.loads(SECOND_LIVE.read_text(encoding="utf-8")))


def card(**over) -> dict:
    base = {
        "payer_name": "Sunshine Health",
        "program": "florida_medicaid_mma",
        "member_age_group": "under_21",
        "service": "private duty nursing, 8 hours/day",
        "service_code": "T1000",
        "dates_of_service": "2026-09-01/2026-09-30",
        "amount_billed": 4320.0,
        "denial_reason": "Services exceed the authorized amount.",
        "letter_date": "2026-10-14",
        "appeal_deadline_claimed": "2026-12-13",
    }
    base.update(over)
    return {k: {"value": v, "confidence": "high"} for k, v in base.items()}


def cite(doc_id, page, quote, title=None):
    return {"doc_id": doc_id, "title": title or f"Title of {doc_id}", "page": page, "quote": quote, "overlap": 1.0}


def finding(fid, topic, status, answer, citations=(), jurisdiction="Florida", question=None, struck=()):
    return {
        "id": fid,
        "question": question or f"Question about {topic} for {fid}?",
        "topic": topic,
        "jurisdiction": jurisdiction,
        "status": status,
        "answer": answer,
        "citations": list(citations),
        "struck": list(struck),
        "passages": [],
        "error": None,
    }


def investigation(*findings) -> dict:
    return {"status": "done", "findings": list(findings), "coverage": {}, "trace": {"spans": [], "total_ms": 0.0}}


LIMIT_QUOTE = "Florida Medicaid covers up to 24 hours of PDN services per day, per recipient, in accordance with the applicable Florida Medicaid fee schedule"
EXCEED_QUOTE = "services for recipients under the age of 21 years exceeding the coverage described within this policy or the associated fee schedule may be approved, if medically necessary."
POC_QUOTE = "Florida Medicaid does not cover the following: a skill level other than what is prescribed in the order for services and approved plan of care (POC)"
APPEAL_QUOTE = "An enrollee may file an appeal within sixty (60) days of the date on the notice of adverse benefit determination."


def small_investigation() -> dict:
    """f1 limits supported, f2 conditions supported, f3 reason not settled, f4 conditions unsupported, f5 appeal supported, f6 error."""
    return investigation(
        finding("f1", "limits", "supported", "Florida Medicaid covers up to 24 hours of private duty nursing per day.", [cite("fl-04", 5, LIMIT_QUOTE)]),
        finding("f2", "conditions", "supported", "Services above the policy may be approved for recipients under 21 if medically necessary.", [cite("fl-04", 6, EXCEED_QUOTE), cite("fl-04", 6, POC_QUOTE)]),
        finding("f3", "reason", "not_settled", "Not covered by the corpus.", question="What do the rules say when billed hours exceed authorized hours?"),
        finding("f4", "conditions", "unsupported", "Authorization must be renewed every 180 days.", struck=[{"doc_id": "fl-04", "title": "t", "page": 4, "quote": "Authorization is renewed every 180 days with a plan of care.", "reason": "quote not found on the cited page"}], question="How often must authorization be renewed?"),
        finding("f5", "appeal", "supported", "The member may appeal to the plan within 60 days of the notice. The member may ask for a fair hearing after the plan appeal.", [cite("fl-21", 41, APPEAL_QUOTE)]),
        {**finding("f6", "exclusions", "error", "", question="What exclusions apply?"), "error": "TimeoutError: slow"},
    )


def case_with(inv=None, **card_over) -> dict:
    return {"case_id": "c_test01", "card": card(**card_over), "raw_text": "Member ID: 00000000-SAMPLE\nSunshine Health", "investigation": inv}

"""Action: appeal letter verification, deadline, evidence checklist, filing path, export. No network."""
import json
from datetime import date

import pytest

from casebuilders import (
    APPEAL_QUOTE,
    EXCEED_QUOTE,
    LIMIT_QUOTE,
    POC_QUOTE,
    case_with,
    cite,
    finding,
    investigation,
    second_live_case,
    small_investigation,
)
from policyqa.generate import TruncatedResponse
from policyqa.letter import (
    LETTER_MAX_TOKENS,
    LETTER_SCHEMA,
    LETTER_SYSTEM_PROMPT,
    FixtureLetter,
    compute_deadline,
    draft_letter,
    evidence_checklist,
    filing_path,
    letter_text,
    verify_letter,
)
from policyqa.verdict import FixtureVerdict, verdict_from_data, _meta

TODAY = date(2026, 10, 26)


def s(text, claim=False, citation=None):
    return {"text": text, "claim": claim, "citation": citation}


def inconsistent_verdict(inv):
    return verdict_from_data(
        {
            "steelman": {"argument": "The plan approved fewer hours.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "rule": {"statement": "The policy covers up to 24 hours a day.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "outcome": "inconsistent",
            "gap": "The letter treats the authorization as the ceiling.",
            "what_would_change": None,
        },
        inv,
        _meta("fake"),
    )


def consistent_verdict(inv):
    return verdict_from_data(
        {
            "steelman": {"argument": "Hours above the authorization were billed.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "rule": {"statement": "The policy pays for the hours the plan authorizes.", "citations": [{"finding_id": "f1", "quote": LIMIT_QUOTE}]},
            "outcome": "consistent",
            "gap": "The letter's reason is the rule: the hours went past the authorization.",
            "what_would_change": "An authorization for the extra hours before the care was given.",
        },
        inv,
        _meta("fake"),
    )


# ---- verify_letter -----------------------------------------------------------------


def test_verify_letter_marks_claims_and_never_strikes_non_claims():
    inv = small_investigation()
    raw = {
        "paragraphs": [
            {"sentences": [s("Dear Sunshine Health,"), s("I am appealing the denial dated October 14, 2026.", citation={"finding_id": "f1", "quote": "made up quote that is not anywhere"})]},
            {
                "sentences": [
                    s("Florida Medicaid covers up to 24 hours of private duty nursing a day.", True, {"finding_id": "f1", "quote": LIMIT_QUOTE}),
                    s("The policy says the plan must pay every billed hour.", True, {"finding_id": "f1", "quote": "the plan must pay for every billed hour of care"}),
                    s("The policy also limits hours to eight a day.", True, None),
                    s("Extra services may be approved.", True, {"finding_id": "f3", "quote": LIMIT_QUOTE}),
                ]
            },
            {"sentences": [s("  "), s("Sincerely,")]},
        ]
    }
    out = verify_letter(raw, inv)
    p1, p2, p3 = out["paragraphs"]
    assert all(not x["struck"] and x["citation"] is None and not x["verified"] for x in p1["sentences"])
    good, bad, bare, unsettled = p2["sentences"]
    assert good["verified"] is True and good["struck"] is False and good["citation"]["doc_id"] == "fl-04" and good["citation"]["page"] == 5
    assert set(good["citation"]) == {"finding_id", "doc_id", "title", "page", "quote"}
    assert bad["verified"] is False and bad["struck"] is True and bad["citation"] is None
    assert bare["struck"] is True and unsettled["struck"] is True
    assert [x["text"] for x in p3["sentences"]] == ["Sincerely,"]  # empty sentences dropped
    assert out["verification"] == {"claims": 4, "verified": 1, "struck": 3}
    assert set(good) >= {"text", "claim", "citation", "verified", "struck"}


def test_a_sentence_about_whether_the_care_was_needed_is_struck():
    inv = small_investigation()
    out = verify_letter({"paragraphs": [{"sentences": [s("My child needed every one of these hours."), s("The nursing services were medically necessary.")]}]}, inv)
    assert all(x["struck"] for x in out["paragraphs"][0]["sentences"])
    assert "medical" in out["paragraphs"][0]["sentences"][0]["reason"]


# ---- deadline -------------------------------------------------------------------------


def test_deadline_from_the_letter_counts_days_from_today():
    d = compute_deadline(case_with()["card"], small_investigation(), today=TODAY)
    assert d == {"date": "2026-12-13", "days_left": 48, "source": "letter", "citation": None, "note": "The letter states this deadline."}


def test_deadline_from_policy_days_counts_from_the_letter_date():
    c = case_with(appeal_deadline_claimed=None)["card"]
    d = compute_deadline(c, small_investigation(), today=TODAY)
    assert d["source"] == "policy" and d["date"] == "2026-12-13" and d["days_left"] == 48
    assert d["citation"]["finding_id"] == "f5" and d["citation"]["quote"] == APPEAL_QUOTE
    assert "60 days" in d["note"]


def test_deadline_from_policy_without_a_letter_date():
    c = case_with(appeal_deadline_claimed=None, letter_date=None)["card"]
    d = compute_deadline(c, small_investigation(), today=TODAY)
    assert d["source"] == "policy" and d["date"] is None and d["days_left"] is None and d["citation"]


def test_deadline_unknown():
    inv = investigation(finding("f1", "appeal", "supported", "You can appeal.", [cite("fl-21", 40, "An enrollee may file an appeal with the managed care plan.")]))
    d = compute_deadline(case_with(appeal_deadline_claimed=None)["card"], inv, today=TODAY)
    assert d == {"date": None, "days_left": None, "source": "unknown", "citation": None, "note": "Neither the letter nor the documents we found state a deadline. Check the letter and call the plan."}


def test_deadline_prefers_the_programs_jurisdiction_on_a_dual_route():
    inv = investigation(
        finding("f1", "appeal", "supported", "Medicare: 120 days.", [cite("fed-17", 3, "A redetermination request must be filed within 120 days from the date of receipt.")], jurisdiction="Federal"),
        finding("f2", "appeal", "supported", "Medicaid: 60 days.", [cite("fl-21", 41, APPEAL_QUOTE)]),
    )
    d = compute_deadline(case_with(appeal_deadline_claimed=None)["card"], inv, today=TODAY)
    assert d["citation"]["finding_id"] == "f2" and d["date"] == "2026-12-13"
    d = compute_deadline(case_with(appeal_deadline_claimed=None, program="medicare_b")["card"], inv, today=TODAY)
    assert d["citation"]["finding_id"] == "f1" and d["date"] == "2027-02-11"


def test_business_days_are_not_counted_as_calendar_days():
    inv = investigation(finding("f1", "appeal", "supported", "x", [cite("fl-21", 2, "The plan resolves each appeal within thirty (30) business days of receipt.")]))
    assert compute_deadline(case_with(appeal_deadline_claimed=None)["card"], inv, today=TODAY)["source"] == "unknown"


# ---- checklist and filing ---------------------------------------------------------------


def test_checklist_from_conditions_and_limits_on_the_second_live_record():
    inv = second_live_case()["investigation"]
    items = evidence_checklist(inv)
    assert 3 <= len(items) <= 7
    text = " ".join(i["item"].lower() for i in items)
    assert "plan of care" in text and "order" in text and "hours" in text
    for i in items:
        assert set(i) == {"item", "why", "citation"} and i["why"]
        if i["citation"] is not None:
            assert i["citation"]["finding_id"] in {"f2", "f3"}


def test_checklist_is_padded_to_three_and_empty_when_nothing_supported():
    inv = investigation(finding("f1", "limits", "supported", "Up to 24 hours a day.", [cite("fl-04", 5, LIMIT_QUOTE)]))
    items = evidence_checklist(inv)
    assert len(items) == 3 and items[0]["citation"]["finding_id"] == "f1"
    assert evidence_checklist(investigation(finding("f1", "coverage", "supported", "x", [cite("fl-04", 5, LIMIT_QUOTE)]))) == []
    assert evidence_checklist(investigation(finding("f1", "conditions", "not_settled", "Not covered by the corpus."))) == []


def test_filing_from_the_appeal_finding():
    f = filing_path(small_investigation())
    assert f["where"] == "The member may appeal to the plan within 60 days of the notice."
    assert f["citation"]["finding_id"] == "f5"
    assert f["how"] == "Check the appeal section of the letter or call the number on it."


def test_filing_fallback_when_the_appeal_finding_names_neither():
    f = filing_path(second_live_case()["investigation"])  # f5 says the passages do not state how or where to file
    assert f == {"where": "Not stated in the documents we found.", "how": "Check the appeal section of the letter or call the number on it.", "citation": None}
    assert filing_path(investigation()) == f


# ---- draft_letter -------------------------------------------------------------------------


class FakeProvider:
    model = "fake-muse"

    def __init__(self, content=None, raise_exc=None):
        self.content, self.raise_exc, self.calls = content, raise_exc, []
        self.last_response = {"usage": {"completion_tokens_details": {"reasoning_tokens": 800}}}

    def complete_parts(self, system, parts, schema=None, max_tokens=1500):
        self.calls.append({"system": system, "parts": parts, "schema": schema, "max_tokens": max_tokens})
        if self.raise_exc:
            raise self.raise_exc
        return (self.content if isinstance(self.content, str) else json.dumps(self.content)), 1200, 1500

    def cost(self, n_in, n_out):
        return 0.01


GOOD_LETTER = {
    "paragraphs": [
        {"sentences": [s("Dear Sunshine Health appeals team,")]},
        {"sentences": [s("I am writing to appeal the denial of private duty nursing for September 2026."), s('Your letter gives this reason: "Services exceed the authorized amount."')]},
        {"sentences": [s("Florida Medicaid covers up to 24 hours of private duty nursing per day.", True, {"finding_id": "f1", "quote": LIMIT_QUOTE}), s("The policy requires payment for every hour billed.", True, {"finding_id": "f2", "quote": "the plan pays every hour billed by the nurse"})]},
        {"sentences": [s("Please reverse the denial."), s("Sincerely, [Your name]")]},
    ]
}


def test_draft_letter_inconsistent_with_a_fake_model():
    inv = small_investigation()
    p = FakeProvider(GOOD_LETTER)
    case = case_with(inv)
    L = draft_letter(case, inv, inconsistent_verdict(inv), p, today=TODAY)
    assert L["status"] == "done" and L["applicable"] is True and L["explanation"] is None and L["error"] is None
    assert L["to"] == "Sunshine Health"
    assert L["re"] == "Appeal of the denial of private duty nursing, 8 hours/day for dates of service September 1, 2026 through September 30, 2026, member 00000000-SAMPLE"
    assert L["verification"] == {"claims": 2, "verified": 1, "struck": 1}
    assert L["deadline"]["source"] == "letter" and L["deadline"]["days_left"] == 48
    assert L["filing"]["citation"]["finding_id"] == "f5"
    assert 3 <= len(L["evidence_checklist"]) <= 7
    assert L["model"] == "fake-muse" and L["input_tokens"] == 1200 and L["output_tokens"] == 1500 and L["reasoning_tokens"] == 800 and L["cost_usd"] == 0.01
    call = p.calls[0]
    assert call["max_tokens"] == LETTER_MAX_TOKENS >= 6000 and call["schema"] is LETTER_SCHEMA
    user = "".join(x["text"] for x in call["parts"])
    assert "The policy covers up to 24 hours a day." in user and "[f1]" in user and "Authorization must be renewed" not in user
    assert "whether the care was needed" in LETTER_SYSTEM_PROMPT.lower() and "medical advice" in LETTER_SYSTEM_PROMPT.lower()


def test_member_reference_falls_back_to_on_file_and_missing_dates():
    inv = small_investigation()
    case = case_with(inv, dates_of_service="2026-09-03", service=None)
    case["raw_text"] = "No reference here."
    L = draft_letter(case, inv, inconsistent_verdict(inv), FakeProvider(GOOD_LETTER), today=TODAY)
    assert L["re"] == "Appeal of the denial of the service for dates of service September 3, 2026, member on file"


def test_consistent_outcome_gives_an_explanation_and_no_letter_or_model_call():
    inv = small_investigation()
    p = FakeProvider(GOOD_LETTER)
    L = draft_letter(case_with(inv), inv, consistent_verdict(inv), p, today=TODAY)
    assert p.calls == []
    assert L["applicable"] is False and L["paragraphs"] == [] and L["status"] == "done"
    assert "The policy pays for the hours the plan authorizes." in L["explanation"]
    assert "An authorization for the extra hours" in L["explanation"]
    assert L["verification"] == {"claims": 0, "verified": 0, "struck": 0}
    assert L["deadline"]["date"] == "2026-12-13"
    with pytest.raises(ValueError):
        letter_text(L)


@pytest.mark.parametrize("provider", [FakeProvider("not json"), FakeProvider({"paragraphs": "x"}), FakeProvider(raise_exc=TruncatedResponse("budget"))])
def test_model_failure_gives_a_template_letter_from_the_verified_rule(provider):
    inv = small_investigation()
    L = draft_letter(case_with(inv), inv, inconsistent_verdict(inv), provider, today=TODAY)
    assert L["status"] == "done" and L["error"] and L["applicable"] is True
    claims = [x for p in L["paragraphs"] for x in p["sentences"] if x["claim"]]
    assert claims and all(x["verified"] for x in claims)
    assert L["verification"]["struck"] == 0


def test_letter_text_drops_struck_sentences_and_marks_verified_claims():
    inv = small_investigation()
    L = draft_letter(case_with(inv), inv, inconsistent_verdict(inv), FakeProvider(GOOD_LETTER), today=TODAY)
    txt = letter_text(L)
    assert txt.startswith("To: Sunshine Health\nRe: Appeal of the denial of")
    assert "Florida Medicaid covers up to 24 hours of private duty nursing per day. [cite: Title of fl-04, p. 5]" in txt
    assert "requires payment for every hour" not in txt
    assert "Please reverse the denial." in txt and "[cite:" not in txt.split("Please reverse")[1]


# ---- fixture --------------------------------------------------------------------------------


def test_fixture_letter_on_the_second_live_record():
    rec = second_live_case()
    inv = rec["investigation"]
    v = FixtureVerdict(delay=0).decide(rec, inv)
    L = FixtureLetter(delay=0).draft(rec, inv, v, today=TODAY)
    assert L["model"] == "fixture" and L["applicable"] is True and L["status"] == "done"
    assert L["verification"]["struck"] == 1 and L["verification"]["verified"] >= 2
    assert "fixture" in L["paragraphs"][0]["sentences"][0]["text"].lower()
    assert L["re"].endswith("member 00000000-SAMPLE")
    assert L["deadline"]["source"] == "letter" and L["filing"]["citation"] is None
    assert len(L["evidence_checklist"]) >= 3
    txt = letter_text(L)
    assert "[cite:" in txt and "every hour a provider bills" not in txt


def test_live_letter_through_the_real_provider_over_a_fake_transport():
    import httpx

    from policyqa.generate import Provider
    from policyqa.letter import LiveLetter

    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD_LETTER)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2500, "completion_tokens": 3000, "completion_tokens_details": {"reasoning_tokens": 2200}}})

    p = Provider(base_url="https://api.meta.ai/v1", api_key="k", model="muse-spark-1.3", transport=httpx.MockTransport(handler))
    inv = small_investigation()
    L = LiveLetter(p).draft(case_with(inv), inv, inconsistent_verdict(inv), today=TODAY)
    assert L["verification"] == {"claims": 2, "verified": 1, "struck": 1} and L["reasoning_tokens"] == 2200
    assert sent[0]["max_tokens"] == LETTER_MAX_TOKENS and sent[0]["response_format"]["json_schema"]["schema"] == LETTER_SCHEMA


def test_today_eastern_survives_a_missing_time_zone_database(monkeypatch):
    import datetime as dt
    import policyqa.letter as L

    def boom(_key):
        raise LookupError("No time zone found with key America/New_York")

    monkeypatch.setattr("zoneinfo.ZoneInfo", boom)
    assert isinstance(L.today_ny(), dt.date)


# ---- Oct 27: dates spelled out, like the Re line -------------------------------------------


def test_the_letter_spells_dates_out_like_the_re_line():
    """The first live letters wrote '2026-09-01'. The model is shown spelled dates and told to write them so,
    and any ISO date that still comes back in a sentence (the draft or a critic revision) is spelled out."""
    inv = small_investigation()
    case = case_with(inv)
    case["summary"] = "Sunshine Health denied part of the private duty nursing hours."
    reply = {"paragraphs": [{"sentences": [
        s("I am writing to appeal your letter dated 2026-10-14 about services from 2026-09-01/2026-09-30."),
        s("Florida Medicaid covers up to 24 hours of private duty nursing per day.", True, {"finding_id": "f1", "quote": LIMIT_QUOTE}),
    ]}]}
    p = FakeProvider(reply)
    L = draft_letter(case, inv, inconsistent_verdict(inv), p, today=TODAY)
    assert L["paragraphs"][0]["sentences"][0]["text"] == "I am writing to appeal your letter dated October 14, 2026 about services from September 1, 2026 through September 30, 2026."
    assert L["paragraphs"][0]["sentences"][1]["verified"] is True
    u = "".join(part["text"] for part in p.calls[0]["parts"])
    assert "2026-09-01" not in u and "2026-10-14" not in u
    assert "September 1, 2026 through September 30, 2026" in u and "October 14, 2026" in u and "December 13, 2026" in u
    assert case["summary"] in u and "Member ID" not in u
    assert "September 1, 2026" in LETTER_SYSTEM_PROMPT
    # an invalid date-shaped string is left alone
    from policyqa.letter import verify_letter

    out = verify_letter({"paragraphs": [{"sentences": [s("Claim number 2026-13-45 is on file.")]}]}, inv)
    assert out["paragraphs"][0]["sentences"][0]["text"] == "Claim number 2026-13-45 is on file."

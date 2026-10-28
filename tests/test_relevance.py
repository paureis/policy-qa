"""The exception relevance check (policyqa/relevance.py): an exception counts against the letter only when
its quoted words name the letter's fact. No network, no model call: the rule is token matching.

Quotes are the real sentences from the corpus pages the Oct 27 case rows point at (cases/cases.csv hinge
quotes and notes): fed-16 p8 (cataract), fed-10 p13 and p14 (cosmetic, rosacea), fed-20 p7 (QMB), fl-04 p6
(under 21), fl-16 p8 (attendant nursing, LTC), fl-03 p5 (three visits a day)."""
import pytest

from casebuilders import card, cite, finding, investigation
from policyqa.relevance import is_exception_finding, letter_facts, mark_exceptions, quote_relevance

CATARACT = "1 pair of eyeglasses or contact lenses after each cataract surgery with insertion of an intraocular lens"
ROSACEA = "Part D drugs indicated for the treatment of psoriasis, acne, rosacea, or vitiligo are not considered cosmetic."
COSMETIC = "Agents when used for cosmetic purposes or hair growth."
QMB = "All Original Medicare and MA providers and suppliers (not only those that accept Medicaid) can't charge QMBs Medicare Part A and Part B cost-sharing for covered services."
UNDER_21 = "As such, services for recipients under the age of 21 years exceeding the coverage described within this policy or the associated fee schedule may be approved, if medically necessary."
ATTENDANT = (
    "To provide nursing care of both a supportive and health-related nature, specific to the needs of a medically stable, physically handicapped "
    "enrollee age 21 and older who requires more individual and continuous care than an intermittent nursing visit. The scope and nature of these "
    "services do not otherwise differ from private duty nursing services furnished to persons under the age of 21 years."
)
LTC_TITLE = "Florida Medicaid Statewide Medicaid Managed Care Long-term Care Program Coverage Policy (Rule 59G-4.192)"
THREE_VISITS = "Up to three intermittent home health visits, per day, for non-pregnant recipients age 21 years and older"


def facts(summary=None, **over):
    return letter_facts(card(**over), summary)


# ---- positive: the quote names the letter's fact --------------------------------------------


def test_the_procedure_in_the_service_is_named_by_the_exception():
    """dc-018: the letter states the cataract surgery; the exception names it."""
    f = facts(program="medicare_b", member_age_group="65_plus", service="Eyeglass frames after cataract surgery", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    r = quote_relevance(CATARACT, f)
    assert r["relevant"] is True and r["named"] == ["cataract surgery"]
    assert "cataract surgery" in r["reason"]


def test_the_fact_in_the_intake_summary_counts_in_a_different_form():
    """The card's service field has no qualifier; the intake summary says 'surgeries' where the quote says 'surgery'."""
    f = facts("Medicare denied eyeglass frames ordered after two cataract surgeries, each with a lens implant.", program="medicare_b", member_age_group="65_plus",
              service="Eyeglass frames", denial_reason="Medicare does not cover eyeglasses or contact lenses.")
    r = quote_relevance(CATARACT, f)
    assert r["relevant"] is True and "cataract" in r["named"][0]


def test_the_drug_purpose_is_named_and_a_different_purpose_is_not():
    """dc-026 (rosacea) against dc-025 (hair loss): the rosacea exception covers one and not the other."""
    reason = "Medicare Part D does not cover drugs used for cosmetic purposes."
    rosacea = facts(program="medicare_part_d", member_age_group="65_plus", service="Azelaic acid 15% gel, prescribed for rosacea", denial_reason=reason)
    hair = facts(program="medicare_part_d", member_age_group="65_plus", service="Finasteride 1 mg tablets, prescribed for hair loss", denial_reason=reason)
    assert quote_relevance(ROSACEA, rosacea)["relevant"] is True
    r = quote_relevance(ROSACEA, hair)
    assert r["relevant"] is False and "hair loss" in r["reason"]
    # "hair growth" is not "hair loss": every word of the fact must be in the quote
    assert quote_relevance(COSMETIC, hair)["relevant"] is False


@pytest.mark.parametrize("summary", [
    "The plan denied azelaic acid 15% gel. The prescription says it is for rosacea.",  # dc-026's letter words
    "The plan denied azelaic acid 15% gel, which the prescription says is for rosacea.",
    "The plan denied azelaic acid 15% gel; the drug is for rosacea.",
])
def test_the_drug_purpose_in_the_letters_own_words_counts(summary):
    """dc-026: the card's service may be only the drug; the letter says 'The prescription says it is for rosacea.'"""
    f = facts(summary, program="medicare_part_d", member_age_group="65_plus", service="Azelaic acid 15% gel",
              denial_reason="This is a skin product used for a cosmetic purpose. Medicare Part D does not cover drugs used for cosmetic purposes.")
    assert [x.label for x in f.facts] == ["rosacea"]
    assert quote_relevance(ROSACEA, f)["relevant"] is True


def test_the_other_programs_name_alone_is_not_a_fact_so_the_qmb_rule_is_unchecked():
    """dc-021, card only: the letter says Florida Medicaid did not pay the Medicare coinsurance, so the member has
    both programs, but "Medicaid" alone names no specific coverage (fix round: any Medicaid sentence matched it).
    The QMB rule is then unchecked, not failed: the guard cannot touch it."""
    f = facts(program="medicare_b", member_age_group="65_plus", service="Office visit, established patient", payer_name="Sample Medical Group",
              denial_reason="Florida Medicaid did not pay the Medicare coinsurance for this visit, so the remaining balance is the patient's responsibility.")
    assert f.facts == ()
    r = quote_relevance(QMB, f)
    assert r["state"] == "unchecked" and r["relevant"] is None
    assert quote_relevance("Florida Medicaid does not cover eyeglasses for adults.", f)["state"] == "unchecked"


def test_qmb_named_in_the_letter_matches_the_plural_in_the_quote():
    f = facts("U. Sample has Medicare Part B and is in the Qualified Medicare Beneficiary (QMB) program.", program="medicare_b", member_age_group="65_plus",
              service="Office visit, established patient", payer_name="Sample Medical Group", denial_reason="The balance is the patient's responsibility.")
    r = quote_relevance("Providers can't charge QMBs cost-sharing for covered services.", f)
    assert r["relevant"] is True and "QMB" in r["named"]


def test_a_procedure_named_by_its_initials_counts():
    f = facts("The plan denied cardiac rehabilitation sessions ordered following coronary artery bypass graft surgery.", program="medicare_b",
              member_age_group="65_plus", service="Cardiac rehabilitation", denial_reason="The sessions exceed the limit.")
    assert quote_relevance("Additional sessions are covered after a CABG when the physician orders them.", f)["relevant"] is True


# ---- negative: the exception exists but does not name the letter's fact ----------------------


def test_an_exception_for_a_different_age_group_is_not_relevant():
    """dc-002: the member is 21 or older; the 'may be approved' sentence is for recipients under 21."""
    f = facts(member_age_group="adult", service="Private duty nursing, 12 hours per day",
              denial_reason="Private duty nursing is covered only for members under the age of 21. Our records show the member turned 21 before the dates of service.")
    r = quote_relevance(UNDER_21, f)
    assert r["relevant"] is False and "under 21" in r["reason"] and "21 or older" in r["reason"]


def test_the_same_age_sentence_for_a_member_under_21_is_not_a_contradiction():
    f = facts(member_age_group="under_21", service="Private duty nursing after a tracheostomy")
    assert quote_relevance(UNDER_21 + " This includes care after a tracheostomy.", f)["relevant"] is True


def test_an_exception_from_another_programs_document_is_not_relevant():
    """dc-002: adult attendant nursing exists under the Long-term Care program (fl-16 p8); the member is in MMA.
    The quote names the service and the member's age group, but it is another program's rule."""
    f = facts(member_age_group="adult", service="Private duty nursing, 12 hours per day",
              denial_reason="Private duty nursing is covered only for members under the age of 21.")
    r = quote_relevance(ATTENDANT, f, title=LTC_TITLE)
    assert r["relevant"] is False and "Long-term Care" in r["reason"]


def test_the_service_alone_in_any_form_is_not_the_letters_fact():
    """dc-003: the exclusion and the 'three visits a day' rule are both about home health visits; naming the
    service (here as 'intermittent home health visits') does not make the exception cover the spacing."""
    f = facts(member_age_group="adult", service="Home health skilled nursing visit (second visit of the day)", service_code="",
              denial_reason="Intermittent home health visits rendered less than an hour apart are not covered. The second visit on August 14, 2026 began 40 minutes after the first visit ended.")
    r = quote_relevance(THREE_VISITS, f)
    assert r["relevant"] is False and "names none of the letter's facts" in r["reason"]
    # PDN for private duty nursing: the service by its initials is still only the service
    pdn = facts(member_age_group="under_21", service="Private duty nursing")
    assert pdn.facts == () and quote_relevance("PDN services may be approved above the fee schedule.", pdn)["state"] == "unchecked"


def test_the_services_other_name_and_its_attributes_are_not_facts():
    """dc-006: '(BIPAP)' is the service's other name and 'rental' an attribute; the CPAP rule names both."""
    f = facts(member_age_group="adult", service="Bi-level positive airway pressure device (BIPAP), rental",
              denial_reason="A bi-level device (BIPAP) is covered only after a CPAP device was tried without success.")
    assert f.facts == ()
    quote = "Heated or non-heated humidifiers prescribed for use with the covered CPAP or BIPAP device are not included in the device's monthly rental fee."
    assert quote_relevance(quote, f)["state"] == "unchecked"
    # a parenthesis with two words or more is a fact, split at its commas
    g = facts(member_age_group="under_21", service="Physical therapy session (session 25 in 60 days, same injury)")
    assert [x.label for x in g.facts] == ["session 25 in 60 days", "same injury"]


def test_the_stated_reasons_terms_are_not_the_letters_facts():
    """dc-026 without the purpose on the card: 'cosmetic' is the rule's own word, in the exclusion and in its exception alike."""
    f = facts(program="medicare_part_d", member_age_group="65_plus", service="Azelaic acid 15% gel",
              denial_reason="This is a skin product used for a cosmetic purpose. Medicare Part D does not cover drugs used for cosmetic purposes.")
    assert f.facts == () and quote_relevance(ROSACEA, f)["relevant"] is not True


def test_a_summary_sentence_that_restates_the_reason_is_not_a_fact():
    """dc-029: the summary repeats the rule ('after a qualifying inpatient hospital stay'), which is not a fact of the claim."""
    reason = "Part A covers skilled nursing facility care only after a qualifying inpatient hospital stay of at least 3 days in a row."
    f = facts("Medicare says Part A covers skilled nursing facility care only after a qualifying inpatient hospital stay of 3 days in a row.",
              program="medicare_a", member_age_group="65_plus", service="Skilled nursing facility stay", denial_reason=reason)
    r = quote_relevance("Time under observation doesn't count toward the three-day qualifying inpatient hospital stay.", f)
    assert f.facts == () and r["relevant"] is not True


def test_no_quote_or_no_facts_is_unchecked_not_failed():
    f = facts(service="Private duty nursing")
    assert quote_relevance("", f)["state"] == "unchecked"
    r = quote_relevance(CATARACT, f)
    assert r["state"] == "unchecked" and r["relevant"] is None and "states no specific fact" in r["reason"]
    # an age contradiction is decisive even when the letter states no other fact (dc-002)
    g = facts(member_age_group="adult", service="Private duty nursing")
    assert quote_relevance(UNDER_21, g)["state"] == "not_relevant"


@pytest.mark.parametrize("over, summary", [
    # dc-027: "first fill after joining the plan" gives the single verb form "joining"
    ({"program": "medicare_part_d", "member_age_group": "65_plus", "service": "Non-formulary drug, first fill after joining the plan",
      "denial_reason": "This drug is not on the plan's formulary. Non-formulary drugs are not covered unless an exception is approved."}, None),
    # dc-023: the letter's "After review of the medical records" gives only process words
    ({"program": "medicare_advantage", "member_age_group": "65_plus", "service": "Emergency department visit, high severity",
      "denial_reason": "The final diagnosis was not an emergency medical condition."}, "After review of the medical records, we have denied payment for this claim."),
    # dc-012: an LTC member with Medicare on file; the other program's name alone
    ({"program": "florida_medicaid_ltc", "member_age_group": "65_plus", "service": "Home-delivered meals, 1 meal per day",
      "denial_reason": "Home-delivered meals are not a covered benefit of the Long-term Care program."}, "Other coverage on file: Medicare Part A and Part B. Florida Medicaid denied the meals."),
])
def test_junk_phrases_are_not_facts(over, summary):
    """Evaluator, fix round: "joining", "review of the medical records" and "Medicare" alone made every exception in
    dc-027, dc-023 and dc-012 fail the fact test. None of them is a fact, so those cases are unchecked."""
    f = facts(summary, **over)
    assert f.facts == ()
    assert quote_relevance("Plans must provide a transition supply within the first 90 days of coverage under a new plan.", f)["state"] == "unchecked"


@pytest.mark.parametrize("over, summary", [
    ({"service": "Eyeglass frames (post cataract surgery)"}, None),
    ({"service": "Eyeglass frames"}, "Medicare denied eyeglass frames ordered post-cataract surgery."),
])
def test_post_before_a_procedure_is_a_cue(over, summary):
    f = facts(summary, program="medicare_b", member_age_group="65_plus", denial_reason="Medicare does not cover eyeglasses or contact lenses.", **over)
    assert [x.label for x in f.facts] == ["cataract surgery"]
    assert quote_relevance(CATARACT, f)["state"] == "relevant"


def test_an_exception_finding_that_quotes_the_rule_another_finding_quotes_is_unchecked():
    """dc-001 shape: the exception question came back quoting the 24-hour rule itself, which the limits finding
    also quotes. That is the rule, not an exception failing the fact test, even when the letter has a fact."""
    rule = "Florida Medicaid covers up to 24 hours of PDN services per day, per recipient, in accordance with the applicable Florida Medicaid fee schedule"
    c = {"card": card(member_age_group="under_21", service="Private duty nursing after a tracheostomy, 16 hours per day",
                      denial_reason="Florida Medicaid limits private duty nursing to 8 hours per day."), "summary": None}
    inv = investigation(
        finding("f2", "limits", "supported", "Up to 24 hours a day.", [cite("fl-04", 5, rule)]),
        finding("f3", "exclusions", "supported", "Up to 24 hours a day.", [cite("fl-04", 5, rule)],
                question="Is there an exception under Florida Medicaid (MMA) that covers private duty nursing, 16 hours per day even though it is limited to 8 hours?"),
    )
    m = mark_exceptions(inv, c)[0]
    assert m["state"] == "unchecked" and m["relevant"] is None and "same rule as f2" in m["reason"]


def test_member_names_and_amounts_in_the_summary_are_not_facts():
    f = facts("Sample Health Plan denied private duty nursing for A. Sample, approving 8 hours per day, with $11,520.00 billed for September 2026.",
              service="private duty nursing, 16 hours per day")
    assert all(x.label.lower() not in ("a. sample", "sample") for x in f.facts)
    assert f.facts == () and quote_relevance("Florida Medicaid covers up to 24 hours of PDN services per day, per recipient.", f)["relevant"] is not True


# ---- which findings are exception findings, and the marks ----------------------------------


@pytest.mark.parametrize("question, expected", [
    ("Is there an exception under Medicare Part B that covers eyeglass frames after cataract surgery even though medicare does not cover eyeglasses?", True),
    ("Can a provider bill a member in the Qualified Medicare Beneficiary (QMB) program for Medicare cost-sharing for office visit?", True),
    ("Is eyeglass frames covered under Medicare Part B?", False),
    ("What exclusions apply to private duty nursing under Florida Medicaid (MMA)?", False),
])
def test_exception_findings_are_the_exception_and_qmb_questions(question, expected):
    assert is_exception_finding({"question": question}) is expected


def test_mark_exceptions_keeps_every_exception_finding_and_marks_it():
    c = {"card": card(member_age_group="adult", service="Private duty nursing, 12 hours per day",
                      denial_reason="Private duty nursing is covered only for members under the age of 21."), "summary": None}
    inv = investigation(
        finding("f1", "coverage", "supported", "PDN is for under 21.", [cite("fl-04", 4, "Florida Medicaid recipients under the age of 21 years requiring medically necessary PDN.")]),
        finding("f2", "exclusions", "supported", "Services above the policy may be approved for under 21.", [cite("fl-04", 6, UNDER_21)],
                question="Is there an exception under Florida Medicaid (MMA) that covers private duty nursing even though it is only for under 21?"),
        finding("f3", "exclusions", "supported", "Adults may get attendant nursing care under LTC.", [cite("fl-16", 8, ATTENDANT, title=LTC_TITLE)],
                question="Is there an exception for adults who need private duty nursing?"),
        finding("f4", "exclusions", "not_settled", "Not covered by the corpus.", question="Is there an exception for members who turned 21?"),
    )
    marks = mark_exceptions(inv, c)
    assert [m["finding_id"] for m in marks] == ["f2", "f3", "f4"]  # f1 is not an exception question
    assert [m["relevant"] for m in marks] == [False, False, None]
    assert [m["state"] for m in marks] == ["not_relevant", "not_relevant", "unchecked"]
    assert "under 21" in marks[0]["reason"] and "Long-term Care" in marks[1]["reason"]
    assert marks[2]["status"] == "not_settled" and "no verified quote" in marks[2]["reason"]
    assert set(marks[0]) == {"finding_id", "question", "status", "state", "relevant", "reason", "named"}
    # nothing is hidden: the investigation is not changed
    assert "exception" not in inv["findings"][1]


def test_an_exception_quote_that_contains_the_rule_quote_is_not_a_restatement():
    """dc-018 (evaluator re-check): the exclusion bullet "Eyeglasses or contact lenses." (fed-16 p7) sits inside the
    p8 exception quote. Only the exception quote inside a rule quote is a restatement, never the reverse."""
    c = {"card": card(program="medicare_b", member_age_group="65_plus", service="Eyeglass frames after cataract surgery",
                      denial_reason="Medicare does not cover eyeglasses or contact lenses."), "summary": None}
    inv = investigation(
        finding("f1", "exclusions", "supported", "Medicare does not cover eyeglasses.", [cite("fed-16", 7, "Eyeglasses or contact lenses.")], jurisdiction="Federal"),
        finding("f2", "exclusions", "supported", "One pair after each cataract surgery with a lens.", [cite("fed-16", 8, CATARACT)], jurisdiction="Federal",
                question="Is there an exception under Medicare Part B that covers eyeglass frames after cataract surgery?"),
    )
    m = mark_exceptions(inv, c)[0]
    assert m["state"] == "relevant" and m["named"] == ["cataract surgery"]


def test_one_relevant_citation_makes_the_finding_relevant():
    c = {"card": card(program="medicare_b", member_age_group="65_plus", service="Eyeglass frames after cataract surgery",
                      denial_reason="Medicare does not cover eyeglasses or contact lenses."), "summary": None}
    inv = investigation(finding("f7", "exclusions", "supported", "One pair after cataract surgery.",
                                [cite("fed-16", 7, "Eyeglasses or contact lenses."), cite("fed-16", 8, CATARACT)], jurisdiction="Federal",
                                question="Is there an exception under Medicare Part B that covers eyeglass frames after cataract surgery?"))
    m = mark_exceptions(inv, c)[0]
    assert m["relevant"] is True and m["named"] == ["cataract surgery"]

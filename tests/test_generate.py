import json

from policyqa.generate import enforce_citations, parse_model_json, ABSTAIN_TEXT

PASSAGES = [
    {"tag": "P1", "doc_id": "fl-03", "page": 5, "title": "t", "jurisdiction": "Florida", "text": "Florida Medicaid covers up to four intermittent home health visits per day for recipients under the age of 21 years. Visits must be medically necessary."},
    {"tag": "P2", "doc_id": "fed-24", "page": 6, "title": "t", "jurisdiction": "Federal", "text": "Medicare covers part-time or intermittent skilled nursing care."},
]


def test_valid_citation_is_kept():
    data = {"answer": "Up to four visits a day for children under 21.", "abstain": False, "citations": [{"passage": "P1", "quote": "up to four intermittent home health visits per day for recipients under the age of 21 years"}]}
    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, PASSAGES)
    assert not abst and not forced and dropped == 0 and len(kept) == 1
    assert kept[0].doc_id == "fl-03" and kept[0].page == 5


def test_fabricated_quote_is_dropped_and_answer_becomes_abstention():
    data = {"answer": "Six visits a day.", "abstain": False, "citations": [{"passage": "P1", "quote": "Florida Medicaid covers six home health visits per day for everyone"}]}
    ans, abst, kept, proposed, dropped, forced = enforce_citations(data, PASSAGES)
    assert abst and forced and dropped == 1 and kept == [] and ans == ABSTAIN_TEXT


def test_citation_to_unknown_passage_is_dropped():
    data = {"answer": "x", "abstain": False, "citations": [{"passage": "P9", "quote": "Medicare covers part-time or intermittent skilled nursing care."}]}
    _, abst, kept, _, dropped, _ = enforce_citations(data, PASSAGES)
    assert dropped == 1 and abst


def test_explicit_abstention_clears_citations():
    data = {"answer": "Not covered by the corpus.", "abstain": True, "citations": [{"passage": "P1", "quote": "Visits must be medically necessary."}]}
    ans, abst, kept, _, _, forced = enforce_citations(data, PASSAGES)
    assert abst and not forced and kept == [] and ans == ABSTAIN_TEXT


def test_bracketed_tag_and_lowercase_are_accepted():
    data = {"answer": "x", "abstain": False, "citations": [{"passage": "[p2]", "quote": "Medicare covers part-time or intermittent skilled nursing care."}]}
    _, abst, kept, _, _, _ = enforce_citations(data, PASSAGES)
    assert not abst and kept[0].doc_id == "fed-24"


def test_parse_model_json_handles_fences_and_prose():
    obj = {"answer": "a", "abstain": False, "citations": []}
    assert parse_model_json(json.dumps(obj)) == obj
    assert parse_model_json("```json\n" + json.dumps(obj) + "\n```") == obj
    assert parse_model_json("Here you go: " + json.dumps(obj) + " hope that helps") == obj

"""Exception relevance: an exception counts against the letter only when its quoted words name the letter's fact.

Oct 27, second tuning pass. The exception question (investigate.exception_question) finds real exceptions
somewhere in a document; dc-002 and dc-003 were consistent denials that the verdict then called inconsistent,
treating "an exception exists" as "the exception covers this letter". This module is the code check, with no
model call: does a verified quote name a fact the letter states?

The letter's facts (letter_facts) come from the case card and the intake summary, never from the raw letter:
- the service field's qualifiers: the words after a cue (after, following, during, post, prescribed for,
  prescribed to treat, ordered for, to treat, for the treatment of, indicated for, diagnosed with, "the
  prescription says it is for", "the drug is for"), and a parenthesis of two words or more ("Eyeglass frames
  after cataract surgery" gives "cataract surgery"; "Azelaic acid 15% gel, prescribed for rosacea" gives
  "rosacea"; "visit (second visit of the day)" gives "second visit of the day"; "post-cataract surgery" gives
  "cataract surgery"). A one-word parenthesis is the service's other name ("(BIPAP)", "(bridge)") and a comma
  tail is a service attribute ("rental", "12 hours per day"); neither is a fact;
- the same cues in the intake summary, unless every word of the phrase is also in the stated reason (the
  summary restating the payer's rule is not a fact of the claim);
- other coverage: for a member with Medicare and Medicaid (investigate.medicare_and_medicaid), the QMB program
  when the letter names it ("QMB", "Qualified Medicare Beneficiary");
- the member's age group, used only as a check against the quote (below), never as a match on its own.
A fact must be specific (fix round after the evaluation, Oct 27): it needs at least one content word that is
neither generic (GENERIC: member, plan, Medicare, Medicaid, service...) nor a word of the payer's process
(PROCESS: review, medical records, determination, request...), and a one-word fact must not be a verb form
ending in -ing or -ed. So "joining" (dc-027, "after joining the plan"), "review of the medical records"
(dc-023) and the other program's name alone ("Medicare" for an LTC member, dc-012; "Medicaid" for a dual
member) are not facts. A one-word fact is allowed when it passes ("rosacea", "tracheostomy"): a two-word
minimum would have dropped dc-026's rosacea, the control case.
Deliberately not facts: the service name itself (the exclusion and its exception are both about the service,
so naming it proves nothing: dc-003's "three visits a day" names home health visits) and the stated reason's
terms (they are the rule's own words, which an exclusion and its exception share: "cosmetic" in dc-025 and
dc-026). Member names, amounts and dates carry no cue and are not picked up.

The rule (quote_relevance) gives one of three states, in order:
1. "not_relevant" when the quote names an age group and none of the groups it names includes the member
   (under 21 against a member 21 or older: dc-002). This holds with or without other facts.
2. "not_relevant" when the citation's document (its title, from the manifest, not from the model) is about
   another program than the member's (the Long-term Care program against an MMA member: dc-002, fl-16 p8).
3. "unchecked" when the letter states no specific fact (above): the quote cannot be judged, so nothing may
   say it fails (dc-022 emergency care regardless of network, dc-027 a transition supply: both right on Oct 27).
4. "relevant" when the quote names at least one fact; otherwise "not_relevant".
Matching: tokens are textnorm.tokens (lower case, punctuation folded, stop words dropped); plural forms match
("surgeries" and "surgery", "QMBs" and "QMB"). A fact is named when every one of its words is in the quote,
or when the quote has the fact's initials (three letters or more: "CABG" for coronary artery bypass graft).
Facts keep at most four content words.

Exception findings (mark_exceptions) are the planner's exception or QMB question, recognised by the question
(is_exception_finding), not by topic: the QMB question has topic "other", and "What exclusions apply" has
topic "exclusions" without being an exception question. A quote of an exception finding that a supported
non-exception finding also quotes (4-gram overlap 0.8) is the rule itself, not an exception (dc-001 shape: the
exception question came back with the 24-hour rule) and is "unchecked", never "not_relevant".

How the verdict uses it (verdict.verdict_from_data): every state is shown to the model; only "not_relevant"
carries "do not rely on it". The guard turns an inconsistent outcome that the model says relies on an
exception into not_settled by the exception relied on (Oct 29, dc-008): the cited exception quotes count, each
judged on its own (cited_exception_relevance), or every cited quote when no exception finding is cited, and the
guard fires only when every counted quote is "not_relevant". Relevance is necessary, not sufficient: a relevant exception may still not
cover the claim (a spouse's surgery reads as "names the fact"); the verdict decides that.

Known limits (evaluator, Oct 27; not fixed tonight):
- Synonyms are not matched: "cataract extraction" or "cataract operation" against "cataract surgery"; "new
  plan" against "joining the plan".
- A bare "for <condition>" in the summary ("for her rosacea") and "because she had cataract surgery" carry no
  cue, so the fact is missed when the card's service field lacks it ("for" alone is too broad: "for 12 hours",
  "for A. Sample").
- The program check sees only document titles that name a program (Long-term Care, KidCare): the MMA contract
  fl-21 can hold LTC content under an MMA title.
- An age word in passing ("unlike adult day care") reads as an age group.
- QMB facts need the word QMB or "Qualified Medicare Beneficiary" in the card or summary; a dual member named
  only by both program names is unchecked (the QMB rule is then left to the model, never guarded).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .textnorm import STOP, norm, tokens

MAX_FACT_WORDS = 4
MIN_INITIALS = 3

# Words that never make a fact: the letter's and the policy's generic vocabulary, and the sample names the
# cases use ("A. Sample"). Units (day, hour) stay: "second visit of the day" needs both words.
GENERIC = set(
    """member members recipient recipients enrollee enrollees patient patients person people beneficiary beneficiaries
    service services covered cover covers coverage plan plans program programs policy policies letter letters payer
    denied deny denies denial claim claims request requested requests approved approve billed bill amount sample
    medicare medicaid florida part provider providers doctor physician also only says said
    you your yours my our we us i he she him his her their appeal appeals grievance hearing""".split()
)
# Words of the payer's process, not of the claim: a phrase made only of these is not a fact (dc-023, "after
# review of the medical records").
PROCESS = set(
    """review reviewed reviews record records medical note notes determination decision decisions documentation document
    documents information request requests approval authorization enrollment assessment evaluation notice file date dates""".split()
)

_CUE = re.compile(
    r"\b(?:after|following|during|prescribed\s+(?:for|to\s+treat)|ordered\s+(?:for|after)|to\s+treat|for\s+the\s+treatment\s+of|indicated\s+for|diagnosed\s+with"
    r"|says\s+(?:(?:it|the\s+drug|this\s+drug)\s+)?is\s+for|(?:drug|medication|medicine|prescription)\s+(?:is|was)\s+for|post(?:-|\s+))\b",
    re.I,
)
# A fact phrase ends at punctuation or at one of these words.
_BOUNDARY = re.compile(
    r"[.,;:()\[\]\n]|\b(?:and|but|or|which|that|because|so|while|with|when|on|in|from|to|before|by|was|were|is|are|has|had|who|where|than|you|we|they|he|she|it)\b",
    re.I,
)

# Age groups a quote can name, and which groups include a member of each card age group.
_UNDER_21 = re.compile(r"\b(?:under|below|younger\s+than)\s+(?:the\s+)?(?:age\s+(?:of\s+)?)?21\b", re.I)
_ADULT = re.compile(r"\b21\s+(?:years\s+)?(?:of\s+age\s+)?(?:and|or)\s+(?:older|over)\b|\badults?\b", re.I)
_SENIOR = re.compile(r"\b65\s+(?:years\s+)?(?:of\s+age\s+)?(?:and|or)\s+(?:older|over)\b|\bage\s+65\b", re.I)
AGE_PATTERNS = {"under_21": _UNDER_21, "adult": _ADULT, "65_plus": _SENIOR}
AGE_LABELS = {"under_21": "under 21", "adult": "21 or older", "65_plus": "65 or older"}
AGE_INCLUDES = {"under_21": {"under_21"}, "adult": {"adult"}, "65_plus": {"adult", "65_plus"}}
# Age words are stripped from fact phrases: the age is checked on its own (rule 2).
_AGE_WORDS = re.compile(_UNDER_21.pattern + "|" + _ADULT.pattern + "|" + _SENIOR.pattern + r"|\bturned\s+\d+\b|\b\d+\s+years?\s+old\b|\baged?\s+\d+\b", re.I)

# A document about one Florida program, from its manifest title.
_DOC_PROGRAMS = (
    ("florida_medicaid_ltc", re.compile(r"long-term care|\bLTC\b", re.I)),
    ("florida_kidcare", re.compile(r"kidcare|healthy kids", re.I)),
)
_QMB_TEXT = re.compile(r"\bQMB\b|qualified medicare beneficiar", re.I)
# The same two patterns investigate.py uses to recognise the second-rule question (_asks_second_rule).
_EXCEPTION_Q = re.compile(r"\bexcept", re.I)
_DUAL_Q = re.compile(r"\bQMB\b|qualified medicare beneficiar|cost.sharing", re.I)


@dataclass(frozen=True)
class Fact:
    label: str  # the words as the letter says them, for the reader
    words: tuple[str, ...]  # content words, every one must be in the quote
    source: str  # "service", "summary", or "coverage"


@dataclass(frozen=True)
class LetterFacts:
    facts: tuple[Fact, ...]
    age_group: str | None
    program: str | None


def _cell(card, field: str):
    cell = card.get(field) if isinstance(card, dict) else None
    return cell.get("value") if isinstance(cell, dict) else cell


def _keys(word: str) -> set[str]:
    """The forms a word matches: itself and its singular (surgeries/surgery, lenses/lens, QMBs/QMB)."""
    out = {word}
    if word.endswith("ies") and len(word) > 4:
        out.add(word[:-3] + "y")
    if word.endswith("es") and len(word) > 4:
        out.add(word[:-2])
    if word.endswith("s") and len(word) > 3:
        out.add(word[:-1])
    return out


def _content_words(text: str) -> list[str]:
    return [t for t in tokens(_AGE_WORDS.sub(" ", text)) if t not in GENERIC and t not in STOP]


def _fact(phrase: str, source: str) -> Fact | None:
    """A Fact, or None when the phrase fails the minimum (see the module docstring, "A fact must be specific")."""
    words = _content_words(phrase)[:MAX_FACT_WORDS]
    if not any(re.search(r"[a-z]", w) and w not in PROCESS for w in words):
        return None  # only numbers or process words: "review of the medical records"
    if len(words) == 1 and re.search(r"(?:ing|ed)$", words[0]):
        return None  # a single verb form: "joining" (dc-027, "after joining the plan")
    shown = norm(_AGE_WORDS.sub(" ", phrase)).split()
    last = max((i for i, w in enumerate(shown) if words[-1] in tokens(w)), default=len(shown) - 1)  # the label ends at the last word kept
    return Fact(label=" ".join(shown[: last + 1]), words=tuple(words), source=source)


def _cue_phrases(text: str) -> list[str]:
    out = []
    for m in _CUE.finditer(text or ""):
        rest = text[m.end():]
        b = _BOUNDARY.search(rest)
        phrase = rest[: b.start()] if b else rest
        phrase = re.sub(r"^\s*(?:the|a|an|each|his|her|their|two|one)\s+", "", phrase.strip(), flags=re.I)
        if phrase:
            out.append(phrase)
    return out


def _service_phrases(service: str) -> list[str]:
    """Qualifier phrases of the service field: cue phrases, and the parts of a parenthesis that have two words or more."""
    out = list(_cue_phrases(service))
    for inside in re.findall(r"\(([^)]*)\)", service):
        if _CUE.search(inside):
            continue
        out += [p.strip() for p in re.split(r"[,;]", inside) if len(p.split()) >= 2]
    return out


def letter_facts(card, summary: str | None = None, program: str | None = None) -> LetterFacts:
    """The letter's facts an exception could turn on (see the module docstring)."""
    from .investigate import medicare_and_medicaid

    service = str(_cell(card, "service") or "")
    reason_keys = {k for w in _content_words(str(_cell(card, "denial_reason") or "")) for k in _keys(w)}
    program = program or _cell(card, "program")
    found: list[Fact] = []
    for phrase in _service_phrases(service):
        f = _fact(phrase, "service")
        if f:
            found.append(f)
    for phrase in _cue_phrases(str(summary or "")):
        f = _fact(phrase, "summary")
        if f and not all(_keys(w) & reason_keys for w in f.words):
            found.append(f)
    if medicare_and_medicaid(card, summary):
        # The other program's name alone is not a fact (fix round: "Medicare" for an LTC member, dc-012, and any
        # Medicaid sentence for a dual member matched it). The QMB program, when the letter names it, is.
        text = " ".join(str(_cell(card, f) or "") for f in ("payer_name", "service", "denial_reason")) + " " + str(summary or "")
        if _QMB_TEXT.search(text):
            found.append(Fact("QMB", ("qmb",), "coverage"))
            found.append(Fact("Qualified Medicare Beneficiary", ("qualified", "medicare", "beneficiary"), "coverage"))
    seen, facts = set(), []
    for f in found:
        if f.words not in seen:
            seen.add(f.words)
            facts.append(f)
    age = _cell(card, "member_age_group")
    return LetterFacts(tuple(facts), age if age in AGE_LABELS else None, program)


def _named(fact: Fact, quote_words: list[str], quote_keys: set[str]) -> bool:
    if all(_keys(w) & quote_keys for w in fact.words):
        return True
    if len(fact.words) >= MIN_INITIALS:
        initials = "".join(w[0] for w in fact.words)
        return any(initials in _keys(w) for w in quote_words)
    return False


def _doc_program(title: str | None) -> str | None:
    for program, pattern in _DOC_PROGRAMS:
        if title and pattern.search(title):
            return program
    return None


STATES = ("relevant", "not_relevant", "unchecked")
NO_FACT_REASON = "the letter states no specific fact an exception could turn on (a procedure, what the drug is for, a program such as QMB), so the quote could not be checked against one"


def _result(state: str, reason: str, named: list[str] | None = None) -> dict:
    """state is one of STATES; relevant is True, False, or None (unchecked)."""
    return {"state": state, "relevant": {"relevant": True, "not_relevant": False}.get(state), "reason": reason, "named": list(named or [])}


def quote_relevance(quote: str | None, facts: LetterFacts, title: str | None = None) -> dict:
    """{"state", "relevant", "reason", "named"} for one verified quote (see the module docstring for the rule)."""
    from .investigate import program_label

    quote = str(quote or "").strip()
    if not quote:
        return _result("unchecked", "it has no verified quote")
    if facts.age_group:
        groups = [g for g, p in AGE_PATTERNS.items() if p.search(quote)]
        if groups and not set(groups) & AGE_INCLUDES[facts.age_group]:
            named = " and ".join(AGE_LABELS[g] for g in groups)
            return _result("not_relevant", f"it is for members {named}, and the member is {AGE_LABELS[facts.age_group]}")
    doc_program = _doc_program(title)
    if doc_program and facts.program and facts.program != "unknown" and doc_program != facts.program:
        return _result("not_relevant", f"it comes from a document about the {program_label(doc_program).replace('Florida Medicaid ', '')} program ({title}), and the member's program is {program_label(facts.program)}")
    if not facts.facts:
        return _result("unchecked", NO_FACT_REASON)
    words = tokens(quote)
    keys = {k for w in words for k in _keys(w)}
    named = [f.label for f in facts.facts if _named(f, words, keys)]
    if named:
        return _result("relevant", "it names the letter's fact: " + "; ".join(f'"{n}"' for n in named), named)
    checked = "; ".join(f'"{f.label}"' for f in facts.facts)
    return _result("not_relevant", f"it names none of the letter's facts (checked: {checked})")


def is_exception_finding(finding) -> bool:
    """True for the planner's second-rule question: an exception question, or the QMB cost-sharing question."""
    q = str((finding or {}).get("question") or "")
    return bool(_EXCEPTION_Q.search(q) or _DUAL_Q.search(q))


def case_letter_facts(case: dict) -> LetterFacts:
    route = case.get("route") if isinstance(case.get("route"), dict) else {}
    card = case.get("card") or {}
    return letter_facts(card, case.get("summary"), _cell(card, "program") or route.get("program"))


RESTATED_OVERLAP = 0.8  # the verdict's own quote threshold (verdict.QUOTE_THRESHOLD)


def _restates(quote: str, rule_quotes: list[tuple[str, str]]) -> str | None:
    """The id of a non-exception finding that quotes the same text, or None."""
    from .textnorm import quote_overlap

    for fid, other in rule_quotes:
        # One direction only: the exception quote inside the rule quote. A rule quote inside the exception quote is
        # not a restatement (dc-018: "Eyeglasses or contact lenses." sits inside the p8 cataract exception).
        if quote_overlap(quote, other) >= RESTATED_OVERLAP:
            return fid
    return None


def mark_exceptions(investigation, case: dict) -> list[dict]:
    """One mark per exception finding, in finding order: {finding_id, question, status, state, relevant, reason, named}.

    A finding is "relevant" when one of its verified quotes is, else "not_relevant" when one of them fails the
    check (an age group or program contradiction, or a case with facts that the quote does not name), else
    "unchecked": no verified quote, a case with no specific fact, or every quote is a rule that a supported
    non-exception finding also quotes (dc-001 shape: the exception question came back with the 24-hour rule
    itself; that is the rule, not an exception failing the test). The investigation itself is not changed."""
    facts = case_letter_facts(case or {})
    findings = [f for f in (investigation or {}).get("findings") or [] if isinstance(f, dict)]
    rule_quotes = [(f.get("id"), str(c.get("quote") or "")) for f in findings
                   if f.get("status") == "supported" and not is_exception_finding(f) for c in f.get("citations") or []]
    out = []
    for f in findings:
        if not is_exception_finding(f):
            continue
        mark = {"finding_id": f.get("id"), "question": f.get("question"), "status": f.get("status")}
        cites = (f.get("citations") or []) if f.get("status") == "supported" else []
        if not cites:
            out.append({**mark, **_result("unchecked", f"no verified quote (status {f.get('status')})")})
            continue
        results = []
        for c in cites:
            same = _restates(str(c.get("quote") or ""), rule_quotes)
            results.append(_result("unchecked", f"it quotes the same rule as {same}, so it is the rule, not an exception") if same
                           else quote_relevance(c.get("quote"), facts, c.get("title")))
        chosen = next((r for r in results if r["state"] == "relevant"), None) or next((r for r in results if r["state"] == "not_relevant"), None) or results[0]
        out.append({**mark, **chosen})
    return out


def cited_exception_relevance(refs, investigation, case: dict) -> list[dict]:
    """One {finding_id, quote, state, reason} per CitationRef that comes from an exception finding, in order (Oct 29,
    fix round): "unchecked" when the quote restates a supported non-exception finding's quote (as in mark_exceptions),
    else quote_relevance of that quote with the case's facts and the citation's title. The quote the model cited is
    judged, not the best quote of its finding."""
    facts = case_letter_facts(case or {})
    findings = [f for f in (investigation or {}).get("findings") or [] if isinstance(f, dict)]
    exc_ids = {f.get("id") for f in findings if is_exception_finding(f)}
    rule_quotes = [(f.get("id"), str(c.get("quote") or "")) for f in findings
                   if f.get("status") == "supported" and not is_exception_finding(f) for c in f.get("citations") or []]
    out = []
    for r in refs or []:
        if r.get("finding_id") not in exc_ids:
            continue
        quote = str(r.get("quote") or "")
        same = _restates(quote, rule_quotes)
        res = _result("unchecked", f"it quotes the same rule as {same}, so it is the rule, not an exception") if same else quote_relevance(quote, facts, r.get("title"))
        out.append({"finding_id": r.get("finding_id"), "quote": quote, "state": res["state"], "reason": res["reason"]})
    return out


def citation_relevance(refs, case: dict) -> list[dict]:
    """quote_relevance for each CitationRef ({finding_id, doc_id, title, page, quote}), in order."""
    facts = case_letter_facts(case or {})
    return [{"finding_id": r.get("finding_id"), **quote_relevance(r.get("quote"), facts, r.get("title"))} for r in refs or []]

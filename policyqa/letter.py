"""Action: the appeal letter, the evidence checklist, the deadline with day count, the filing path.

draft_letter(case, investigation, verdict, provider) makes one Muse Spark call
(`complete_parts`, strict schema) that writes the letter as paragraphs of sentences,
each {text, claim, citation: {finding_id, quote} | null}. The model sees the case card,
the letter's stated reason, the verdict (outcome, rule, gap) and the same findings block
as the verdict step: supported findings with verified quotes, the rest by question only.

verify_letter applies the rules that make the letter honest:
- a claim sentence (what a policy says, requires, limits, or allows) is `verified` only
  when its citation passes verdict.validate_ref; otherwise it is `struck` (kept in the
  record, shown struck, left out of letter_text) with a `reason`;
- a non-claim sentence (greeting, the letter's own facts, the request, the closing)
  carries no citation and is never struck for its citation;
- the one exception is the scope guardrail: a sentence that says the care was needed
  (MEDICAL_NEED) is struck whatever its flag, because Recourse never gives medical advice.

The deadline, the filing path and the evidence checklist are computed without the model
(compute_deadline, filing_path, evidence_checklist) from the card and the supported
findings, each item carrying the finding's citation. A `consistent` verdict makes no model
call: `applicable: false`, `explanation` in plain words, no paragraphs. A model failure
(error, truncation, bad JSON) gives a template letter built from the verdict's verified
rule, with `error` set; only an exception outside these steps fails the stage (api/main.py).

Letter shape: {status, applicable, explanation, to, re, paragraphs: [{sentences: [{text,
claim, citation, verified, struck, reason}]}], evidence_checklist: [{item, why, citation}],
evidence_note, deadline: {date, days_left, source, citation, note}, filing: {where, how,
citation}, verification: {claims, verified, struck}, model, input_tokens, output_tokens,
reasoning_tokens, latency_ms, cost_usd, error}.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta

from .generate import parse_model_json, reasoning_tokens
from .textnorm import tokens
from .verdict import (
    _meta,
    card_value,
    case_facts,
    citation_ref,
    findings_block,
    supported_findings,
    validate_ref,
)

LETTER_MAX_TOKENS = 10000  # reasoning model; a letter of 10 to 16 sentences plus its thinking
MIN_ITEMS, MAX_ITEMS = 3, 7
NY_TZ = "America/New_York"

DEADLINE_LETTER_NOTE = "The letter states this deadline."
DEADLINE_UNKNOWN_NOTE = "Neither the letter nor the documents we found state a deadline. Check the letter and call the plan."
FILING_WHERE_UNKNOWN = "Not stated in the documents we found."
FILING_HOW_UNKNOWN = "Check the appeal section of the letter or call the number on it."
CHECKLIST_EMPTY_NOTE = "The documents we found do not state what the policy requires for this service, so no evidence checklist could be drawn from them."

STRUCK_NO_CITATION = "claim without a citation"
STRUCK_BAD_CITATION = "citation not found in the verified findings"
STRUCK_MEDICAL = "says whether the care was needed; Recourse never gives medical advice"

_CITATION = {
    "anyOf": [
        {"type": "object", "properties": {"finding_id": {"type": "string"}, "quote": {"type": "string"}}, "required": ["finding_id", "quote"], "additionalProperties": False},
        {"type": "null"},
    ]
}
LETTER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}, "claim": {"type": "boolean"}, "citation": _CITATION},
                            "required": ["text", "claim", "citation"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["sentences"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["paragraphs"],
    "additionalProperties": False,
}

LETTER_SYSTEM_PROMPT = """You draft an appeal letter from a health plan member (or the member's caregiver) to the plan that denied a service. You are given the case card (what the denial letter says), the letter's stated reason, the verdict with the governing rule and the gap, and the supported findings from public policy documents with their verified quotes.

Rules:
1. Plain, polite, firm English in the first person ("I am writing to appeal ..."), addressed to the plan. Three to five short paragraphs: (a) what is being appealed: the service, the dates of service, the letter date, and the stated reason; (b) what the policy says, one rule per sentence, from the supported findings; (c) why the stated reason does not match the rule; (d) the request: reverse the denial, or send the specific rule and the records used to decide; (e) the closing.
2. Split every paragraph into sentences. Set "claim": true on every sentence that states what a policy or rule says, covers, requires, limits, excludes, or allows. Every claim sentence carries a citation: the id of a supported finding (for example "f2") and a quote copied word for word from that finding's verified quotes. Sentences that only repeat the denial letter's own facts (service, dates, amounts, the stated reason), make the request, greet, or close are "claim": false with "citation": null.
3. Claims come only from the supported findings. Never cite a question listed as not settled. Never add a rule from outside knowledge. Citations are checked: a claim whose quote is not in the cited finding is struck out of the letter.
4. Never give medical advice. Do not say whether the care was needed, that it was medically necessary for this member, or anything about treatment, diagnosis, or the member's health. Argue only from the written rules and the denial letter's own facts. You may repeat what a rule says about medical necessity, as a rule, with its citation.
5. Do not invent facts: no names, member numbers, phone numbers, or addresses. Use placeholders in square brackets, such as [Your name], where the person must fill something in.
6. When the verdict is "The documents do not settle it.", do not claim the denial is wrong: ask the plan to review the denial, to name the rule it applied, and to send the documents it relied on.

Return JSON only, matching the schema: {"paragraphs": [{"sentences": [{"text": "...", "claim": false, "citation": null}, {"text": "...", "claim": true, "citation": {"finding_id": "f2", "quote": "..."}}]}]}"""

# Statements that the care was needed: the scope guardrail, applied to every sentence.
MEDICAL_NEED = re.compile(
    r"\b(care|services?|nursing|treatment|hours|therapy|visits?)\s+(is|are|was|were)\s+(medically\s+)?(necessary|needed|required|essential)\b"
    r"|\b(my child|my son|my daughter|my (?:husband|wife|mother|father)|the member|the patient|the child|i|he|she)\s+(really\s+)?(needs?|needed|requires?|required)\b",
    re.I,
)


# ---- small helpers --------------------------------------------------------------------


def _parse_date(v) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _long(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"  # portable: no %-d (Windows strftime lacks it)


def today_ny() -> date:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(NY_TZ)).date()
    except Exception:  # noqa: BLE001 - Windows without the tzdata package has no IANA database
        from datetime import timedelta, timezone

        # Eastern time without DST rules: at most one hour off at the day boundary, never a crash.
        return datetime.now(timezone(timedelta(hours=-5))).date()


def format_dates(v) -> str:
    """'2026-09-01/2026-09-30' -> 'September 1, 2026 through September 30, 2026'."""
    if not v:
        return "on file"
    parts = [p for p in str(v).split("/") if p]
    ds = [_parse_date(p) for p in parts]
    if ds and all(ds):
        return " through ".join(_long(d) for d in ds) if len(ds) == 2 and ds[0] != ds[1] else _long(ds[0])
    return str(v)


_MEMBER_REF = re.compile(r"\bmember\s*(?:id|identification number|number|no\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{3,})", re.I)


def member_reference(case: dict) -> str:
    m = _MEMBER_REF.search(str(case.get("raw_text") or ""))
    return m.group(1) if m else "on file"


def _jurisdiction_order(card) -> list[str]:
    program = str(card_value(card, "program") or "")
    if program.startswith("medicare_"):
        return ["Federal", "Florida"]
    return ["Florida", "Federal"]


def _appeal_findings(investigation, card=None) -> list[dict]:
    fs = [f for f in supported_findings(investigation) if f.get("topic") == "appeal"]
    order = _jurisdiction_order(card or {})
    return sorted(fs, key=lambda f: order.index(f.get("jurisdiction")) if f.get("jurisdiction") in order else len(order))


# ---- deadline ---------------------------------------------------------------------------

_NUMBER_WORDS = {"ten": 10, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45, "sixty": 60, "ninety": 90}
_DAYS = re.compile(r"\b(\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s*\)?\s+(business\s+|working\s+|calendar\s+)?days?\b", re.I)


def days_stated(text: str) -> int | None:
    """The first calendar-day count in a quote ('sixty (60) days', 'within 120 days'); business days do not count."""
    for m in _DAYS.finditer(text or ""):
        if m.group(2) and m.group(2).strip().lower() in ("business", "working"):
            continue
        raw = m.group(1).lower()
        n = int(raw) if raw.isdigit() else _NUMBER_WORDS.get(raw)
        if n:
            return n
    return None


def compute_deadline(card, investigation, today: date | None = None) -> dict:
    today = today or today_ny()
    claimed = _parse_date(card_value(card, "appeal_deadline_claimed"))
    if claimed:
        return {"date": claimed.isoformat(), "days_left": (claimed - today).days, "source": "letter", "citation": None, "note": DEADLINE_LETTER_NOTE}
    for f in _appeal_findings(investigation, card):
        for c in f.get("citations") or []:
            n = days_stated(str(c.get("quote") or ""))
            if not n:
                continue
            ref = citation_ref(f, c)
            sent = _parse_date(card_value(card, "letter_date"))
            if sent is None:
                return {"date": None, "days_left": None, "source": "policy", "citation": ref, "note": f"The letter does not state a deadline. The policy allows {n} days, but the letter date is missing, so the date could not be counted. Check the letter."}
            due = sent + timedelta(days=n)
            return {
                "date": due.isoformat(),
                "days_left": (due - today).days,
                "source": "policy",
                "citation": ref,
                "note": f"The letter does not state a deadline. The policy allows {n} days; this date counts {n} days from the letter date, {_long(sent)}. Check the letter in case the clock starts on another day.",
            }
    return {"date": None, "days_left": None, "source": "unknown", "citation": None, "note": DEADLINE_UNKNOWN_NOTE}


# ---- filing path -------------------------------------------------------------------------

_NEGATION = re.compile(r"\b(do|does|did)\s+not\s+(state|say|name|specify|describe)\b|\bnot\s+stated\b|\bnot\s+specified\b", re.I)
_WHERE = re.compile(r"\b(appeal|file[sd]?|filing|submit(?:s|ted)?|send|sent|mail(?:ed)?|request(?:s|ed)?|ask(?:s|ed)?\s+for)\b[^.]{0,80}?\b(with|to|at)\s+(the|your|a|an)\b", re.I)
_HOW = re.compile(r"\b(in writing|orally|by (?:phone|telephone|mail|fax|e-?mail)|online|written request|form\b|call(?:ing)?\b)", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _best_citation(f: dict, sentence: str) -> dict:
    words = set(tokens(sentence))
    cs = f.get("citations") or []
    best = max(cs, key=lambda c: len(words & set(tokens(str(c.get("quote") or "")))))
    return citation_ref(f, best)


def filing_path(investigation, card=None) -> dict:
    where = how = None
    citation = None
    for f in _appeal_findings(investigation, card):
        for sent in _SENTENCE.split(str(f.get("answer") or "").strip()):
            sent = sent.strip()
            if not sent or _NEGATION.search(sent):
                continue
            if where is None and _WHERE.search(sent):
                where = sent
                citation = citation or _best_citation(f, sent)
            if how is None and _HOW.search(sent):
                how = sent
                citation = citation or _best_citation(f, sent)
        if where or how:
            break
    if not (where or how):
        return {"where": FILING_WHERE_UNKNOWN, "how": FILING_HOW_UNKNOWN, "citation": None}
    return {"where": where or FILING_WHERE_UNKNOWN, "how": how or FILING_HOW_UNKNOWN, "citation": citation}


# ---- evidence checklist ------------------------------------------------------------------

# (pattern on a verified quote, item, why). Documents, never statements about the care itself.
_EVIDENCE_RULES = [
    (re.compile(r"\bprior authori[sz]|\bauthori[sz](ation|ed)\b", re.I), "The plan's authorization notice for this service, showing the hours or units approved and their dates", "The policy ties payment to what the plan authorizes, so the appeal should show exactly what was approved."),
    (re.compile(r"\bplan of care\b|\bPOC\b"), "The plan of care that covers the dates of service", "The policy refers to an approved plan of care."),
    (re.compile(r"\border(s|ed)?\b|\bprescribed\b", re.I), "The written order for the service from the treating practitioner", "The policy refers to the order for services."),
    (re.compile(r"\bhours?\b|\bper day\b|\bunits?\b|\bvisits?\b", re.I), "A day-by-day record of the hours requested, approved, and billed for the dates of service", "The policy sets its limits in hours, so the appeal should show the hours for each day."),
    (re.compile(r"medically necessary|medical necessity", re.I), "The provider's records that address the policy's medical necessity standard", "The policy lets the plan approve services that meet its medical necessity standard, and the plan decides that from the provider's records."),
    (re.compile(r"under the age of (21|twenty)|under 21|younger than 21", re.I), "Proof of the member's age", "Some rules in the policy apply only to recipients under 21."),
    (re.compile(r"\bcase management\b", re.I), "Notes from the plan's case manager, if one was assigned", "The documents require the plan to provide case management in some cases, and those notes may record what was approved."),
    (re.compile(r"\bcertif", re.I), "The doctor's certification for the service", "The policy refers to a certification."),
]
_PADDING = [
    ("A copy of the denial letter", "The appeal answers the reason and the dates the letter states."),
    ("The claim or billing record for the dates of service", "It shows the service code, the dates, and the amount the plan denied."),
]


def evidence_checklist(investigation) -> list[dict]:
    """3 to 7 items from the supported `conditions` and `limits` findings, each with the finding's citation; [] when there are none."""
    sources = [f for topic in ("conditions", "limits") for f in supported_findings(investigation) if f.get("topic") == topic]
    if not sources:
        return []
    items: list[dict] = []
    seen = set()
    for f in sources:
        for c in f.get("citations") or []:
            q = str(c.get("quote") or "")
            for pat, item, why in _EVIDENCE_RULES:
                if item not in seen and pat.search(q):
                    seen.add(item)
                    items.append({"item": item, "why": why, "citation": citation_ref(f, c)})
    items = items[:MAX_ITEMS]
    if not items:
        f = sources[0]
        items.append({"item": "The policy pages cited in this case", "why": "They hold the rules the appeal relies on.", "citation": citation_ref(f, f["citations"][0])})
    for item, why in _PADDING:
        if len(items) >= MIN_ITEMS:
            break
        items.append({"item": item, "why": why, "citation": None})
    return items


# ---- verification -----------------------------------------------------------------------


def verify_letter(letter: dict, investigation) -> dict:
    """Return a copy of `letter` whose sentences are verified or struck, with `verification` counts."""
    by_id = {f["id"]: f for f in supported_findings(investigation)}
    paragraphs = []
    claims = verified = struck = 0
    for p in letter.get("paragraphs") or []:
        sentences = p.get("sentences") if isinstance(p, dict) else None
        out = []
        for s in sentences or []:
            if not isinstance(s, dict):
                continue
            text = " ".join(str(s.get("text") or "").split())
            if not text:
                continue
            claim = bool(s.get("claim"))
            row = {"text": text, "claim": claim, "citation": None, "verified": False, "struck": False, "reason": None}
            if claim:
                claims += 1
                raw = s.get("citation")
                ref = validate_ref(raw, investigation, by_id) if raw else None
                if ref is not None:
                    row.update(citation=ref, verified=True)
                else:
                    row.update(struck=True, reason=STRUCK_BAD_CITATION if raw else STRUCK_NO_CITATION)
            if MEDICAL_NEED.search(text):
                row.update(struck=True, verified=False, citation=None, reason=STRUCK_MEDICAL)
            verified += row["verified"]
            struck += row["struck"]
            out.append(row)
        if out:
            paragraphs.append({"sentences": out})
    return {**letter, "paragraphs": paragraphs, "verification": {"claims": claims, "verified": verified, "struck": struck}}


def letter_text(letter: dict) -> str:
    """Plain text for export: struck sentences removed, '[cite: title, p. N]' after each verified claim."""
    if not letter.get("applicable", True):
        raise ValueError("no appeal letter: the denial matches the policy")
    lines = [f"To: {letter.get('to') or ''}", f"Re: {letter.get('re') or ''}", ""]
    for p in letter.get("paragraphs") or []:
        parts = []
        for s in p.get("sentences") or []:
            if s.get("struck"):
                continue
            t = s["text"]
            c = s.get("citation")
            if s.get("claim") and s.get("verified") and c:
                t += f" [cite: {c.get('title') or c.get('doc_id')}, p. {c.get('page')}]"
            parts.append(t)
        if parts:
            lines += [" ".join(parts), ""]
    return "\n".join(lines).rstrip() + "\n"


# ---- drafting ------------------------------------------------------------------------------


def _verdict_block(verdict: dict) -> str:
    rule = verdict.get("rule") or {}
    quotes = "\n".join(f'- [{c["finding_id"]}] "{c["quote"]}"' for c in rule.get("citations") or [])
    return (
        f"Verdict: {verdict.get('headline')}\n"
        f"Governing rule: {rule.get('statement')}\n"
        f"Rule citations:\n{quotes or '(none)'}\n"
        f"Gap: {verdict.get('gap')}"
    )


def letter_user_message(case: dict, investigation, verdict: dict) -> str:
    return case_facts(case.get("card") or {}) + "\n\n" + _verdict_block(verdict) + "\n\n" + findings_block(investigation) + "\n\nDraft the appeal letter. Return JSON only."


def consistent_explanation(verdict: dict) -> str:
    rule = (verdict.get("rule") or {}).get("statement") or ""
    return "\n\n".join(
        x
        for x in (
            f"What the rule says: {rule}",
            f"Why the denial matches it: {verdict.get('gap') or ''}".rstrip(": "),
            f"What would have made the service covered: {verdict.get('what_would_change') or ''}".rstrip(": "),
        )
        if x
    )


def _sentence(text: str, claim: bool = False, ref: dict | None = None) -> dict:
    return {"text": text, "claim": claim, "citation": {"finding_id": ref["finding_id"], "quote": ref["quote"]} if ref else None}


def _opening(case: dict) -> list[dict]:
    card = case.get("card") or {}
    payer = card_value(card, "payer_name") or "plan"
    service = card_value(card, "service") or "the service"
    sent = _parse_date(card_value(card, "letter_date"))
    reason = card_value(card, "denial_reason")
    out = [
        {"sentences": [_sentence(f"Dear {payer} appeals team,")]},
        {"sentences": [_sentence(f"I am writing to appeal your denial of {service} for dates of service {format_dates(card_value(card, 'dates_of_service'))}.")]
         + ([_sentence(f'Your letter dated {_long(sent)} gives this reason: "{reason}"')] if sent and reason else [])},
    ]
    return out


def _closing(outcome: str) -> list[dict]:
    if outcome == "not_settled":
        ask = "I ask you to review this denial, to tell me the specific rule you applied, and to send me the documents and records you relied on."
    else:
        ask = "I ask you to reverse this denial, or to send me the specific rule and the records you used to decide."
    return [{"sentences": [_sentence(ask)]}, {"sentences": [_sentence("Sincerely,"), _sentence("[Your name]")]}]


def template_paragraphs(case: dict, verdict: dict) -> list[dict]:
    """A letter from the verdict's verified rule only: used when the model step fails."""
    rule = verdict.get("rule") or {}
    refs = rule.get("citations") or []
    middle = []
    if refs and verdict.get("outcome") != "not_settled":
        body = [_sentence(rule.get("statement") or "", True, refs[0])]
        if verdict.get("gap"):
            body.append(_sentence(verdict["gap"], True, refs[-1]))
        middle = [{"sentences": body}]
    return _opening(case) + middle + _closing(verdict.get("outcome") or "not_settled")


def empty_letter(model: str, status: str = "running", error: str | None = None) -> dict:
    """The letter while it is drafted, or after an exception outside the model step: every key, no content."""
    return {
        "status": status, "applicable": None, "explanation": None, "to": None, "re": None, "paragraphs": [],
        "evidence_checklist": [], "evidence_note": None, "deadline": None, "filing": None,
        "verification": {"claims": 0, "verified": 0, "struck": 0}, **_meta(model, error=error),
    }


def _base(case: dict, investigation, today: date | None) -> dict:
    card = case.get("card") or {}
    items = evidence_checklist(investigation)
    return {
        "status": "done",
        "applicable": True,
        "explanation": None,
        "to": card_value(card, "payer_name") or "The health plan",
        "re": f"Appeal of the denial of {card_value(card, 'service') or 'the service'} for dates of service {format_dates(card_value(card, 'dates_of_service'))}, member {member_reference(case)}",
        "paragraphs": [],
        "evidence_checklist": items,
        "evidence_note": None if items else CHECKLIST_EMPTY_NOTE,
        "deadline": compute_deadline(card, investigation, today=today),
        "filing": filing_path(investigation, card),
        "verification": {"claims": 0, "verified": 0, "struck": 0},
    }


def assemble_letter(case: dict, investigation, verdict: dict, paragraphs: list | None, meta: dict, today: date | None = None) -> dict:
    letter = {**_base(case, investigation, today), **meta}
    if verdict.get("outcome") == "consistent":
        letter.update(applicable=False, explanation=consistent_explanation(verdict))
        return letter
    letter["paragraphs"] = paragraphs if paragraphs is not None else template_paragraphs(case, verdict)
    return verify_letter(letter, investigation)


def _usable_paragraphs(data) -> list:
    ps = data.get("paragraphs") if isinstance(data, dict) else None
    if not isinstance(ps, list) or not ps or not all(isinstance(p, dict) and isinstance(p.get("sentences"), list) for p in ps):
        raise ValueError("reply has no paragraphs of sentences")
    return ps


def draft_letter(case: dict, investigation, verdict: dict, provider, today: date | None = None) -> dict:
    model = getattr(provider, "model", "?")
    if verdict.get("outcome") == "consistent":
        return assemble_letter(case, investigation, verdict, [], _meta(model), today)
    t = time.perf_counter()
    reply = None
    try:
        text, n_in, n_out = provider.complete_parts(LETTER_SYSTEM_PROMPT, [{"type": "text", "text": letter_user_message(case, investigation, verdict)}], schema=LETTER_SCHEMA, max_tokens=LETTER_MAX_TOKENS)
        reply = (int(n_in or 0), int(n_out or 0))
        paragraphs, error = _usable_paragraphs(parse_model_json(text)), None
    except Exception as e:  # noqa: BLE001 - a template letter from the verified rule, with the reason recorded
        paragraphs, error = None, f"{type(e).__name__}: {e}"[:300]
    if reply:
        cost = getattr(provider, "cost", None)
        meta = _meta(model, reply[0], reply[1], reasoning_tokens(provider), (time.perf_counter() - t) * 1000, float(cost(*reply)) if callable(cost) else 0.0, error)
    else:
        meta = _meta(model, latency_ms=(time.perf_counter() - t) * 1000, error=error)
    return assemble_letter(case, investigation, verdict, paragraphs, meta, today)


class LiveLetter:
    """draft_letter bound to a provider (Muse Spark 1.3 through the Meta Model API)."""

    def __init__(self, provider):
        self.provider = provider
        self.model = getattr(provider, "model", "?")

    def draft(self, case: dict, investigation, verdict: dict, today: date | None = None) -> dict:
        return draft_letter(case, investigation, verdict, self.provider, today=today)


class FixtureLetter:
    """No network. A model-shaped letter for the Sunshine Health sample, verified like a real one.
    It cites the verdict's verified rule references and carries one claim with a paraphrased
    quote, so the screen can show a struck sentence. Marked as fixture in its first sentence."""

    model = "fixture"

    def __init__(self, delay: float = 0.8):
        self.delay = delay

    def paragraphs(self, case: dict, verdict: dict) -> list[dict]:
        refs = (verdict.get("rule") or {}).get("citations") or []
        head = [{"sentences": [_sentence("[Synthetic fixture letter for a software demonstration; not drafted by a model.]")]}]
        if not refs or verdict.get("outcome") != "inconsistent":
            return head + _opening(case) + _closing(verdict.get("outcome") or "not_settled")
        body = [
            _sentence("Florida Medicaid covers up to 24 hours of private duty nursing per day for a recipient who meets the policy's criteria.", True, refs[0]),
        ]
        if len(refs) > 1:
            body.append(_sentence("For a recipient under 21, services beyond the coverage described in the policy may be approved when medically necessary.", True, refs[1]))
        body.append({"text": "The policy also says the plan must pay for every hour a provider bills.", "claim": True, "citation": {"finding_id": refs[0]["finding_id"], "quote": "the plan must pay for every hour that a provider bills for the member"}})
        gap = [
            _sentence("Your letter treats the authorized amount as the limit, but the rule sets a higher ceiling and allows more hours to be approved.", True, refs[-1]),
        ]
        return head + _opening(case) + [{"sentences": body}, {"sentences": gap}] + _closing("inconsistent")

    def draft(self, case: dict, investigation, verdict: dict, today: date | None = None) -> dict:
        if self.delay:
            time.sleep(self.delay)
        paragraphs = json.loads(json.dumps(self.paragraphs(case, verdict)))
        return assemble_letter(case, investigation, verdict, paragraphs, _meta(self.model, latency_ms=self.delay * 1000), today)

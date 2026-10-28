"""Steelman and Verdict: the investigation's verified findings become one of three verdicts.

Steps (PRODUCT.md vocabulary): Steelman, then Verdict. One Muse Spark call
(`complete_parts` with a strict JSON schema) argues the payer's side first, states the
governing rule, and only then decides among the three outcomes. The model sees only:
the case card (not the raw letter), the letter's stated reason, the `supported`
findings (answer and verified quotes), and the questions of every other finding,
listed as "not settled by the documents".

Citations are checked, not trusted (validate_refs): a reference names a supported
finding and quotes it; the quote must reach 4-gram overlap 0.8 (textnorm.quote_overlap)
with one of that finding's kept citation quotes. doc_id, title, page and the quote
itself are then copied from that citation, never from the model. Invalid references
are dropped. A steelman or rule left with no valid citation keeps its text and is
marked `unsupported: true` (the screen strikes it); a rule with no valid citation also
turns the outcome into `not_settled`, and `proposed_outcome` keeps what the model said.

Failure: a model error, a truncated reply (TruncatedResponse) or bad JSON gives the
`not_settled` template with `error` set and status "done"; tokens of a reply that came
back but could not be used are still recorded. No supported finding at all gives the
same template without a model call and without an error.

Exceptions (Oct 27, second pass): the model sees a code check of every exception finding
(policyqa.relevance: does its verified quote name a fact the letter states?) and says whether
its outcome relies on an exception. Each exception is "relevant", "not_relevant" or
"unchecked" (the letter states no specific fact, or the quote is the rule itself). An
inconsistent outcome that relies on an exception, where no validated rule quote is relevant
and one is not_relevant, becomes `not_settled` (proposed_outcome keeps the model's call); an
unchecked case is never guarded. Nothing is hidden: the findings and the rule's citations stay.

Verdict shape: {status, steelman: {argument, citations, unsupported}, outcome,
proposed_outcome, headline, rule: {statement, citations, unsupported}, gap,
what_would_change, decisive_fact: {fact, settled_by} or null, relies_on_exception,
exceptions: [{finding_id, question, status, relevant, reason, named}], model,
input_tokens, output_tokens, reasoning_tokens, latency_ms, cost_usd, error}.
CitationRef: {finding_id, doc_id, title, page, quote}.

FixtureVerdict: no network. The Sunshine Health sample decided `inconsistent` with
synthetic text marked "[fixture]", citing the investigation's own supported findings
(limits first, then conditions, else coverage), each by the citation that carries the
sentence ("24 hours", "exceed"): f2 and f3 on the second live record, f2 and f1 on the
FixtureInvestigator (whose f3 is unsupported by design). It goes through the same
validation as a model reply.
"""
from __future__ import annotations

import json
import time

from .generate import parse_model_json, reasoning_tokens
from .textnorm import quote_overlap

OUTCOMES = ("consistent", "inconsistent", "not_settled")
HEADLINES = {
    "consistent": "The denial matches the policy.",
    "inconsistent": "The denial appears inconsistent with the policy.",
    "not_settled": "The documents do not settle it.",
}
VERDICT_MAX_TOKENS = 8000  # Muse Spark 1.3 reasons before it answers; thinking counts against this budget
QUOTE_THRESHOLD = 0.8
MIN_QUOTE_CHARS = 15
FIXTURE_MARK = "[fixture] "

DEFAULT_SETTLE = "A policy page that states the rule for this service and this reason, quoted word for word. You can ask the plan for a copy of the rule it used."
DEFAULT_COVERED = "The documents we found do not say what would have made this service covered. You can ask the plan which rule it applied and what it would need."
FALLBACK_GAP = "The rule this verdict would rest on could not be matched to a verified quote, so the documents we found do not settle the letter's reason."

# Who settles the fact the letter's reason turns on (Oct 27, the not-settled misses dc-009, dc-014, dc-017).
# The last two are open facts: a consistent or inconsistent outcome resting on one becomes not_settled.
SETTLED_BY = ("documents", "letter", "payer_determination", "outside_documents")
OPEN_FACT_GAPS = {
    "payer_determination": "The letter's reason rests on the plan's own determination, which the documents do not state: {fact}",
    "outside_documents": "The letter's reason rests on a rule or list outside these documents, so the documents do not state it: {fact}",
}

_REFS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"finding_id": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["finding_id", "quote"],
        "additionalProperties": False,
    },
}

# Property order matters to a model that writes in order: the steelman comes before the outcome.
VERDICT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "steelman": {
            "type": "object",
            "properties": {"argument": {"type": "string"}, "citations": _REFS},
            "required": ["argument", "citations"],
            "additionalProperties": False,
        },
        "rule": {
            "type": "object",
            "properties": {"statement": {"type": "string"}, "citations": _REFS},
            "required": ["statement", "citations"],
            "additionalProperties": False,
        },
        "decisive_fact": {
            "type": "object",
            "properties": {"fact": {"type": "string"}, "settled_by": {"type": "string", "enum": list(SETTLED_BY)}},
            "required": ["fact", "settled_by"],
            "additionalProperties": False,
        },
        "relies_on_exception": {"type": "boolean"},
        "outcome": {"type": "string", "enum": list(OUTCOMES)},
        "gap": {"type": "string"},
        "what_would_change": {"type": ["string", "null"]},
    },
    "required": ["steelman", "rule", "decisive_fact", "relies_on_exception", "outcome", "gap", "what_would_change"],
    "additionalProperties": False,
}

VERDICT_SYSTEM_PROMPT = f"""You decide whether a health coverage denial holds against the written policy. You are given a case card (what the denial letter says), the letter's stated reason for the denial, sometimes the letter's facts in plain words, and findings from an investigation of public Florida Medicaid and Medicare documents. Each supported finding has verified quotes. Questions listed as "not settled by the documents" have no verified quote and prove nothing either way: each is an open question.

Work in this order.
1. Steelman. First argue the payer's side: write the strongest honest case, in two to four plain sentences, that the denial follows the policy, using only the supported findings. Cite them.
2. Rule. State the rule that governs this service and this stated reason, in one or two plain sentences a reader with no insurance background understands. Cite it. When the letter cites an exclusion or a limit, look in the supported findings for an exception to it: policies often state an exclusion on one page and its exception on the next, or a second program's rule protects the member (for example a member in the Qualified Medicare Beneficiary (QMB) program cannot be billed Medicare cost-sharing). An exception that covers the letter's own facts is part of the rule. An exception counts against the letter only when its quoted words name the letter's own fact (the procedure or surgery, what the drug is for, the member's other coverage, the member's age group). The findings end with an exception check done in code: an exception marked as not naming the letter's facts shows that exceptions exist, not that this denial is wrong.
3. Decisive fact. Name the one fact the letter's reason turns on, and who settles it (settled_by):
   - "documents": a supported finding states it.
   - "letter": the letter states it as a fact about the claim: the member's age, the dates, the service or quantity billed, what the prescription says the drug is for, a related surgery, other coverage on file. Take the letter's own facts as given.
   - "payer_determination": the rule leaves it to an individual decision (a prior authorization decision, an assessment, a plan of care, the authorized amount, medical necessity for this member) and the letter only reports the payer's own conclusion about it. The payer's conclusion is not proof that the rule was met or not met.
   - "outside_documents": it is set by a document the findings refer to but do not contain (a plan's preferred drug list or formulary, a form a contract requires, the plan's own policy) or by a rule outside these documents.
   relies_on_exception: true when the denial would be inconsistent because an exception covers the letter's facts (the rule the letter cites is real, but an exception to it applies); then cite the exception's quote in the rule. False otherwise, including when a cited rule itself contradicts the letter's reason or the letter misstates the rule. Citations are checked: an inconsistent outcome that relies on an exception whose cited quotes do not name the letter's facts becomes "not_settled".
4. Outcome. Only then decide, choosing exactly one:
   - "consistent": {HEADLINES["consistent"]}
   - "inconsistent": {HEADLINES["inconsistent"]}
   - "not_settled": {HEADLINES["not_settled"]}
   Choose "consistent" only when a cited rule states the exclusion, limit, or requirement the letter cites, the letter's own facts meet it, and no cited exception covers those facts. Choose "inconsistent" only when a cited rule contradicts the letter's stated reason or the reason goes beyond what the rule allows the plan to do, including an exclusion that a cited exception covers on the letter's own facts. Choose "not_settled" when the decisive fact is "payer_determination" or "outside_documents", or when the supported findings do not state the rule that decides the letter's reason. "not_settled" is a correct answer, not a failure; do not guess.
5. Gap. For inconsistent: the difference between the letter's reason and the rule. For consistent: why the reason matches the rule. For not_settled: what is missing.
6. what_would_change. For consistent: what would have made the service covered under the rule (for example an authorization or a document the rule names). For not_settled: the decisive fact and the document that would show it. For inconsistent: null.

Citations: each citation names a supported finding by its id (for example "f2") and copies a quote from that finding's verified quotes exactly, word for word. Citations are checked. A quote that is not in the finding is dropped, and a rule left with no valid citation turns the outcome into "not_settled". Never cite a question listed as not settled.

Never give medical advice. Do not say whether the care was needed, whether it was medically necessary for this member, or anything about treatment, diagnosis, or the member's health. Argue only from the written rules and the letter's own facts. You may repeat what a rule says about medical necessity, as a rule.

Write plain English, short sentences, no legal jargon. Return JSON only, matching the schema:
{{"steelman": {{"argument": "...", "citations": [{{"finding_id": "f1", "quote": "..."}}]}}, "rule": {{"statement": "...", "citations": [...]}}, "decisive_fact": {{"fact": "...", "settled_by": "documents" | "letter" | "payer_determination" | "outside_documents"}}, "relies_on_exception": true | false, "outcome": "consistent" | "inconsistent" | "not_settled", "gap": "...", "what_would_change": "..." or null}}"""


# ---- helpers shared with letter.py ---------------------------------------------


def card_value(card, field: str):
    """A card cell is {"value", "confidence"}; a plain value is accepted too."""
    cell = card.get(field) if isinstance(card, dict) else None
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def supported_findings(investigation) -> list[dict]:
    fs = (investigation or {}).get("findings") or []
    return [f for f in fs if isinstance(f, dict) and f.get("status") == "supported" and f.get("citations")]


def unsettled_findings(investigation) -> list[dict]:
    fs = (investigation or {}).get("findings") or []
    return [f for f in fs if isinstance(f, dict) and f not in supported_findings(investigation)]


def citation_ref(finding: dict, citation: dict) -> dict:
    """A CitationRef built from a finding's kept citation (the only source of doc, title, page, quote)."""
    return {"finding_id": finding["id"], "doc_id": citation.get("doc_id"), "title": citation.get("title"), "page": citation.get("page"), "quote": citation.get("quote")}


def validate_ref(ref, investigation, _by_id: dict | None = None) -> dict | None:
    """The CitationRef for a model reference ({finding_id, quote}), or None when it does not hold."""
    if not isinstance(ref, dict):
        return None
    fid = str(ref.get("finding_id") or "").strip()
    quote = str(ref.get("quote") or "").strip()
    if not fid or len(quote) < MIN_QUOTE_CHARS:
        return None
    by_id = _by_id if _by_id is not None else {f["id"]: f for f in supported_findings(investigation)}
    f = by_id.get(fid)
    if f is None:
        return None
    best, best_ov = None, 0.0
    for c in f.get("citations") or []:
        ov = quote_overlap(quote, str(c.get("quote") or ""))
        if ov > best_ov:
            best, best_ov = c, ov
    if best is None or best_ov < QUOTE_THRESHOLD:
        return None
    return citation_ref(f, best)


def validate_refs(refs, investigation) -> list[dict]:
    """Keep the references that hold (see the module docstring), de-duplicated, in the model's order."""
    if not isinstance(refs, list):
        return []
    by_id = {f["id"]: f for f in supported_findings(investigation)}
    out, seen = [], set()
    for r in refs:
        v = validate_ref(r, investigation, by_id)
        if v is None:
            continue
        key = (v["finding_id"], v["doc_id"], v["page"], v["quote"])
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _amount(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "not stated"


def case_facts(card) -> str:
    """The case card as the model sees it (the letter's own facts, nothing else)."""
    from .investigate import program_label

    rows = [
        ("Payer", card_value(card, "payer_name")),
        ("Program", program_label(card_value(card, "program"))),
        ("Member age group", card_value(card, "member_age_group") or "unknown"),
        ("Service", card_value(card, "service")),
        ("Service code", card_value(card, "service_code")),
        ("Dates of service", card_value(card, "dates_of_service")),
        ("Amount billed", _amount(card_value(card, "amount_billed")) if card_value(card, "amount_billed") is not None else None),
        ("Letter date", card_value(card, "letter_date")),
        ("Appeal deadline stated in the letter", card_value(card, "appeal_deadline_claimed")),
    ]
    lines = [f"{k}: {v if v not in (None, '') else 'not stated'}" for k, v in rows]
    reason = card_value(card, "denial_reason") or "not stated"
    return "Case card:\n" + "\n".join(lines) + f'\n\nThe letter\'s stated reason for the denial: "{reason}"'


def exception_check_block(marks: list[dict] | None) -> str:
    """The code's exception check as the verdict reads it: one line per supported exception finding."""
    lines = []
    for m in marks or []:
        if m.get("status") != "supported":
            continue
        if m.get("state") == "relevant":
            lines.append(f"- [{m['finding_id']}] names the letter's facts: {m['reason']}. It can count against the denial.")
        elif m.get("state") == "unchecked":
            lines.append(f"- [{m['finding_id']}] was not checked: {m['reason']}. Decide from its quotes.")
        else:
            lines.append(f"- [{m['finding_id']}] does not name the letter's facts: {m['reason']}. It shows that exceptions exist, not that this denial is wrong; do not rely on it for an inconsistent outcome.")
    if not lines:
        return ""
    return "Exception check (done in code, no model: does each exception finding's verified quote name a fact the letter states?):\n" + "\n".join(lines)


def findings_block(investigation, exception_marks: list[dict] | None = None) -> str:
    """Supported findings with their verified quotes, the exception check when given, then the other questions by question only."""
    parts = ["Supported findings (verified quotes from public policy documents; the only facts you may use):"]
    sup = supported_findings(investigation)
    if not sup:
        parts.append("(none)")
    for f in sup:
        quotes = "\n".join(f'- "{c.get("quote")}" ({c.get("title") or c.get("doc_id")}, page {c.get("page")})' for c in f.get("citations") or [])
        parts.append(f"[{f['id']}] topic: {f.get('topic')}, jurisdiction: {f.get('jurisdiction')}\nQuestion: {f.get('question')}\nAnswer: {f.get('answer')}\nVerified quotes:\n{quotes}")
    check = exception_check_block(exception_marks)
    if check:
        parts.append(check)
    rest = unsettled_findings(investigation)
    if rest:
        parts.append("Not settled by the documents (no verified quote; each is an open question: if the letter's reason turns on one, the decisive fact is not in the documents; do not argue from these, do not cite them):\n" + "\n".join(f"- [{f.get('id')}] {f.get('question')}" for f in rest))
    return "\n\n".join(parts)


def verdict_user_message(case: dict, investigation) -> str:
    from .investigate import letter_summary_block
    from .relevance import mark_exceptions

    marks = mark_exceptions(investigation, case)
    return case_facts(case.get("card") or {}) + letter_summary_block(case.get("summary")) + "\n\n" + findings_block(investigation, marks) + "\n\nArgue the payer's side first, then decide. Return JSON only."


# ---- verdict ---------------------------------------------------------------------


def _meta(model: str, n_in: int = 0, n_out: int = 0, reasoning: int = 0, latency_ms: float = 0.0, cost_usd: float = 0.0, error: str | None = None) -> dict:
    return {"model": model, "input_tokens": int(n_in), "output_tokens": int(n_out), "reasoning_tokens": int(reasoning), "latency_ms": round(float(latency_ms), 1), "cost_usd": float(cost_usd), "error": error}


def _verdict(steelman: dict, outcome: str, proposed: str, rule: dict, gap: str, wwc, meta: dict, decisive_fact: dict | None = None,
             relies_on_exception: bool = False, exceptions: list[dict] | None = None) -> dict:
    return {
        "status": "done",
        "steelman": steelman,
        "outcome": outcome,
        "proposed_outcome": proposed,
        "headline": HEADLINES[outcome],
        "rule": rule,
        "gap": gap,
        "what_would_change": wwc,
        "decisive_fact": decisive_fact,
        "relies_on_exception": bool(relies_on_exception),
        "exceptions": list(exceptions or []),
        **meta,
    }


def empty_verdict(model: str, status: str = "running", error: str | None = None) -> dict:
    """The verdict while it runs, or after an exception outside the model step: every key, no content."""
    return {"status": status, "steelman": None, "outcome": None, "proposed_outcome": None, "headline": None, "rule": None, "gap": None, "what_would_change": None,
            "decisive_fact": None, "relies_on_exception": False, "exceptions": [], **_meta(model, error=error)}


def template_verdict(meta: dict, no_findings: bool = False) -> dict:
    """The not_settled verdict used when no supported finding exists or the model step fails."""
    if no_findings:
        argument = "No finding from the documents we found supports the payer's reason with a verified quote, so there is no cited case for the denial to make."
        statement = "The documents we found do not state the rule that governs this service and this reason."
        gap = "None of the investigation's questions came back with a verified quote, so the letter's reason cannot be checked against a written rule."
        wwc = DEFAULT_SETTLE
    else:
        argument = "The payer's side could not be drafted because the verdict step failed."
        statement = "No governing rule could be stated with a verified quote."
        gap = "The verdict step failed, so the documents are treated as not settling the denial. The supported findings still stand on their own."
        wwc = "Running the verdict again, or reading the supported findings against the letter's reason."
    return _verdict(
        {"argument": argument, "citations": [], "unsupported": True},
        "not_settled",
        "not_settled",
        {"statement": statement, "citations": [], "unsupported": True},
        gap,
        wwc,
        meta,
    )


def route_outside_corpus(case: dict) -> bool:
    """True when the router said no corpus document governs the plan (an employer or commercial plan)."""
    route = case.get("route") if isinstance(case, dict) else None
    return bool(isinstance(route, dict) and route.get("outside_corpus"))


OUTSIDE_CORPUS_SETTLE = "The plan's own benefit documents: the summary plan description, the certificate of coverage, or the policy the denial letter cites. Ask the plan or the employer's benefits administrator for the written rule it applied."


def outside_corpus_verdict(meta: dict, route_reason: str = "") -> dict:
    """The not_settled verdict for a plan outside the corpus: no model call, no rule cited, the reason stated plainly."""
    argument = "The payer's side cannot be argued from these documents: none of them is this plan's policy."
    statement = "No document in the corpus governs this plan. The Florida Medicaid and Medicare rules found here do not apply to it, so no rule can be cited for or against the denial."
    gap = (route_reason + " " if route_reason else "") + "The letter's reason can only be checked against the plan's own documents, which are not in this corpus, so the documents do not settle it."
    return _verdict(
        {"argument": argument, "citations": [], "unsupported": True},
        "not_settled",
        "not_settled",
        {"statement": statement, "citations": [], "unsupported": True},
        " ".join(gap.split()),
        OUTSIDE_CORPUS_SETTLE,
        meta,
    )


EXCEPTION_GAP = "The only exception cited against the denial does not name the letter's facts: {reason}. It shows that exceptions exist, not that this denial is wrong, so the documents found do not settle it."
EXCEPTION_SETTLE = "An exception whose own words name the letter's facts (the procedure or surgery, what the drug is for, the member's other coverage or age group), quoted word for word; without one, the rule the letter cites, read against the letter's own facts."


def verdict_from_data(data, investigation, meta: dict, case: dict | None = None) -> dict:
    """Validate a model-shaped reply into the verdict. Raises ValueError when the reply is malformed.

    With `case` (the card and the intake summary), the exception check runs (policyqa.relevance): every
    exception finding is marked relevant or not and recorded in `exceptions`, and an inconsistent outcome
    the model says relies on an exception (`relies_on_exception`) becomes not_settled when none of the
    rule's validated quotes is "relevant" and at least one is "not_relevant". A case whose letter states no
    specific fact leaves its quotes "unchecked" and is never guarded. Without `case` there is no check."""
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    outcome = str(data.get("outcome") or "").strip().lower()
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} is not one of {OUTCOMES}")
    st = data.get("steelman") if isinstance(data.get("steelman"), dict) else {}
    ru = data.get("rule") if isinstance(data.get("rule"), dict) else {}
    argument = " ".join(str(st.get("argument") or "").split())
    statement = " ".join(str(ru.get("statement") or "").split())
    if not argument or not statement:
        raise ValueError("the steelman argument or the rule statement is empty")
    steel_refs = validate_refs(st.get("citations"), investigation)
    rule_refs = validate_refs(ru.get("citations"), investigation)
    proposed = outcome
    gap = " ".join(str(data.get("gap") or "").split())
    wwc = data.get("what_would_change")
    wwc = " ".join(str(wwc).split()) if isinstance(wwc, str) and wwc.strip() else None
    df = data.get("decisive_fact") if isinstance(data.get("decisive_fact"), dict) else {}
    fact = " ".join(str(df.get("fact") or "").split())
    settled_by = str(df.get("settled_by") or "").strip().lower()
    if not rule_refs and outcome != "not_settled":
        outcome = "not_settled"
        gap = FALLBACK_GAP
        wwc = DEFAULT_SETTLE
    if settled_by in OPEN_FACT_GAPS and outcome != "not_settled":
        # The model named an open fact (the payer's own determination, or a list outside the documents)
        # and still decided: the documents do not settle it. proposed_outcome keeps what the model said.
        outcome = "not_settled"
        gap = OPEN_FACT_GAPS[settled_by].format(fact=fact or "the fact the letter's reason turns on.")
        wwc = fact or DEFAULT_SETTLE
    relies = data.get("relies_on_exception") is True
    marks: list[dict] = []
    if case is not None:
        from .relevance import citation_relevance, mark_exceptions

        marks = mark_exceptions(investigation, case)
        if outcome == "inconsistent" and relies:
            # Oct 27, second pass (dc-002, dc-003): an exception counts against the letter only when its quoted
            # words name the letter's fact. The cited rule stays as written; only the outcome changes.
            # Three states (fix round): the guard fires only when no cited rule quote names a letter fact and at
            # least one fails the check. A case with no specific fact leaves every quote "unchecked" (dc-022,
            # dc-027), so it is never guarded; an age or program contradiction fails it with or without facts (dc-002).
            rels = citation_relevance(rule_refs, case)
            failed = [r for r in rels if r["state"] == "not_relevant"]
            if failed and not any(r["state"] == "relevant" for r in rels):
                exc_ids = {m["finding_id"] for m in marks}
                pick = next((r for r in failed if r["finding_id"] in exc_ids), failed[0])
                reason = pick["reason"]
                outcome = "not_settled"
                gap = EXCEPTION_GAP.format(reason=reason)
                wwc = EXCEPTION_SETTLE
    if outcome == "inconsistent":
        wwc = None
    elif wwc is None:
        wwc = DEFAULT_COVERED if outcome == "consistent" else (fact or DEFAULT_SETTLE)
    if not gap:
        gap = FALLBACK_GAP if outcome == "not_settled" else ""
    return _verdict(
        {"argument": argument, "citations": steel_refs, "unsupported": not steel_refs},
        outcome,
        proposed,
        {"statement": statement, "citations": rule_refs, "unsupported": not rule_refs},
        gap,
        wwc,
        meta,
        decisive_fact={"fact": fact, "settled_by": settled_by} if (fact or settled_by) else None,
        relies_on_exception=relies,
        exceptions=marks,
    )


def build_steelman_verdict(case: dict, investigation, provider) -> dict:
    """One model call; never raises for a model failure (see the module docstring)."""
    model = getattr(provider, "model", "?")
    if route_outside_corpus(case):
        return outside_corpus_verdict(_meta(model), str((case.get("route") or {}).get("reason") or ""))
    if not supported_findings(investigation):
        return template_verdict(_meta(model), no_findings=True)
    t = time.perf_counter()
    reply: tuple[int, int] | None = None
    try:
        text, n_in, n_out = provider.complete_parts(VERDICT_SYSTEM_PROMPT, [{"type": "text", "text": verdict_user_message(case, investigation)}], schema=VERDICT_SCHEMA, max_tokens=VERDICT_MAX_TOKENS)
        reply = (int(n_in or 0), int(n_out or 0))
        data = parse_model_json(text)
        return verdict_from_data(data, investigation, _reply_meta(provider, model, reply, t), case=case)
    except Exception as e:  # noqa: BLE001 - any failure is the not_settled template, with the reason recorded
        meta = _reply_meta(provider, model, reply, t) if reply else _meta(model, latency_ms=(time.perf_counter() - t) * 1000)
        meta["error"] = f"{type(e).__name__}: {e}"[:300]
        return template_verdict(meta)


def _reply_meta(provider, model: str, reply: tuple[int, int], t0: float) -> dict:
    cost = getattr(provider, "cost", None)
    return _meta(model, reply[0], reply[1], reasoning_tokens(provider), (time.perf_counter() - t0) * 1000, float(cost(*reply)) if callable(cost) else 0.0)


class LiveVerdict:
    """build_steelman_verdict bound to a provider (Muse Spark 1.3 through the Meta Model API)."""

    def __init__(self, provider):
        self.provider = provider
        self.model = getattr(provider, "model", "?")

    def decide(self, case: dict, investigation) -> dict:
        return build_steelman_verdict(case, investigation, self.provider)


def _pick(findings: list[dict], *topics: str, exclude: tuple = ()) -> dict | None:
    for topic in topics:
        for f in findings:
            if f.get("topic") == topic and f["id"] not in exclude:
                return f
    return None


def _ref_matching(f: dict, word: str) -> dict:
    """A {finding_id, quote} reference to the finding's first citation that contains `word`, else its first citation."""
    cs = f["citations"]
    c = next((c for c in cs if word.lower() in str(c.get("quote") or "").lower()), cs[0])
    return {"finding_id": f["id"], "quote": c["quote"]}


class FixtureVerdict:
    """No network. A model-shaped reply for the Sunshine Health sample, validated like a real one."""

    model = "fixture"

    def __init__(self, delay: float = 0.8):
        self.delay = delay

    def reply(self, investigation) -> dict | None:
        sup = supported_findings(investigation)
        if not sup:
            return None
        first = _pick(sup, "limits") or sup[0]
        second = _pick(sup, "conditions", "coverage", exclude=(first["id"],))
        refs = [_ref_matching(first, "24 hours")] + ([_ref_matching(second, "exceed")] if second else [])
        return {
            "steelman": {
                "argument": FIXTURE_MARK + "The plan's strongest case: the letter says the services went past the amount the plan authorized, and the policy pays for private duty nursing within the hours the rules and the authorization allow. On that reading, hours billed beyond what the plan approved are outside what it agreed to pay.",
                "citations": [_ref_matching(first, "authorized")],
            },
            "rule": {
                "statement": FIXTURE_MARK + "Florida Medicaid covers up to 24 hours of private duty nursing per day for a recipient who meets the policy's criteria, and for a recipient under 21, services beyond the policy's coverage may be approved when medically necessary.",
                "citations": refs,
            },
            "outcome": "inconsistent",
            "gap": FIXTURE_MARK + "The letter treats the plan's authorized amount as the limit. The rule sets a ceiling of 24 hours a day and lets the plan approve more for a recipient under 21, so the letter's reason alone does not show the hours fall outside the policy.",
            "what_would_change": None,
        }

    def decide(self, case: dict, investigation) -> dict:
        if self.delay:
            time.sleep(self.delay)
        if route_outside_corpus(case):
            return outside_corpus_verdict(_meta(self.model), str((case.get("route") or {}).get("reason") or ""))
        data = self.reply(investigation)
        if data is None:
            return template_verdict(_meta(self.model), no_findings=True)
        return verdict_from_data(json.loads(json.dumps(data)), investigation, _meta(self.model, latency_ms=self.delay * 1000), case=case)

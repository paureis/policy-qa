"""Critic: a second Muse Spark pass attacks the drafted appeal letter and proposes a revision.

critique_letter(case, investigation, verdict, letter, provider, rounds=1) runs up to two
review rounds after the letter is drafted and verified. Each round is one `complete_parts`
call with a strict schema. The model sees the case card and the letter's stated reason, the
verdict, the supported findings with their verified quotes (the only citable material), the
computed deadline and filing path, and the current letter with every sentence labelled
[paragraph.sentence] (zero-based) and its verification result. It returns `issues` (kind,
severity, where, note) and `revised_paragraphs` in the letter's sentence shape.

The revision goes through letter.verify_letter, the same verifier as the draft (citation
check and the medical-need guard). It replaces the current letter only when it is at least
as well verified: verified count not lower and struck count not higher. A revision that
changes nothing is not counted as accepted. Otherwise the current letter stands and the
round records `rejected_reason`.

An issue is `fixed` when its round was accepted and either the sentence it points at is no
longer in the revision in the same state (rewritten, removed, or re-verified), or the issue
is about the whole letter (where is null, or kind missing_deadline, missing_request, tone).

Rounds: RECOURSE_CRITIC_ROUNDS (default 1; 0 disables; capped at 2). The second round
reviews the current letter (the first round's revision when accepted) and is told what the
first round found. A round stops the review when it errors or finds no issue.

Failure: a model error, a truncated reply (TruncatedResponse) or bad JSON makes that round's
`error` with `accepted: false`, `after: []`; the critique is still `status: "done"` with
`error` set, and the letter stays as drafted. Tokens of a reply that came back are counted.

Critique shape: {status: running|done|failed, skipped, reason, rounds: [{round, issues: [{kind,
severity, where: {paragraph, sentence} | null, note, fixed}], before, after,
verification_before, verification_after, accepted, rejected_reason, model, input_tokens,
output_tokens, reasoning_tokens, latency_ms, cost_usd, error}], issues_found, issues_fixed,
accepted, model, cost_usd, latency_ms, error}.

apply_critique(letter, critique) returns the final letter: `paragraphs` and `verification`
from the last accepted round, `draft_paragraphs` always the original draft.

FixtureCritic: no network. On the fixture letter it finds the struck claim (removed) and a
missing request for the authorization records (added), and the revision is accepted.
"""
from __future__ import annotations

import copy
import json
import os
import time

from .generate import parse_model_json, reasoning_tokens
from .letter import LETTER_SCHEMA, LETTER_SYSTEM_PROMPT, _verdict_block, verify_letter
from .verdict import FIXTURE_MARK, _meta, case_facts, findings_block

CRITIC_MAX_TOKENS = 12000  # reasoning model: the critique, a full revised letter, and the thinking before both
MAX_ROUNDS = 2
DEFAULT_ROUNDS = 1
ROUNDS_ENV = "RECOURSE_CRITIC_ROUNDS"

ISSUE_KINDS = ("unverified_claim", "missing_deadline", "wrong_program", "medical_statement", "unsupported_fact", "missing_request", "tone", "other")
SEVERITIES = ("high", "medium", "low")
GLOBAL_KINDS = frozenset({"missing_deadline", "missing_request", "tone"})

SKIP_OFF = "The letter review is turned off (RECOURSE_CRITIC_ROUNDS is 0)."
SKIP_NOT_APPLICABLE = "There is no appeal letter to review: the denial matches the policy."
SKIP_EMPTY = "There is no appeal letter to review."
REJECT_EMPTY = "The revision has no sentences, so the draft stands."
REJECT_SAME = "The revision made no change to the letter."

_ZERO = {"claims": 0, "verified": 0, "struck": 0}

_WHERE = {
    "anyOf": [
        {"type": "object", "properties": {"paragraph": {"type": "integer"}, "sentence": {"type": "integer"}}, "required": ["paragraph", "sentence"], "additionalProperties": False},
        {"type": "null"},
    ]
}
CRITIC_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(ISSUE_KINDS)},
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "where": _WHERE,
                    "note": {"type": "string"},
                },
                "required": ["kind", "severity", "where", "note"],
                "additionalProperties": False,
            },
        },
        "revised_paragraphs": LETTER_SCHEMA["properties"]["paragraphs"],
    },
    "required": ["issues", "revised_paragraphs"],
    "additionalProperties": False,
}

# The drafting rules, reused word for word so the revision is written to the same standard as the draft.
_LETTER_RULES = LETTER_SYSTEM_PROMPT.split("Rules:\n", 1)[1].split("\n\nReturn JSON only", 1)[0]

CRITIC_SYSTEM_PROMPT = f"""You review a draft appeal letter that a health plan member (or the member's caregiver) will send to the plan that denied a service. First attack the draft: find what would weaken the appeal or mislead the plan. Then return a revised letter that fixes what you found.

You are given the case card (what the denial letter says), the letter's stated reason, the verdict with the governing rule and the gap, the supported findings with their verified quotes (the only material a claim may cite), the deadline and the filing path computed from the card and the findings, and the current letter. Each sentence of the current letter is labelled [paragraph.sentence], numbered from zero, with its verification result: VERIFIED (its citation matched a verified quote), STRUCK (with the reason; a struck sentence is left out of the letter that is sent), or NOT A CLAIM.

Issue kinds, one issue per problem:
- unverified_claim: a claim sentence that is struck, or whose quote does not support what the sentence says.
- missing_deadline: the letter states a deadline or date that differs from the card or the computed deadline, or it should state that the appeal is filed within the deadline and does not.
- wrong_program: the letter names a program, plan, payer, or jurisdiction other than the case card's.
- medical_statement: a sentence that says or implies the care was needed, was medically necessary for this member, or anything about treatment, diagnosis, or the member's health.
- unsupported_fact: a fact that is neither on the case card nor in a supported finding (names, numbers, codes, dates, amounts, events).
- missing_request: the letter does not say plainly what the plan should do (reverse the denial, or name the rule and send the records it used).
- tone: rude, pleading, threatening, legalistic, or unclear wording.
- other: anything else that would weaken the appeal.
Give each issue a severity (high: could make the appeal fail or mislead the plan; medium: weakens it; low: polish), the sentence it points at as {{"paragraph": n, "sentence": m}} using the labels (null when the issue is about the whole letter or about something missing), and a one-sentence note in plain English.

Write the revised letter under the same rules as the draft:
{_LETTER_RULES}

Revision rules:
7. Keep every sentence that has no problem word for word, with its claim flag and citation. Change only what an issue names.
8. Remove a claim you cannot support with a verified quote. Do not keep it as a sentence without a citation, and do not add a claim without a verified quote.
9. Remove any sentence about whether the care was needed. Never replace it with another statement about the member's health or treatment.
10. If you find no issue, return an empty issues list and the current letter unchanged.

Return JSON only, matching the schema: {{"issues": [{{"kind": "unverified_claim", "severity": "high", "where": {{"paragraph": 2, "sentence": 1}}, "note": "..."}}], "revised_paragraphs": [{{"sentences": [{{"text": "...", "claim": false, "citation": null}}, {{"text": "...", "claim": true, "citation": {{"finding_id": "f2", "quote": "..."}}}}]}}]}}"""


# ---- environment and empty shapes -------------------------------------------------------


def critic_rounds() -> int:
    """RECOURSE_CRITIC_ROUNDS as 0..2; unset or not a number gives the default (1)."""
    raw = os.environ.get(ROUNDS_ENV)
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_ROUNDS
    return max(0, min(MAX_ROUNDS, n))


def empty_critique(model: str, status: str = "running", error: str | None = None, skipped: bool = False, reason: str | None = None) -> dict:
    """The critique while it runs, when it is skipped, or after an exception outside the model step."""
    return {
        "status": status, "skipped": skipped, "reason": reason, "rounds": [], "issues_found": 0, "issues_fixed": 0,
        "accepted": False, "model": model, "cost_usd": 0.0, "latency_ms": 0.0, "error": error,
    }


# ---- prompt -------------------------------------------------------------------------------


def _sentence_line(p: int, i: int, x: dict) -> str:
    label = f"[{p}.{i}]"
    if x.get("struck"):
        state = f"STRUCK ({x.get('reason') or 'struck'})"
    elif x.get("claim") and x.get("verified"):
        c = x.get("citation") or {}
        state = f'VERIFIED, cites [{c.get("finding_id")}] "{c.get("quote")}"'
    elif x.get("claim"):
        state = "CLAIM, NOT VERIFIED"
    else:
        state = "NOT A CLAIM"
    return f"{label} {state}: {x.get('text')}"


def letter_block(letter: dict) -> str:
    lines = [f"To: {letter.get('to') or ''}", f"Re: {letter.get('re') or ''}"]
    for p, para in enumerate(letter.get("paragraphs") or []):
        lines.append("")
        lines += [_sentence_line(p, i, x) for i, x in enumerate(para.get("sentences") or [])]
    v = letter.get("verification") or _ZERO
    lines.append("")
    lines.append(f"Verification: {v.get('claims', 0)} claims, {v.get('verified', 0)} verified, {v.get('struck', 0)} struck.")
    return "\n".join(lines)


def _action_block(letter: dict) -> str:
    d = letter.get("deadline") or {}
    f = letter.get("filing") or {}
    return (
        f"Deadline: {d.get('date') or 'not known'} ({d.get('note') or ''})\n"
        f"Filing path: where: {f.get('where') or 'not stated'}; how: {f.get('how') or 'not stated'}"
    )


def _previous_block(prev: dict | None) -> str:
    if not prev:
        return ""
    issues = "\n".join(f"- {i['kind']} ({i['severity']}): {i['note']}" for i in prev.get("issues") or []) or "- none"
    outcome = "accepted; the current letter is that revision" if prev.get("accepted") else f"rejected: {prev.get('rejected_reason') or prev.get('error')}"
    return f"\n\nThe previous review round (round {prev['round']}) found:\n{issues}\nIts revision was {outcome}."


def critic_user_message(case: dict, investigation, verdict: dict, letter: dict, prev: dict | None = None) -> str:
    return (
        case_facts(case.get("card") or {})
        + "\n\n" + _verdict_block(verdict)
        + "\n\n" + findings_block(investigation)
        + "\n\n" + _action_block(letter)
        + "\n\nCurrent letter:\n" + letter_block(letter)
        + _previous_block(prev)
        + "\n\nReview the letter, then return the issues and the revised letter. Return JSON only."
    )


# ---- one round ------------------------------------------------------------------------------


def _usable_reply(data) -> tuple[list, list]:
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    ps = data.get("revised_paragraphs")
    if not isinstance(ps, list) or not all(isinstance(p, dict) and isinstance(p.get("sentences"), list) for p in ps):
        raise ValueError("reply has no revised_paragraphs of sentences")
    issues = data.get("issues")
    return (issues if isinstance(issues, list) else []), ps


def _where(raw, paragraphs: list) -> dict | None:
    if not isinstance(raw, dict):
        return None
    try:
        p, i = int(raw.get("paragraph")), int(raw.get("sentence"))
    except (TypeError, ValueError):
        return None
    if 0 <= p < len(paragraphs) and 0 <= i < len(paragraphs[p].get("sentences") or []):
        return {"paragraph": p, "sentence": i}
    return None


def _issues(raw: list, before: list) -> list[dict]:
    out = []
    for x in raw:
        if not isinstance(x, dict):
            continue
        note = " ".join(str(x.get("note") or "").split())
        if not note:
            continue
        kind = str(x.get("kind") or "").strip().lower()
        sev = str(x.get("severity") or "").strip().lower()
        out.append({
            "kind": kind if kind in ISSUE_KINDS else "other",
            "severity": sev if sev in SEVERITIES else "medium",
            "where": _where(x.get("where"), before),
            "note": note,
            "fixed": False,
        })
    return out


def _state(x: dict) -> tuple:
    return (x.get("text"), bool(x.get("verified")), bool(x.get("struck")))


def _states(paragraphs: list) -> list[list[tuple]]:
    return [[_state(x) for x in p.get("sentences") or []] for p in paragraphs]


def _mark_fixed(issues: list[dict], before: list, after: list) -> None:
    kept = {st for para in _states(after) for st in para}
    for i in issues:
        w = i["where"]
        if i["kind"] in GLOBAL_KINDS or w is None:
            i["fixed"] = True
        else:
            i["fixed"] = _state(before[w["paragraph"]]["sentences"][w["sentence"]]) not in kept


def _decide(vb: dict, va: dict, before: list, after: list) -> str | None:
    """None when the revision replaces the letter, else the reason it does not."""
    if not after:
        return REJECT_EMPTY
    if _states(after) == _states(before):
        return REJECT_SAME
    if va["verified"] < vb["verified"]:
        return f"the revised letter verified fewer sentences than the one it reviewed ({va['verified']}, was {vb['verified']})"
    if va["struck"] > vb["struck"]:
        return f"the revised letter had more struck sentences than the one it reviewed ({va['struck']}, was {vb['struck']})"
    return None


def _round(n: int, current: dict, investigation, ask, model: str, prev: dict | None) -> dict:
    before = copy.deepcopy(current.get("paragraphs") or [])
    vb = dict(current.get("verification") or _ZERO)
    t = time.perf_counter()
    reply_meta = None
    try:
        text, n_in, n_out, meta_fn = ask(current, prev)
        reply_meta = (int(n_in or 0), int(n_out or 0), meta_fn)
        raw_issues, revised = _usable_reply(parse_model_json(text))
        error = None
    except Exception as e:  # noqa: BLE001 - the round records the failure; the letter stays as it is
        raw_issues, revised, error = [], None, f"{type(e).__name__}: {e}"[:300]
    ms = (time.perf_counter() - t) * 1000
    if reply_meta:
        n_in, n_out, meta_fn = reply_meta
        reasoning, cost = meta_fn(n_in, n_out)
        meta = _meta(model, n_in, n_out, reasoning, ms, cost, error)
    else:
        meta = _meta(model, latency_ms=ms, error=error)
    if error:
        return {"round": n, "issues": [], "before": before, "after": [], "verification_before": vb, "verification_after": dict(_ZERO),
                "accepted": False, "rejected_reason": None, **meta}
    checked = verify_letter({"paragraphs": revised}, investigation)
    after, va = checked["paragraphs"], checked["verification"]
    issues = _issues(raw_issues, before)
    rejected = _decide(vb, va, before, after)
    if rejected is None:
        _mark_fixed(issues, before, after)
    return {"round": n, "issues": issues, "before": before, "after": after, "verification_before": vb, "verification_after": va,
            "accepted": rejected is None, "rejected_reason": rejected, **meta}


def _review(case: dict, investigation, verdict: dict, letter: dict, rounds: int, model: str, ask) -> dict:
    rounds = max(0, min(MAX_ROUNDS, int(rounds)))
    if rounds == 0:
        return empty_critique(model, "done", skipped=True, reason=SKIP_OFF)
    if letter.get("applicable") is False or verdict.get("outcome") == "consistent":
        return empty_critique(model, "done", skipped=True, reason=SKIP_NOT_APPLICABLE)
    if not letter.get("paragraphs"):
        return empty_critique(model, "done", skipped=True, reason=SKIP_EMPTY)
    current = copy.deepcopy(letter)
    out: list[dict] = []
    for n in range(1, rounds + 1):
        r = _round(n, current, investigation, ask, model, out[-1] if out else None)
        out.append(r)
        if r["accepted"]:
            current = {**current, "paragraphs": copy.deepcopy(r["after"]), "verification": dict(r["verification_after"])}
        if r["error"] or not r["issues"]:
            break
    errors = [r["error"] for r in out if r["error"]]
    return {
        "status": "done",
        "skipped": False,
        "reason": None,
        "rounds": out,
        "issues_found": sum(len(r["issues"]) for r in out),
        "issues_fixed": sum(i["fixed"] for r in out for i in r["issues"]),
        "accepted": any(r["accepted"] for r in out),
        "model": model,
        "cost_usd": round(sum(float(r["cost_usd"]) for r in out), 6),
        "latency_ms": round(sum(float(r["latency_ms"]) for r in out), 1),
        "error": errors[0] if errors else None,
    }


def critique_letter(case: dict, investigation, verdict: dict, letter: dict, provider, rounds: int = DEFAULT_ROUNDS) -> dict:
    """Review the drafted letter with the model; never raises for a model failure (see the module docstring)."""
    model = getattr(provider, "model", "?")

    def usage(n_in: int, n_out: int) -> tuple[int, float]:
        cost = getattr(provider, "cost", None)
        return reasoning_tokens(provider), (float(cost(n_in, n_out)) if callable(cost) else 0.0)

    def ask(current: dict, prev: dict | None):
        text, n_in, n_out = provider.complete_parts(
            CRITIC_SYSTEM_PROMPT,
            [{"type": "text", "text": critic_user_message(case, investigation, verdict, current, prev)}],
            schema=CRITIC_SCHEMA,
            max_tokens=CRITIC_MAX_TOKENS,
            schema_name="letter_critique",
        )
        return text, n_in, n_out, usage

    return _review(case, investigation, verdict, letter, rounds, model, ask)


def apply_critique(letter: dict, critique: dict | None) -> dict:
    """The final letter: the last accepted round's paragraphs and verification; `draft_paragraphs` keeps the draft."""
    out = copy.deepcopy(letter)
    out["draft_paragraphs"] = copy.deepcopy(letter.get("draft_paragraphs") if letter.get("draft_paragraphs") is not None else letter.get("paragraphs") or [])
    accepted = [r for r in (critique or {}).get("rounds") or [] if r.get("accepted")]
    if accepted:
        out["paragraphs"] = copy.deepcopy(accepted[-1]["after"])
        out["verification"] = dict(accepted[-1]["verification_after"])
    return out


class LiveCritic:
    """critique_letter bound to a provider (Muse Spark 1.3 through the Meta Model API)."""

    def __init__(self, provider, rounds: int | None = None):
        self.provider = provider
        self.model = getattr(provider, "model", "?")
        self.rounds = critic_rounds() if rounds is None else rounds

    def review(self, case: dict, investigation, verdict: dict, letter: dict) -> dict:
        return critique_letter(case, investigation, verdict, letter, self.provider, rounds=self.rounds)


FIXTURE_REQUEST = "Please also send me a copy of the authorization in effect for these dates and the records you used to set the authorized hours."


class FixtureCritic:
    """No network. A model-shaped review of the fixture letter, verified like a real one: the
    struck claim is removed (unverified_claim) and a request for the authorization records is
    added to the request paragraph (missing_request). Notes are marked "[fixture]"."""

    model = "fixture"

    def __init__(self, delay: float = 0.8, rounds: int | None = None):
        self.delay = delay
        self.rounds = critic_rounds() if rounds is None else rounds

    @staticmethod
    def reply(letter: dict) -> dict:
        issues, paragraphs = [], []
        asked = any(FIXTURE_REQUEST == x.get("text") for p in letter.get("paragraphs") or [] for x in p.get("sentences") or [])
        for p, para in enumerate(letter.get("paragraphs") or []):
            sentences = []
            for i, x in enumerate(para.get("sentences") or []):
                if x.get("claim") and x.get("struck"):
                    issues.append({"kind": "unverified_claim", "severity": "high", "where": {"paragraph": p, "sentence": i},
                                   "note": FIXTURE_MARK + "This claim's quote is not in the cited finding, so the plan could dismiss it. Remove it."})
                    continue
                c = x.get("citation")
                sentences.append({"text": x["text"], "claim": bool(x.get("claim")), "citation": {"finding_id": c["finding_id"], "quote": c["quote"]} if c else None})
                if not asked and str(x.get("text") or "").startswith("I ask you to"):
                    sentences.append({"text": FIXTURE_REQUEST, "claim": False, "citation": None})
                    issues.append({"kind": "missing_request", "severity": "medium", "where": None,
                                   "note": FIXTURE_MARK + "The letter does not ask for the authorization and the records behind the authorized hours."})
                    asked = True
            if sentences:
                paragraphs.append({"sentences": sentences})
        return {"issues": issues, "revised_paragraphs": paragraphs}

    def review(self, case: dict, investigation, verdict: dict, letter: dict) -> dict:
        def ask(current: dict, prev: dict | None):
            if self.delay:
                time.sleep(self.delay)
            return json.dumps(self.reply(current)), 0, 0, lambda n_in, n_out: (0, 0.0)

        return _review(case, investigation, verdict, letter, self.rounds, self.model, ask)

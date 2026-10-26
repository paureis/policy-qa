"""Investigation agent: a confirmed case card becomes a list of findings.

Steps (PRODUCT.md vocabulary): Routing, then Investigation.

- route_case(card): which jurisdictions' documents govern (Florida, Federal, or both
  side by side for dual-eligible and ambiguous cases), with a one-sentence reason.
- plan_questions(card, route, provider): one Muse Spark call plans 4 to 7 questions a
  policy document could answer (coverage, limits, conditions, exclusions, appeal, the
  letter's reason). Any failure falls back to template_questions. A planned question
  that asks for medical advice is dropped (policyqa.intake.scope_check).
- investigate_case(case, retriever, provider, on_progress): for each question and each
  jurisdiction, retrieve with the jurisdiction filter, answer with enforced citations,
  and map the answer to a finding: `supported` (a citation survived the verifier),
  `not_settled` (the model abstained), or `unsupported` (the model answered but every
  citation was struck; the original answer is kept so the screen can strike it out).
  One failing question becomes a not_settled finding; only a failure outside the loop
  fails the investigation. on_progress(partial) fires after every finding.
- FixtureInvestigator: no network, no index; a realistic synthetic investigation for the
  Sunshine Health sample with all three finding states, quotes marked synthetic.

Muse Spark 1.3 is a reasoning model: completion tokens include its reasoning, so every
call gets a generous max_tokens and reasoning tokens are recorded next to the others.
"""
from __future__ import annotations

import copy
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .generate import ABSTAIN_TEXT, STRUCK_NOT_FOUND, answer_question, parse_model_json, reasoning_tokens
from .intake import scope_check
from .trace import Trace

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "corpus" / "manifest.csv"

TOPICS = ("coverage", "limits", "conditions", "exclusions", "appeal", "reason", "other")
FINDING_STATUSES = ("supported", "not_settled", "unsupported")
MIN_PLANNED, MAX_PLANNED, MIN_USABLE = 4, 7, 3
MIN_QUESTION_CHARS = 15
PLAN_MAX_TOKENS = 2000
ANSWER_MAX_TOKENS = 2000
PASSAGES_PER_QUESTION = 5

PROGRAM_LABELS = {
    "florida_medicaid_mma": "Florida Medicaid (MMA)",
    "florida_medicaid_ltc": "Florida Medicaid Long-term Care",
    "florida_kidcare": "Florida KidCare",
    "medicare_a": "Medicare Part A",
    "medicare_b": "Medicare Part B",
    "medicare_advantage": "Medicare Advantage",
    "medicare_part_d": "Medicare Part D",
    "unknown": "Florida Medicaid or Medicare",
}
AGE_PHRASES = {"under_21": "for a member under 21", "65_plus": "for a member who is 65 or older"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _val(card, field: str):
    """A card cell is {"value", "confidence"}; a plain value is accepted too."""
    cell = card.get(field) if isinstance(card, dict) else None
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def program_label(program: str | None) -> str:
    return PROGRAM_LABELS.get(program or "unknown", PROGRAM_LABELS["unknown"])


# ---- routing ---------------------------------------------------------------


@dataclass
class Route:
    program: str
    jurisdictions: list[str]
    dual: bool
    reason: str

    def to_dict(self) -> dict:
        return {"program": self.program, "jurisdictions": list(self.jurisdictions), "dual": self.dual, "reason": self.reason}


def route_case(card) -> Route:
    """Which documents govern. Pure: the same card always routes the same way."""
    program = _val(card, "program")
    program = program if program in PROGRAM_LABELS else "unknown"
    age = _val(card, "member_age_group")
    payer = str(_val(card, "payer_name") or "")
    label = program_label(program)
    both = ["Florida", "Federal"]
    if program.startswith("florida_"):
        if age == "65_plus":
            return Route(program, both, True, f"The letter is from a {label} plan and the member is 65 or older, so Medicare may also cover this service; both sets of rules are checked side by side.")
        return Route(program, ["Florida"], False, f"The letter is about {label}, so the Florida Medicaid rules decide this case.")
    if program.startswith("medicare_"):
        if "medicaid" in payer.lower():
            return Route(program, both, True, f"The letter is about {label}, but the payer ({payer.strip()}) also handles Medicaid, so the Medicare rules and the Florida Medicaid rules are checked side by side.")
        return Route(program, ["Federal"], False, f"The letter is about {label}, so the federal Medicare rules decide this case.")
    return Route("unknown", both, True, "The letter does not say which program paid for the care, so the Florida Medicaid rules and the federal Medicare rules are checked side by side.")


# ---- question planning -----------------------------------------------------


@dataclass
class PlannedQuestion:
    topic: str
    question: str


PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": MIN_PLANNED,
            "maxItems": MAX_PLANNED,
            "items": {
                "type": "object",
                "properties": {"topic": {"type": "string", "enum": list(TOPICS)}, "question": {"type": "string"}},
                "required": ["topic", "question"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}

PLAN_SYSTEM_PROMPT = f"""You plan the investigation of a health coverage denial. You will be given a case card (the program, the service, the payer's stated reason for the denial, and the member's age group). Write {MIN_PLANNED} to {MAX_PLANNED} questions that a public policy document (a Florida Medicaid coverage policy, a managed care contract, a Medicare manual, or a Medicare booklet) could answer with a verbatim quote.

Rules:
1. Each question names the service and the program in plain words, as a reader with no insurance background would say them. One question per line of inquiry.
2. Topics, one per question: coverage (is the service covered), limits (hours, visits, amounts, frequency), conditions (prior authorization, medical necessity criteria, documentation), exclusions, appeal (appeal rights, deadlines, fair hearing, where to file), reason (what the rules say about the payer's stated denial reason), other.
3. Include at least one appeal question and at least one reason question about the letter's stated denial reason.
4. Ask only about coverage, billing, and appeal rules. Never ask about treatment, diagnosis, medication, dosage, or whether the care was needed. This tool never gives medical advice.
5. Return JSON only, matching the schema: {{"questions": [{{"topic": "...", "question": "..."}}]}}"""


def _clean_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    r = " ".join(str(reason).split()).strip().rstrip(".")
    if not r:
        return None
    return r[0].lower() + r[1:]


def template_questions(card, route: Route) -> list[PlannedQuestion]:
    """The fixed plan used when the model plan fails: one question per topic, in the order the screen shows them."""
    service = str(_val(card, "service") or "").strip() or "the service"
    label = program_label(route.program)
    age = AGE_PHRASES.get(_val(card, "member_age_group") or "", "")
    age_part = f" {age}" if age else ""
    reason = _clean_reason(_val(card, "denial_reason"))
    return [
        PlannedQuestion("coverage", f"Is {service} covered under {label}{age_part}?"),
        PlannedQuestion("limits", f"What limits apply to {service} under {label}{age_part}, such as hours, visits, or amounts?"),
        PlannedQuestion("conditions", f"What conditions or prior authorization does {label} require for {service}?"),
        PlannedQuestion("exclusions", f"What exclusions apply to {service} under {label}?"),
        PlannedQuestion("appeal", f"What are the appeal rights and the deadline to appeal a denial under {label}?"),
        PlannedQuestion("reason", f"What do the rules say when {reason}?" if reason else f"What reasons allow {label} to deny {service}?"),
    ]


def _card_summary_for_plan(card, route: Route) -> str:
    lines = [
        f"Program: {program_label(route.program)} (jurisdictions: {', '.join(route.jurisdictions)})",
        f"Payer: {_val(card, 'payer_name') or 'not stated'}",
        f"Service: {_val(card, 'service') or 'not stated'}",
        f"Service code: {_val(card, 'service_code') or 'not stated'}",
        f"Member age group: {_val(card, 'member_age_group') or 'unknown'}",
        f"Payer's stated denial reason: {_val(card, 'denial_reason') or 'not stated'}",
        f"Amount billed: {_val(card, 'amount_billed') if _val(card, 'amount_billed') is not None else 'not stated'}",
    ]
    return "Case card:\n" + "\n".join(lines) + "\n\nPlan the questions. Return JSON only."


def _usable_questions(raw) -> list[PlannedQuestion]:
    items = raw.get("questions") if isinstance(raw, dict) else None
    out: list[PlannedQuestion] = []
    seen = set()
    for it in items or []:
        if not isinstance(it, dict):
            continue
        q = " ".join(str(it.get("question") or "").split()).strip()
        if len(q) < MIN_QUESTION_CHARS or q.lower() in seen:
            continue
        if scope_check(q) == "out_of_scope":
            continue
        topic = str(it.get("topic") or "").strip().lower()
        out.append(PlannedQuestion(topic if topic in TOPICS else "other", q))
        seen.add(q.lower())
    return out


def _complete_plan(card, route: Route, provider, template: list[PlannedQuestion]) -> list[PlannedQuestion]:
    qs = _usable_questions(parse_model_json(provider.complete_parts(PLAN_SYSTEM_PROMPT, [{"type": "text", "text": _card_summary_for_plan(card, route)}], schema=PLAN_SCHEMA, max_tokens=PLAN_MAX_TOKENS)[0]))
    if len(qs) < MIN_USABLE:
        raise ValueError(f"only {len(qs)} usable questions")
    topics = {q.topic for q in qs}
    for need in ("appeal", "reason"):
        if need not in topics:
            qs.append(next(t for t in template if t.topic == need))
    if len(qs) > MAX_PLANNED:
        required = [next(q for q in qs if q.topic == "appeal"), next(q for q in qs if q.topic == "reason")]
        others = [q for q in qs if q not in required][: MAX_PLANNED - len(required)]
        qs = [q for q in qs if q in required or q in others]
    return qs


def plan_questions(card, route: Route, provider, stats: dict | None = None) -> list[PlannedQuestion]:
    """4 to 7 planned questions. `stats`, when given, receives source, tokens, latency and cost of the planning call."""
    template = template_questions(card, route)
    t = time.perf_counter()
    rec = {"source": "template", "model": getattr(provider, "model", "?"), "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "latency_ms": 0.0, "cost_usd": 0.0, "error": None}
    try:
        qs = _complete_plan(card, route, provider, template)
        rec["source"] = "model"
    except Exception as e:  # noqa: BLE001 - any planning failure means the fixed plan
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
        qs = template
    rec["latency_ms"] = round((time.perf_counter() - t) * 1000, 1)
    last = getattr(provider, "last_response", None) or {}
    usage = last.get("usage") or {} if isinstance(last, dict) else {}
    if rec["source"] == "model":
        rec["input_tokens"] = int(usage.get("prompt_tokens", 0) or 0)
        rec["output_tokens"] = int(usage.get("completion_tokens", 0) or 0)
        rec["reasoning_tokens"] = reasoning_tokens(provider)
        cost = getattr(provider, "cost", None)
        rec["cost_usd"] = float(cost(rec["input_tokens"], rec["output_tokens"])) if callable(cost) else 0.0
    if stats is not None:
        stats.update(rec)
    return qs


# ---- findings --------------------------------------------------------------


def _empty_investigation(model: str) -> dict:
    return {
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "questions_planned": 0,
        "questions_done": 0,
        "findings": [],
        "coverage": {"claims": 0, "supported": 0},
        "cost_usd": 0.0,
        "latency_ms": 0.0,
        "model": model,
        "error": None,
    }


def _finding_base(fid: str, q: PlannedQuestion, jurisdiction: str, model: str) -> dict:
    return {
        "id": fid,
        "question": q.question,
        "topic": q.topic,
        "jurisdiction": jurisdiction,
        "status": "not_settled",
        "answer": ABSTAIN_TEXT,
        "citations": [],
        "struck": [],
        "model": model,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "latency_ms": 0.0,
        "cost_usd": 0.0,
    }


def finding_from_answer(fid: str, q: PlannedQuestion, jurisdiction: str, ans) -> dict:
    """Map a generate.Answer to the finding shape the screen reads."""
    f = _finding_base(fid, q, jurisdiction, ans.model)
    f.update(model=ans.model, input_tokens=ans.input_tokens, output_tokens=ans.output_tokens, reasoning_tokens=ans.reasoning_tokens, latency_ms=ans.latency_ms, cost_usd=ans.cost_usd)
    if ans.error:
        f["answer"] = "Could not investigate this question: " + ans.error.split(":", 1)[0].strip()
        return f
    titles = {p["tag"]: p.get("title") for p in ans.passages}
    f["struck"] = [dict(s) for s in ans.struck]
    if ans.forced_abstain:
        f["status"] = "unsupported"
        f["answer"] = ans.original_answer
    elif ans.abstained:
        f["status"] = "not_settled"
        f["answer"] = ABSTAIN_TEXT
    else:
        f["status"] = "supported"
        f["answer"] = ans.answer
        f["citations"] = [{"doc_id": c.doc_id, "title": titles.get(c.passage), "page": c.page, "quote": c.quote, "overlap": c.overlap} for c in ans.citations]
    return f


def _finding_from_error(fid: str, q: PlannedQuestion, jurisdiction: str, model: str, exc: Exception, latency_ms: float) -> dict:
    f = _finding_base(fid, q, jurisdiction, model)
    f["answer"] = f"Could not investigate this question: {type(exc).__name__}"
    f["latency_ms"] = round(latency_ms, 1)
    return f


def _roll_up(inv: dict) -> None:
    fs = inv["findings"]
    supported = sum(1 for f in fs if f["status"] == "supported")
    unsupported = sum(1 for f in fs if f["status"] == "unsupported")
    inv["coverage"] = {"claims": supported + unsupported, "supported": supported}
    inv["questions_done"] = len(fs)
    inv["cost_usd"] = round(sum(f["cost_usd"] for f in fs) + float(inv.get("plan", {}).get("cost_usd", 0.0)), 6)


def _emit(on_progress, inv: dict, trace: Trace | None) -> None:
    if on_progress is None:
        return
    snap = copy.deepcopy(inv)
    if trace is not None:
        snap["trace"] = trace.to_dict()
    on_progress(snap)


def investigate_case(case: dict, retriever, provider, on_progress=None, k: int = PASSAGES_PER_QUESTION, max_tokens: int = ANSWER_MAX_TOKENS) -> dict:
    """Run the investigation for a stored case ({"case_id", "card", ...}). Returns the investigation object."""
    model = getattr(provider, "model", "?")
    inv = _empty_investigation(model)
    t0 = time.perf_counter()
    trace = Trace(f"case {case.get('case_id', '?') if isinstance(case, dict) else '?'}")
    try:
        card = case["card"]
        with trace.span("route"):
            route = route_case(card)
        trace.set(route=route.to_dict())
        plan_stats: dict = {}
        with trace.span("plan", model=model):
            questions = plan_questions(card, route, provider, stats=plan_stats)
        inv["plan"] = {**plan_stats, "questions": len(questions)}
        inv["questions_planned"] = len(questions) * len(route.jurisdictions)
        n = 0
        for q in questions:
            for j in route.jurisdictions:
                n += 1
                fid = f"f{n}"
                tq = time.perf_counter()
                with trace.span("question", id=fid, topic=q.topic, jurisdiction=j):
                    try:
                        with trace.span("retrieve", id=fid, jurisdiction=j, k=k):
                            hits = retriever.search(q.question, k=k, jurisdictions={j})
                        with trace.span("generate", id=fid, model=model, passages=len(hits)):
                            ans = answer_question(q.question, hits, provider, max_tokens=max_tokens)
                        finding = finding_from_answer(fid, q, j, ans)
                        finding["latency_ms"] = round((time.perf_counter() - tq) * 1000, 1)
                    except Exception as e:  # noqa: BLE001 - one question must not kill the case
                        finding = _finding_from_error(fid, q, j, model, e, (time.perf_counter() - tq) * 1000)
                inv["findings"].append(finding)
                _roll_up(inv)
                inv["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                _emit(on_progress, inv, trace)
        inv["status"] = "done"
    except Exception as e:  # noqa: BLE001 - recorded on the investigation, not raised
        inv["status"] = "failed"
        inv["error"] = f"{type(e).__name__}: {e}"[:500]
    _roll_up(inv)
    inv["finished_at"] = _now()
    inv["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    trace.set(status=inv["status"], findings=len(inv["findings"]), cost_usd=inv["cost_usd"])
    inv["trace"] = trace.to_dict()
    if on_progress is not None:
        on_progress(copy.deepcopy(inv))
    return inv


class LiveInvestigator:
    """investigate_case bound to a retriever and a provider (Muse Spark 1.3 through the Meta Model API)."""

    def __init__(self, retriever, provider):
        self.retriever = retriever
        self.provider = provider
        self.model = getattr(provider, "model", "?")

    def route(self, card) -> Route:
        return route_case(card)

    def investigate(self, case: dict, on_progress=None) -> dict:
        return investigate_case(case, self.retriever, self.provider, on_progress=on_progress)


# ---- fixture ---------------------------------------------------------------


def _manifest_rows() -> list[dict]:
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def _pick_doc(rows: list[dict], *needles: str, jurisdiction: str = "Florida", fallback: tuple[str, str] = ("fl-04", "Florida Medicaid Private Duty Nursing Services Coverage Policy")) -> tuple[str, str]:
    for needle in needles:
        for r in rows:
            if r.get("jurisdiction") == jurisdiction and needle in r.get("title", "").lower():
                return r["id"], r["title"]
    return fallback


SYNTHETIC = "[synthetic fixture quote, not from the document] "


class FixtureInvestigator:
    """No network, no index. The Sunshine Health sample (Florida Medicaid MMA, private duty
    nursing, under 21) investigated with five canned findings: three supported, one not
    settled, one unsupported, so the screen can show every state. Quotes are synthetic and
    say so; the document ids and titles are real rows of corpus/manifest.csv."""

    model = "fixture"

    def __init__(self, delay: float = 0.8):
        self.delay = delay
        rows = _manifest_rows()
        self.pdn = _pick_doc(rows, "private duty nursing", "home health")
        self.mma = _pick_doc(rows, "managed medical assistance (mma)", "scope of services", fallback=("fl-21", "SMMC Model Health Plan Contract, Exhibit II-A: Managed Medical Assistance (MMA) Program"))

    def route(self, card) -> Route:
        return route_case(card)

    def _findings(self, card) -> list[dict]:
        pdn_id, pdn_title = self.pdn
        mma_id, mma_title = self.mma
        service = str(_val(card, "service") or "private duty nursing")
        reason = _clean_reason(_val(card, "denial_reason")) or "services exceed the authorized amount"

        def cite(doc_id, title, page, quote, overlap=1.0):
            return {"doc_id": doc_id, "title": title, "page": page, "quote": SYNTHETIC + quote, "overlap": overlap}

        def struck(doc_id, title, page, quote):
            return {"doc_id": doc_id, "title": title, "page": page, "quote": SYNTHETIC + quote, "reason": STRUCK_NOT_FOUND}

        specs = [
            ("coverage", f"Is {service} covered under Florida Medicaid (MMA) for a member under 21?", "supported",
             "Yes. Florida Medicaid covers private duty nursing for recipients under 21 when it is medically necessary and prior authorized.",
             [cite(pdn_id, pdn_title, 3, "Florida Medicaid covers private duty nursing services for recipients under the age of 21 years when medically necessary.")], []),
            ("limits", f"What limits apply to {service} under Florida Medicaid (MMA), such as hours per day?", "supported",
             "Hours are limited to what the plan authorizes for the recipient; the authorization sets the hours per day and the period it covers.",
             [cite(pdn_id, pdn_title, 5, "Private duty nursing services are reimbursed for the number of hours authorized for the recipient in the prior authorization.")], []),
            ("conditions", f"What conditions or prior authorization does Florida Medicaid (MMA) require for {service}?", "unsupported",
             "Prior authorization must be renewed every 180 days with a new plan of care signed by the treating physician.",
             [], [struck(pdn_id, pdn_title, 4, "Authorization is renewed every 180 days with a plan of care signed by the treating physician.")]),
            ("appeal", "What are the appeal rights and the deadline to appeal a denial under Florida Medicaid (MMA)?", "supported",
             "The member may appeal to the plan within 60 days of the notice and may ask for a Medicaid fair hearing after the plan appeal.",
             [cite(mma_id, mma_title, 41, "An enrollee may file an appeal within sixty (60) days of the date on the notice of adverse benefit determination.")], []),
            ("reason", f"What do the rules say when {reason}?", "not_settled", ABSTAIN_TEXT, [], []),
        ]
        out = []
        for i, (topic, question, status, answer, citations, struck_list) in enumerate(specs, start=1):
            f = _finding_base(f"f{i}", PlannedQuestion(topic, question), "Florida", self.model)
            f.update(status=status, answer=answer, citations=citations, struck=struck_list, latency_ms=round(self.delay * 1000, 1))
            out.append(f)
        return out

    def investigate(self, case: dict, on_progress=None) -> dict:
        inv = _empty_investigation(self.model)
        t0 = time.perf_counter()
        trace = Trace(f"case {case.get('case_id', '?')} (fixture)")
        trace.set(synthetic=True, route=self.route(case.get("card", {})).to_dict())
        findings = self._findings(case.get("card", {}))
        inv["questions_planned"] = len(findings)
        inv["plan"] = {"source": "fixture", "model": self.model, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "latency_ms": 0.0, "cost_usd": 0.0, "error": None, "questions": len(findings)}
        for i, f in enumerate(findings):
            if i and self.delay:
                time.sleep(self.delay)
            with trace.span("question", id=f["id"], topic=f["topic"], jurisdiction=f["jurisdiction"]):
                pass
            inv["findings"].append(f)
            _roll_up(inv)
            inv["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            _emit(on_progress, inv, trace)
        inv["status"] = "done"
        inv["finished_at"] = _now()
        inv["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        trace.set(status="done", findings=len(findings), cost_usd=0.0)
        inv["trace"] = trace.to_dict()
        if on_progress is not None:
            on_progress(copy.deepcopy(inv))
        return inv

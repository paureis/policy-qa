"""Investigation agent: a confirmed case card becomes a list of findings.

Steps (PRODUCT.md vocabulary): Routing, then Investigation.

- route_case(card): which jurisdictions' documents govern (Florida, Federal, or both
  side by side for dual-eligible and ambiguous cases), with a one-sentence reason.
- plan_questions(card, route, provider): one Muse Spark call plans 4 to 7 questions a
  policy document could answer (coverage, limits, conditions, exclusions, appeal, the
  letter's reason). Appeal questions ask about the program's appeal process and never
  name the service, so the grievance and fair hearing documents can reach the model.
  Any failure falls back to template_questions; tokens and cost of a reply that came
  back but could not be used are still recorded. A planned question is dropped when it
  asks for medical advice (intake's scope_check plus a stricter planner pattern set) or
  names no coverage, billing, or appeal rule word (planned_question_allowed).
- investigate_case(case, retriever, provider, on_progress): for each question and each
  jurisdiction, retrieve a pool of candidates with the jurisdiction filter, drop
  documents about another program (program_excludes), keep 8 passages with at most 3
  from any one document (select_passages), and answer with enforced citations; the
  user message names the program. Answers run three at a time in a thread pool; the
  findings keep the planned order. Each answer maps to a finding:
  `supported` (a citation survived the verifier), `not_settled` (the model abstained),
  `unsupported` (the model answered but every citation was struck; the original answer
  is kept so the screen can strike it out), or `error` (retrieval or the model call
  raised, or the reply could not be parsed; `answer` is empty and `error` says why).
  Errors are counted in coverage.errors and never as claims. Only a failure outside the
  loop fails the investigation. on_progress(partial) fires after every completed
  finding, with questions_done = findings completed so far.
- FixtureInvestigator: no network, no index; a realistic synthetic investigation for the
  Sunshine Health sample with all three answer states, quotes marked synthetic, and
  Federal findings too when the route is dual or Medicare only.

Finding shape: {id, question, topic, jurisdiction, status, answer, citations, struck,
passages: [{chunk_id, doc_id, title, page}] (what the model saw, in order), error,
model, input_tokens, output_tokens, reasoning_tokens, latency_ms, cost_usd}.
Investigation coverage: {claims, supported, errors}.

Muse Spark 1.3 is a reasoning model: completion tokens include its reasoning, so every
call gets a generous max_tokens and reasoning tokens are recorded next to the others.
"""
from __future__ import annotations

import copy
import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

from .generate import ABSTAIN_TEXT, STRUCK_NOT_FOUND, answer_question, parse_model_json, reasoning_tokens
from .intake import scope_check
from .trace import Trace

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "corpus" / "manifest.csv"

TOPICS = ("coverage", "limits", "conditions", "exclusions", "appeal", "reason", "other")
FINDING_STATUSES = ("supported", "not_settled", "unsupported", "error")
MIN_PLANNED, MAX_PLANNED, MIN_USABLE = 4, 7, 3
MIN_QUESTION_CHARS = 15
PLAN_MAX_TOKENS = 2000
ANSWER_MAX_TOKENS = 2000
PASSAGES_PER_QUESTION = 8
PER_DOC_CAP = 3  # at most this many passages from one document, so one document cannot fill the list
CANDIDATE_MULTIPLIER = 4  # candidates pulled per passage kept, before the program filter and the cap
ANSWER_WORKERS = 3  # answers run this many at a time

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
1. Each question names the service and the program in plain words, as a reader with no insurance background would say them. One question per line of inquiry. The exception is the appeal question (rule 2).
2. Topics, one per question: coverage (is the service covered), limits (hours, visits, amounts, frequency), conditions (prior authorization, medical necessity criteria, documentation), exclusions, appeal, reason (what the rules say about the payer's stated denial reason), other. An appeal question asks about the program's appeal process: the adverse benefit determination, the grievance or appeal, the fair hearing, the deadline, and where to file. Appeal questions name the program but do not name the service.
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
        PlannedQuestion("appeal", f"How does a member appeal an adverse benefit determination under {label}: the appeal or grievance, the fair hearing, the deadline, and where to file?"),
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


# Planned questions only; intake's scope_check (for whole letters) is unchanged. A planned
# question is a query we send ourselves, so the bar is stricter: any treatment-shaped
# phrasing drops it, and it must name at least one coverage, billing, or appeal rule word.
_PLANNED_MEDICAL = re.compile(
    r"\b(which|what)\s+(medication|medicine|drug)s?\b|\bswitch(ed|ing)? to\b|\binstead of\b"
    r"|\bmedically necessary for\b|\bdiagnosis of\b|\btreatment for\b|\bappropriate for the patient\b"
    r"|\bis it safe\b|\bshould the (member|patient) take\b",
    re.I,
)
# Word starts, so inflections count (covered, coverage, limits, authorized, approved, excluded, requirements, billed, denied).
_RULE_WORDS = re.compile(
    r"\b(cover|limit|authoriz|approv|appeal|deadline|exclu|requir|polic|rule|hours?\b|units?\b|fil(e|ed|es|ing)\b"
    r"|grievance|hearing|reimburs|bill|denial|denied|deny|prior\b)",
    re.I,
)


def planned_question_allowed(question: str) -> bool:
    """False when a planned question asks for medical advice or names no rule word (see the patterns above)."""
    if scope_check(question) == "out_of_scope" or _PLANNED_MEDICAL.search(question):
        return False
    return bool(_RULE_WORDS.search(question))


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
        if not planned_question_allowed(q):
            continue
        topic = str(it.get("topic") or "").strip().lower()
        out.append(PlannedQuestion(topic if topic in TOPICS else "other", q))
        seen.add(q.lower())
    return out


def _plan_from_reply(text: str, template: list[PlannedQuestion]) -> list[PlannedQuestion]:
    qs = _usable_questions(parse_model_json(text))
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
    reply: tuple[int, int] | None = None
    try:
        text, n_in, n_out = provider.complete_parts(PLAN_SYSTEM_PROMPT, [{"type": "text", "text": _card_summary_for_plan(card, route)}], schema=PLAN_SCHEMA, max_tokens=PLAN_MAX_TOKENS)
        reply = (int(n_in or 0), int(n_out or 0))
        qs = _plan_from_reply(text, template)
        rec["source"] = "model"
    except Exception as e:  # noqa: BLE001 - any planning failure means the fixed plan
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
        qs = template
    rec["latency_ms"] = round((time.perf_counter() - t) * 1000, 1)
    if reply is not None:  # the model replied: its tokens were spent whether or not the plan was used
        rec["input_tokens"], rec["output_tokens"] = reply
        rec["reasoning_tokens"] = reasoning_tokens(provider)
        cost = getattr(provider, "cost", None)
        rec["cost_usd"] = float(cost(*reply)) if callable(cost) else 0.0
    if stats is not None:
        stats.update(rec)
    return qs


# ---- passages ----------------------------------------------------------------

_KIDCARE_TITLE = re.compile(r"kidcare|healthy kids", re.I)


@lru_cache(maxsize=1)
def _kidcare_doc_ids() -> frozenset[str]:
    return frozenset(r["id"] for r in _manifest_rows() if _KIDCARE_TITLE.search(r.get("title", "")))


def program_excludes(program: str | None) -> set[str]:
    """Document ids that are about another program, so their passages are not shown.

    A heuristic on corpus/manifest.csv titles, not a classification of every page:
    for Florida Medicaid MMA and LTC cases, documents whose title mentions KidCare or
    Healthy Kids (a separate program with its own benefits) are excluded. KidCare cases
    and Medicare cases exclude nothing; an unknown program excludes nothing.
    """
    if program in ("florida_medicaid_mma", "florida_medicaid_ltc"):
        return set(_kidcare_doc_ids())
    return set()


def program_sentence(route: Route, jurisdiction: str) -> str:
    """The case sentence the answer prompt carries. On a dual route the other jurisdiction's
    half names that jurisdiction's program (Medicare or Florida Medicaid), so its own
    passages are not ruled out."""
    program = route.program
    if program.startswith("florida_") and jurisdiction == "Florida" or program.startswith("medicare_") and jurisdiction == "Federal":
        label = program_label(program)
    else:
        label = "Medicare" if jurisdiction == "Federal" else "Florida Medicaid"
    return f"The case is under {label}. Prefer passages about that program; if a passage is about another program, do not use it."


def select_passages(hits: list, k: int = PASSAGES_PER_QUESTION, per_doc_cap: int | None = PER_DOC_CAP, exclude=frozenset()) -> list:
    """The first `k` hits in rank order, skipping excluded documents and any hit past `per_doc_cap` from its document."""
    out, per_doc = [], {}
    for h in hits:
        doc = h.chunk.get("doc_id")
        if doc in exclude:
            continue
        if per_doc_cap is not None and per_doc.get(doc, 0) >= per_doc_cap:
            continue
        per_doc[doc] = per_doc.get(doc, 0) + 1
        out.append(h)
        if len(out) >= k:
            break
    return out


def retrieve_passages(retriever, question: str, jurisdiction: str, k: int = PASSAGES_PER_QUESTION, per_doc_cap: int | None = PER_DOC_CAP, exclude=frozenset()) -> list:
    """Pull k x CANDIDATE_MULTIPLIER candidates in one jurisdiction, then filter and cap them down to k.
    Only `k` and `jurisdictions` are passed, so the API's wrapped search (which fixes `candidates`) works too."""
    hits = retriever.search(question, k=k * CANDIDATE_MULTIPLIER, jurisdictions={jurisdiction})
    return select_passages(hits, k=k, per_doc_cap=per_doc_cap, exclude=exclude)


def _passage_refs(items) -> list[dict]:
    """[{chunk_id, doc_id, title, page}] from Hits or from formatted passages."""
    out = []
    for it in items:
        c = it.chunk if hasattr(it, "chunk") else it
        out.append({"chunk_id": c.get("chunk_id"), "doc_id": c.get("doc_id"), "title": c.get("title"), "page": c.get("page")})
    return out


# ---- findings --------------------------------------------------------------


def _empty_investigation(model: str) -> dict:
    return {
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "questions_planned": 0,
        "questions_done": 0,
        "findings": [],
        "coverage": {"claims": 0, "supported": 0, "errors": 0},
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
        "passages": [],
        "error": None,
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
    f["passages"] = _passage_refs(ans.passages)
    if ans.error:
        f.update(status="error", answer="", error=ans.error[:300])
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


def _finding_from_error(fid: str, q: PlannedQuestion, jurisdiction: str, model: str, exc: BaseException, latency_ms: float, passages: list[dict] | None = None) -> dict:
    f = _finding_base(fid, q, jurisdiction, model)
    f.update(status="error", answer="", error=f"{type(exc).__name__}: {exc}"[:300], passages=list(passages or []), latency_ms=round(latency_ms, 1))
    return f


def _roll_up(inv: dict) -> None:
    fs = inv["findings"]
    supported = sum(1 for f in fs if f["status"] == "supported")
    unsupported = sum(1 for f in fs if f["status"] == "unsupported")
    errors = sum(1 for f in fs if f["status"] == "error")
    inv["coverage"] = {"claims": supported + unsupported, "supported": supported, "errors": errors}
    inv["questions_done"] = len(fs)
    inv["cost_usd"] = round(sum(f["cost_usd"] for f in fs) + float(inv.get("plan", {}).get("cost_usd", 0.0)), 6)


def _emit(on_progress, inv: dict, trace: Trace | None) -> None:
    if on_progress is None:
        return
    snap = copy.deepcopy(inv)
    if trace is not None:
        d = trace.to_dict()
        snap["trace"] = copy.deepcopy({**d, "spans": list(d["spans"])})  # workers may still be appending spans
    on_progress(snap)


def _answer_one(fid: str, q: PlannedQuestion, jurisdiction: str, route: Route, retriever, provider, k: int, per_doc_cap: int | None, exclude: set[str], max_tokens: int, trace: Trace, model: str) -> dict:
    """One question in one jurisdiction, run in a worker thread. Never raises."""
    tq = time.perf_counter()
    hits: list = []
    with trace.span("question", id=fid, topic=q.topic, jurisdiction=jurisdiction):
        try:
            with trace.span("retrieve", id=fid, jurisdiction=jurisdiction, k=k):
                hits = retrieve_passages(retriever, q.question, jurisdiction, k=k, per_doc_cap=per_doc_cap, exclude=exclude)
            with trace.span("generate", id=fid, model=model, passages=len(hits)):
                ans = answer_question(q.question, hits, provider, max_tokens=max_tokens, context=program_sentence(route, jurisdiction))
            finding = finding_from_answer(fid, q, jurisdiction, ans)
        except Exception as e:  # noqa: BLE001 - one question must not kill the case
            finding = _finding_from_error(fid, q, jurisdiction, model, e, 0.0, passages=_passage_refs(hits))
    finding["latency_ms"] = round((time.perf_counter() - tq) * 1000, 1)
    return finding


def investigate_case(case: dict, retriever, provider, on_progress=None, k: int = PASSAGES_PER_QUESTION, max_tokens: int = ANSWER_MAX_TOKENS, per_doc_cap: int | None = PER_DOC_CAP, max_workers: int = ANSWER_WORKERS) -> dict:
    """Run the investigation for a stored case ({"case_id", "card", ...}). Returns the investigation object.

    Answers run `max_workers` at a time; findings fill their planned slot, so the list is
    always in planned order. on_progress runs on the calling thread after each completion.
    latency_ms is wall time; cost_usd sums the plan and every answer."""
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
        jobs = [(q, j) for q in questions for j in route.jurisdictions]
        inv["questions_planned"] = len(jobs)
        exclude = program_excludes(route.program)
        slots: list[dict | None] = [None] * len(jobs)
        with ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="investigate") as pool:
            futures = {pool.submit(_answer_one, f"f{i + 1}", q, j, route, retriever, provider, k, per_doc_cap, exclude, max_tokens, trace, model): i for i, (q, j) in enumerate(jobs)}
            for fut in as_completed(futures):
                i = futures[fut]
                try:
                    slots[i] = fut.result()
                except BaseException as e:  # noqa: BLE001 - _answer_one does not raise; belt and braces
                    q, j = jobs[i]
                    slots[i] = _finding_from_error(f"f{i + 1}", q, j, model, e, 0.0)
                inv["findings"] = [f for f in slots if f is not None]
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


def _fixture_passages(citations: list[dict], struck: list[dict]) -> list[dict]:
    """The passages a fixture finding claims the model saw: one per cited or struck page, marked as fixture chunks."""
    out, seen = [], set()
    for c in citations + struck:
        key = (c["doc_id"], c["page"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"chunk_id": f"{c['doc_id']}:p{int(c['page']):03d}:fixture", "doc_id": c["doc_id"], "title": c["title"], "page": c["page"]})
    return out


class FixtureInvestigator:
    """No network, no index. The Sunshine Health sample (Florida Medicaid MMA, private duty
    nursing, under 21) investigated with five canned Florida findings: three supported, one
    not settled, one unsupported, so the screen can show every state. The fixture honors
    the route: a dual route (for example the same card with a member 65 or older) adds
    five Federal findings about Medicare, interleaved per question as the live agent does,
    and a Medicare-only route shows only those. Quotes are synthetic and say so; the
    document ids and titles are real rows of corpus/manifest.csv."""

    model = "fixture"

    def __init__(self, delay: float = 0.8):
        self.delay = delay
        rows = _manifest_rows()
        self.pdn = _pick_doc(rows, "private duty nursing", "home health")
        self.mma = _pick_doc(rows, "managed medical assistance (mma)", "scope of services", fallback=("fl-21", "SMMC Model Health Plan Contract, Exhibit II-A: Managed Medical Assistance (MMA) Program"))
        self.fed_home = _pick_doc(rows, "medicare & home health care", "home health services", jurisdiction="Federal", fallback=("fed-24", "Medicare & Home Health Care (CMS Product No. 10969)"))
        self.fed_appeal = _pick_doc(rows, "appeals process", jurisdiction="Federal", fallback=("fed-17", "Medicare Parts A & B Appeals Process (MLN006562)"))

    def route(self, card) -> Route:
        return route_case(card)

    @staticmethod
    def _cite(doc, page, quote, overlap=1.0):
        return {"doc_id": doc[0], "title": doc[1], "page": page, "quote": SYNTHETIC + quote, "overlap": overlap}

    @staticmethod
    def _struck(doc, page, quote):
        return {"doc_id": doc[0], "title": doc[1], "page": page, "quote": SYNTHETIC + quote, "reason": STRUCK_NOT_FOUND}

    def _florida_specs(self, card) -> list[tuple]:
        service = str(_val(card, "service") or "private duty nursing")
        reason = _clean_reason(_val(card, "denial_reason")) or "services exceed the authorized amount"
        cite, struck = self._cite, self._struck
        return [
            ("coverage", f"Is {service} covered under Florida Medicaid (MMA) for a member under 21?", "supported",
             "Yes. Florida Medicaid covers private duty nursing for recipients under 21 when it is medically necessary and prior authorized.",
             [cite(self.pdn, 3, "Florida Medicaid covers private duty nursing services for recipients under the age of 21 years when medically necessary.")], []),
            ("limits", f"What limits apply to {service} under Florida Medicaid (MMA), such as hours per day?", "supported",
             "Hours are limited to what the plan authorizes for the recipient; the authorization sets the hours per day and the period it covers.",
             [cite(self.pdn, 5, "Private duty nursing services are reimbursed for the number of hours authorized for the recipient in the prior authorization.")], []),
            ("conditions", f"What conditions or prior authorization does Florida Medicaid (MMA) require for {service}?", "unsupported",
             "Prior authorization must be renewed every 180 days with a new plan of care signed by the treating physician.",
             [], [struck(self.pdn, 4, "Authorization is renewed every 180 days with a plan of care signed by the treating physician.")]),
            ("appeal", "How does a member appeal an adverse benefit determination under Florida Medicaid (MMA): the appeal or grievance, the fair hearing, the deadline, and where to file?", "supported",
             "The member may appeal to the plan within 60 days of the notice and may ask for a Medicaid fair hearing after the plan appeal.",
             [cite(self.mma, 41, "An enrollee may file an appeal within sixty (60) days of the date on the notice of adverse benefit determination.")], []),
            ("reason", f"What do the rules say when {reason}?", "not_settled", ABSTAIN_TEXT, [], []),
        ]

    def _federal_specs(self, card) -> list[tuple]:
        service = str(_val(card, "service") or "private duty nursing")
        reason = _clean_reason(_val(card, "denial_reason")) or "services exceed the authorized amount"
        cite, struck = self._cite, self._struck
        return [
            ("coverage", f"Is {service} covered under Medicare for a member who is 65 or older?", "supported",
             "Medicare covers part-time or intermittent skilled nursing care at home for a homebound member under a plan of care; it does not cover full-time nursing care at home.",
             [cite(self.fed_home, 4, "Medicare covers part-time or intermittent skilled nursing care if you are homebound and a doctor certifies you need it."),
              cite(self.fed_home, 9, "Medicare does not pay for 24-hour-a-day care at home.")], []),
            ("limits", f"What limits apply to {service} under Medicare, such as hours per day?", "unsupported",
             "Medicare pays for up to 35 hours a week of combined skilled nursing and aide services.",
             [], [struck(self.fed_home, 6, "Medicare covers up to 35 hours a week of skilled nursing and home health aide services combined.")]),
            ("conditions", f"What conditions or prior authorization does Medicare require for {service}?", "not_settled", ABSTAIN_TEXT, [], []),
            ("appeal", "How does a member appeal a coverage denial under Medicare: the redetermination, the deadline, and where to file?", "supported",
             "The member asks for a redetermination within 120 days of receiving the notice, filed with the contractor named on the notice.",
             [cite(self.fed_appeal, 3, "A redetermination request must be filed within 120 days from the date of receipt of the initial determination.")], []),
            ("reason", f"What do the Medicare rules say when {reason}?", "not_settled", ABSTAIN_TEXT, [], []),
        ]

    def _findings(self, card, route: Route | None = None) -> list[dict]:
        route = route or route_case(card)
        by_j = {"Florida": self._florida_specs(card), "Federal": self._federal_specs(card)}
        rows = [(spec, j) for i in range(5) for j in route.jurisdictions for spec in [by_j[j][i]]]
        out = []
        for n, ((topic, question, status, answer, citations, struck_list), j) in enumerate(rows, start=1):
            f = _finding_base(f"f{n}", PlannedQuestion(topic, question), j, self.model)
            f.update(status=status, answer=answer, citations=citations, struck=struck_list, passages=_fixture_passages(citations, struck_list), latency_ms=round(self.delay * 1000, 1))
            out.append(f)
        return out

    def investigate(self, case: dict, on_progress=None) -> dict:
        inv = _empty_investigation(self.model)
        t0 = time.perf_counter()
        trace = Trace(f"case {case.get('case_id', '?')} (fixture)")
        card = case.get("card", {})
        route = self.route(card)
        trace.set(synthetic=True, route=route.to_dict())
        findings = self._findings(card, route)
        inv["questions_planned"] = len(findings)
        inv["plan"] = {"source": "fixture", "model": self.model, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "latency_ms": 0.0, "cost_usd": 0.0, "error": None, "questions": 5}
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

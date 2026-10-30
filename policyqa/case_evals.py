"""Denial-case evaluation: how often is the verdict right on the 30 reviewed letters in cases/?

Per case the harness reads the letter text and runs it through the API's own code path, with no
HTTP: the intake route function (`api.main.case_intake`, text path: length check, `scope_check`,
then the configured extractor), then `api.main.case_investigate`, which routes the case and runs
the investigation, Steelman and Verdict, the letter, and the critic in the API's background
thread; the harness waits for that thread. Providers are chosen exactly as the API chooses them
(live when POLICYQA_LLM_* are set and the index exists, the fixtures otherwise). The run uses a
private in-memory case store, so no eval case lands in data/cases or in the running server.

Scoring (`score`):
- `got` is the verdict outcome. A case is correct when got == intended_outcome, or when got is in
  that case's ALTERNATES set.
- dc-011 is scored on refusal: correct only when intake refuses it as `out_of_scope` (no verdict,
  no letter); any verdict, or a different refusal, is wrong.
- A refused ordinary case, a failed stage, or an exception in the harness is wrong, and the row
  carries `error` (or `refused`); one failing case never stops the run.
- A verdict model failure (the not_settled template with `error`), or an investigation whose
  findings all errored, is an error, never a real not_settled; `stage_errors` names each stage.
- A template letter (letter `error`) does not change the score but is left out of the letter
  verification and struck rates (`letter_failures`); a critic failure does not change the score
  either (the product keeps the letter as drafted) and is counted as `critic_failures`.
- dc-030 (a commercial plan outside the corpus) expects not_settled; the summary records the
  route's program, whether it is "unknown", and `route_outside_corpus` (the router says no
  document in the corpus governs the plan; added Oct 26 for employer and commercial payers).

Reported per case: verdict, refusal, route, findings by status, letter verification, the critic's
rounds and issues, cost per stage and in total, and seconds. Since Oct 27 (second tuning pass) also,
so every miss traces to a stage: `proposed_outcome` (the model's call before any code guard), the
verdict's `decisive_fact` and `settled_by`, `relies_on_exception`, the plan's source and
`planned_questions`, `exceptions` (each exception finding, relevant or not, and why:
policyqa.relevance), `hinge` (which findings' passages reached the case's hinge page and which quote
it), and `miss` ({stage, why}: miss_stage). The summary adds accuracy overall and by intended
outcome, program, and jurisdiction, the refusal result, the letter verification and struck rates,
critic acceptance, mean and p50 cost and seconds, the list of wrong cases, and the misses by stage.
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = ROOT / "cases" / "cases.csv"
DEFAULT_LETTERS = ROOT / "cases" / "letters"
CASE_TIMEOUT_S = 900  # one case's chain; a live case took about a minute on Oct 26

# Outcomes accepted besides intended_outcome. Both blind reviewers on Oct 26 said these readings
# are defensible:
# - dc-008: not settled, when the answer asks whether days 46 to 51 were emergency services as
#   defined in fl-01 (59G-1.010); the same page (fl-14 p5) covers emergency days past the limit.
# - dc-020: the intended verdict is not settled, but "the records we received do not show" can be
#   read as consistent with the rule (transport covered only when other means would endanger health).
ALTERNATES: dict[str, set[str]] = {"dc-008": {"not_settled"}, "dc-020": {"consistent"}}

# Scored on refusal, not on a verdict: the treatment question disguised as a pharmacy notice.
REFUSAL_IDS = {"dc-011"}
REFUSAL_CODE = "out_of_scope"
# A program outside the corpus: the route should say that no document in the corpus governs it (route.outside_corpus).
OUTSIDE_CORPUS_IDS = {"dc-030"}
# Intake codes that mean "the product declined the letter", recorded as `refused`, not as `error`.
INTAKE_REFUSALS = ("out_of_scope", "not_a_denial_letter")
FINDING_STATUSES = ("supported", "not_settled", "unsupported", "error")
STAGES = ("intake", "investigation", "verdict", "letter", "critique")


# ---- scoring -------------------------------------------------------------------


def score(case_id: str, intended: str, got: str | None, refused: str | None = None, error: str | None = None) -> bool:
    """True when the case counts as right. See the module docstring for the rule."""
    if error:
        return False
    if case_id in REFUSAL_IDS:
        return refused == REFUSAL_CODE and got is None
    if refused or got is None:
        return False
    return got == intended or got in ALTERNATES.get(case_id, set())


# ---- cases ---------------------------------------------------------------------


def load_cases(path: Path = DEFAULT_CASES, ids: list[str] | None = None, limit: int | None = None) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if ids:
        known = {r["id"] for r in rows}
        missing = [i for i in ids if i not in known]
        if missing:
            raise ValueError(f"unknown case ids: {', '.join(missing)}")
        wanted = set(ids)
        rows = [r for r in rows if r["id"] in wanted]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be 1 or more (leave it out to run every case)")
        rows = rows[:limit]
    return rows


def intended_of(row: dict) -> str:
    return REFUSAL_CODE if row["id"] in REFUSAL_IDS else row["intended_outcome"]


# ---- the chain -------------------------------------------------------------------


def api_chain(case_id: str, text: str) -> dict:
    """The API's own path for one letter: {"refused": code or None, "case": the finished case or None}."""
    import asyncio

    from fastapi import HTTPException

    import api.main as m
    from policyqa.second_opinion import second_wait_s

    t0 = time.perf_counter()
    try:
        case = asyncio.run(m.case_intake(file=None, text=text))
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
        if detail.get("code") in INTAKE_REFUSALS:
            return {"refused": detail["code"], "case": None}
        raise RuntimeError(f"intake {e.status_code} {detail.get('code')}: {detail.get('message')}") from None
    cid = case["case_id"]
    m.case_investigate(cid)
    thread = m.INVESTIGATION_THREADS.pop(cid, None)  # absent when the API runs the chain inline
    if thread is not None:
        thread.join(CASE_TIMEOUT_S)
        if thread.is_alive():
            raise TimeoutError(f"the chain did not finish in {CASE_TIMEOUT_S} s (last status {(m.STORE.get(cid) or {}).get('status')})")
    seconds = time.perf_counter() - t0  # the chain to its terminal status; the second opinion's extra wait is not in it
    bound = second_wait_s()
    finished = m.wait_for_second_opinion(cid, bound)
    case = m.STORE.get(cid)
    if not finished and case is not None:
        # Recorded on the row's copy only: the thread may still land in the store later.
        case["second_opinion"] = {**(case.get("second_opinion") or {}), "status": "timeout", "error": f"no answer within {bound:g} s"}
    return {"refused": None, "case": case, "seconds": seconds}


@contextmanager
def private_store():
    """Point the API at a memory-only case store for the run, then put the real one back."""
    import api.main as m
    from api.cases import CaseStore

    saved = m.STORE
    m.STORE = CaseStore(None)
    try:
        yield m.STORE
    finally:
        m.STORE = saved


@contextmanager
def critic_switch(enabled: bool):
    """--no-critic: RECOURSE_CRITIC_ROUNDS=0 for this run only (the API reads it per case)."""
    from policyqa.critic import ROUNDS_ENV

    if enabled:
        yield
        return
    old = os.environ.get(ROUNDS_ENV)
    os.environ[ROUNDS_ENV] = "0"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(ROUNDS_ENV, None)
        else:
            os.environ[ROUNDS_ENV] = old


# ---- one row ---------------------------------------------------------------------


def _cost(stage) -> float:
    try:
        return float((stage or {}).get("cost_usd") or 0)
    except (TypeError, ValueError):
        return 0.0


def stage_errors(case: dict) -> list[dict]:
    """Every stage that failed or fell back to a template, as [{stage, error, fatal}].

    Fatal (the row is an error and counts as wrong): a stage with status "failed" up to the letter;
    a verdict with `error` set (a model failure gives the not_settled template with status "done");
    an investigation whose findings errored with none supported (the verdict then has nothing to
    argue from and returns the not_settled template without an error). Not fatal: a letter with
    `error` (a template letter; left out of the verification rates) and a critic failure (the
    product keeps the letter as drafted by design)."""
    out: list[dict] = []
    inv = case.get("investigation") or {}
    findings = [f for f in inv.get("findings") or [] if isinstance(f, dict)]
    n_err = sum(1 for f in findings if f.get("status") == "error")
    n_sup = sum(1 for f in findings if f.get("status") == "supported")
    if inv.get("status") == "failed":
        out.append({"stage": "investigation", "error": inv.get("error") or "failed", "fatal": True})
    elif n_err and not n_sup:
        first = next((f.get("error") for f in findings if f.get("status") == "error" and f.get("error")), None)
        out.append({"stage": "investigation", "error": f"{n_err} of {len(findings)} findings errored, none supported" + (f" ({first})" if first else ""), "fatal": True})
    for field in ("verdict", "letter"):
        stage = case.get(field)
        if not isinstance(stage, dict):
            continue
        if stage.get("status") == "failed":
            out.append({"stage": field, "error": stage.get("error") or "failed", "fatal": True})
        elif stage.get("error"):
            out.append({"stage": field, "error": stage["error"], "fatal": field == "verdict"})
    critique = case.get("critique")
    if isinstance(critique, dict) and (critique.get("error") or critique.get("status") == "failed"):
        out.append({"stage": "critique", "error": critique.get("error") or "failed", "fatal": False})
    if not out and case.get("status") != "reviewed":
        out.append({"stage": "chain", "error": f"the case ended at status {case.get('status')!r}, not reviewed", "fatal": True})
    return out


def planned_questions(inv: dict) -> list[dict]:
    """The planner's questions, once each and in planned order ({topic, question}); a dual route asks each twice."""
    out, seen = [], set()
    for f in (inv or {}).get("findings") or []:
        if not isinstance(f, dict):
            continue
        key = (f.get("topic"), f.get("question"))
        if key not in seen:
            seen.add(key)
            out.append({"topic": f.get("topic"), "question": f.get("question")})
    return out


def _page(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def hinge_trace(row: dict, inv: dict) -> dict | None:
    """Where the case's hinge page (cases.csv hinge_doc_id, hinge_page) went: the findings whose passages
    reached it, and the supported findings that quote it. None when the case has no hinge page."""
    doc, page = (row.get("hinge_doc_id") or "").strip(), _page(row.get("hinge_page"))
    if not doc or page is None:
        return None
    fs = [f for f in (inv or {}).get("findings") or [] if isinstance(f, dict)]

    def hit(items) -> bool:
        return any(i.get("doc_id") == doc and _page(i.get("page")) == page for i in items or [])

    return {"doc_id": doc, "page": page, "reached": [f.get("id") for f in fs if hit(f.get("passages"))],
            "cited": [f.get("id") for f in fs if f.get("status") == "supported" and hit(f.get("citations"))]}


GUARDED = {"payer_determination": "the decisive fact is the payer's own determination", "outside_documents": "the decisive fact is in a document outside the corpus"}


def miss_stage(rec: dict) -> dict | None:
    """The stage a wrong row traces to, with one line why ({stage, why}); None for a right row.

    In order: an error names its failed stage (or "harness" when the chain itself raised or timed out); a
    refusal is "intake"; a model proposal that was right before a code guard changed it is "verdict" (the
    guard); then by the hinge page: quoted in a supported finding means the evidence was there ("verdict"),
    reached but never quoted is "answer", never reached is "retrieval", or "planning" when no planned
    question asked for an exception or a second rule either. Without a hinge page the miss is "verdict"."""
    from .relevance import is_exception_finding

    if rec.get("correct"):
        return None
    if rec.get("error"):
        stages = [e["stage"] for e in rec.get("stage_errors") or []]
        return {"stage": stages[0] if stages else "harness", "why": f"error: {rec['error']}"[:300]}
    if rec.get("refused"):
        return {"stage": "intake", "why": f"intake refused the letter ({rec['refused']})"}
    got, proposed, intended = rec.get("got"), rec.get("proposed_outcome"), rec.get("intended")
    if got is None:
        return {"stage": "verdict", "why": "no verdict"}
    exc = ", ".join(f"{e['finding_id']} {str(e.get('state') or 'unchecked').replace('_', ' ')}" for e in rec.get("exceptions") or [] if e.get("status") == "supported")
    exc_part = f"; exceptions: {exc}" if exc else "; no exception finding was supported"
    fact = f"decisive fact \"{rec.get('decisive_fact')}\" ({rec.get('settled_by')})" if rec.get("decisive_fact") else "no decisive fact named"
    if proposed and proposed != got and score(rec["id"], intended, proposed):
        if rec.get("settled_by") in GUARDED:
            how = GUARDED[rec["settled_by"]]
        elif rec.get("relies_on_exception"):
            how = "the exception it relied on does not name the letter's facts"
        else:
            how = "the rule had no valid citation"
        return {"stage": "verdict", "why": f"code guard: the model proposed {proposed}, and a guard made it {got} because {how}{exc_part}"}
    hinge = rec.get("hinge")
    if hinge:
        where = f"{hinge['doc_id']} p{hinge['page']}"
        if hinge["cited"]:
            return {"stage": "verdict", "why": f"the hinge page {where} was quoted ({', '.join(hinge['cited'])}); the model proposed {proposed}, {fact}{exc_part}"}
        if hinge["reached"]:
            return {"stage": "answer", "why": f"the hinge page {where} reached the model ({', '.join(hinge['reached'])}) but no verified quote came from it"}
        if not any(is_exception_finding(q) for q in rec.get("planned_questions") or []):
            return {"stage": "planning", "why": f"no question's passages reached the hinge page {where}, and no planned question asked for an exception or a second rule"}
        return {"stage": "retrieval", "why": f"no question's passages reached the hinge page {where} ({len(rec.get('planned_questions') or [])} questions planned, plan from the {rec.get('plan_source')})"}
    return {"stage": "verdict", "why": f"the model proposed {proposed}, {fact}{exc_part}"}


def second_fields(so) -> dict:
    """The row's second-opinion fields (policyqa/second_opinion.py). Skipped, absent (a case from before it
    existed) or still running reads "skipped" with nulls, `second_reason` saying why when known. A failed one
    keeps its cost and latency, no outcome; a "timeout" (api_chain stopped waiting) has neither.
    Its cost stays out of the row's cost_usd, so case costs stay comparable with the runs before it."""
    base = {"second_status": "skipped", "second_reason": None, "second_model": None, "second_outcome": None,
            "second_agrees": None, "second_cost_usd": None, "second_latency_ms": None}
    if not isinstance(so, dict):
        return {**base, "second_reason": "the chain did not reach the verdict"}
    status = so.get("status")
    base["second_model"] = so.get("model")
    if status == "timeout":
        return {**base, "second_status": "timeout", "second_reason": so.get("error")}
    if status not in ("done", "failed"):
        return {**base, "second_reason": so.get("reason") or (f"still {status}" if status else None)}
    done = status == "done"
    return {**base, "second_status": status, "second_reason": None if done else so.get("error"),
            "second_outcome": so.get("outcome") if done else None, "second_agrees": so.get("agrees") if done else None,
            "second_cost_usd": float(so.get("cost_usd") or 0), "second_latency_ms": float(so.get("latency_ms") or 0)}


def build_row(row: dict, result: dict | None, seconds: float, error: str | None = None) -> dict:
    case = (result or {}).get("case") or None
    refused = (result or {}).get("refused")
    if error is None and case is None and not refused:
        error = "no result"
    rec = {
        "id": row["id"], "program": row.get("program"), "jurisdiction": row.get("jurisdiction"), "trap": row.get("trap"),
        "demo": row.get("demo"), "intended": intended_of(row), "intended_csv": row.get("intended_outcome"), "got": None,
        "correct": False, "refused": refused, "route_program": None, "route_reason": None, "route_outside_corpus": None,
        "route_dual": None, "route_jurisdictions": None, "stage_errors": [],
        "findings": {s: 0 for s in FINDING_STATUSES}, "letter": None, "critique": None, "cost_usd": 0.0,
        "stage_cost_usd": {s: 0.0 for s in STAGES}, "seconds": round(seconds, 1), "error": error,
        "proposed_outcome": None, "decisive_fact": None, "settled_by": None, "relies_on_exception": None, "plan_source": None,
        "planned_questions": [], "exceptions": [], "hinge": hinge_trace(row, {}), "miss": None,
        **second_fields(None),
    }
    if case:
        rec.update(second_fields(case.get("second_opinion")))
        route = case.get("route") or {}
        inv = case.get("investigation") or {}
        verdict = case.get("verdict") or {}
        letter = case.get("letter")
        critique = case.get("critique")
        if verdict.get("status") == "done":
            rec["got"] = verdict.get("outcome")
        rec["route_program"] = route.get("program")
        rec["route_outside_corpus"] = route.get("outside_corpus")
        rec["route_reason"] = route.get("reason")
        if route:  # a routed case: dual is a bool (missing means single), jurisdictions the list the router gave
            rec["route_dual"] = bool(route.get("dual"))
            j = route.get("jurisdictions")
            rec["route_jurisdictions"] = list(j) if j is not None else None
        counts = Counter(f.get("status") for f in inv.get("findings") or [] if isinstance(f, dict))
        rec["findings"] = {s: counts.get(s, 0) for s in FINDING_STATUSES}
        if isinstance(letter, dict) and letter.get("status") == "done":
            v = letter.get("verification") or {}
            rec["letter"] = {"applicable": bool(letter.get("applicable")), "claims": int(v.get("claims") or 0),
                             "verified": int(v.get("verified") or 0), "struck": int(v.get("struck") or 0), "error": letter.get("error")}
        if isinstance(critique, dict):
            crit_error = critique.get("error") or ("failed" if critique.get("status") == "failed" else None)
            rec["critique"] = {"rounds": len(critique.get("rounds") or []), "issues_found": critique.get("issues_found"),
                               "issues_fixed": critique.get("issues_fixed"), "accepted": critique.get("accepted"),
                               "skipped": bool(critique.get("skipped")), "error": crit_error}
        rec["stage_cost_usd"] = {"intake": _cost(case), "investigation": _cost(inv), "verdict": _cost(verdict),
                                 "letter": _cost(letter), "critique": _cost(critique)}
        rec["cost_usd"] = round(sum(rec["stage_cost_usd"].values()), 6)
        errs = stage_errors(case)
        rec["stage_errors"] = [{"stage": e["stage"], "error": e["error"]} for e in errs]
        fatal = [e for e in errs if e["fatal"]]
        if fatal and not rec["error"]:
            rec["error"] = "; ".join(f"{e['stage']}: {e['error']}" for e in fatal)[:500]
        from .relevance import mark_exceptions

        df = verdict.get("decisive_fact") if isinstance(verdict.get("decisive_fact"), dict) else {}
        rec["proposed_outcome"] = verdict.get("proposed_outcome")
        rec["decisive_fact"] = df.get("fact") or None
        rec["settled_by"] = df.get("settled_by") or None
        rec["relies_on_exception"] = verdict.get("relies_on_exception")
        rec["plan_source"] = (inv.get("plan") or {}).get("source")
        rec["planned_questions"] = planned_questions(inv)
        rec["exceptions"] = [{k: m[k] for k in ("finding_id", "question", "status", "state", "relevant", "reason")} for m in mark_exceptions(inv, case)]
        rec["hinge"] = hinge_trace(row, inv)
    rec["correct"] = score(row["id"], rec["intended"], rec["got"], refused=rec["refused"], error=rec["error"])
    rec["miss"] = miss_stage(rec)
    return rec


def run_case(row: dict, letters_dir: Path, chain) -> dict:
    t = time.perf_counter()
    try:
        text = (Path(letters_dir) / f"{row['id']}.txt").read_text(encoding="utf-8")
        result = chain(row["id"], text)
        seconds = (result or {}).get("seconds")  # api_chain's own measure leaves out the wait for the second opinion
        return build_row(row, result, float(seconds) if seconds is not None else time.perf_counter() - t)
    except Exception as e:  # noqa: BLE001 - the row records the failure; the run goes on
        return build_row(row, None, time.perf_counter() - t, error=f"{type(e).__name__}: {e}"[:500])


# ---- the run ---------------------------------------------------------------------


def _env_float(name: str) -> float | None:
    raw = os.environ.get(name)
    try:
        return float(raw) if raw not in (None, "") else None
    except ValueError:
        return None


def run_config(cases_path, ids, limit, concurrency) -> dict:
    import api.main as m
    from policyqa.critic import critic_rounds
    from policyqa.second_opinion import second_model_name

    live_intake = m._live_configured()
    return {
        "date": date.today().isoformat(),
        "model": m.investigation_mode(),
        "reasoning_effort": os.environ.get("POLICYQA_LLM_REASONING_EFFORT") or None,
        "prices": {"input_usd_per_m": _env_float("POLICYQA_LLM_INPUT_USD_PER_M"), "output_usd_per_m": _env_float("POLICYQA_LLM_OUTPUT_USD_PER_M")},
        "second_model": second_model_name(),  # the second opinion's model (POLICYQA_SECOND_LLM_*), None when not configured
        "modes": {"intake": os.environ.get("POLICYQA_LLM_MODEL") if live_intake else "fixture", "investigation": m.investigation_mode(),
                  "verdict": m.verdict_mode(), "critic": m.critic_mode()},
        "critic_rounds": critic_rounds(),
        "concurrency": concurrency,
        "cases": str(cases_path),
        "ids": ids,
        "limit": limit,
        "alternates": {k: sorted(v) for k, v in ALTERNATES.items()},
        "refusal_ids": sorted(REFUSAL_IDS),
    }


def run_evals(cases_path: Path = DEFAULT_CASES, letters_dir: Path = DEFAULT_LETTERS, ids: list[str] | None = None, limit: int | None = None,
              concurrency: int = 3, critic: bool = True, chain=None, on_row=None) -> dict:
    """Run the cases and return {"config", "summary", "rows"}; rows keep the CSV order."""
    rows = load_cases(cases_path, ids=ids, limit=limit)
    chain = chain or api_chain
    t0 = time.perf_counter()
    with critic_switch(critic), private_store():
        config = run_config(cases_path, ids, limit, concurrency)

        def one(row):
            rec = run_case(row, letters_dir, chain)
            if on_row:
                on_row(rec)
            return rec

        with ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as pool:
            results = list(pool.map(one, rows))
    config["wall_s"] = round(time.perf_counter() - t0, 1)
    return {"config": config, "summary": summarize(results), "rows": results}


# ---- summary -----------------------------------------------------------------------


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _acc(rows: list[dict]) -> dict:
    c = sum(1 for r in rows if r["correct"])
    return {"n": len(rows), "correct": c, "accuracy": _rate(c, len(rows))}


def _group(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[str(r.get(key))].append(r)
    return {k: _acc(v) for k, v in sorted(groups.items())}


def _stats(values: list[float], digits: int) -> dict:
    if not values:
        return {"total": 0, "mean": None, "p50": None}
    return {"total": round(sum(values), digits), "mean": round(statistics.mean(values), digits), "p50": round(statistics.median(values), digits)}


def _got_label(r: dict) -> str:
    if r.get("error"):
        return "error"
    if r.get("refused"):
        return f"refused:{r['refused']}"
    return r.get("got") or "none"


def summarize(rows: list[dict]) -> dict:
    overall = _acc(rows)
    all_letters = [r["letter"] for r in rows if isinstance(r.get("letter"), dict)]
    letters = [x for x in all_letters if x.get("applicable") and not x.get("error")]  # template letters are left out
    claims = sum(x["claims"] for x in letters)
    verified = sum(x["verified"] for x in letters)
    struck = sum(x["struck"] for x in letters)
    crit = [r["critique"] for r in rows if isinstance(r.get("critique"), dict)]
    reviewed = [c for c in crit if not c.get("skipped") and not c.get("error")]
    refusal = [r for r in rows if r["id"] in REFUSAL_IDS]
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        confusion[r["intended"]][_got_label(r)] += 1
    misses = [{"id": r["id"], "intended": r["intended"], "got": r.get("got"), "stage": r["miss"]["stage"], "why": r["miss"]["why"]}
              for r in rows if not r["correct"] and isinstance(r.get("miss"), dict)]
    return {
        "n": overall["n"],
        "correct": overall["correct"],
        "accuracy": overall["accuracy"],
        "by_intended": _group(rows, "intended"),
        "by_program": _group(rows, "program"),
        "by_jurisdiction": _group(rows, "jurisdiction"),
        "refusal_correct": refusal[0]["correct"] if refusal else None,
        "letter_failures": sum(1 for x in all_letters if x.get("error")),
        "critic_failures": sum(1 for c in crit if c.get("error")),
        "outside_corpus": [{"id": r["id"], "got": r["got"], "correct": r["correct"], "route_program": r.get("route_program"),
                            "route_reason": r.get("route_reason"), "route_unknown": r.get("route_program") == "unknown",
                            "route_outside_corpus": bool(r.get("route_outside_corpus"))}
                           for r in rows if r["id"] in OUTSIDE_CORPUS_IDS],
        "letters": {"applicable": len(letters), "claims": claims, "verified": verified, "struck": struck,
                    "verification_rate": _rate(verified, claims), "struck_rate": _rate(struck, claims)},
        "critic": {"reviewed": len(reviewed), "accepted": sum(1 for c in reviewed if c.get("accepted")),
                   "skipped": sum(1 for c in crit if c.get("skipped")), "errors": sum(1 for c in crit if c.get("error")),
                   "issues_found": sum(int(c.get("issues_found") or 0) for c in reviewed),
                   "issues_fixed": sum(int(c.get("issues_fixed") or 0) for c in reviewed)},
        "cost_usd": _stats([float(r.get("cost_usd") or 0) for r in rows], 6),
        "seconds": _stats([float(r.get("seconds") or 0) for r in rows], 1),
        "confusion": {k: dict(v) for k, v in sorted(confusion.items())},
        "errors": [{"id": r["id"], "error": r["error"]} for r in rows if r.get("error")],
        "wrong": [{"id": r["id"], "intended": r["intended"], "got": r["got"], "refused": r.get("refused"), "error": r.get("error")}
                  for r in rows if not r["correct"]],
        "misses": misses,
        "misses_by_stage": dict(Counter(m["stage"] for m in misses)),
        "second_opinion": summarize_second(rows),
        "dual_routes": summarize_dual(rows),
    }


def summarize_dual(rows: list[dict]) -> dict:
    """The cases the router sent down both programs side by side (Florida Medicaid and Medicare): how many, how
    many were scored correct, and each one's intended and got. Rows from result files written before Oct 30 have no
    route_dual key; when no row has one, recorded is False and the count means "not recorded", not "none"."""
    dual = [r for r in rows if r.get("route_dual") is True]
    return {"recorded": any("route_dual" in r for r in rows), "routed": len(dual), "correct": sum(1 for r in dual if r.get("correct")),
            "cases": [{"id": r["id"], "intended": r.get("intended"), "got": r.get("got"), "correct": bool(r.get("correct"))} for r in dual]}


def summarize_second(rows: list[dict]) -> dict:
    """Agreement between the verdict and the second opinion, over the cases where both are done; who was right when
    they differ (scored by the same rule as the verdict); the second opinion's cost over the cases where it answered
    or failed (a timeout's cost is unknown). Configured means a row names a second model, whether or not it ran."""
    ran = [r for r in rows if r.get("second_status") in ("done", "failed", "timeout")]
    answered = [r for r in ran if r.get("second_status") != "timeout"]
    skipped = [r for r in rows if r.get("second_status", "skipped") == "skipped"]
    both = [r for r in rows if r.get("second_status") == "done" and r.get("got") is not None]
    agree = sum(1 for r in both if r.get("second_agrees") is True)

    def second_right(r) -> bool:
        return score(r["id"], r["intended"], r.get("second_outcome"))

    def primary_right(r) -> bool:  # the verdict alone: a later stage's error does not make the verdict wrong here
        return score(r["id"], r["intended"], r.get("got"))

    return {
        "configured": any(r.get("second_model") for r in rows),
        "models": sorted({str(r.get("second_model")) for r in rows if r.get("second_model")}),
        "ran": len(ran),
        "done": sum(1 for r in rows if r.get("second_status") == "done"),
        "failed": sum(1 for r in rows if r.get("second_status") == "failed"),
        "timeout": sum(1 for r in rows if r.get("second_status") == "timeout"),
        "skipped": len(skipped),
        "skip_reasons": dict(Counter(r.get("second_reason") or "no reason recorded" for r in skipped)),
        "both_done": len(both),
        "agree": agree,
        "agreement_rate": _rate(agree, len(both)),
        "second_right_primary_wrong": [r["id"] for r in both if second_right(r) and not primary_right(r)],
        "primary_right_second_wrong": [r["id"] for r in both if primary_right(r) and not second_right(r)],
        "cost_usd": _stats([float(r.get("second_cost_usd") or 0) for r in answered], 6),
        "latency_ms": _stats([float(r.get("second_latency_ms") or 0) for r in answered], 1),
    }


# ---- outputs -------------------------------------------------------------------------


def _frac(n: int, d: int) -> str:
    return f"{n} / {d} ({n / d:.1%})" if d else f"{n} / {d}"


def _money(x) -> str:
    return "n/a" if x is None else f"${x:.4f}"


def _second_cell(r: dict) -> str:
    status = r.get("second_status") or "skipped"
    if status != "done":
        return status
    return f"{r.get('second_outcome') or 'none'} ({'agrees' if r.get('second_agrees') else 'disagrees'})"


def render_markdown(res: dict) -> str:
    cfg, s, rows = res["config"], res["summary"], res["rows"]
    lt, cr = s["letters"], s["critic"]
    effort = cfg.get("reasoning_effort") or "default"
    so = s.get("second_opinion") or summarize_second(rows)
    dr = s.get("dual_routes") or summarize_dual(rows)  # older result files have no dual_routes block
    if not dr.get("recorded", True):
        dual_cell = "not recorded (before Oct 30)"
    else:
        dual_cell = f"{dr['correct']} / {dr['routed']} ({', '.join(c['id'] for c in dr['cases'])})" if dr["routed"] else "0"
    second_model = cfg.get("second_model") or ", ".join(so.get("models") or [])
    second_on = bool(second_model)  # "not configured" only when no second model is named, by the run or by a row
    second_line = f"Second opinion: {second_model}, {so.get('ran', 0)} ran." if second_on else "Second opinion: not configured."
    lines = [
        f"# Denial-case evaluation, {cfg['date']}",
        "",
        f"Model: {cfg['model']} (reasoning effort: {effort}). Critic rounds: {cfg['critic_rounds']}. Cases: {s['n']}. Wall time: {cfg.get('wall_s', 'n/a')} s. {second_line}",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Accuracy | {_frac(s['correct'], s['n'])} |",
    ]
    for outcome, g in s["by_intended"].items():
        lines.append(f"| Intended {outcome} | {_frac(g['correct'], g['n'])} |")
    refusal = {True: "correct", False: "wrong", None: "not run"}[s["refusal_correct"]]
    lines += [
        f"| Refusal on the medical question (dc-011) | {refusal} |",
        f"| Letter claims verified | {_frac(lt['verified'], lt['claims'])} over {lt['applicable']} letters |",
        f"| Letter claims struck | {_frac(lt['struck'], lt['claims'])} |",
        f"| Critic revisions accepted | {cr['accepted']} of {cr['reviewed']} reviewed |",
        f"| Cost per case | mean {_money(s['cost_usd']['mean'])}, p50 {_money(s['cost_usd']['p50'])}, total {_money(s['cost_usd']['total'])} |",
        f"| Seconds per case | mean {s['seconds']['mean']}, p50 {s['seconds']['p50']} |",
        f"| Errors (scored wrong) | {len(s['errors'])} |",
        f"| Template letters (left out of the rates) | {s['letter_failures']} |",
        f"| Critic failures (letter kept as drafted) | {s['critic_failures']} |",
        f"| Dual routes (side by side) | {dual_cell} |",
    ]
    reasons = "; ".join(f"{k} ({v})" for k, v in sorted((so.get("skip_reasons") or {}).items())) or "no reason recorded"
    if second_on and so.get("ran"):
        def ids(xs: list[str]) -> str:  # "2 (dc-002, dc-017)", or "0"
            return f"{len(xs)} ({', '.join(xs)})" if xs else "0"

        lines += [
            f"| Second opinion agrees with the verdict | {_frac(so['agree'], so['both_done'])} of the cases where both ran |",
            f"| Second opinion right, verdict wrong | {ids(so['second_right_primary_wrong'])} |",
            f"| Verdict right, second opinion wrong | {ids(so['primary_right_second_wrong'])} |",
            f"| Second opinion cost per case | mean {_money(so['cost_usd']['mean'])} over {so['done'] + so['failed']} runs |",
            f"| Second opinion failed, timed out, skipped | {so['failed']}, {so.get('timeout', 0)}, {so['skipped']} |",
        ]
        if so["skipped"]:
            lines.append(f"| Second opinion skip reasons | {reasons} |")
    elif second_on:
        lines.append(f"| Second opinion | 0 ran; skipped {so['skipped']}: {reasons} |")
    else:
        lines.append("| Second opinion | not configured |")
    lines.append("")
    for title, key in (("Program", "by_program"), ("Jurisdiction", "by_jurisdiction")):
        lines += [f"| {title} | Correct |", "|---|---|"]
        lines += [f"| {k} | {_frac(g['correct'], g['n'])} |" for k, g in s[key].items()]
        lines.append("")
    lines += ["| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        got = (f"error ({r['got']})" if r.get("got") else "error") if r.get("error") else (f"refused ({r['refused']})" if r.get("refused") else (r.get("got") or "none"))
        lt_r = r.get("letter")
        vc = "template" if lt_r and lt_r.get("error") else (f"{lt_r['verified']} / {lt_r['claims']}" if lt_r and lt_r.get("applicable") else "n/a")
        lines.append(f"| {r['id']} | {r['intended']} | {got} | {'yes' if r['correct'] else 'no'} | {vc} | {_money(r.get('cost_usd'))} | {r.get('seconds')} | {_second_cell(r)} |")
    lines.append("")
    if s["wrong"]:
        lines.append("Wrong cases:")
        lines.append("")
        for w in s["wrong"]:
            why = f"error: {w['error']}" if w.get("error") else (f"refused ({w['refused']})" if w.get("refused") else f"got {w['got']}")
            lines.append(f"- {w['id']}: intended {w['intended']}, {why}")
        lines.append("")
    if s.get("misses"):
        lines += ["Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):", "",
                  "| Case | Intended | Got | Stage | Why |", "|---|---|---|---|---|"]
        for m in s["misses"]:
            why = str(m["why"]).replace("|", "/")
            lines.append(f"| {m['id']} | {m['intended']} | {m.get('got') or 'none'} | {m['stage']} | {why} |")
        lines.append("")
    for o in s["outside_corpus"]:
        lines.append(f"{o['id']} route: program {o['route_program']} ({'unknown, as expected outside the corpus' if o['route_unknown'] else 'not unknown'}; {'the router said no corpus document governs it' if o['route_outside_corpus'] else 'the router did not say no corpus document governs it'}). Reason given: {o['route_reason']}")
        lines.append("")
    lines.append("Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.")
    return "\n".join(lines) + "\n"


def write_outputs(res: dict, out: Path, md: Path) -> None:
    out, md = Path(out), Path(md)
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    md.write_text(render_markdown(res), encoding="utf-8")

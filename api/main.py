"""Recourse API. FastAPI over the policyqa package.

Surface:
  GET   /health                  index, model, and intake status
  GET   /search?q=&k=            hybrid retrieval with the answering reranker
  POST  /answer                  {"question": "..."} -> answer with verified citations
                                 (mock provider until POLICYQA_LLM_* are set)
  POST  /case/intake             multipart: one of `file` (jpeg/png/webp/pdf, 10 MB) or `text`
                                 (200 to 6,000 chars) -> the case with its card
  GET   /case/{id}               the case, with `route` and `investigation` (null until started)
  PATCH /case/{id}               {field: plain value, ...} -> the case; edited cells become high
  POST  /case/{id}/investigate   202 {case_id, status: "investigating"}; runs the investigation in a
                                 background thread; poll GET /case/{id} to watch findings arrive;
                                 the case ends as `investigated` or `failed`. The move out of intake
                                 is atomic (CaseStore.claim_for_investigation): of concurrent posts,
                                 one gets 202 and the rest 409 wrong_status. Findings carry `passages`
                                 and may be `status: "error"` with an `error` string; coverage has
                                 `errors` (see policyqa/investigate.py). When the investigation is done the
                                 same thread runs the Steelman and Verdict, then the Action (letter):
                                 investigating -> investigated -> deciding -> decided -> drafting -> drafted,
                                 or failed with `status: "failed"` and `error` on the stage that failed
                                 (earlier stages are kept). After `drafted` the critic reviews the letter:
                                 -> reviewing -> reviewed, the end of the chain. `critique` holds the issues
                                 and a before/after per round; `letter.paragraphs` and `letter.verification`
                                 become the accepted revision's, `letter.draft_paragraphs` keeps the draft.
                                 A critic that is off (RECOURSE_CRITIC_ROUNDS=0), a letter that is not
                                 applicable, a model failure, or an exception in the critic all still end
                                 `reviewed` (critique.skipped with a reason, critique.error, or
                                 critique.status "failed") with the letter as drafted.
                                 Shapes: policyqa/verdict.py, policyqa/letter.py, policyqa/critic.py.
  GET   /doc/{doc_id}/page/{page}.png?dpi=110
                                 the real PDF page as a PNG (pdftoppm, disk cache), Cache-Control public 1 day
  GET   /doc/{doc_id}/page/{page}/highlight?quote=&dpi=110
                                 {doc_id, title, page, dpi, width_px, height_px, boxes_px: [{x0,y0,x1,y1}],
                                 score, found, matched, image_url}: the quote located on the page (policyqa/pages.py)
  POST  /doc/{doc_id}/page/{page}/vision-check  {quote, dpi?}
                                 the highlight plus `vision`: Muse Spark reads the boxed text and confirms it holds
                                 the quote (FixtureVision without POLICYQA_LLM_*); cached in memory per (doc, page,
                                 quote, dpi, model). 404 not_found / bad_page, 503 no_pdf (RECOURSE_PDF_DIR).
  GET   /case/{id}/letter.txt    the appeal letter as plain text (the final paragraphs: the accepted revision
                                 once reviewed): struck sentences left out, "[cite: title,
                                 p. N]" after each verified claim. 404 not_ready until drafted, 409
                                 not_applicable when the denial matches the policy (read `explanation`).

Errors are {"detail": {"code": ..., "message": ...}}: 400 bad_request, 404 not_found,
404 not_ready, 409 wrong_status, 409 not_applicable, 422 one of the intake codes (unsupported_type, too_large,
text_length, unreadable, not_a_denial_letter, out_of_scope) or invalid_field
(with "field").

The investigation runs live (Muse Spark 1.3 through POLICYQA_LLM_*, hybrid retrieval over
data/chunks.jsonl) only when both the env and the index exist; otherwise the fixture
investigator serves a synthetic Sunshine Health investigation. The verdict and the letter follow
the same mode (verdict_mode): live with the investigation, else FixtureVerdict and FixtureLetter.
The critic follows it too (critic_mode: the model, "fixture", or "off" when RECOURSE_CRITIC_ROUNDS
is 0; default 1 round, at most 2).
`RUN_INVESTIGATION_INLINE` makes the POST run the whole chain synchronously (tests);
`FIXTURE_DELAY` is the pause between fixture findings and before each fixture stage.

Run: uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.cases import STORE

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAX_UPLOAD = 10 * 1024 * 1024
RUN_INVESTIGATION_INLINE = False  # True: POST /case/{id}/investigate runs the whole investigation before answering (tests)
FIXTURE_DELAY = 0.8  # seconds between fixture findings, so progress is visible on screen
INVESTIGATION_THREADS: dict[str, threading.Thread] = {}
VISION_CACHE: dict[tuple, dict] = {}  # (doc_id, page, quote, dpi, model) -> vision result; a second open costs nothing

app = FastAPI(title="Recourse API", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def _validation_error(_request, exc: RequestValidationError):
    """Keep every 4xx body in the one shape the screen reads: {"detail": {"code", "message"}}."""
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
    message = f"{where}: {first.get('msg', 'invalid request')}" if where else str(first.get("msg", "invalid request"))
    return JSONResponse(status_code=422, content={"detail": {"code": "invalid_field", "field": where or None, "message": message}})
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("RECOURSE_CORS_ORIGINS", "http://localhost:3000").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def retriever():
    from policyqa.index import Index
    from policyqa.retrieve import Retriever, ANSWER_RERANK_MODEL, ANSWER_CANDIDATES

    chunks = DATA / "chunks.jsonl"
    if not chunks.exists():
        raise HTTPException(503, "index not built: run `python -m policyqa.cli chunk` and `embed` first")
    r = Retriever(Index(chunks, DATA / "dense.npy"), mode="hybrid", rerank=True, rerank_model=ANSWER_RERANK_MODEL)
    search = r.search
    r.search = lambda q, k=5, **kw: search(q, k=k, candidates=ANSWER_CANDIDATES, **kw)
    return r


def _live_configured() -> bool:
    return bool(os.environ.get("POLICYQA_LLM_BASE_URL") and os.environ.get("POLICYQA_LLM_MODEL"))


def investigation_mode() -> str:
    """The model name when a live investigation is possible (env set and index built), else "fixture"."""
    if _live_configured() and (DATA / "chunks.jsonl").exists():
        return os.environ["POLICYQA_LLM_MODEL"]
    return "fixture"


@lru_cache(maxsize=1)
def investigator():
    from policyqa.investigate import FixtureInvestigator, LiveInvestigator

    if investigation_mode() == "fixture":
        return FixtureInvestigator(delay=FIXTURE_DELAY)
    return LiveInvestigator(retriever(), provider())


def verdict_mode() -> str:
    """The verdict and the letter run live exactly when the investigation does, so a live verdict never argues from fixture findings."""
    return investigation_mode()


def verdicter():
    from policyqa.verdict import FixtureVerdict, LiveVerdict

    if verdict_mode() == "fixture":
        return FixtureVerdict(delay=FIXTURE_DELAY)
    return LiveVerdict(provider())


def letterer():
    from policyqa.letter import FixtureLetter, LiveLetter

    if verdict_mode() == "fixture":
        return FixtureLetter(delay=FIXTURE_DELAY)
    return LiveLetter(provider())


def critic_mode() -> str:
    """The critic's model, "fixture", or "off" (RECOURSE_CRITIC_ROUNDS=0); it runs live exactly when the letter does."""
    from policyqa.critic import critic_rounds

    return "off" if critic_rounds() == 0 else verdict_mode()


def critic():
    from policyqa.critic import FixtureCritic, LiveCritic

    if verdict_mode() == "fixture":
        return FixtureCritic(delay=FIXTURE_DELAY)
    return LiveCritic(provider())


@lru_cache(maxsize=1)
def provider():
    from policyqa.generate import Provider, MockProvider

    if os.environ.get("POLICYQA_LLM_BASE_URL") and os.environ.get("POLICYQA_LLM_MODEL"):
        return Provider()
    return MockProvider()


@lru_cache(maxsize=1)
def extractor():
    from policyqa.intake import FixtureExtractor, MuseSparkExtractor

    if os.environ.get("POLICYQA_LLM_BASE_URL") and os.environ.get("POLICYQA_LLM_MODEL"):
        return MuseSparkExtractor(provider())
    return FixtureExtractor()


class AnswerRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=5, ge=1, le=10)


@app.get("/health")
def health():
    return {
        "ok": True,
        "index_built": (DATA / "chunks.jsonl").exists(),
        "dense_built": (DATA / "dense.npy").exists(),
        "model": os.environ.get("POLICYQA_LLM_MODEL") or "mock",
        "intake": os.environ.get("POLICYQA_LLM_MODEL") if _live_configured() else "fixture",
        "investigation": investigation_mode(),
        "verdict": verdict_mode(),
        "critic": critic_mode(),
        "pdfs": _pdf_count(),
    }


def _pdf_count() -> int:
    from policyqa.pages import pdf_count

    return pdf_count()


@app.get("/search")
def search(q: str, k: int = 5):
    if not (3 <= len(q) <= 2000):
        raise HTTPException(422, "q must be 3 to 2000 characters")
    hits = retriever().search(q, k=min(max(k, 1), 10))
    return {
        "query": q,
        "hits": [
            {"chunk_id": h.chunk["chunk_id"], "doc_id": h.chunk["doc_id"], "page": h.chunk["page"], "title": h.chunk["title"], "jurisdiction": h.chunk["jurisdiction"], "score": h.score, "text": h.chunk["text"]}
            for h in hits
        ],
    }


@app.post("/answer")
def answer(req: AnswerRequest):
    from policyqa.generate import answer_question
    from policyqa.trace import Trace

    tr = Trace(req.question)
    hits = retriever().search(req.question, k=req.k, trace=tr)
    a = answer_question(req.question, hits, provider(), trace=tr)
    d = a.to_dict()
    d.pop("raw", None)
    d["trace"] = tr.to_dict()
    return d


# ---- cases ----------------------------------------------------------------


def _err(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status, {"code": code, "message": message, **extra})


def _sniff(data: bytes) -> tuple[str, str] | None:
    """(source, mime) from the first bytes, or None when the type is not one we take."""
    if data.startswith(b"%PDF"):
        return "pdf", "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", "image/webp"
    return None


def _load_case(case_id: str) -> dict:
    c = STORE.get(case_id)
    if c is None:
        raise _err(404, "not_found", f"No case {case_id}.")
    return c


@app.post("/case/intake")
async def case_intake(file: UploadFile | None = File(default=None), text: str | None = Form(default=None)):
    from policyqa.intake import IntakeError, TEXT_MAX, TEXT_MIN, scope_check

    has_file = file is not None and (file.filename or file.size)
    has_text = text is not None and text.strip() != ""
    if bool(has_file) == bool(has_text):
        raise _err(400, "bad_request", "Send exactly one of `file` or `text`.")
    try:
        if has_text:
            body = text.strip()
            if not (TEXT_MIN <= len(body) <= TEXT_MAX):
                raise IntakeError("text_length", f"Paste between {TEXT_MIN} and {TEXT_MAX:,} characters of the letter (you sent {len(body):,}).")
            code = scope_check(body)
            if code == "out_of_scope":
                raise IntakeError(code, "Recourse handles coverage denials and billing only. It does not answer treatment or diagnosis questions.")
            if code == "not_a_denial_letter":
                raise IntakeError(code, "This does not look like a coverage denial letter, notice of action, or explanation of benefits.")
            ex = extractor().extract("text", text=body)
        else:
            data = await file.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                raise IntakeError("too_large", "The file is over 10 MB. Send a smaller photo or PDF.")
            kind = _sniff(data)
            if kind is None:
                raise IntakeError("unsupported_type", "Send a JPEG, PNG, or WebP photo, or a PDF.")
            source, mime = kind
            ex = extractor().extract(source, data=data, mime=mime, filename=file.filename or "letter.pdf")
    except IntakeError as e:
        raise _err(422, e.code, e.message)
    return STORE.create({
        "source": ex.source,
        "raw_text": ex.raw_text,
        "summary": ex.summary,
        "card": ex.card,
        "model": ex.model,
        "cost_usd": ex.cost_usd,
        "latency_ms": ex.latency_ms,
    })


@app.get("/case/{case_id}")
def case_get(case_id: str):
    return _load_case(case_id)


@app.patch("/case/{case_id}")
def case_patch(case_id: str, body: dict = Body(...)):
    from policyqa.intake import CARD_FIELDS, ENUM_FIELDS, coerce_field

    c = _load_case(case_id)
    if c["status"] != "intake":
        raise _err(409, "wrong_status", f"Case {case_id} is {c['status']}; the card can only be edited during intake.")
    if not isinstance(body, dict) or not body:
        raise _err(422, "invalid_field", "Send a JSON object with at least one card field.", field=None)
    updates = {}
    for field, value in body.items():
        if field not in CARD_FIELDS:
            raise _err(422, "invalid_field", f"{field} is not a card field.", field=field)
        if value is None and field not in ENUM_FIELDS:
            # The person cleared the field: the letter does not state it. Keep that as a deliberate answer.
            updates[field] = {"value": None, "confidence": "high", "edited": True}
            continue
        clean, ok = coerce_field(field, value)
        if not ok:
            raise _err(422, "invalid_field", f"{field}: {value!r} is not a valid value.", field=field)
        updates[field] = {"value": clean, "confidence": "high", "edited": True}
    return STORE.patch(case_id, updates)


_CASE_STATUS = {"running": "investigating", "done": "investigated", "failed": "failed"}


def _run_investigation(case_id: str) -> None:
    """Body of the investigation thread: every finding is stored as it lands, then the final state."""
    from policyqa.investigate import _empty_investigation

    c = STORE.get(case_id)
    if c is None:
        return
    route = c.get("route")

    def progress(partial: dict) -> None:
        STORE.set_investigation(case_id, route, partial, _CASE_STATUS.get(partial.get("status"), "investigating"))

    try:
        final = investigator().investigate(c, on_progress=progress)
        STORE.set_investigation(case_id, route, final, _CASE_STATUS.get(final.get("status"), "failed"))
    except Exception as e:  # noqa: BLE001 - the case records the failure; the thread must not die silently
        cur = (STORE.get(case_id) or {}).get("investigation") or _empty_investigation(getattr(investigator(), "model", "?"))
        cur.update(status="failed", error=f"{type(e).__name__}: {e}"[:500], finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        STORE.set_investigation(case_id, route, cur, "failed")
        return
    if final.get("status") == "done":
        try:
            _run_decision(case_id)
        except Exception as e:  # noqa: BLE001 - bookkeeping failed outside a stage: fail the stage that was running
            cur = STORE.get(case_id) or {}
            for field in ("critique", "letter", "verdict"):
                stage = cur.get(field)
                if isinstance(stage, dict) and stage.get("status") == "running":
                    # a critic failure keeps the drafted letter: the case still ends reviewed
                    STORE.set_stage(case_id, field, {**stage, "status": "failed", "error": _err_text(e)}, "reviewed" if field == "critique" else "failed")
                    break
            else:
                STORE.set_status(case_id, "failed")


def _add_span(case_id: str, span: dict) -> None:
    """Append a stage span to the investigation's trace, so the case keeps one readable trace."""
    inv = (STORE.get(case_id) or {}).get("investigation")
    if not isinstance(inv, dict):
        return
    trace = inv.setdefault("trace", {"spans": []})
    trace.setdefault("spans", []).append(span)
    trace["total_ms"] = round(sum(float(s.get("ms", 0)) for s in trace["spans"]), 1)
    STORE.set_stage(case_id, "investigation", inv)


def _err_text(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"[:500]


def _run_decision(case_id: str) -> None:
    """Steelman and Verdict, then the Action stage, each stored as it lands. Never raises."""
    import time

    from policyqa.letter import empty_letter
    from policyqa.verdict import empty_verdict

    c = STORE.get(case_id)
    inv = c["investigation"]
    agent = verdicter()
    model = getattr(agent, "model", "?")
    STORE.set_stage(case_id, "verdict", empty_verdict(model), "deciding")
    t = time.perf_counter()
    try:
        verdict = agent.decide(c, inv)
    except Exception as e:  # noqa: BLE001 - the stage records the failure; the investigation is kept
        _add_span(case_id, {"name": "steelman_verdict", "ms": round((time.perf_counter() - t) * 1000, 1), "model": model, "error": _err_text(e)})
        STORE.set_stage(case_id, "verdict", empty_verdict(model, "failed", _err_text(e)), "failed")
        return
    _add_span(case_id, {
        "name": "steelman_verdict", "ms": round((time.perf_counter() - t) * 1000, 1), "model": verdict.get("model"),
        "outcome": verdict.get("outcome"), "proposed_outcome": verdict.get("proposed_outcome"),
        "rule_citations": len((verdict.get("rule") or {}).get("citations") or []),
        "steelman_citations": len((verdict.get("steelman") or {}).get("citations") or []),
        "input_tokens": verdict.get("input_tokens"), "output_tokens": verdict.get("output_tokens"),
        "reasoning_tokens": verdict.get("reasoning_tokens"), "cost_usd": verdict.get("cost_usd"), "error": verdict.get("error"),
    })
    STORE.set_stage(case_id, "verdict", verdict, "decided")

    agent = letterer()
    model = getattr(agent, "model", "?")
    STORE.set_stage(case_id, "letter", empty_letter(model), "drafting")
    t = time.perf_counter()
    try:
        letter = agent.draft(STORE.get(case_id), inv, verdict)
    except Exception as e:  # noqa: BLE001
        _add_span(case_id, {"name": "letter", "ms": round((time.perf_counter() - t) * 1000, 1), "model": model, "error": _err_text(e)})
        STORE.set_stage(case_id, "letter", empty_letter(model, "failed", _err_text(e)), "failed")
        return
    _add_span(case_id, {
        "name": "letter", "ms": round((time.perf_counter() - t) * 1000, 1), "model": letter.get("model"),
        "applicable": letter.get("applicable"), **(letter.get("verification") or {}),
        "input_tokens": letter.get("input_tokens"), "output_tokens": letter.get("output_tokens"),
        "reasoning_tokens": letter.get("reasoning_tokens"), "cost_usd": letter.get("cost_usd"), "error": letter.get("error"),
    })
    STORE.set_stage(case_id, "letter", letter, "drafted")
    _run_critic(case_id, inv, verdict, letter)


def _run_critic(case_id: str, inv: dict, verdict: dict, letter: dict) -> None:
    """The critic reviews the drafted letter; the case ends `reviewed` whatever happens here."""
    import time

    from policyqa.critic import apply_critique, empty_critique

    agent = critic()
    model = getattr(agent, "model", "?")
    STORE.set_stage(case_id, "critique", empty_critique(model), "reviewing")
    t = time.perf_counter()
    try:
        critique = agent.review(STORE.get(case_id), inv, verdict, letter)
    except Exception as e:  # noqa: BLE001 - the letter as drafted stands; the critique records why
        _add_span(case_id, {"name": "critic", "ms": round((time.perf_counter() - t) * 1000, 1), "model": model, "error": _err_text(e)})
        STORE.set_stage(case_id, "critique", empty_critique(model, "failed", _err_text(e)), "reviewed")
        return
    rounds = critique.get("rounds") or []
    _add_span(case_id, {
        "name": "critic", "ms": round((time.perf_counter() - t) * 1000, 1), "model": critique.get("model"),
        "skipped": critique.get("skipped"), "rounds": len(rounds), "accepted": critique.get("accepted"),
        "issues_found": critique.get("issues_found"), "issues_fixed": critique.get("issues_fixed"),
        "input_tokens": sum(int(r.get("input_tokens") or 0) for r in rounds), "output_tokens": sum(int(r.get("output_tokens") or 0) for r in rounds),
        "reasoning_tokens": sum(int(r.get("reasoning_tokens") or 0) for r in rounds), "cost_usd": critique.get("cost_usd"), "error": critique.get("error"),
    })
    STORE.set_stage(case_id, "letter", apply_critique(letter, critique))
    STORE.set_stage(case_id, "critique", critique, "reviewed")


@app.post("/case/{case_id}/investigate", status_code=202)
def case_investigate(case_id: str):
    from policyqa.investigate import _empty_investigation

    c = _load_case(case_id)
    inv = investigator()
    route = inv.route(c["card"]).to_dict()  # pure; computed before the claim so a failure here leaves the case in intake
    if not STORE.claim_for_investigation(case_id):
        current = (STORE.get(case_id) or c)["status"]
        raise _err(409, "wrong_status", f"Case {case_id} is already {current}.")
    STORE.set_investigation(case_id, route, _empty_investigation(getattr(inv, "model", "?")), "investigating")
    if RUN_INVESTIGATION_INLINE:
        _run_investigation(case_id)
    else:
        t = threading.Thread(target=_run_investigation, args=(case_id,), name=f"investigate-{case_id}", daemon=True)
        INVESTIGATION_THREADS[case_id] = t
        t.start()
    return {"case_id": case_id, "status": "investigating"}


@app.get("/case/{case_id}/letter.txt")
def case_letter_txt(case_id: str):
    from policyqa.letter import letter_text

    c = _load_case(case_id)
    letter = c.get("letter")
    if not isinstance(letter, dict) or letter.get("status") != "done":
        raise _err(404, "not_ready", f"The appeal letter for case {case_id} is not drafted yet.")
    if not letter.get("applicable"):
        raise _err(409, "not_applicable", "The denial matches the policy, so there is no appeal letter. Read the explanation instead.")
    return PlainTextResponse(letter_text(letter), headers={"Content-Disposition": f'inline; filename="recourse-appeal-{case_id}.txt"'})


# ---- highlighted page images ----------------------------------------------

_PAGE_STATUS = {"not_found": 404, "bad_page": 404, "no_pdf": 503, "render_failed": 500}
DPI_MIN, DPI_MAX = 50, 300
QUOTE_MIN, QUOTE_MAX = 15, 2000


def _page_err(e) -> HTTPException:
    return _err(_PAGE_STATUS.get(e.code, 500), e.code, e.message)


def vision_provider():
    """Muse Spark (the shared provider) when POLICYQA_LLM_* are set, else FixtureVision."""
    from policyqa.pages import FixtureVision

    return provider() if _live_configured() else FixtureVision()


class VisionCheckRequest(BaseModel):
    quote: str = Field(min_length=QUOTE_MIN, max_length=QUOTE_MAX)
    dpi: int = Field(default=110, ge=DPI_MIN, le=DPI_MAX)


@app.get("/doc/{doc_id}/page/{page}.png")
def doc_page_png(doc_id: str, page: int, dpi: int = Query(default=110, ge=DPI_MIN, le=DPI_MAX)):
    from policyqa.pages import PageError, render_page

    try:
        png = render_page(doc_id, page, dpi)
    except PageError as e:
        raise _page_err(e)
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/doc/{doc_id}/page/{page}/highlight")
def doc_page_highlight(doc_id: str, page: int, quote: str = Query(min_length=QUOTE_MIN, max_length=QUOTE_MAX), dpi: int = Query(default=110, ge=DPI_MIN, le=DPI_MAX)):
    from policyqa.pages import PageError, highlight

    try:
        return highlight(doc_id, page, quote, dpi)
    except PageError as e:
        raise _page_err(e)


@app.post("/doc/{doc_id}/page/{page}/vision-check")
def doc_page_vision_check(doc_id: str, page: int, req: VisionCheckRequest):
    from policyqa import pages

    try:
        hl = pages.highlight(doc_id, page, req.quote, req.dpi)
        vp = vision_provider()
        key = (doc_id, page, req.quote, req.dpi, getattr(vp, "model", "?"))
        vision = VISION_CACHE.get(key)
        if vision is None:
            vision = pages.vision_check(doc_id, page, req.quote, vp, dpi=req.dpi, hl=hl)
            if vision.get("checked"):  # failures are not cached, so the next open retries
                VISION_CACHE[key] = vision
    except pages.PageError as e:
        raise _page_err(e)
    return {**hl, "vision": vision}

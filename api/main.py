"""Recourse API. FastAPI over the policyqa package.

Surface:
  GET   /health                  index, model, and intake status
  GET   /search?q=&k=            hybrid retrieval with the answering reranker
  POST  /answer                  {"question": "..."} -> answer with verified citations
                                 (mock provider until POLICYQA_LLM_* are set)
  POST  /case/intake             multipart: one of `file` (jpeg/png/webp/pdf, 10 MB) or `text`
                                 (200 to 6,000 chars) -> the case with its card
  GET   /case/{id}               the case
  PATCH /case/{id}               {field: plain value, ...} -> the case; edited cells become high
  POST  /case/{id}/investigate   intake -> investigating (stub; the agent lands next)

Errors are {"detail": {"code": ..., "message": ...}}: 400 bad_request, 404 not_found,
409 wrong_status, 422 one of the intake codes (unsupported_type, too_large,
text_length, unreadable, not_a_denial_letter, out_of_scope) or invalid_field
(with "field").

Run: uvicorn api.main:app --reload --port 8000
Verdict and letter endpoints land as the agent is built.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.cases import STORE

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAX_UPLOAD = 10 * 1024 * 1024

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
    r.search = lambda q, k=5, trace=None: search(q, k=k, candidates=ANSWER_CANDIDATES, trace=trace)
    return r


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
        "intake": os.environ.get("POLICYQA_LLM_MODEL") if (os.environ.get("POLICYQA_LLM_BASE_URL") and os.environ.get("POLICYQA_LLM_MODEL")) else "fixture",
    }


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


@app.post("/case/{case_id}/investigate")
def case_investigate(case_id: str):
    c = _load_case(case_id)
    if c["status"] != "intake":
        raise _err(409, "wrong_status", f"Case {case_id} is already {c['status']}.")
    STORE.set_status(case_id, "investigating")
    return {"case_id": case_id, "status": "investigating"}

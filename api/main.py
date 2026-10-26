"""Recourse API. FastAPI over the policyqa package.

Day-one surface so the front end has something real to call:
  GET  /health            index and model status
  GET  /search?q=&k=      hybrid retrieval with the answering reranker
  POST /answer            {"question": "..."} -> answer with verified citations
                          (mock provider until POLICYQA_LLM_* are set)

Run: uvicorn api.main:app --reload --port 8000
The case endpoints (intake, investigate, verdict, letter) land as the agent is built.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

app = FastAPI(title="Recourse API", version="0.1.0")
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

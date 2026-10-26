"""Hybrid retrieval: BM25 and dense lists fused by reciprocal rank fusion, then an
optional cross-encoder reranker over the fused top-N.

Why RRF and not score mixing: BM25 and cosine scores live on different scales,
and RRF needs no tuning to combine them. k=60 is the usual constant.
"""
from dataclasses import dataclass

import numpy as np

from .index import Index

RERANK_MODEL = "BAAI/bge-reranker-base"  # batch evaluation: best recall, about 9 s a query on CPU
ANSWER_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # live answering: under a second on CPU
ANSWER_CANDIDATES = 20


@dataclass
class Hit:
    chunk: dict
    score: float
    source: str  # "bm25", "dense", "hybrid", "rerank"


def _topk(scores: np.ndarray, k: int) -> list[int]:
    k = min(k, len(scores))
    idx = np.argpartition(-scores, k - 1)[:k]
    return idx[np.argsort(-scores[idx])].tolist()


class Retriever:
    def __init__(self, index: Index, mode: str = "hybrid", rerank: bool = False, rerank_model: str = RERANK_MODEL):
        self.index = index
        self.mode = mode
        self.reranker = None
        if rerank:
            from sentence_transformers import CrossEncoder

            self.reranker = CrossEncoder(rerank_model)

    def search(self, query: str, k: int = 10, candidates: int = 40, rrf_k: int = 60, trace=None, jurisdictions: set[str] | None = None) -> list[Hit]:
        """Top `k` hits. With `jurisdictions` (for example {"Florida"}), only chunks from those
        jurisdictions count: the candidate pool is widened until `k` of them are found or the
        index runs out, and at most `candidates` filtered hits go to the reranker."""
        from contextlib import nullcontext

        span = trace.span if trace is not None else (lambda name, **kw: nullcontext())
        with span("retrieve", mode=self.mode, candidates=candidates, jurisdictions=sorted(jurisdictions) if jurisdictions else None):
            if jurisdictions:
                hits = self._search_filtered(query, k, candidates, rrf_k, set(jurisdictions))
            else:
                hits = self._search(query, candidates, rrf_k)
        if self.reranker is not None and hits:
            with span("rerank", model=getattr(self.reranker, "model_name", None) or "cross-encoder", pairs=len(hits)):
                pairs = [(query, h.chunk["text"]) for h in hits]
                scores = self.reranker.predict(pairs, batch_size=16)
                hits = [Hit(h.chunk, float(s), "rerank") for h, s in zip(hits, scores)]
                hits.sort(key=lambda h: -h.score)
        return hits[:k]

    def _search_filtered(self, query: str, k: int, candidates: int, rrf_k: int, allowed: set[str]) -> list[Hit]:
        total = len(self.index.chunks)
        pool = candidates
        while True:
            hits = [h for h in self._search(query, pool, rrf_k) if h.chunk.get("jurisdiction") in allowed]
            if len(hits) >= k or pool >= total:
                return hits[: max(candidates, k)]
            pool = min(total, pool * 4)

    def _search(self, query: str, candidates: int, rrf_k: int) -> list[Hit]:
        idx = self.index
        if self.mode == "bm25" or idx.dense is None:
            s = idx.bm25_scores(query)
            order = _topk(s, candidates)
            hits = [Hit(idx.chunks[i], float(s[i]), "bm25") for i in order]
        elif self.mode == "dense":
            s = idx.dense_scores(query)
            order = _topk(s, candidates)
            hits = [Hit(idx.chunks[i], float(s[i]), "dense") for i in order]
        else:
            b = idx.bm25_scores(query)
            d = idx.dense_scores(query)
            fused: dict[int, float] = {}
            for rank, i in enumerate(_topk(b, candidates)):
                fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank + 1)
            for rank, i in enumerate(_topk(d, candidates)):
                fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank + 1)
            order = sorted(fused, key=lambda i: -fused[i])[:candidates]
            hits = [Hit(idx.chunks[i], fused[i], "hybrid") for i in order]
        return hits

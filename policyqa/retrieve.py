"""Hybrid retrieval: BM25 and dense lists fused by reciprocal rank fusion, then an
optional cross-encoder reranker over the fused top-N.

Why RRF and not score mixing: BM25 and cosine scores live on different scales,
and RRF needs no tuning to combine them. k=60 is the usual constant.
"""
from dataclasses import dataclass

import numpy as np

from .index import Index

RERANK_MODEL = "BAAI/bge-reranker-base"


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

    def search(self, query: str, k: int = 10, candidates: int = 40, rrf_k: int = 60) -> list[Hit]:
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

        if self.reranker is not None and hits:
            pairs = [(query, h.chunk["text"]) for h in hits]
            scores = self.reranker.predict(pairs, batch_size=16)
            hits = [Hit(h.chunk, float(s), "rerank") for h, s in zip(hits, scores)]
            hits.sort(key=lambda h: -h.score)
        return hits[:k]

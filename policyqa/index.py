"""Build and load the two indexes: BM25 over tokens, dense embeddings over text.

The dense model is bge-small-en-v1.5 (384 dims, runs on CPU). Embeddings are
stored as a float32 matrix next to the chunks file. BM25 is rebuilt from the
chunks at load time, which takes a second or two for ~10k chunks.
"""
import json
from pathlib import Path

import numpy as np

from .chunk import load_chunks
from .textnorm import tokens

EMBED_MODEL = "BAAI/bge-small-en-v1.5"


def build_dense(chunks_path: Path, out_path: Path, model_name: str = EMBED_MODEL, batch_size: int = 64) -> dict:
    from sentence_transformers import SentenceTransformer

    chunks = load_chunks(chunks_path)
    model = SentenceTransformer(model_name)
    # bge recommends passages without an instruction prefix; queries get one at search time.
    texts = [f"{c['title']}\n{c['text']}" for c in chunks]
    emb = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
    np.save(out_path, emb.astype(np.float32))
    meta = {"model": model_name, "chunks": len(chunks), "dims": int(emb.shape[1])}
    (out_path.with_suffix(".json")).write_text(json.dumps(meta))
    return meta


class Index:
    def __init__(self, chunks_path: Path, dense_path: Path | None = None, model_name: str = EMBED_MODEL):
        from rank_bm25 import BM25Okapi

        self.chunks = load_chunks(chunks_path)
        self.bm25 = BM25Okapi([tokens(c["text"]) for c in self.chunks])
        self.dense = None
        self.model = None
        if dense_path and Path(dense_path).exists():
            self.dense = np.load(dense_path)
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)

    def bm25_scores(self, query: str) -> np.ndarray:
        return np.asarray(self.bm25.get_scores(tokens(query)), dtype=np.float32)

    def dense_scores(self, query: str) -> np.ndarray:
        q = self.model.encode(
            ["Represent this sentence for searching relevant passages: " + query],
            normalize_embeddings=True,
        )[0]
        return self.dense @ q

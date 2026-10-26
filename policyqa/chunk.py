"""Page text to chunks.

Rules:
- A chunk never crosses a page. Citations are (doc_id, page), and a chunk that
  spans pages cannot be cited honestly.
- Within a page, text is split into windows of `size` words with `overlap` words
  shared between neighbors, so a quote that sits on a window edge still lands
  whole in one of them.
- Each chunk carries doc_id, page, the document title and jurisdiction from the
  manifest, and its position, so the answer layer can cite without a lookup.
"""
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    page: int
    pos: int
    title: str
    jurisdiction: str
    text: str


def _clean_page(raw: str) -> str:
    # Collapse the column padding pdftotext -layout inserts, keep line breaks for
    # readability in citations. Normalization for matching happens later.
    lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in raw.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def chunk_page(text: str, size: int, overlap: int):
    words = text.split()
    if not words:
        return
    step = max(1, size - overlap)
    start = 0
    while True:
        window = words[start : start + size]
        yield " ".join(window)
        if start + size >= len(words):
            break
        start += step


def chunk_corpus(manifest: Path, text_dir: Path, out: Path, size: int = 300, overlap: int = 60) -> dict:
    meta = {r["id"]: r for r in csv.DictReader(open(manifest, encoding="utf-8"))}
    n_chunks = n_pages = 0
    docs = 0
    with open(out, "w", encoding="utf-8") as f:
        for doc_id in sorted(meta):
            d = text_dir / doc_id
            if not d.exists():
                continue
            docs += 1
            for page_file in sorted(d.glob("p*.txt")):
                page = int(page_file.stem[1:])
                n_pages += 1
                body = _clean_page(page_file.read_text(encoding="utf-8", errors="ignore"))
                for pos, window in enumerate(chunk_page(body, size, overlap)):
                    c = Chunk(
                        chunk_id=f"{doc_id}:p{page:03d}:{pos}",
                        doc_id=doc_id,
                        page=page,
                        pos=pos,
                        title=meta[doc_id]["title"],
                        jurisdiction=meta[doc_id]["jurisdiction"],
                        text=window,
                    )
                    f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
                    n_chunks += 1
    return {"docs": docs, "pages": n_pages, "chunks": n_chunks, "size": size, "overlap": overlap}


def load_chunks(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]

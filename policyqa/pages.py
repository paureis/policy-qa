"""Highlighted page images: the real PDF page with the cited quote boxed.

Every citation names a doc and a page. This module turns that into something a
person can check with their own eyes:

- `render_page` draws the page as a PNG with pdftoppm and caches it on disk
  (RECOURSE_PAGE_CACHE, default data/pages/<doc_id>/pNNN-<dpi>.png).
- `page_words` reads every word and its box with `pdftotext -bbox`, the same
  poppler text layer the golden-set quotes were copied from.
- `locate_quote` finds the run of words that best matches the quote, tolerating
  edge punctuation, case, line-break hyphenation, and up to 15 percent missed
  words, in reading order and also row by row (table rows), and returns one box
  per line in PDF points.
- `highlight` scales those boxes to pixels for one dpi.
- `vision_check` sends the page image and the rectangles to Muse Spark and asks it
  to read the text inside them, so a second, independent reader confirms the box
  holds the quote. `FixtureVision` stands in when no model is configured.

The PDFs are not in the repo. RECOURSE_PDF_DIR (default data/pdfs) says where they
are on this machine; a doc in the manifest whose PDF is absent is `no_pdf`, not an error
in the code. Files under 10 KB are treated as absent, the same rule ingest.py uses for
stub downloads.

Coordinates: PDF points, origin top left (pdftotext reports yMin from the top), and
pixels = points * dpi / 72.
"""
from __future__ import annotations

import base64
import csv
import html
import math
import os
import re
import struct
import subprocess
import tempfile
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

from .textnorm import norm, quote_overlap

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "corpus" / "manifest.csv"
DEFAULT_DPI = 110
MIN_PDF_BYTES = 10_000
FOUND_THRESHOLD = 0.8
MISS_ALLOWANCE = 0.15
LINE_TOLERANCE = 2.0  # points: words whose yMin differ by at most this are on one line
VISION_MAX_TOKENS = 6000  # Muse Spark is a reasoning model: the thinking shares this budget


class PageError(Exception):
    """A page that cannot be served. `code` is one of not_found, no_pdf, bad_page, render_failed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---- where the PDFs are -----------------------------------------------------


@lru_cache(maxsize=1)
def manifest() -> dict[str, dict]:
    with open(MANIFEST, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def pdf_dir() -> Path:
    return Path(os.environ.get("RECOURSE_PDF_DIR") or ROOT / "data" / "pdfs")


def page_cache_dir() -> Path:
    return Path(os.environ.get("RECOURSE_PAGE_CACHE") or ROOT / "data" / "pages")


def _usable(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size >= MIN_PDF_BYTES
    except OSError:
        return False


def pdf_path(doc_id: str) -> Path:
    if doc_id not in manifest():
        raise PageError("not_found", f"No document {doc_id} in the corpus.")
    p = pdf_dir() / f"{doc_id}.pdf"
    if not _usable(p):
        raise PageError("no_pdf", f"The PDF for {doc_id} is not fetched on this machine. Set RECOURSE_PDF_DIR to the folder that holds the corpus PDFs.")
    return p


def pdf_count() -> int:
    """How many manifest documents have a usable PDF on this machine."""
    d = pdf_dir()
    return sum(1 for doc_id in manifest() if _usable(d / f"{doc_id}.pdf"))


@lru_cache(maxsize=256)
def _page_count(path: str, mtime: float) -> int:
    from .ingest import pdf_pages

    return pdf_pages(Path(path))


def _check_page(doc_id: str, page: int) -> Path:
    p = pdf_path(doc_id)
    try:
        n = _page_count(str(p), p.stat().st_mtime)
    except (subprocess.CalledProcessError, RuntimeError, OSError):
        n = int(manifest()[doc_id].get("pages") or 0)
    if not (1 <= page <= n):
        raise PageError("bad_page", f"{doc_id} has {n} pages; page {page} does not exist.")
    return p


# ---- render -----------------------------------------------------------------


def render_page(doc_id: str, page: int, dpi: int = DEFAULT_DPI) -> bytes:
    """The page as a PNG, drawn once by pdftoppm and then read from the disk cache."""
    pdf = _check_page(doc_id, page)
    target = page_cache_dir() / doc_id / f"p{page:03d}-{dpi}.png"
    if target.exists():
        return target.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        prefix = Path(tmp) / "page"
        try:
            subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-singlefile", str(pdf), str(prefix)],
                check=True, capture_output=True, timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise PageError("render_failed", f"pdftoppm could not draw {doc_id} page {page}: {type(e).__name__}") from e
        out = prefix.with_suffix(".png")
        data = out.read_bytes()
        os.replace(out, target)  # atomic: a concurrent reader sees the whole file or none
    return data


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) from a PNG's IHDR chunk."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def page_size_px(width_pt: float, height_pt: float, dpi: int) -> tuple[int, int]:
    """The pixel size pdftoppm gives a page of this size (it rounds up)."""
    return math.ceil(width_pt * dpi / 72 - 1e-6), math.ceil(height_pt * dpi / 72 - 1e-6)


# ---- words and boxes --------------------------------------------------------

_PAGE_TAG = re.compile(r'<page\s+width="([\d.]+)"\s+height="([\d.]+)"')
_WORD_TAG = re.compile(r'<word\s+xMin="([\d.\-]+)"\s+yMin="([\d.\-]+)"\s+xMax="([\d.\-]+)"\s+yMax="([\d.\-]+)">(.*?)</word>', re.S)


def parse_bbox(xhtml: str) -> dict:
    """Parse `pdftotext -bbox` output for one page into {width, height, words}."""
    m = _PAGE_TAG.search(xhtml)
    width, height = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    words = [
        {"text": html.unescape(t), "x0": float(a), "y0": float(b), "x1": float(c), "y1": float(d)}
        for a, b, c, d, t in _WORD_TAG.findall(xhtml)
    ]
    return {"width": width, "height": height, "words": words}


@lru_cache(maxsize=512)
def _words_cached(path: str, mtime: float, page: int) -> dict:
    out = subprocess.run(
        ["pdftotext", "-bbox", "-f", str(page), "-l", str(page), path, "-"],
        check=True, capture_output=True, timeout=60,
    ).stdout.decode("utf-8", errors="replace")
    return parse_bbox(out)


def page_words(doc_id: str, page: int) -> dict:
    """{width, height, words: [{text, x0, y0, x1, y1}]} in PDF points, cached per process."""
    pdf = _check_page(doc_id, page)
    try:
        r = _words_cached(str(pdf), pdf.stat().st_mtime, page)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise PageError("render_failed", f"pdftotext could not read {doc_id} page {page}: {type(e).__name__}") from e
    return {"width": r["width"], "height": r["height"], "words": [dict(w) for w in r["words"]]}


_HYPHENS = str.maketrans({"­": "-", "‐": "-", "‑": "-", "‒": "-"})
_EDGE = re.compile(r"^[^0-9a-z]+|[^0-9a-z]+$")


def _raw(w: str) -> str:
    """textnorm.norm plus NFKC (ligatures) and hyphen variants; may still end with '-'."""
    return norm(unicodedata.normalize("NFKC", w).translate(_HYPHENS))


def _clean(w: str) -> str:
    return _EDGE.sub("", w)


def _quote_tokens(quote: str) -> list[str]:
    raw = [_raw(w) for w in quote.split()]
    out: list[str] = []
    i = 0
    while i < len(raw):
        w = raw[i]
        if w.endswith("-") and len(w) > 1 and i + 1 < len(raw) and _clean(raw[i + 1]):
            out.append(_clean(w[:-1]) + _clean(raw[i + 1]))  # "con- tinual" copied from layout text
            i += 2
            continue
        c = _clean(w)
        if c:
            out.append(c)
        i += 1
    return out


def _row_order(words: list[dict]) -> list[int]:
    """Word indices line by line (yMin within LINE_TOLERANCE), left to right.

    pdftotext -bbox emits a table column by column; a quote copied from a table row
    (a fee schedule line, a product list) reads across, so it is matched in this order too.
    """
    by_y = sorted(range(len(words)), key=lambda i: (words[i]["y0"], words[i]["x0"]))
    lines: list[list[int]] = []
    for i in by_y:
        if lines and abs(words[i]["y0"] - words[lines[-1][0]]["y0"]) <= LINE_TOLERANCE:
            lines[-1].append(i)
        else:
            lines.append([i])
    return [i for line in lines for i in sorted(line, key=lambda k: words[k]["x0"])]


def _streams(words: list[dict]) -> list[tuple[list[int], list[tuple[frozenset, list[int]]]]]:
    """Token streams over the page words, each paired with the word order it reads.

    For each order (as printed, then row by row) two streams: words as printed, and
    with line-end hyphens joined. A token is (accepted forms, positions in the order).
    """
    out = []
    reading = list(range(len(words)))
    rows = _row_order(words)
    for order in ([reading] if rows == reading else [reading, rows]):
        raw = [_raw(words[i]["text"]) for i in order]
        plain = [(frozenset({c}), [k]) for k, c in ((k, _clean(r)) for k, r in enumerate(raw)) if c]
        joined: list[tuple[frozenset, list[int]]] = []
        k = 0
        while k < len(raw):
            r = raw[k]
            if r.endswith("-") and len(r) > 1 and k + 1 < len(raw) and _clean(raw[k + 1]):
                head, tail = _clean(r[:-1]), _clean(raw[k + 1])
                joined.append((frozenset({head + tail, f"{head}-{tail}"}), [k, k + 1]))
                k += 2
                continue
            c = _clean(r)
            if c:
                joined.append((frozenset({c}), [k]))
            k += 1
        out.append((order, plain))
        if joined != plain:
            out.append((order, joined))
    return out


def _lcs(q: list[str], window: list[tuple[frozenset, list[int]]]) -> list[int]:
    """Indices into `window` of an in-order longest match against the quote tokens."""
    n, m = len(q), len(window)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        qi, row, nxt = q[i], dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            row[j] = nxt[j + 1] + 1 if qi in window[j][0] else max(nxt[j], row[j + 1])
    hits, i, j = [], 0, 0
    while i < n and j < m:
        if q[i] in window[j][0]:
            hits.append(j)
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return hits


def _line_boxes(run: list[dict]) -> list[dict]:
    """One box per line over a run of words (consecutive words with yMin within LINE_TOLERANCE merge)."""
    boxes: list[dict] = []
    for w in run:
        if boxes and abs(w["y0"] - boxes[-1]["_y"]) <= LINE_TOLERANCE:
            b = boxes[-1]
            b["x0"], b["y0"], b["x1"], b["y1"] = min(b["x0"], w["x0"]), min(b["y0"], w["y0"]), max(b["x1"], w["x1"]), max(b["y1"], w["y1"])
        else:
            boxes.append({"x0": w["x0"], "y0": w["y0"], "x1": w["x1"], "y1": w["y1"], "_y": w["y0"]})
    return [{k: round(b[k], 2) for k in ("x0", "y0", "x1", "y1")} for b in boxes]


def locate_quote(words: list[dict], quote: str) -> dict:
    """The run of consecutive page words that best matches the quote.

    score is the fraction of quote words matched in order inside a window of the
    quote's length plus 15 percent (so up to 15 percent of words may be missing or
    extra); `score >= 0.8` counts as found. Boxes are one per line, in PDF points.
    """
    q = _quote_tokens(quote)
    empty = {"boxes": [], "matched": "", "score": 0.0}
    if not q or not words:
        return empty
    allow = math.ceil(len(q) * MISS_ALLOWANCE)
    span_len = len(q) + allow
    lead = set(q[: allow + 1])
    best = None  # ((score, -span, -start), order, first position, last position)
    for order, stream in _streams(words):
        for start, (forms, _) in enumerate(stream):
            if not (forms & lead):
                continue
            window = stream[start : start + span_len]
            hits = _lcs(q, window)
            if not hits:
                continue
            first, last = window[hits[0]][1][0], window[hits[-1]][1][-1]
            key = (len(hits) / len(q), -(last - first), -first)
            if best is None or key > best[0]:  # ties keep the earlier stream: reading order first
                best = (key, order, first, last)
    if best is None:
        return empty
    (score, _, _), order, first, last = best
    run = [words[i] for i in order[first : last + 1]]
    return {
        "boxes": _line_boxes(run),
        "matched": " ".join(w["text"] for w in run),
        "score": round(score, 4),
    }


def highlight(doc_id: str, page: int, quote: str, dpi: int = DEFAULT_DPI) -> dict:
    """The quote's boxes on one page, in pixels at `dpi`, with the image URL to draw them on."""
    pw = page_words(doc_id, page)
    loc = locate_quote(pw["words"], quote)
    scale = dpi / 72
    w_px, h_px = page_size_px(pw["width"], pw["height"], dpi)
    return {
        "doc_id": doc_id,
        "title": manifest()[doc_id]["title"],
        "page": page,
        "dpi": dpi,
        "width_px": w_px,
        "height_px": h_px,
        "boxes_px": [{k: round(b[k] * scale, 1) for k in ("x0", "y0", "x1", "y1")} for b in loc["boxes"]],
        "score": loc["score"],
        "found": loc["score"] >= FOUND_THRESHOLD,
        "matched": loc["matched"],
        "image_url": f"/doc/{doc_id}/page/{page}.png?dpi={dpi}",
    }


# ---- vision check -----------------------------------------------------------

VISION_SYSTEM = """You read text from an image of one page of a healthcare policy document. You are a careful proofreader, not an interpreter.

You are given the page image, its size in pixels, one or more rectangles on it in pixels (origin at the top left), and a quote.
1. Read the printed text that lies inside the rectangles, in reading order, rectangle 1 first. Copy it exactly as printed. Do not add text from outside the rectangles.
2. Set contains_quote to true only when that text contains the quote word for word, allowing for line breaks, hyphenation at a line end, and punctuation.
3. Return JSON only, matching the schema."""

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "text_in_highlight": {"type": "string"},
        "contains_quote": {"type": "boolean"},
    },
    "required": ["text_in_highlight", "contains_quote"],
    "additionalProperties": False,
}


def vision_prompt(hl: dict, quote: str) -> str:
    rects = "\n".join(
        f"{i}. x0={b['x0']:g}, y0={b['y0']:g}, x1={b['x1']:g}, y1={b['y1']:g}" for i, b in enumerate(hl["boxes_px"], start=1)
    )
    return (
        f"The image is page {hl['page']} of \"{hl['title']}\", {hl['width_px']} x {hl['height_px']} pixels.\n"
        f"Highlight rectangles in pixels (x0, y0 top left; x1, y1 bottom right):\n{rects}\n\n"
        f"Quote:\n{quote}\n\n"
        "Read the text inside the rectangles and say whether it contains the quote."
    )


class FixtureVision:
    """Stands in for the model when POLICYQA_LLM_* are not set: it agrees with the quote."""

    model = "fixture"


def _vision_meta(model: str) -> dict:
    return {"checked": False, "model": model}


def vision_check(doc_id: str, page: int, quote: str, provider, dpi: int = DEFAULT_DPI, hl: dict | None = None) -> dict:
    """Ask the vision model to read the highlighted rectangles and confirm they hold the quote.

    agrees = quote_overlap(quote, text_in_highlight) >= 0.8, or the model's contains_quote.
    Any provider failure (HTTP, timeout, truncation, bad JSON) is returned as
    {checked: false, error}, never raised. PageError (no PDF, bad page) is raised.
    """
    from .generate import parse_model_json, reasoning_tokens

    model = getattr(provider, "model", "?")
    hl = hl if hl is not None else highlight(doc_id, page, quote, dpi)
    t = time.perf_counter()
    if not hl.get("found") or not hl.get("boxes_px"):
        return {**_vision_meta(model), "error": f"quote not located on the page (score {hl.get('score', 0.0)}), so there is no highlight to check"}
    if isinstance(provider, FixtureVision):
        return {
            "checked": True, "model": "fixture", "text_in_highlight": quote, "agrees": True,
            "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0,
            "latency_ms": round((time.perf_counter() - t) * 1000, 1), "cost_usd": 0.0,
        }
    png = render_page(doc_id, page, dpi)
    parts = [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}},
        {"type": "text", "text": vision_prompt(hl, quote)},
    ]
    try:
        raw, n_in, n_out = provider.complete_parts(VISION_SYSTEM, parts, schema=VISION_SCHEMA, max_tokens=VISION_MAX_TOKENS, schema_name="highlight_check")
        data = parse_model_json(raw)
        if not isinstance(data, dict) or not isinstance(data.get("text_in_highlight"), str):
            raise ValueError(f"reply is not the highlight_check shape: {raw[:200]!r}")
    except Exception as e:  # noqa: BLE001 - reported to the screen, not hidden
        return {**_vision_meta(model), "error": f"{type(e).__name__}: {e}"[:500], "latency_ms": round((time.perf_counter() - t) * 1000, 1)}
    text = data["text_in_highlight"]
    contains = data.get("contains_quote") is True
    cost = getattr(provider, "cost", None)
    return {
        "checked": True,
        "model": model,
        "text_in_highlight": text,
        "agrees": bool(quote_overlap(quote, text) >= FOUND_THRESHOLD or contains),
        "input_tokens": int(n_in),
        "output_tokens": int(n_out),
        "reasoning_tokens": reasoning_tokens(provider),
        "latency_ms": round((time.perf_counter() - t) * 1000, 1),
        "cost_usd": float(cost(n_in, n_out)) if callable(cost) else 0.0,
    }

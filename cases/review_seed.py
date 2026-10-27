"""Build cases/review-seed.json, the seed rows for the Case Review page.

Stdlib only. Run from the repo root:  .venv/Scripts/python.exe cases/review_seed.py

For each row of cases/cases.csv the seed holds every CSV column plus:
  - letter_text      the full text of cases/letters/<id>.txt
  - hinge_doc_title  the document title from corpus/manifest.csv
  - hinge_context    about 700 characters of whitespace-normalized page text around the hinge
                     quote, from data/text/<hinge_doc_id>/p<NNN>.txt. The quote itself is wrapped
                     in [[ and ]] so the page can highlight it. Empty when the page text is
                     missing or the quote is not on the page (the script says which).
  - verdict          null (unreviewed)

Rows are sorted by id and written with sorted keys, so the output is deterministic.
Exit code 0 when every row has a letter and a non-empty context, 1 otherwise.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CSV_PATH = HERE / "cases.csv"
LETTERS = HERE / "letters"
MANIFEST = REPO / "corpus" / "manifest.csv"
TEXT = REPO / "data" / "text"
OUT = HERE / "review-seed.json"

CONTEXT_CHARS = 700   # target length of the whole context, quote included
MIN_SIDE = 120        # always show at least this much on each side of the quote
OPEN, CLOSE = "[[", "]]"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def display(text: str) -> str:
    """Symbol-font bullets come out of the PDFs as private-use characters (U+F0B7 and friends),
    which render as boxes. Show them as a bullet."""
    return re.sub("[\ue000-\uf8ff]", "\u2022", text)


def titles() -> dict[str, str]:
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        return {r["id"]: r["title"] for r in csv.DictReader(f)}


def context(doc_id: str, page: str, quote: str) -> tuple[str, str]:
    """Return (context, problem). problem is "" when the context is good."""
    try:
        n = int(page)
    except ValueError:
        return "", f"hinge_page {page!r} is not a number"
    folder = TEXT / doc_id
    if not folder.is_dir():
        return "", f"page text folder data/text/{doc_id} is missing on this machine"
    path = folder / f"p{n:03d}.txt"
    if not path.is_file():
        return "", f"page file data/text/{doc_id}/p{n:03d}.txt is missing"
    page_text = display(norm(path.read_text(encoding="utf-8", errors="replace")))
    q = display(norm(quote))
    if OPEN in page_text or CLOSE in page_text:
        return "", f"page text contains the marker {OPEN} or {CLOSE}"
    start = page_text.find(q)
    if start < 0:
        return "", f"hinge quote not found on data/text/{doc_id}/p{n:03d}.txt"
    end = start + len(q)
    side = max(MIN_SIDE, (CONTEXT_CHARS - len(q)) // 2)
    a = max(0, start - side)
    b = min(len(page_text), end + side)
    # Snap to word boundaries so the context does not start or end mid-word.
    if a > 0:
        sp = page_text.find(" ", a, start)
        a = sp + 1 if sp >= 0 else a
    if b < len(page_text):
        sp = page_text.rfind(" ", end, b)
        b = sp if sp >= 0 else b
    before = ("… " if a > 0 else "") + page_text[a:start]
    after = page_text[end:b] + (" …" if b < len(page_text) else "")
    return f"{before}{OPEN}{q}{CLOSE}{after}", ""


def main() -> int:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    names = titles()
    out: list[dict] = []
    problems: list[str] = []
    for r in sorted(rows, key=lambda x: x["id"]):
        row = {c: r.get(c, "") for c in columns}
        letter = LETTERS / f"{r['id']}.txt"
        if letter.is_file():
            row["letter_text"] = letter.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        else:
            row["letter_text"] = ""
            problems.append(f"{r['id']}: letter cases/letters/{r['id']}.txt is missing")
        row["hinge_doc_title"] = names.get(r["hinge_doc_id"], "")
        if not row["hinge_doc_title"]:
            problems.append(f"{r['id']}: {r['hinge_doc_id']} has no title in corpus/manifest.csv")
        ctx, problem = context(r["hinge_doc_id"], r["hinge_page"], r["hinge_quote"])
        row["hinge_context"] = ctx
        if problem:
            problems.append(f"{r['id']}: empty hinge_context, {problem}")
        row["verdict"] = None
        out.append(row)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with_letter = sum(1 for x in out if x["letter_text"])
    with_ctx = sum(1 for x in out if x["hinge_context"])
    print(f"wrote {OUT.relative_to(REPO).as_posix()}: {len(out)} rows, "
          f"{with_letter} letters, {with_ctx} contexts, {OUT.stat().st_size} bytes")
    for p in problems:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

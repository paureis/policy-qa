"""PDF to page text. One file per page, text/<doc_id>/pNNN.txt, via pdftotext -layout.

This is the exact layout the golden-set quotes were copied from, which is why we
keep it instead of a Python PDF library: the quotes must match byte for byte
after whitespace normalization.
"""
import csv
import subprocess
from pathlib import Path


def pdf_pages(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError(f"no page count for {pdf}")


def ingest_doc(pdf: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = pdf_pages(pdf)
    for p in range(1, n + 1):
        target = out_dir / f"p{p:03d}.txt"
        if target.exists():
            continue
        subprocess.run(
            ["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(pdf), str(target)],
            check=True,
            capture_output=True,
        )
    return n


def ingest(manifest: Path, pdf_dir: Path, text_dir: Path) -> dict:
    rows = list(csv.DictReader(open(manifest, encoding="utf-8")))
    report = {"docs": 0, "pages": 0, "missing": [], "page_mismatch": []}
    for r in rows:
        pdf = pdf_dir / f"{r['id']}.pdf"
        if not pdf.exists() or pdf.stat().st_size < 10_000:
            report["missing"].append(r["id"])
            continue
        try:
            n = ingest_doc(pdf, text_dir / r["id"])
        except subprocess.CalledProcessError:
            report["missing"].append(r["id"])
            continue
        if str(n) != r["pages"]:
            report["page_mismatch"].append((r["id"], r["pages"], n))
        report["docs"] += 1
        report["pages"] += n
    return report

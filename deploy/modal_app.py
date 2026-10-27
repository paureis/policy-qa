"""Recourse API on Modal: the FastAPI app in api/main.py behind one warm container.

Runbook: deploy/README.md. Commands (from the repo root, in the venv where `pip install modal` ran):

    modal run deploy/modal_app.py::inventory     # what the data volume holds
    modal run deploy/modal_app.py::populate      # optional: fetch the 64 PDFs and build the index in the cloud
    modal deploy deploy/modal_app.py             # serve the API

Layout inside the container. api/main.py computes ROOT from its own file (ROOT = parent of api/)
and reads the index from ROOT/data with no env override, so the source goes to /root/api and
/root/policyqa, the manifest to /root/corpus/manifest.csv, and the Volume mounts at /root/data:

    /root/data/chunks.jsonl, dense.npy, dense.json   the index (main.py reads these directly)
    /root/data/text/<doc_id>/pNNN.txt                page text (ingest output; populate needs it)
    /root/data/pdfs/<doc_id>.pdf                     RECOURSE_PDF_DIR
    /root/data/pages/                                RECOURSE_PAGE_CACHE (rendered PNGs, rebuilt on demand)
    /root/data/cases/                                RECOURSE_CASE_DIR (one JSON file per case)

Why one container (max_containers=1, min_containers=1, many concurrent inputs):
- The case store (api/cases.py) is a dict in process memory, loaded from RECOURSE_CASE_DIR once at
  start. A second container would not see cases the first one created after it started, so a
  GET /case/{id} routed to it would 404, and claim_for_investigation's lock would not span both.
- The investigation, verdict, letter and critic run in a background thread after
  POST /case/{id}/investigate has answered 202. Modal considers the request finished at that
  point; only a container that stays up keeps the thread alive for the 60 to 90 s a case takes.
- A cold start (torch, two sentence-transformers models, BM25 over 4,131 chunks) is slower than
  the front end's 30-second intake timeout, so the container is kept warm.

Importing this file needs no Modal credentials: Modal objects are lazy until `modal run` or
`modal deploy`. Without the `modal` package the import still works and `app` is None, so the
repo's tests run in a venv that never installed Modal (see deploy/test_modal_app.py).
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

try:  # the owner installs Modal by hand (`pip install modal`); it is not in pyproject
    import modal
except ImportError as _e:  # pragma: no cover - depends on the venv
    modal = None
    MODAL_IMPORT_ERROR: str | None = f"{_e}. Install it with `pip install modal` to deploy."
else:
    MODAL_IMPORT_ERROR = None

# ---- names (the README and the test read these) ------------------------------------------------

APP_NAME = "recourse-api"
ASGI_LABEL = "recourse-api"  # URL: https://<workspace>--recourse-api.modal.run
VOLUME_NAME = "recourse-data"
SECRET_NAME = "recourse-muse-spark"
SECRET_KEYS = (
    "POLICYQA_LLM_BASE_URL",
    "POLICYQA_LLM_API_KEY",
    "POLICYQA_LLM_MODEL",
    "POLICYQA_LLM_INPUT_USD_PER_M",
    "POLICYQA_LLM_OUTPUT_USD_PER_M",
    "POLICYQA_LLM_REASONING_EFFORT",
)

REPO = Path(__file__).resolve().parent.parent  # the repo root on the owner's machine
REMOTE_ROOT = "/root"  # ROOT as api/main.py and policyqa/pages.py compute it in the container
DATA_MOUNT = f"{REMOTE_ROOT}/data"  # must equal ROOT/data: main.py reads data/chunks.jsonl there
REMOTE_MANIFEST = f"{REMOTE_ROOT}/corpus/manifest.csv"
HF_HOME = "/models/hf"  # model cache baked into the image, outside the volume mount

# Must match policyqa/index.py EMBED_MODEL and policyqa/retrieve.py ANSWER_RERANK_MODEL (the test checks).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
ANSWER_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# The versions in the owner's working venv on Oct 26, 2026 (`pip freeze`), so the cloud runs what
# was tested. torch comes from the CPU wheel index: the default wheel pulls several GB of CUDA.
TORCH_PIN = "torch==2.14.1"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
PIP_PINS = (
    "fastapi==0.162.0",
    "uvicorn[standard]==0.54.0",
    "python-multipart==0.0.32",
    "sentence-transformers==6.2.0",
    "transformers==5.20.2",
    "huggingface_hub==2.3.0",
    "numpy==2.5.4",
    "rank-bm25==0.2.2",
    "httpx==0.28.1",
    "anthropic==2.3.0",
    "tzdata==2026.5",
)

# CORS: the Vercel production URL, read from the deploying shell so no URL is hard-coded here.
# PowerShell: $env:RECOURSE_CORS_ORIGINS = "https://<project>.vercel.app,http://localhost:3000"
CORS_PLACEHOLDER = "https://REPLACE-WITH-YOUR-PROJECT.vercel.app,http://localhost:3000"
CORS_ORIGINS = os.environ.get("RECOURSE_CORS_ORIGINS") or CORS_PLACEHOLDER

# Keep one container up. RECOURSE_MODAL_MIN_CONTAINERS=0 in the deploying shell scales to zero
# between demos (cheaper; the first request then waits for a cold start; see the README).
MIN_CONTAINERS = int(os.environ.get("RECOURSE_MODAL_MIN_CONTAINERS", "1"))
MAX_INPUTS = 32  # concurrent requests in the one container (polls, page images, intake)

RUNTIME_ENV = {
    "RECOURSE_PDF_DIR": f"{DATA_MOUNT}/pdfs",
    "RECOURSE_PAGE_CACHE": f"{DATA_MOUNT}/pages",
    "RECOURSE_CASE_DIR": f"{DATA_MOUNT}/cases",
    "RECOURSE_CORS_ORIGINS": CORS_ORIGINS,
    "RECOURSE_CRITIC_ROUNDS": "1",
    "HF_HUB_OFFLINE": "1",  # the models are in the image; never reach the Hub at run time
    "TOKENIZERS_PARALLELISM": "false",
}

MIN_PDF_BYTES = 10_000  # the same rule as policyqa/ingest.py and pages.py: smaller files are stubs


# ---- plain helpers (no Modal, testable locally) ------------------------------------------------


def manifest_rows(path: str | os.PathLike) -> list[dict]:
    """The corpus manifest as rows with at least `id` and `url`."""
    with open(path, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]


def missing_pdfs(rows: list[dict], pdf_dir: str | os.PathLike) -> list[dict]:
    """Manifest rows whose PDF is absent or a stub under pdf_dir."""
    d = Path(pdf_dir)
    out = []
    for r in rows:
        p = d / f"{r['id']}.pdf"
        if not (p.is_file() and p.stat().st_size >= MIN_PDF_BYTES):
            out.append(r)
    return out


def build_asgi():
    """Import the API inside the container (the volume is mounted by then) and warm the retriever.

    Warming loads BM25, the dense matrix and both sentence-transformers models before the first
    request, so the first case does not pay for it. RECOURSE_WARM_RETRIEVER=0 skips it.
    """
    from api import main

    if os.environ.get("RECOURSE_WARM_RETRIEVER", "1") == "1":
        try:
            main.retriever()
        except Exception as e:  # no index yet: /health says so; the API serves fixture mode
            print(f"retriever not warmed: {e!r}")
    return main.app


# ---- Modal objects -----------------------------------------------------------------------------

if modal is None:
    app = None
else:
    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("poppler-utils")  # pdftoppm, pdftotext, pdfinfo (policyqa/pages.py, ingest.py)
        .pip_install(TORCH_PIN, index_url=TORCH_INDEX)
        .pip_install(*PIP_PINS)
        .env({"HF_HOME": HF_HOME})
        .run_commands(
            "python -c \"from sentence_transformers import SentenceTransformer, CrossEncoder; "
            f"SentenceTransformer('{EMBED_MODEL}'); CrossEncoder('{ANSWER_RERANK_MODEL}')\""
        )
    )
    if modal.is_local():  # source files are added from the owner's checkout at deploy time
        image = (
            image.add_local_dir(REPO / "api", f"{REMOTE_ROOT}/api", ignore=["**/__pycache__/**"])
            .add_local_dir(REPO / "policyqa", f"{REMOTE_ROOT}/policyqa", ignore=["**/__pycache__/**"])
            .add_local_file(REPO / "corpus" / "manifest.csv", REMOTE_MANIFEST)
        )

    app = modal.App(APP_NAME)
    data_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=False)
    muse_secret = modal.Secret.from_name(SECRET_NAME, required_keys=["POLICYQA_LLM_BASE_URL", "POLICYQA_LLM_API_KEY", "POLICYQA_LLM_MODEL"])
    runtime_env = modal.Secret.from_dict(RUNTIME_ENV)  # listed after the Muse secret so these paths win

    @app.function(
        image=image,
        volumes={DATA_MOUNT: data_volume},
        secrets=[muse_secret, runtime_env],
        cpu=2.0,
        memory=4096,
        min_containers=MIN_CONTAINERS,
        max_containers=1,  # one in-process case store; see the module docstring
        scaledown_window=1200,  # 20 min idle before scale-down when MIN_CONTAINERS is 0
        timeout=600,  # per request; a case runs in a thread after its 202, so no request is long
    )
    @modal.concurrent(max_inputs=MAX_INPUTS)
    @modal.asgi_app(label=ASGI_LABEL)
    def web():
        return build_asgi()

    @app.function(image=image, volumes={DATA_MOUNT: data_volume}, timeout=60 * 60, cpu=4.0, memory=8192)
    def populate(force: bool = False, skip_fetch: bool = False) -> dict:
        """One-time cloud build of the data volume: fetch the PDFs, ingest, chunk, embed.

        The README prefers uploading the owner's prepared data/ (the index the evals ran on).
        This is the fallback. It refuses to overwrite an existing index unless --force.
        """
        import json

        import httpx

        from policyqa.chunk import chunk_corpus
        from policyqa.index import build_dense
        from policyqa.ingest import ingest

        data = Path(DATA_MOUNT)
        pdfs, text, chunks, dense = data / "pdfs", data / "text", data / "chunks.jsonl", data / "dense.npy"
        if chunks.exists() and not force:
            msg = f"{chunks} exists; refusing to rebuild the index. Run with --force to rebuild."
            print(msg)
            return {"skipped": msg}

        report: dict = {"fetched": [], "fetch_failed": []}
        rows = manifest_rows(REMOTE_MANIFEST)
        if not skip_fetch:
            pdfs.mkdir(parents=True, exist_ok=True)
            headers = {"User-Agent": "Mozilla/5.0 (compatible; recourse-corpus-fetch/1.0)"}
            with httpx.Client(follow_redirects=True, timeout=180, headers=headers) as client:
                for r in missing_pdfs(rows, pdfs):
                    try:
                        resp = client.get(r["url"])
                        resp.raise_for_status()
                        (pdfs / f"{r['id']}.pdf").write_bytes(resp.content)
                        report["fetched"].append(r["id"])
                    except httpx.HTTPError as e:
                        report["fetch_failed"].append({"id": r["id"], "url": r["url"], "error": str(e)})
                        print(f"FAILED {r['id']} {r['url']}: {e}")
            data_volume.commit()

        report["still_missing"] = [r["id"] for r in missing_pdfs(rows, pdfs)]
        manifest = Path(REMOTE_MANIFEST)
        report["ingest"] = ingest(manifest, pdfs, text)
        report["chunk"] = chunk_corpus(manifest, text, chunks)
        report["embed"] = build_dense(chunks, dense, EMBED_MODEL)
        data_volume.commit()
        print(json.dumps(report, indent=2, default=str))
        return report

    @app.function(image=image, volumes={DATA_MOUNT: data_volume}, timeout=300)
    def inventory() -> dict:
        """What the data volume holds: run after an upload or populate, before `modal deploy`."""
        import json

        data = Path(DATA_MOUNT)
        rows = manifest_rows(REMOTE_MANIFEST)
        chunks = data / "chunks.jsonl"
        meta = data / "dense.json"
        out = {
            "chunks_lines": sum(1 for _ in open(chunks, encoding="utf-8")) if chunks.exists() else 0,
            "dense_npy": (data / "dense.npy").exists(),
            "dense_meta": json.loads(meta.read_text()) if meta.exists() else None,
            "text_docs": len([p for p in (data / "text").iterdir() if p.is_dir()]) if (data / "text").exists() else 0,
            "manifest_docs": len(rows),
            "pdfs_usable": len(rows) - len(missing_pdfs(rows, data / "pdfs")),
            "pdfs_missing": [r["id"] for r in missing_pdfs(rows, data / "pdfs")],
            "cases": len(list((data / "cases").glob("*.json"))) if (data / "cases").exists() else 0,
        }
        print(json.dumps(out, indent=2))
        return out

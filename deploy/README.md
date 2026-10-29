# Deploying Recourse: Saturday Oct 31 runbook

The API (`api/main.py` over `policyqa`) runs on Modal from `deploy/modal_app.py`. The front end (`web/`) runs on Vercel, see `deploy/vercel.md`. Nothing here has been deployed yet: every expected output below is what the code should produce, not something observed. The last section lists what is unverified.

## What gets built

| Piece | Name | Notes |
|---|---|---|
| Modal app | `recourse-api` | one function `web`, plus `populate` and `inventory` for setup |
| API URL | `https://<workspace>--recourse-api.modal.run` | `<workspace>` is your Modal workspace name |
| Modal Volume | `recourse-data` | mounted at `/root/data`, which is `data/` as `api/main.py` sees it |
| Modal Secret | `recourse-muse-spark` | the six `POLICYQA_LLM_*` values |
| Image | Debian slim, Python 3.12 | `poppler-utils`, CPU torch, pinned deps from your venv, both sentence-transformers models baked in |

The volume holds the same files your `data/` does, plus the PDFs:

```
chunks.jsonl  dense.npy  dense.json   the index (4,131 chunks on Oct 26)
text/<doc_id>/pNNN.txt                page text
pdfs/<doc_id>.pdf                     RECOURSE_PDF_DIR
pages/                                RECOURSE_PAGE_CACHE, PNGs rendered on demand
cases/                                RECOURSE_CASE_DIR, one JSON file per case
```

Why one container, kept warm (`min_containers=1`, `max_containers=1`, 32 concurrent requests):

- Cases live in a dict in the API process (`api/cases.py`), loaded from `cases/` once at start. A second container would not see cases the first one created, so polling `GET /case/{id}` could 404 and two containers could both run one case.
- A case runs in a background thread after `POST /case/{id}/investigate` answers 202. Modal counts the request as done at that point. Only a container that stays up finishes the 60 to 90 seconds of work.
- A cold start loads torch, two models, and BM25. It is likely longer than the front end's 30-second intake timeout.

Concurrency inside the one container is enough for a demo: most of a case is waiting on Muse Spark.

## Runbook

Run everything from PowerShell in `~\recourse`, in the venv (`.\.venv\Scripts\Activate.ps1`). If you run a step from Git Bash instead, prefix `modal volume` commands with `MSYS_NO_PATHCONV=1`, or Git Bash rewrites `/text` into a Windows path.

### A. Modal account (about 5 minutes)

1. `pip install "modal>=1.0"`
   Verify: `modal --version` prints a version, 1.0 or later. Modal is not in `pyproject.toml` on purpose. Done on Oct 27 (modal 1.6.3 in the venv).
2. The token. Done on Oct 27 without the CLI: an API token created in the Modal dashboard (Settings, API Tokens) is saved in `.env` as `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, the two names the `modal` package reads from the environment. Load `.env` into the window before any `modal` command (PowerShell: the loop in `scripts/dev-api.ps1`; Git Bash: `set -a; . ./.env; set +a`). `modal token new` is only the fallback if those are missing.
3. `modal app list`
   Expected: a table (empty before the first deploy), which proves the token. Verified Oct 27 together with `modal secret list`. The workspace is `alpau-reis`, so the API URL will be `https://alpau-reis--recourse-api.modal.run`. The credits are on that workspace.

### B. Secret (2 minutes)

4. Check the key is in this window without printing it: `$env:POLICYQA_LLM_API_KEY.Length`
   Expected: a number above 0. If it prints nothing or 0, create the secret in the Modal dashboard instead (Secrets, Create new secret, Custom) with the six names below, and skip step 5.
5. Create the secret. The key comes from the environment, so its value never appears in the command or in your PowerShell history:
   ```powershell
   modal secret create recourse-muse-spark `
     POLICYQA_LLM_BASE_URL=https://api.meta.ai/v1 `
     POLICYQA_LLM_API_KEY=$env:POLICYQA_LLM_API_KEY `
     POLICYQA_LLM_MODEL=muse-spark-1.3 `
     POLICYQA_LLM_INPUT_USD_PER_M=1.25 `
     POLICYQA_LLM_OUTPUT_USD_PER_M=4.25 `
     POLICYQA_LLM_REASONING_EFFORT=low
   ```
   The base URL, model, and prices are the public values from `.env.example`; use whatever your `.env` has if it differs. Leave `POLICYQA_LLM_REASONING_EFFORT` empty (`POLICYQA_LLM_REASONING_EFFORT=`) to send nothing. Add `--force` to replace an existing secret.
   Since Oct 28 the same secret also carries the second opinion (`policyqa/second_opinion.py`), so the deployed API runs it: add `POLICYQA_SECOND_LLM_BASE_URL=$env:POLICYQA_SECOND_LLM_BASE_URL POLICYQA_SECOND_LLM_API_KEY=$env:POLICYQA_SECOND_LLM_API_KEY POLICYQA_SECOND_LLM_MODEL=$env:POLICYQA_SECOND_LLM_MODEL POLICYQA_SECOND_LLM_INPUT_USD_PER_M=$env:POLICYQA_SECOND_LLM_INPUT_USD_PER_M POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M=$env:POLICYQA_SECOND_LLM_OUTPUT_USD_PER_M` to the command. Empty price values fall back to the primary's prices. `deploy/modal_app.py` requires only the three primary names; the rest pass through. Done on Oct 28 from Git Bash with the values read from `.env` into the environment (`set -a; . ./.env; set +a`), never typed.
   Verify: `modal secret list` shows `recourse-muse-spark`.

### C. Data volume (10 to 20 minutes)

6. `modal volume create recourse-data`
   Verify: `modal volume list` shows `recourse-data`.

Then fill it. Option 1 is the recommended one: it ships the exact index the golden-set and denial-case evals ran on, built with your poppler 25.07. Option 2 rebuilds in the cloud with Debian's poppler, whose text layer can differ, and re-downloads PDFs that may have changed since Oct 26.

**Option 1: upload your prepared data (recommended).**

7. `modal volume put recourse-data data/chunks.jsonl /chunks.jsonl`
8. `modal volume put recourse-data data/dense.npy /dense.npy`
9. `modal volume put recourse-data data/dense.json /dense.json`
10. `modal volume put recourse-data data/text /text`
11. `modal volume put recourse-data E:\Downloads\policy-qa-corpus\all /pdfs`
    That is the folder in `RECOURSE_PDF_DIR` in your `.env` on Oct 26 (about 67 MB). It also holds a stray `manifest.csv`, which is harmless. Do not upload `data/cases` (local test cases) or `data/pages` (a cache that rebuilds itself).
    Add `--force` to any of these to overwrite a file already there.
    Done on Oct 28 (steps 6 to 11, about 3 minutes). From Git Bash the local path must be in Windows form (`E:/Downloads/policy-qa-corpus/all`): with `MSYS_NO_PATHCONV=1` set for the remote path, a `/e/...` local path is passed to Modal unconverted and the upload fails with a "does not exist" error. A "'charmap' codec" line after a successful upload is the Windows console failing to print Modal's tick mark, not an error; set `PYTHONIOENCODING=utf-8` to avoid it.

**Option 2: build in the cloud (fallback).**

7. `modal run deploy/modal_app.py::populate`
   Downloads every manifest PDF that is not already on the volume (the same URLs as `corpus/fetch.sh`), then runs ingest, chunk, and embed against the volume. It refuses to overwrite an existing index; `--force` rebuilds. Expected: a JSON report with `fetched`, `fetch_failed`, `still_missing`, and the ingest, chunk, and embed results. The four hhs.gov HIPAA PDFs may land in `fetch_failed` (hhs.gov blocks some non-browser clients); upload those four from your folder with `modal volume put recourse-data E:\Downloads\policy-qa-corpus\all\hipaa-01.pdf /pdfs/hipaa-01.pdf` and so on, then run populate again with `--force`.

**Either way, check before deploying:**

12. `modal run deploy/modal_app.py::inventory`
    Expected with Option 1:
    ```
    "chunks_lines": 4131, "dense_npy": true,
    "dense_meta": {"model": "BAAI/bge-small-en-v1.5", "chunks": 4131, "dims": 384},
    "text_docs": 64, "manifest_docs": 64, "pdfs_usable": 64, "pdfs_missing": [], "cases": 0
    ```
    The first run also builds the image (poppler, CPU torch, the pinned packages, the two models). Allow 5 to 10 minutes; later runs reuse it.

### D. Deploy the API (5 minutes)

13. Set the front-end origin for CORS. You do not know the Vercel domain yet, so use the placeholder now and redeploy in step 20:
    `$env:RECOURSE_CORS_ORIGINS = "http://localhost:3000"`
14. `modal deploy deploy/modal_app.py`
    Expected: the app `recourse-api` is created and the output lists the web endpoint URL, `https://<workspace>--recourse-api.modal.run`. Copy it.
    Done on Oct 28 at about 7:45 pm: the URL carries the region, `https://alpau-reis--recourse-api.us-east.modal.run` (deployed in 2 s after the image built during step 12). Steps 15 to 17 then held: `/health` live on every stage with 64 PDFs (5.7 s on the first request), `/search` returned `fl-04` page 5, the page PNG was 260,281 bytes (the same bytes as the local render), and the highlight for the PDN quote gave the same boxes as the local API to the decimal, so Debian's poppler locates the same text.
15. Health check:
    `curl.exe -s https://<workspace>--recourse-api.modal.run/health`
    (`curl.exe`, not `curl`: in Windows PowerShell `curl` is `Invoke-WebRequest`.) Expected:
    ```json
    {"ok":true,"index_built":true,"dense_built":true,"model":"muse-spark-1.3","intake":"muse-spark-1.3",
     "investigation":"muse-spark-1.3","verdict":"muse-spark-1.3","critic":"muse-spark-1.3","pdfs":64}
    ```
    `"investigation":"fixture"` means the secret is missing or incomplete, or the index is not on the volume. `"pdfs"` below 64 means PDFs are missing (page images for those documents return `no_pdf`).
16. Retrieval check, no model call and no cost:
    `curl.exe -s "https://<workspace>--recourse-api.modal.run/search?q=private%20duty%20nursing%20hours%20per%20day&k=1"`
    Expected: one hit with `doc_id` `fl-04` (the PDN coverage policy), returned in about a second.
17. Page image check: `curl.exe -s -o p5.png "https://<workspace>--recourse-api.modal.run/doc/fl-04/page/5.png"` then open `p5.png`. Expected: page 5 of the PDN policy. This proves poppler and the PDF folder.
18. Logs if anything fails: `modal app logs recourse-api`

### E. Front end (15 minutes)

19. Follow `deploy/vercel.md`: root directory `web`, `NEXT_PUBLIC_API_URL` set to the URL from step 14, `NEXT_PUBLIC_INTAKE_MODE` = `live`. Note the production domain.
20. Redeploy the API with the real origin:
    ```powershell
    $env:RECOURSE_CORS_ORIGINS = "https://<your-project>.vercel.app,http://localhost:3000"
    modal deploy deploy/modal_app.py
    ```
    Verify: `curl.exe -s -i -H "Origin: https://<your-project>.vercel.app" https://<workspace>--recourse-api.modal.run/health` shows `access-control-allow-origin: https://<your-project>.vercel.app`.
    Done on Oct 28 at about 9:50 pm: the Vercel project `recourse` in the Hobby team "Pau Reis' projects" (imported from the dashboard as the single Next.js project under `web/`; Vercel offered the FastAPI app as a second service and it was left out), production domain `https://recourse-murex.vercel.app`, first build 32 s. The API redeployed in 1.6 s with that origin; the preflight for `POST /case/intake` answers `Access-Control-Allow-Origin: https://recourse-murex.vercel.app`. The landing, `/case/c_sample` and `/sample/fl-04-p5.png` answer 200 on the domain.
21. End to end: open the Vercel domain, paste one synthetic sample letter (`cases/letters/`), and watch the case through to `reviewed`. Expected: 50 to 90 seconds, about $0.10 in model credits. Then `modal run deploy/modal_app.py::inventory` shows `"cases": 1`.
    Done against the API alone on Oct 28 at about 7:55 pm, before Vercel, with `curl`-style calls from a script (intake as form text, investigate, poll every 3 s): dc-001 became case `c_2cbfeb`, intake in 4.3 s, `reviewed` at 47.7 s, inconsistent, 6 of 6 findings supported, 4 of 4 letter claims verified, the critic found and fixed 2 issues, the second opinion (Muse Spark Open) agreed in 3.2 s; $0.11 in model credits. So the background thread finishes a case on Modal and the second opinion runs there from the one secret.
    Done from the site at about 10:00 pm with a headless browser (Playwright at 1280 by 800 on `https://recourse-murex.vercel.app/case/new`, the dc-001 text pasted, "Read this letter", "Looks right", "Confirm"): case `c_0f9a1f`, investigating at 1 s after the confirm, deciding at 24 s, drafting at 27 s, reviewing at 33 s, reviewed at 42 s; 6 of 6 findings verified, the second opinion agrees; 29 requests from the page to the Modal URL, 0 console errors, so CORS holds from the real origin.

## Settings you may want to change

| Setting | Where | Default | Change it when |
|---|---|---|---|
| `RECOURSE_CORS_ORIGINS` | shell before `modal deploy` | `https://REPLACE-WITH-YOUR-PROJECT.vercel.app,http://localhost:3000` | always, step 20 |
| `RECOURSE_MODAL_MIN_CONTAINERS` | shell before `modal deploy` | `1` | `0` between demo days to stop paying for the idle container. The first request then waits for a cold start (likely past the 30-second intake timeout), and the container stops after 20 idle minutes. A case keeps it alive because the page polls every few seconds. |
| `cpu`, `memory` | `deploy/modal_app.py`, the `web` function | 2 cores, 4 GiB | `cpu=1.0` halves the CPU bill; reranking gets slower |
| `RECOURSE_CRITIC_ROUNDS` | `RUNTIME_ENV` in `deploy/modal_app.py` | `1` | `0` turns the letter critic off (saves about $0.02 a case) |

Do not raise `max_containers` above 1 without first moving the case store out of process memory.

## Cost (rough)

Modal, the warm container. List prices as I remember them, about $0.0000131 per CPU core per second and $0.00000222 per GiB of memory per second; check modal.com/pricing before trusting them.

| Item | Per day | Oct 31 to Nov 4 (5 days) |
|---|---|---|
| 2 cores, always on | about $2.26 | about $11 |
| 4 GiB, always on | about $0.77 | about $4 |
| Total, warm container | about $3 | about $15 |

The image build, `populate`, and `inventory` add cents. Volume storage (about 90 MB) is negligible. Requests add nothing beyond the reserved container, since a case is mostly waiting on the model.

Model credits: about $0.10 a case with the critic, measured on dc-001 on Oct 26 (DECISIONS.md, 8:40 pm entry; $0.018 of it the critic). A vision check on a page is about $0.006. Fifty demo cases is about $5.

## Things to know

- Redeploying the API restarts the container. A case in progress stops and stays `investigating` forever (the thread is gone; the stored case is not). Do not redeploy during a demo.
- Modal may also restart the container on its own (host maintenance). Cases already saved survive, because the store reloads from `/root/data/cases` at start; one in progress does not.
- Case files and page PNGs are written to the volume while the container runs. Modal commits volume changes in the background and when the container stops.
- `HF_HUB_OFFLINE=1` at run time: the API never calls the Hugging Face Hub. If a model was not baked into the image, startup logs "retriever not warmed" and the first search fails; rebuild the image.
- The ASGI factory warms the retriever (BM25, the dense matrix, both models) before the first request.
- Tests for this folder: `python -m pytest deploy -q` (no network, no Modal credentials needed).

## Not verified (nothing was deployed)

The scaffold was written and tested on Oct 26 without the `modal` package installed and without network calls. What the local test covers: the module imports with no Modal package (`app` is None) and with a stand-in Modal module that runs every definition line; the container paths line up with how `api/main.py` finds `data/`; the baked model names match `policyqa`; every dependency in `pyproject.toml` is pinned; the secret names match `.env.example`; the manifest parses to 64 rows with the same ids and URLs as `corpus/fetch.sh`; the ASGI factory returns the FastAPI app.

Not verified:

- That Modal accepts the arguments as written. They follow the Modal 1.x API (`min_containers`, `max_containers`, `scaledown_window`, `@modal.concurrent`, `@modal.asgi_app(label=...)`, `Image.add_local_dir(..., ignore=...)`, `modal.is_local()`). The first `modal run ...::inventory` is the test.
- That `torch==2.14.1` exists on the PyTorch CPU wheel index for Python 3.12 on Linux, and that the other pins from your Windows venv resolve on Linux.
- That Debian's poppler (older than your 25.07) locates the same quotes on the page. Page highlights use `pdftotext -bbox` on the server. Check one citation's highlight after step 21.
- The cold start time, and that the background thread finishes a case on Modal as it does under uvicorn locally.
- That `modal volume put` uploads a directory recursively as written, and that `populate --force` parses as a flag.
- The API URL format with the `recourse-api` label, the exact CLI output wording, and the cost figures.

"""Supervised fine-tune data for the answer stage, and a small Fireworks REST client.

The dataset: every golden row outside the judge subset becomes one chat example whose system and
user messages are exactly what `policyqa.generate` sends at inference, and whose assistant message
is the gold answer as the JSON the prompt asks for.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from .generate import ABSTAIN_TEXT, QUOTE_THRESHOLD, SYSTEM_PROMPT, build_user_message, format_passages
from .retrieve import Hit
from .textnorm import quote_overlap


def training_rows(golden: list[dict]) -> list[dict]:
    """The rows a model may learn from: every row not in the judge subset, in CSV order."""
    return [r for r in golden if (r.get("judge_subset") or "").strip() != "1"]


def quote_parts(row: dict) -> list[str]:
    """The gold quote, one part per gold document (` || ` separates the parts of a multi row)."""
    return [q.strip() for q in (row.get("gold_quote") or "").split(" || ") if q.strip()]


def _best_passage(quote: str, passages: list[dict], gold: tuple[str, int] | None = None) -> tuple[dict | None, float]:
    """The passage with the highest overlap; on a tie, the one on the gold (document, page), then the first."""
    best, best_key = None, (-1.0, False)
    for p in passages:
        key = (quote_overlap(quote, p["text"]), (p["doc_id"], int(p["page"])) == gold)
        if key > best_key:
            best, best_key = p, key
    return best, max(best_key[0], 0.0)


def _split(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def gold_targets(row: dict) -> list[tuple[str, int, str]]:
    """(document, page, quote part) for each gold document of the row, in order."""
    docs, pages, quotes = _split(row.get("gold_doc_ids")), _split(row.get("gold_pages")), quote_parts(row)
    return [(d, int(p), q) for d, p, q in zip(docs, pages, quotes)]


def pages_index(chunks: list[dict]) -> dict[tuple[str, int], list[dict]]:
    """Chunks grouped by (document, page), in file order."""
    out: dict[tuple[str, int], list[dict]] = {}
    for c in chunks:
        out.setdefault((c["doc_id"], int(c["page"])), []).append(c)
    return out


def gold_chunk(by_page: dict, doc: str, page: int, quote: str) -> dict | None:
    """The chunk on that page of that document with the highest overlap with the quote (first on a tie)."""
    best, best_ov = None, -1.0
    for c in by_page.get((doc, page), []):
        ov = quote_overlap(quote, c["text"])
        if ov > best_ov:
            best, best_ov = c, ov
    return best


def ensure_gold(hits: list[Hit], gold: list[dict], k: int) -> tuple[list[Hit], bool]:
    """Each gold chunk not among the k hits replaces the lowest-ranked hit that is not itself gold."""
    hits = list(hits[:k])
    gold_ids = {c["chunk_id"] for c in gold}
    inserted = False
    for g in gold:
        if any(h.chunk["chunk_id"] == g["chunk_id"] for h in hits):
            continue
        if len(hits) < k:
            hits.append(Hit(g, 0.0, "gold"))
            inserted = True
            continue
        for i in range(len(hits) - 1, -1, -1):
            if hits[i].chunk["chunk_id"] not in gold_ids:
                hits[i] = Hit(g, 0.0, "gold")
                inserted = True
                break
    return hits, inserted


def build_example(row: dict, search, by_page: dict, k: int = 5) -> dict:
    hits = search(row["question"], k)
    inserted = False
    if row["type"] != "none":
        gold = []
        for d, p, q in gold_targets(row):
            # A retrieved chunk of the gold page that already holds the quote part is the gold chunk:
            # nothing is inserted (two overlapping chunks of one page would show that page twice).
            held = next((h.chunk for h in hits[:k] if (h.chunk["doc_id"], int(h.chunk["page"])) == (d, p) and quote_overlap(q, h.chunk["text"]) >= QUOTE_THRESHOLD), None)
            c = held or gold_chunk(by_page, d, p, q)
            if c is not None:
                gold.append(c)
        hits, inserted = ensure_gold(hits, gold, k)
    passages = format_passages(hits)
    if row["type"] == "none":
        answer = {"answer": ABSTAIN_TEXT, "abstain": True, "citations": []}
    else:
        citations = []
        gold_of = {q: (d, p) for d, p, q in gold_targets(row)}
        for q in quote_parts(row):
            p, ov = _best_passage(q, passages, gold_of.get(q))
            if p is None or ov < QUOTE_THRESHOLD:
                return {"id": row["id"], "refused": True, "best_overlap": round(ov, 3), "quote": q}
            citations.append({"passage": p["tag"], "quote": q})
        answer = {"answer": row["answer"], "abstain": False, "citations": citations}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(row["question"], passages)},
        {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
    ]
    return {"id": row["id"], "messages": messages, "passages": passages, "inserted": inserted}


TOKEN_ESTIMATE = "estimate: words x 1.3 (whitespace-split words), not a tokenizer count"
ROLES = ("system", "user", "assistant")


def tokens_est(text: str) -> int:
    return round(len(text.split()) * 1.3)


def example_sizes(ex: dict) -> dict:
    chars = {m["role"]: len(m["content"]) for m in ex["messages"]}
    toks = {m["role"]: tokens_est(m["content"]) for m in ex["messages"]}
    toks["total"] = sum(toks[r] for r in ROLES)
    return {"id": ex["id"], "chars": chars, "tokens_est": toks}


def build_dataset(golden: list[dict], search, chunks: list[dict], k: int = 5) -> dict:
    by_page = pages_index(chunks)
    examples, refused = [], []
    for row in training_rows(golden):
        ex = build_example(row, search, by_page, k)
        if ex.get("refused"):
            refused.append({"id": ex["id"], "best_overlap": ex["best_overlap"], "quote": ex["quote"]})
        else:
            examples.append(ex)
    inserted_ids = [e["id"] for e in examples if e["inserted"]]
    sizes = [example_sizes(e) for e in examples]
    totals = {
        "chars": sum(sum(s["chars"].values()) for s in sizes),
        "tokens_est": sum(s["tokens_est"]["total"] for s in sizes),
        "max_example_tokens_est": max((s["tokens_est"]["total"] for s in sizes), default=0),
    }
    manifest = {"ids": [e["id"] for e in examples], "inserted": len(inserted_ids), "inserted_ids": inserted_ids, "refused": refused, "token_estimate": TOKEN_ESTIMATE, "totals": totals, "sizes": sizes}
    return {"examples": examples, "manifest": manifest}


# Fireworks cuts training examples at 32,768 tokens; the estimate stays well under that.
MAX_EXAMPLE_TOKENS_EST = 16000


class DatasetRefused(RuntimeError):
    """The dataset was not written (an example over the token ceiling, or too few rows)."""


def write_dataset(result: dict, jsonl_path: Path, manifest_path: Path, config: dict, max_tokens: int = MAX_EXAMPLE_TOKENS_EST) -> dict:
    """Write the JSONL (one {"messages": [...]} per line) and its manifest, UTF-8, LF, no BOM.

    Nothing is written when any example's token estimate exceeds `max_tokens`."""
    over = [s for s in result["manifest"]["sizes"] if s["tokens_est"]["total"] > max_tokens]
    if over:
        listed = ", ".join(f"{s['id']} ({s['tokens_est']['total']})" for s in over)
        raise DatasetRefused(f"not written: {len(over)} example(s) over the {max_tokens}-token estimate ceiling: {listed}")
    lines = [json.dumps({"messages": e["messages"]}, ensure_ascii=False) for e in result["examples"]]
    manifest = {"config": config, **result["manifest"]}
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    manifest_path.write_bytes((json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return manifest


def index_fingerprint(chunks_path: Path) -> dict:
    """The chunks file's name, size and md5, so a later run can tell whether the index changed."""
    data = Path(chunks_path).read_bytes()
    return {"file": Path(chunks_path).name, "bytes": len(data), "md5": hashlib.md5(data).hexdigest()}


def counts(manifest: dict) -> dict:
    return {
        "written": len(manifest["ids"]),
        "refused": len(manifest["refused"]),
        "inserted": manifest["inserted"],
        "tokens_est_total": manifest["totals"]["tokens_est"],
        "max_example_tokens_est": manifest["totals"]["max_example_tokens_est"],
    }


# ---- Fireworks REST client ------------------------------------------------------------
#
# The key is read from FIREWORKS_API_KEY and only ever placed in the Authorization header; it is
# never printed, logged or written. Errors carry the status code and the response text, never the
# request headers.

API_BASE = "https://api.fireworks.ai/v1"
BASE_MODEL = "accounts/fireworks/models/muse-glimmer-30b"
ACCELERATORS = {"H100": "NVIDIA_H100_80GB", "H200": "NVIDIA_H200_141GB", "A100": "NVIDIA_A100_80GB", "B200": "NVIDIA_B200_180GB"}
DEPLOY_DONE = {"READY"}
DEPLOY_FAILED = {"FAILED", "DELETED", "DELETING"}
JOB_DONE = {"JOB_STATE_COMPLETED"}
JOB_FAILED = {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED", "JOB_STATE_EARLY_STOPPED", "JOB_STATE_DELETED"}


class FireworksError(RuntimeError):
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text
        super().__init__(f"HTTP {status_code}: {text[:2000]}")


class FireworksClient:
    def __init__(self, api_key: str | None = None, account_id: str | None = None, base_url: str = API_BASE, transport=None, timeout: float = 120.0):
        self._key = api_key if api_key is not None else os.environ.get("FIREWORKS_API_KEY", "")
        self.account_id = account_id if account_id is not None else os.environ.get("FIREWORKS_ACCOUNT_ID", "")
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"FireworksClient(account_id={self.account_id!r}, base_url={self.base_url!r})"

    def _request(self, method: str, path: str, **kw) -> dict:
        import httpx

        with httpx.Client(timeout=self.timeout, transport=self.transport) as c:
            r = c.request(method, f"{self.base_url}{path}", headers={"Authorization": f"Bearer {self._key}"}, **kw)
        if r.status_code >= 400:
            raise FireworksError(r.status_code, r.text)
        return r.json() if r.content else {}

    def _acct(self) -> str:
        if not self.account_id:
            raise FireworksError(0, "FIREWORKS_ACCOUNT_ID is not set")
        return f"/accounts/{self.account_id}"

    def list_accounts(self) -> dict:
        """GET /v1/accounts: the accounts this key can see, each `name` like accounts/my-account.

        https://docs.fireworks.ai/api-reference/list-accounts (whether a user key sees only its own
        account is not stated there; not yet run live)."""
        return self._request("GET", "/accounts")

    def create_dataset(self, dataset_id: str, example_count: int) -> dict:
        """POST /v1/accounts/{account_id}/datasets with {"datasetId", "dataset": {"userUploaded": {}, "exampleCount"}}.

        https://docs.fireworks.ai/api-reference/create-dataset and
        https://docs.fireworks.ai/fine-tuning/fine-tuning-models ("the exampleCount parameter needs to be provided by the client")."""
        body = {"datasetId": dataset_id, "dataset": {"userUploaded": {}, "exampleCount": str(example_count)}}
        return self._request("POST", f"{self._acct()}/datasets", json=body)

    def upload_dataset_file(self, dataset_id: str, path: Path) -> dict:
        """POST /v1/accounts/{account_id}/datasets/{dataset_id}:upload, multipart form field "file" (up to 150 MB).

        https://docs.fireworks.ai/api-reference/upload-dataset-files"""
        data = Path(path).read_bytes()
        return self._request("POST", f"{self._acct()}/datasets/{dataset_id}:upload", files={"file": (Path(path).name, data, "application/jsonl")})

    def get_dataset(self, dataset_id: str) -> dict:
        """GET /v1/accounts/{account_id}/datasets/{dataset_id}; state is UPLOADING or READY.

        https://docs.fireworks.ai/api-reference/get-dataset"""
        return self._request("GET", f"{self._acct()}/datasets/{dataset_id}")


    def _full(self, kind: str, ident: str) -> str:
        """`accounts/<account>/<kind>/<id>` for a bare id; a full resource name passes through."""
        return ident if ident.startswith("accounts/") else f"accounts/{self.account_id}/{kind}/{ident}"

    def create_job(self, dataset: str, output_model: str, base_model: str = BASE_MODEL, epochs: int = 3, learning_rate: float = 0.0001, lora_rank: int = 16, job_id: str | None = None) -> dict:
        """POST /v1/accounts/{account_id}/supervisedFineTuningJobs, optional query supervisedFineTuningJobId.

        Body fields as documented: dataset, baseModel, outputModel, epochs, learningRate, loraRank.
        https://docs.fireworks.ai/api-reference/create-supervised-fine-tuning-job"""
        body = {
            "dataset": self._full("datasets", dataset),
            "baseModel": base_model,
            "outputModel": self._full("models", output_model),
            "epochs": epochs,
            "learningRate": learning_rate,
            "loraRank": lora_rank,
        }
        params = {"supervisedFineTuningJobId": job_id} if job_id else None
        return self._request("POST", f"{self._acct()}/supervisedFineTuningJobs", json=body, params=params)



    def get_job(self, job: str) -> dict:
        """GET /v1/accounts/{account_id}/supervisedFineTuningJobs/{supervised_fine_tuning_job_id}.

        https://docs.fireworks.ai/api-reference/get-supervised-fine-tuning-job"""
        return self._request("GET", f"{self._acct()}/supervisedFineTuningJobs/{job.rstrip('/').split('/')[-1]}")


    def create_deployment(self, model: str, deployment_id: str | None = None, shape: str = "default", gpu: str | None = None) -> dict:
        """POST /v1/accounts/{account_id}/deployments?deploymentId=<id>, body {"baseModel", "deploymentShape",
        "minReplicaCount", "maxReplicaCount"} (plus "acceleratorType" only when `gpu` is given).

        One replica, never scaling up or to zero while it exists (minReplicaCount 1, maxReplicaCount 1);
        `deploymentShape: "default"` lets Fireworks pick a validated shape for the model. A fine-tuned
        LoRA deployed this way is merged live into its base (one adapter per deployment).
        https://docs.fireworks.ai/api-reference/create-deployment,
        https://docs.fireworks.ai/guides/ondemand-deployments (the "default" shape),
        https://docs.fireworks.ai/fine-tuning/deploying-loras (live merge)."""
        body = {"baseModel": model, "deploymentShape": shape, "minReplicaCount": 1, "maxReplicaCount": 1}
        if gpu:
            body["acceleratorType"] = ACCELERATORS.get(gpu.upper(), gpu)
        params = {"deploymentId": deployment_id} if deployment_id else None
        return self._request("POST", f"{self._acct()}/deployments", json=body, params=params)


    def get_deployment(self, deployment: str) -> dict:
        """GET /v1/accounts/{account_id}/deployments/{deployment_id}; state CREATING, READY, UPDATING,
        DELETING, DELETED or FAILED.

        https://docs.fireworks.ai/api-reference/get-deployment"""
        return self._request("GET", f"{self._acct()}/deployments/{deployment.rstrip('/').split('/')[-1]}")


    def delete_deployment(self, deployment: str) -> dict:
        """DELETE /v1/accounts/{account_id}/deployments/{deployment_id} (no hard or ignoreChecks flag).

        https://docs.fireworks.ai/api-reference/delete-deployment"""
        return self._request("DELETE", f"{self._acct()}/deployments/{deployment.rstrip('/').split('/')[-1]}")


def deployment_summary(d: dict) -> dict:
    """State, and the model string for chat completions against this deployment.

    `chat_model` is the deployment's resource name, the form the on-demand guide's curl example
    sends as "model" (https://docs.fireworks.ai/guides/ondemand-deployments). The alternative is
    `<model>#<deployment>`, the form https://docs.fireworks.ai/fine-tuning/deploying-loras gives for an
    adapter on a multi-LoRA deployment; for a live-merged LoRA that page queries the fine-tuned model
    id itself."""
    name = d.get("name") or ""
    base = d.get("baseModel") or ""
    return {
        "name": name,
        "state": d.get("state"),
        "baseModel": base,
        "chat_model": name,
        "chat_model_alternatives": [f"{base}#{name}"] if base and name else [],
        "message": (d.get("status") or {}).get("message") or None,
    }


def job_summary(j: dict) -> dict:
    return {"name": j.get("name"), "state": j.get("state"), "percent": (j.get("jobProgress") or {}).get("percent"), "outputModel": j.get("outputModel"), "message": (j.get("status") or {}).get("message") or None}


_sleep = time.sleep
_clock = time.monotonic


def poll(get, done: set, failed: set, poll_s: float, timeout_s: float, emit, summary) -> tuple[int, dict]:
    """Call `get` every `poll_s` seconds, emitting a line on each state change, until a state in
    `done` (exit 0), in `failed` (exit 1, with the reason), or `timeout_s` passes (exit 1)."""
    start = _clock()
    last = None
    while True:
        s = summary(get())
        if s["state"] != last:
            emit(s)
            last = s["state"]
        if s["state"] in done:
            return 0, s
        if s["state"] in failed:
            return 1, s
        if _clock() - start + poll_s > timeout_s:
            emit({"error": f"timed out after {timeout_s:g} s", "state": s["state"]})
            return 1, s
        _sleep(poll_s)


def make_client() -> FireworksClient:
    return FireworksClient()


def _count_lines(path: Path) -> int:
    return sum(1 for line in Path(path).read_bytes().split(b"\n") if line.strip())


def job_action(args, client: FireworksClient, emit=None) -> int:
    """Run one `finetune-job` action; every result is one JSON object per line on stdout. Returns the exit code."""
    emit = emit or (lambda obj: print(json.dumps(obj), flush=True))
    try:
        if args.action == "upload":
            client.create_dataset(args.dataset_id, _count_lines(args.jsonl))
            client.upload_dataset_file(args.dataset_id, args.jsonl)
            d = client.get_dataset(args.dataset_id)
            emit({"name": d.get("name"), "state": d.get("state"), "exampleCount": d.get("exampleCount")})
            return 0
        if args.action == "whoami":
            accts = client.list_accounts().get("accounts") or []
            emit({"account_ids": [a.get("name", "").split("/")[-1] for a in accts]})
            return 0
        if args.action == "model":
            s = job_summary(client.get_job(args.job))
            if s["state"] not in JOB_DONE:
                emit({"error": "job not completed", "state": s["state"]})
                return 1
            emit({"model": client._full("models", s["outputModel"]), "state": s["state"]})
            return 0
        if args.action == "deploy":
            d = client.create_deployment(args.model, deployment_id=args.deployment_id, shape=args.shape, gpu=args.gpu)
            emit({"name": d.get("name"), "state": d.get("state")})
            return 0
        if args.action == "deploy-status":
            emit(deployment_summary(client.get_deployment(args.deployment)))
            return 0
        if args.action == "wait-deploy":
            code, _ = poll(lambda: client.get_deployment(args.deployment), DEPLOY_DONE, DEPLOY_FAILED, args.poll, args.timeout, emit, deployment_summary)
            return code
        if args.action == "undeploy":
            try:
                client.delete_deployment(args.deployment)
            except FireworksError as e:
                if e.status_code != 404:
                    raise
                emit({"deployment": args.deployment, "deleted": False, "status_code": 404, "state": "DELETED", "note": f"already gone: {e.text[:300]}"})
                return 0
            try:
                state = client.get_deployment(args.deployment).get("state")
            except FireworksError as e:
                if e.status_code != 404:
                    raise
                state = "DELETED"
            emit({"deployment": args.deployment, "deleted": True, "state": state})
            return 0
        if args.action == "status":
            emit(job_summary(client.get_job(args.job)))
            return 0
        if args.action == "wait":
            code, _ = poll(lambda: client.get_job(args.job), JOB_DONE, JOB_FAILED, args.poll, args.timeout, emit, job_summary)
            return code
        if args.action == "create":
            j = client.create_job(args.dataset, args.output_model, base_model=args.base_model or BASE_MODEL, epochs=args.epochs, learning_rate=args.learning_rate, lora_rank=args.lora_rank, job_id=args.job_id)
            emit({"name": j.get("name"), "state": j.get("state")})
            return 0
    except FireworksError as e:
        emit({"error": str(e), "status_code": e.status_code})
        return 1
    emit({"error": f"unknown action {args.action}"})
    return 2

"""Fine-tune dataset builder and Fireworks job client (policyqa/finetune.py).

No network and no model: the dataset tests use a fake retriever (a function of question and k)
or a real BM25-only Index over a tiny chunks file; the REST client runs on httpx.MockTransport.
"""
import json

from policyqa import finetune as ft
from policyqa.generate import ABSTAIN_TEXT, QUOTE_THRESHOLD, SYSTEM_PROMPT, build_user_message, format_passages
from policyqa.retrieve import Hit

GOLD_A = "Prior authorization is required for every home health visit after the first thirty days of care."
GOLD_M1 = "Florida Medicaid covers up to four intermittent home health visits per day for recipients under 21."
GOLD_M2 = "Medicare covers part-time or intermittent skilled nursing care when a physician certifies the need."

CHUNKS = [
    {"chunk_id": "fl-01:p008:0", "doc_id": "fl-01", "page": 8, "title": "Home Health Policy", "jurisdiction": "Florida", "text": "Section 4.1 Home health services. " + GOLD_A + " Requests are made through the portal."},
    {"chunk_id": "fl-01:p008:1", "doc_id": "fl-01", "page": 8, "title": "Home Health Policy", "jurisdiction": "Florida", "text": "Requests are made through the portal. The portal opens at eight in the morning."},
    {"chunk_id": "fl-03:p005:0", "doc_id": "fl-03", "page": 5, "title": "Visits", "jurisdiction": "Florida", "text": "Visit limits. " + GOLD_M1 + " Visits must be medically necessary."},
    {"chunk_id": "fed-24:p006:0", "doc_id": "fed-24", "page": 6, "title": "Medicare Home Health", "jurisdiction": "Federal", "text": "Coverage. " + GOLD_M2},
    {"chunk_id": "fl-09:p001:0", "doc_id": "fl-09", "page": 1, "title": "Dental", "jurisdiction": "Florida", "text": "Dental services for adults are limited to emergency extractions."},
    {"chunk_id": "fl-09:p002:0", "doc_id": "fl-09", "page": 2, "title": "Dental", "jurisdiction": "Florida", "text": "Dentures are covered once every five years."},
    {"chunk_id": "fl-09:p003:0", "doc_id": "fl-09", "page": 3, "title": "Dental", "jurisdiction": "Florida", "text": "Orthodontic services require a prior authorization."},
    {"chunk_id": "fl-09:p004:0", "doc_id": "fl-09", "page": 4, "title": "Dental", "jurisdiction": "Florida", "text": "Fluoride varnish is covered for children."},
    {"chunk_id": "fl-09:p005:0", "doc_id": "fl-09", "page": 5, "title": "Dental", "jurisdiction": "Florida", "text": "Sealants are covered for permanent molars."},
]
BY_ID = {c["chunk_id"]: c for c in CHUNKS}


def _row(id, type="fact", judge="0", docs="fl-01", pages="8", quote=GOLD_A, answer="Yes, after the first thirty days."):
    return {"id": id, "question": f"Question {id}?", "type": type, "answer": answer, "gold_doc_ids": docs, "gold_pages": pages, "gold_quote": quote, "judge_subset": judge}


def fixed_search(chunk_ids):
    """A fake retriever: the same ranked list for every question, cut at k."""

    def search(question, k):
        return [Hit(BY_ID[i], 1.0 / (n + 1), "hybrid") for n, i in enumerate(chunk_ids)][:k]

    return search


GOLD_FIRST = fixed_search(["fl-01:p008:0", "fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0", "fl-09:p005:0"])


# ---- F1: rows -------------------------------------------------------------------


def test_judge_subset_rows_never_reach_the_training_file():
    golden = [_row("gs-001", judge="1"), _row("gs-002"), _row("gs-003", judge="1"), _row("gs-004")]
    res = ft.build_dataset(golden, GOLD_FIRST, CHUNKS, k=5)
    assert [e["id"] for e in res["examples"]] == ["gs-002", "gs-004"]
    assert res["manifest"]["ids"] == ["gs-002", "gs-004"]


# ---- F3: messages ---------------------------------------------------------------


def test_messages_are_the_inference_prompt_and_the_gold_answer_as_json():
    row = _row("gs-002")
    res = ft.build_dataset([row], GOLD_FIRST, CHUNKS, k=5)
    msgs = res["examples"][0]["messages"]
    passages = format_passages(GOLD_FIRST(row["question"], 5))
    assert [m["role"] for m in msgs] == ["system", "user", "assistant"]
    assert msgs[0]["content"] == SYSTEM_PROMPT
    assert msgs[1]["content"] == build_user_message(row["question"], passages)
    want = {"answer": row["answer"], "abstain": False, "citations": [{"passage": "P1", "quote": GOLD_A}]}
    assert msgs[2]["content"] == json.dumps(want, ensure_ascii=False)
    assert list(json.loads(msgs[2]["content"])) == ["answer", "abstain", "citations"]


def test_none_row_teaches_the_abstention_on_the_passages_as_retrieved():
    row = _row("gs-005", type="none", docs="", pages="", quote="", answer="The corpus does not say.")
    search = fixed_search(["fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0", "fl-09:p005:0"])
    res = ft.build_dataset([row], search, CHUNKS, k=5)
    msgs = res["examples"][0]["messages"]
    assert msgs[1]["content"] == build_user_message(row["question"], format_passages(search(row["question"], 5)))
    assert msgs[2]["content"] == json.dumps({"answer": ABSTAIN_TEXT, "abstain": True, "citations": []}, ensure_ascii=False)


# ---- F2: the gold evidence is guaranteed among the passages ---------------------

NO_GOLD = fixed_search(["fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0", "fl-09:p005:0"])


def _chunk_ids(example):
    return [p["chunk_id"] for p in example["passages"]]


def test_missing_gold_chunk_replaces_the_lowest_ranked_hit_and_is_cited():
    row = _row("gs-002")
    res = ft.build_dataset([row], NO_GOLD, CHUNKS, k=5)
    ex = res["examples"][0]
    # the best chunk on the gold page (not the other chunk of fl-01 p8) takes the place of the last hit
    assert _chunk_ids(ex) == ["fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0", "fl-01:p008:0"]
    hits = [Hit(BY_ID[i], 0.0, "hybrid") for i in _chunk_ids(ex)]
    assert ex["messages"][1]["content"] == build_user_message(row["question"], format_passages(hits))
    assert json.loads(ex["messages"][2]["content"])["citations"] == [{"passage": "P5", "quote": GOLD_A}]
    assert res["manifest"]["inserted"] == 1 and res["manifest"]["inserted_ids"] == ["gs-002"]


def test_gold_chunk_already_retrieved_is_not_inserted():
    res = ft.build_dataset([_row("gs-002")], GOLD_FIRST, CHUNKS, k=5)
    assert _chunk_ids(res["examples"][0])[0] == "fl-01:p008:0"
    assert res["manifest"]["inserted"] == 0 and res["manifest"]["inserted_ids"] == []


def test_multi_row_inserts_the_missing_part_without_displacing_the_retrieved_gold_chunk():
    row = _row("gs-006", type="multi", docs="fl-03;fed-24", pages="5;6", quote=GOLD_M1 + " || " + GOLD_M2, answer="Four a day in Florida; Medicare covers part-time care.")
    search = fixed_search(["fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0", "fed-24:p006:0"])
    res = ft.build_dataset([row], search, CHUNKS, k=5)
    ex = res["examples"][0]
    assert _chunk_ids(ex) == ["fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-03:p005:0", "fed-24:p006:0"]
    cites = json.loads(ex["messages"][2]["content"])["citations"]
    assert cites == [{"passage": "P4", "quote": GOLD_M1}, {"passage": "P5", "quote": GOLD_M2}]
    assert res["manifest"]["inserted_ids"] == ["gs-006"]


# ---- F4: every citation passes the product's verbatim check, or the row is refused --


def test_row_whose_quote_is_on_no_passage_is_refused_with_its_best_overlap():
    bad = _row("gs-007", quote="Prior authorization is required for every dental visit after the first thirty days of care.")
    res = ft.build_dataset([_row("gs-002"), bad], NO_GOLD, CHUNKS, k=5)
    assert [e["id"] for e in res["examples"]] == ["gs-002"]
    refused = res["manifest"]["refused"]
    assert [r["id"] for r in refused] == ["gs-007"]
    assert 0 < refused[0]["best_overlap"] < QUOTE_THRESHOLD
    assert res["manifest"]["ids"] == ["gs-002"]
    for ex in res["examples"]:
        by_tag = {p["tag"]: p["text"] for p in ex["passages"]}
        for c in json.loads(ex["messages"][2]["content"])["citations"]:
            assert ft.quote_overlap(c["quote"], by_tag[c["passage"]]) >= QUOTE_THRESHOLD


# ---- F5: sizes ------------------------------------------------------------------


def test_manifest_records_characters_and_estimated_tokens_per_message_and_in_total():
    res = ft.build_dataset([_row("gs-002"), _row("gs-004")], GOLD_FIRST, CHUNKS, k=5)
    m = res["manifest"]
    assert "estimate" in m["token_estimate"] and "1.3" in m["token_estimate"]
    first = m["sizes"][0]
    msgs = res["examples"][0]["messages"]
    assert first["id"] == "gs-002"
    for role, msg in zip(("system", "user", "assistant"), msgs):
        assert first["chars"][role] == len(msg["content"])
        assert first["tokens_est"][role] == round(len(msg["content"].split()) * 1.3)
    assert first["tokens_est"]["total"] == sum(first["tokens_est"][r] for r in ("system", "user", "assistant"))
    assert m["totals"]["tokens_est"] == sum(s["tokens_est"]["total"] for s in m["sizes"])
    assert m["totals"]["chars"] == sum(sum(s["chars"].values()) for s in m["sizes"])
    assert m["totals"]["max_example_tokens_est"] == max(s["tokens_est"]["total"] for s in m["sizes"])


# ---- F7 and F5: writing ---------------------------------------------------------


def test_written_file_is_one_messages_object_per_line_utf8_with_lf_and_no_bom(tmp_path):
    golden = [_row("gs-002", answer="Sí, después de treinta días • siempre."), _row("gs-005", type="none", docs="", pages="", quote="")]
    res = ft.build_dataset(golden, GOLD_FIRST, CHUNKS, k=5)
    out, man = tmp_path / "train.jsonl", tmp_path / "train.manifest.json"
    ft.write_dataset(res, out, man, config={"k": 5})
    raw = out.read_bytes()
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\n")
    lines = raw.decode("utf-8").split("\n")[:-1]
    assert len(lines) == 2
    objs = [json.loads(line) for line in lines]
    assert all(list(o) == ["messages"] for o in objs)
    assert objs[0]["messages"] == res["examples"][0]["messages"]
    assert "después" in lines[0]
    m = json.loads(man.read_text(encoding="utf-8"))
    assert m["ids"] == ["gs-002", "gs-005"] and m["config"] == {"k": 5} and b"\r" not in man.read_bytes()


def test_an_example_over_the_token_ceiling_stops_the_write_and_says_which(tmp_path):
    import pytest

    assert ft.MAX_EXAMPLE_TOKENS_EST == 16000
    res = ft.build_dataset([_row("gs-002")], GOLD_FIRST, CHUNKS, k=5)
    out, man = tmp_path / "train.jsonl", tmp_path / "train.manifest.json"
    with pytest.raises(ft.DatasetRefused, match="gs-002"):
        ft.write_dataset(res, out, man, config={}, max_tokens=res["manifest"]["totals"]["max_example_tokens_est"] - 1)
    assert not out.exists() and not man.exists()
    ft.write_dataset(res, out, man, config={}, max_tokens=res["manifest"]["totals"]["max_example_tokens_est"])
    assert out.exists()


# ---- F6 and the finetune-dataset command, on a real BM25 index over a tiny chunks file ----


def _tiny_index(tmp_path):
    import csv

    chunks = tmp_path / "chunks.jsonl"
    chunks.write_bytes(("\n".join(json.dumps(c) for c in CHUNKS) + "\n").encode("utf-8"))
    golden = tmp_path / "golden.csv"
    rows = [_row("gs-001", judge="1"), _row("gs-002"), _row("gs-006", type="multi", docs="fl-03;fed-24", pages="5;6", quote=GOLD_M1 + " || " + GOLD_M2, answer="Four; part-time."), _row("gs-005", type="none", docs="", pages="", quote="")]
    with golden.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return chunks, golden


def _dataset_argv(tmp_path, chunks, golden, out_dir, *extra):
    return ["finetune-dataset", "--chunks", str(chunks), "--dense", str(tmp_path / "no-dense.npy"), "--mode", "bm25", "--no-rerank", "--golden", str(golden), "--out-dir", str(out_dir), "--date", "2026-10-29", *extra]


def test_two_runs_on_the_same_index_write_identical_bytes_and_fingerprint_the_index(tmp_path, capsys):
    import hashlib

    from policyqa.cli import main

    chunks, golden = _tiny_index(tmp_path)
    main(_dataset_argv(tmp_path, chunks, golden, tmp_path / "a", "--min-rows", "1"))
    main(_dataset_argv(tmp_path, chunks, golden, tmp_path / "b", "--min-rows", "1"))
    a, b = tmp_path / "a" / "train-2026-10-29.jsonl", tmp_path / "b" / "train-2026-10-29.jsonl"
    assert a.read_bytes() == b.read_bytes() and len(a.read_bytes().splitlines()) == 3
    assert (tmp_path / "a" / "train-2026-10-29.manifest.json").read_bytes() == (tmp_path / "b" / "train-2026-10-29.manifest.json").read_bytes()
    cfg = json.loads((tmp_path / "a" / "train-2026-10-29.manifest.json").read_text(encoding="utf-8"))["config"]
    assert cfg["retriever"] == {"mode": "bm25", "rerank": False, "rerank_model": None, "candidates": 20, "k": 5}
    assert cfg["chunks"] == {"file": "chunks.jsonl", "bytes": chunks.stat().st_size, "md5": hashlib.md5(chunks.read_bytes()).hexdigest()}
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["written"] == 3 and printed["refused"] == 0 and "inserted" in printed and printed["tokens_est_total"] > 0


def test_fewer_rows_than_the_floor_exits_non_zero_after_printing_the_counts(tmp_path, capsys):
    import pytest

    from policyqa.cli import main

    chunks, golden = _tiny_index(tmp_path)
    with pytest.raises(SystemExit) as e:
        main(_dataset_argv(tmp_path, chunks, golden, tmp_path / "out"))
    assert e.value.code == 1
    lines = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert lines[0]["written"] == 3 and "fewer than 100" in lines[-1]["error"]


# ---- F8 to F11: the Fireworks client, on httpx.MockTransport only ------------------

DUMMY_KEY = "fw-test-dummy-key-not-real-0123456789"


class FakeFireworks:
    """Records every request; `routes` maps (method, path) to a response or a list of responses served in turn."""

    def __init__(self, routes):
        self.routes = {k: (list(v) if isinstance(v, list) else v) for k, v in routes.items()}
        self.requests = []

    def handler(self, request):
        import httpx

        self.requests.append(request)
        key = (request.method, request.url.path)
        if key not in self.routes:
            return httpx.Response(404, json={"error": {"message": f"no route {key}"}})
        r = self.routes[key]
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        status, body = r
        return httpx.Response(status, json=body) if not isinstance(body, str) else httpx.Response(status, text=body)

    def client(self):
        import httpx

        return ft.FireworksClient(api_key=DUMMY_KEY, account_id="acct-1", transport=httpx.MockTransport(self.handler))


def _run_job(monkeypatch, capsys, fake, *argv):
    import pytest

    from policyqa.cli import main

    monkeypatch.setattr(ft, "make_client", lambda: fake.client())
    with pytest.raises(SystemExit) as e:
        main(["finetune-job", *argv])
    out = capsys.readouterr().out
    assert DUMMY_KEY not in out
    return e.value.code, [json.loads(line) for line in out.strip().splitlines()]


def test_upload_creates_the_dataset_record_then_sends_the_file_bytes_once(tmp_path, monkeypatch, capsys):
    data = tmp_path / "train.jsonl"
    data.write_bytes(b'{"messages": [1]}\n{"messages": [2]}\n{"messages": [3]}\n')
    fake = FakeFireworks({
        ("POST", "/v1/accounts/acct-1/datasets"): (200, {"name": "accounts/acct-1/datasets/recourse-train", "state": "UPLOADING"}),
        ("POST", "/v1/accounts/acct-1/datasets/recourse-train:upload"): (200, {"id": "recourse-train", "bytes": 54}),
        ("GET", "/v1/accounts/acct-1/datasets/recourse-train"): (200, {"name": "accounts/acct-1/datasets/recourse-train", "state": "READY", "exampleCount": "3"}),
    })
    code, out = _run_job(monkeypatch, capsys, fake, "upload", str(data), "--dataset-id", "recourse-train")
    assert code == 0
    assert [(r.method, r.url.path) for r in fake.requests] == [
        ("POST", "/v1/accounts/acct-1/datasets"),
        ("POST", "/v1/accounts/acct-1/datasets/recourse-train:upload"),
        ("GET", "/v1/accounts/acct-1/datasets/recourse-train"),
    ]
    assert json.loads(fake.requests[0].content) == {"datasetId": "recourse-train", "dataset": {"userUploaded": {}, "exampleCount": "3"}}
    assert sum(r.content.count(data.read_bytes()) for r in fake.requests) == 1
    assert b'name="file"' in fake.requests[1].content and fake.requests[1].headers["content-type"].startswith("multipart/form-data")
    assert all(r.headers["authorization"] == f"Bearer {DUMMY_KEY}" for r in fake.requests)
    assert out[-1]["state"] == "READY" and out[-1]["name"] == "accounts/acct-1/datasets/recourse-train"


def test_create_sends_the_documented_body_with_the_defaults(monkeypatch, capsys):
    fake = FakeFireworks({("POST", "/v1/accounts/acct-1/supervisedFineTuningJobs"): (200, {"name": "accounts/acct-1/supervisedFineTuningJobs/job-9", "state": "JOB_STATE_CREATING"})})
    code, out = _run_job(monkeypatch, capsys, fake, "create", "--dataset", "recourse-train", "--output-model", "recourse-glimmer-ft")
    assert code == 0
    assert json.loads(fake.requests[0].content) == {
        "dataset": "accounts/acct-1/datasets/recourse-train",
        "baseModel": "accounts/fireworks/models/muse-glimmer-30b",
        "outputModel": "accounts/acct-1/models/recourse-glimmer-ft",
        "epochs": 3,
        "learningRate": 0.0001,
        "loraRank": 16,
    }
    assert "supervisedFineTuningJobId" not in str(fake.requests[0].url)
    assert out[-1] == {"name": "accounts/acct-1/supervisedFineTuningJobs/job-9", "state": "JOB_STATE_CREATING"}


JOB_PATH = "/v1/accounts/acct-1/supervisedFineTuningJobs/job-9"


def _job(state, percent=0, message=""):
    return (200, {"name": "accounts/acct-1/supervisedFineTuningJobs/job-9", "state": state, "jobProgress": {"percent": percent}, "status": {"code": "OK" if not message else "INTERNAL", "message": message}, "outputModel": "accounts/acct-1/models/recourse-glimmer-ft"})


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def sleep(self, s):
        assert len(self.sleeps) < 1000, "runaway polling loop"
        self.sleeps.append(s)
        self.t += s

    def now(self):
        return self.t


def test_wait_polls_through_running_to_completed_printing_each_change(monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(ft, "_sleep", clock.sleep)
    monkeypatch.setattr(ft, "_clock", clock.now)
    fake = FakeFireworks({("GET", JOB_PATH): [_job("JOB_STATE_CREATING"), _job("JOB_STATE_RUNNING", 10), _job("JOB_STATE_RUNNING", 10), _job("JOB_STATE_COMPLETED", 100)]})
    code, out = _run_job(monkeypatch, capsys, fake, "wait", "accounts/acct-1/supervisedFineTuningJobs/job-9", "--poll", "30")
    assert code == 0
    assert [o["state"] for o in out] == ["JOB_STATE_CREATING", "JOB_STATE_RUNNING", "JOB_STATE_COMPLETED"]
    assert out[-1]["percent"] == 100 and len(fake.requests) == 4 and clock.sleeps == [30, 30, 30]


def test_wait_exits_non_zero_on_failure_and_prints_the_reason(monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(ft, "_sleep", clock.sleep)
    monkeypatch.setattr(ft, "_clock", clock.now)
    fake = FakeFireworks({("GET", JOB_PATH): [_job("JOB_STATE_RUNNING", 40), _job("JOB_STATE_FAILED", 40, "dataset row 12: invalid role")]})
    code, out = _run_job(monkeypatch, capsys, fake, "wait", "job-9", "--poll", "5")
    assert code == 1
    assert out[-1]["state"] == "JOB_STATE_FAILED" and out[-1]["message"] == "dataset row 12: invalid role"


def test_wait_gives_up_at_the_timeout_with_the_last_state(monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(ft, "_sleep", clock.sleep)
    monkeypatch.setattr(ft, "_clock", clock.now)
    fake = FakeFireworks({("GET", JOB_PATH): [_job("JOB_STATE_RUNNING", 50)]})
    code, out = _run_job(monkeypatch, capsys, fake, "wait", "job-9", "--poll", "30", "--timeout", "100")
    assert code == 1
    assert "timed out" in out[-1]["error"] and out[-1]["state"] == "JOB_STATE_RUNNING"
    assert sum(clock.sleeps) <= 100 and len(fake.requests) == 4


def test_an_http_error_surfaces_with_status_and_response_text_never_the_headers(monkeypatch, capsys):
    fake = FakeFireworks({("GET", JOB_PATH): (403, "permission denied for account acct-1")})
    code, out = _run_job(monkeypatch, capsys, fake, "status", "job-9")
    assert code == 1
    assert out[-1]["status_code"] == 403 and "permission denied for account acct-1" in out[-1]["error"]
    assert "authorization" not in json.dumps(out).lower() and "bearer" not in json.dumps(out).lower()


def test_status_prints_state_and_progress_percent(monkeypatch, capsys):
    fake = FakeFireworks({("GET", JOB_PATH): _job("JOB_STATE_RUNNING", 37)})
    code, out = _run_job(monkeypatch, capsys, fake, "status", "accounts/acct-1/supervisedFineTuningJobs/job-9")
    assert code == 0 and out[-1]["state"] == "JOB_STATE_RUNNING" and out[-1]["percent"] == 37


def test_model_prints_the_chat_model_id_once_completed_and_refuses_before(monkeypatch, capsys):
    fake = FakeFireworks({("GET", JOB_PATH): [_job("JOB_STATE_RUNNING", 50), _job("JOB_STATE_COMPLETED", 100)]})
    code, out = _run_job(monkeypatch, capsys, fake, "model", "job-9")
    assert code == 1 and out[-1]["state"] == "JOB_STATE_RUNNING" and "not completed" in out[-1]["error"]
    code, out = _run_job(monkeypatch, capsys, fake, "model", "job-9")
    assert code == 0 and out[-1] == {"model": "accounts/acct-1/models/recourse-glimmer-ft", "state": "JOB_STATE_COMPLETED"}


def test_whoami_lists_the_account_ids_the_key_can_see(monkeypatch, capsys):
    fake = FakeFireworks({("GET", "/v1/accounts"): (200, {"accounts": [{"name": "accounts/alvaro-reis", "displayName": "Alvaro"}], "totalSize": 1})})
    code, out = _run_job(monkeypatch, capsys, fake, "whoami")
    assert code == 0 and out[-1]["account_ids"] == ["alvaro-reis"]


# ---- on-demand deployments (Muse Glimmer 30B is not served serverless) ------------------

DEP_PATH = "/v1/accounts/acct-1/deployments/glimmer-eval"


def _dep(state, message=""):
    return (200, {"name": "accounts/acct-1/deployments/glimmer-eval", "state": state, "baseModel": "accounts/acct-1/models/recourse-glimmer-ft", "status": {"code": "OK" if not message else "INTERNAL", "message": message}})


def test_deploy_sends_the_documented_body_with_one_replica_and_the_default_shape(monkeypatch, capsys):
    fake = FakeFireworks({("POST", "/v1/accounts/acct-1/deployments"): _dep("CREATING")})
    code, out = _run_job(monkeypatch, capsys, fake, "deploy", "--model", "accounts/acct-1/models/recourse-glimmer-ft", "--deployment-id", "glimmer-eval")
    assert code == 0
    req = fake.requests[0]
    assert req.url.params["deploymentId"] == "glimmer-eval"
    assert json.loads(req.content) == {"baseModel": "accounts/acct-1/models/recourse-glimmer-ft", "deploymentShape": "default", "minReplicaCount": 1, "maxReplicaCount": 1}
    assert out[-1]["name"] == "accounts/acct-1/deployments/glimmer-eval" and out[-1]["state"] == "CREATING"


def test_wait_deploy_polls_creating_to_ready_and_deploy_status_gives_the_chat_model(monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(ft, "_sleep", clock.sleep)
    monkeypatch.setattr(ft, "_clock", clock.now)
    fake = FakeFireworks({("GET", DEP_PATH): [_dep("CREATING"), _dep("CREATING"), _dep("READY")]})
    code, out = _run_job(monkeypatch, capsys, fake, "wait-deploy", "glimmer-eval", "--poll", "15")
    assert code == 0 and [o["state"] for o in out] == ["CREATING", "READY"] and clock.sleeps == [15, 15]
    code, out = _run_job(monkeypatch, capsys, fake, "deploy-status", "accounts/acct-1/deployments/glimmer-eval")
    assert code == 0 and out[-1]["state"] == "READY"
    assert out[-1]["chat_model"] == "accounts/acct-1/deployments/glimmer-eval"
    assert out[-1]["chat_model_alternatives"] == ["accounts/acct-1/models/recourse-glimmer-ft#accounts/acct-1/deployments/glimmer-eval"]


def test_wait_deploy_exits_non_zero_on_failed_with_the_reason(monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(ft, "_sleep", clock.sleep)
    monkeypatch.setattr(ft, "_clock", clock.now)
    fake = FakeFireworks({("GET", DEP_PATH): [_dep("CREATING"), _dep("FAILED", "no H100 capacity in region")]})
    code, out = _run_job(monkeypatch, capsys, fake, "wait-deploy", "glimmer-eval")
    assert code == 1 and out[-1]["state"] == "FAILED" and out[-1]["message"] == "no H100 capacity in region"


def test_undeploy_deletes_and_reports_the_final_state(monkeypatch, capsys):
    fake = FakeFireworks({("DELETE", DEP_PATH): (200, {}), ("GET", DEP_PATH): _dep("DELETING")})
    code, out = _run_job(monkeypatch, capsys, fake, "undeploy", "glimmer-eval")
    assert code == 0 and [(r.method, r.url.path) for r in fake.requests] == [("DELETE", DEP_PATH), ("GET", DEP_PATH)]
    assert out[-1]["deleted"] is True and out[-1]["state"] == "DELETING"


def test_undeploy_of_an_already_deleted_deployment_reports_the_404_and_exits_zero(monkeypatch, capsys):
    fake = FakeFireworks({("DELETE", DEP_PATH): (404, "deployment not found")})
    code, out = _run_job(monkeypatch, capsys, fake, "undeploy", "glimmer-eval")
    assert code == 0 and out[-1]["status_code"] == 404 and out[-1]["state"] == "DELETED" and "not found" in out[-1]["note"]


def test_undeploy_failing_for_another_reason_exits_non_zero(monkeypatch, capsys):
    fake = FakeFireworks({("DELETE", DEP_PATH): (500, "internal error")})
    code, out = _run_job(monkeypatch, capsys, fake, "undeploy", "glimmer-eval")
    assert code == 1 and out[-1]["status_code"] == 500 and "internal error" in out[-1]["error"]


def test_client_reads_key_and_account_from_the_environment_and_never_shows_the_key(monkeypatch):
    import httpx

    monkeypatch.setenv("FIREWORKS_API_KEY", DUMMY_KEY)
    monkeypatch.setenv("FIREWORKS_ACCOUNT_ID", "acct-1")
    fake = FakeFireworks({("GET", JOB_PATH): _job("JOB_STATE_RUNNING", 1)})
    c = ft.FireworksClient(transport=httpx.MockTransport(fake.handler))
    c.get_job("job-9")
    assert fake.requests[0].headers["authorization"] == f"Bearer {DUMMY_KEY}"
    assert DUMMY_KEY not in repr(c) and DUMMY_KEY not in str(vars(c).get("account_id"))


def test_missing_account_id_is_an_error_before_any_request(monkeypatch, capsys):
    import httpx

    fake = FakeFireworks({})
    monkeypatch.setattr(ft, "make_client", lambda: ft.FireworksClient(api_key=DUMMY_KEY, account_id="", transport=httpx.MockTransport(fake.handler)))
    import pytest

    from policyqa.cli import main

    with pytest.raises(SystemExit) as e:
        main(["finetune-job", "status", "job-9"])
    out = capsys.readouterr().out
    assert e.value.code == 1 and "FIREWORKS_ACCOUNT_ID" in out and fake.requests == [] and DUMMY_KEY not in out


# ---- fix round: tie-breaks toward the retrieved and the gold passage ----------------

GOLD_T = "Durable medical equipment rentals are capped at thirteen continuous months of payment."
PAGE_CHUNKS = [
    {"chunk_id": "fl-05:p002:0", "doc_id": "fl-05", "page": 2, "title": "DME", "jurisdiction": "Florida", "text": "Rental rules. " + GOLD_T + " After that the equipment belongs to the recipient."},
    {"chunk_id": "fl-05:p002:1", "doc_id": "fl-05", "page": 2, "title": "DME", "jurisdiction": "Florida", "text": GOLD_T.replace("of payment.", "of rent.") + " After that the equipment belongs to the recipient. Repairs are covered."},
    {"chunk_id": "fl-05:p002:2", "doc_id": "fl-05", "page": 2, "title": "DME", "jurisdiction": "Florida", "text": "Repairs are covered. " + GOLD_T},
]


def test_a_retrieved_chunk_on_the_gold_page_that_holds_the_quote_is_cited_and_nothing_is_inserted():
    chunks = CHUNKS + PAGE_CHUNKS
    by_id = {c["chunk_id"]: c for c in chunks}
    row = _row("gs-052", docs="fl-05", pages="2", quote=GOLD_T)
    # (a) two chunks tie at 1.0 on the gold page; the second one was retrieved
    # (b) the retrieved chunk holds the quote only above the threshold; another chunk of the page holds it verbatim
    for retrieved in ("fl-05:p002:2", "fl-05:p002:1"):
        assert ft.QUOTE_THRESHOLD <= ft.quote_overlap(GOLD_T, by_id[retrieved]["text"])
        ids = ["fl-09:p001:0", retrieved, "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0"]

        def search(q, k, ids=ids):
            return [Hit(by_id[i], 1.0, "hybrid") for i in ids][:k]

        res = ft.build_dataset([row], search, chunks, k=5)
        ex = res["examples"][0]
        assert _chunk_ids(ex) == ids, retrieved
        assert json.loads(ex["messages"][2]["content"])["citations"] == [{"passage": "P2", "quote": GOLD_T}]
        assert res["manifest"]["inserted"] == 0


def test_a_retrieved_chunk_on_the_gold_page_that_holds_the_quote_below_the_threshold_does_not_stop_the_insertion():
    """Evaluator, re-check: the holder rule needs its threshold. A retrieved chunk of the gold page that carries
    only a fragment of the quote (6 of the real rows, overlap 0.05 to 0.65) is not the evidence; the chunk that
    holds the quote is inserted and cited, and the weak chunk stays where retrieval put it."""
    weak = {"chunk_id": "fl-05:p002:9", "doc_id": "fl-05", "page": 2, "title": "DME", "jurisdiction": "Florida", "text": "Rental rules apply to durable medical equipment and to its repairs."}
    chunks = CHUNKS + PAGE_CHUNKS + [weak]
    by_id = {c["chunk_id"]: c for c in chunks}
    assert ft.quote_overlap(GOLD_T, weak["text"]) < ft.QUOTE_THRESHOLD
    row = _row("gs-029", docs="fl-05", pages="2", quote=GOLD_T)
    ids = ["fl-09:p001:0", "fl-05:p002:9", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0"]

    def search(q, k):
        return [Hit(by_id[i], 1.0, "hybrid") for i in ids][:k]

    res = ft.build_dataset([row], search, chunks, k=5)
    ex = res["examples"][0]
    got = _chunk_ids(ex)
    assert res["manifest"]["inserted"] == 1
    assert got[1] == "fl-05:p002:9" and got[-1] in ("fl-05:p002:0", "fl-05:p002:2")
    assert json.loads(ex["messages"][2]["content"])["citations"] == [{"passage": "P5", "quote": GOLD_T}]


def test_a_quote_verbatim_in_several_passages_is_cited_on_the_gold_page():
    dup = {"chunk_id": "fl-01:p023:0", "doc_id": "fl-01", "page": 23, "title": "Home Health Policy", "jurisdiction": "Florida", "text": "Appendix restating section 4.1. " + GOLD_A}
    chunks = CHUNKS + [dup]
    by_id = {c["chunk_id"]: c for c in chunks}
    row = _row("gs-031")  # gold fl-01 page 8

    def search_of(ids):
        return lambda q, k: [Hit(by_id[i], 1.0, "hybrid") for i in ids][:k]

    # the gold page was retrieved, after the duplicate: nothing inserted, the gold page cited
    ids = ["fl-01:p023:0", "fl-01:p008:0", "fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0"]
    res = ft.build_dataset([row], search_of(ids), chunks, k=5)
    assert _chunk_ids(res["examples"][0]) == ids and res["manifest"]["inserted"] == 0
    assert json.loads(res["examples"][0]["messages"][2]["content"])["citations"] == [{"passage": "P2", "quote": GOLD_A}]
    # only the duplicate on another page of the gold document was retrieved: the gold page is inserted and cited
    ids = ["fl-01:p023:0", "fl-09:p001:0", "fl-09:p002:0", "fl-09:p003:0", "fl-09:p004:0"]
    res = ft.build_dataset([row], search_of(ids), chunks, k=5)
    assert _chunk_ids(res["examples"][0])[-1] == "fl-01:p008:0" and res["manifest"]["inserted"] == 1
    assert json.loads(res["examples"][0]["messages"][2]["content"])["citations"] == [{"passage": "P5", "quote": GOLD_A}]


def test_the_gold_page_wins_only_ties_never_over_a_passage_that_holds_the_quote_better():
    quote = "Dental services for adults are limited to emergency extractions. Dentures are covered once every five years."
    whole = {"chunk_id": "fl-08:p004:0", "doc_id": "fl-08", "page": 4, "title": "Dental summary", "jurisdiction": "Florida", "text": "Summary. " + quote}
    chunks = CHUNKS + [whole]
    by_id = {c["chunk_id"]: c for c in chunks}
    assert ft.quote_overlap(quote, by_id["fl-09:p001:0"]["text"]) < QUOTE_THRESHOLD
    ids = ["fl-09:p001:0", "fl-08:p004:0", "fl-09:p003:0", "fl-09:p004:0", "fl-09:p005:0"]
    row = _row("gs-104", docs="fl-09", pages="1", quote=quote)
    res = ft.build_dataset([row], lambda q, k: [Hit(by_id[i], 1.0, "hybrid") for i in ids][:k], chunks, k=5)
    assert res["manifest"]["refused"] == []
    assert json.loads(res["examples"][0]["messages"][2]["content"])["citations"] == [{"passage": "P2", "quote": quote}]


def test_deploy_gpu_flag_sends_the_documented_accelerator_enum_and_only_when_given(monkeypatch, capsys):
    fake = FakeFireworks({("POST", "/v1/accounts/acct-1/deployments"): _dep("CREATING")})
    code, _ = _run_job(monkeypatch, capsys, fake, "deploy", "--model", "accounts/fireworks/models/muse-glimmer-30b", "--gpu", "H100")
    assert code == 0 and json.loads(fake.requests[0].content)["acceleratorType"] == "NVIDIA_H100_80GB"
    code, _ = _run_job(monkeypatch, capsys, fake, "deploy", "--model", "accounts/fireworks/models/muse-glimmer-30b")
    assert code == 0 and "acceleratorType" not in json.loads(fake.requests[1].content)

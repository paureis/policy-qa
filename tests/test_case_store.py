"""CaseStore on disk: a case survives a restart of the process (uvicorn reload, a Modal cold start)."""
import json
import os

from api.cases import CaseStore


def _card():
    return {"card": {"payer_name": {"value": "Sample", "confidence": "high", "edited": False}}, "source": "text"}


def test_case_written_on_create_and_read_back_by_a_new_store(tmp_path):
    s = CaseStore(tmp_path)
    c = s.create(_card())
    f = tmp_path / f"{c['case_id']}.json"
    assert f.exists()
    assert json.loads(f.read_text(encoding="utf-8"))["status"] == "intake"

    again = CaseStore(tmp_path)  # a fresh process
    got = again.get(c["case_id"])
    assert got is not None and got["card"] == c["card"] and got["created_at"] == c["created_at"]


def test_every_mutation_is_persisted(tmp_path):
    s = CaseStore(tmp_path)
    cid = s.create(_card())["case_id"]
    s.patch(cid, {"program": {"value": "medicare_b", "confidence": "high", "edited": True}})
    assert s.claim_for_investigation(cid)
    s.set_investigation(cid, {"program": "medicare_b"}, {"status": "done", "findings": []}, "investigated")
    s.set_stage(cid, "verdict", {"outcome": "consistent"}, "decided")
    s.set_status(cid, "drafting")

    fresh = CaseStore(tmp_path).get(cid)
    assert fresh["card"]["program"]["value"] == "medicare_b"
    assert fresh["route"] == {"program": "medicare_b"}
    assert fresh["investigation"]["status"] == "done"
    assert fresh["verdict"] == {"outcome": "consistent"}
    assert fresh["status"] == "drafting"


def test_ids_never_collide_with_cases_loaded_from_disk(tmp_path, monkeypatch):
    s = CaseStore(tmp_path)
    first = s.create(_card())["case_id"]
    again = CaseStore(tmp_path)
    ids = iter([first, "c_fresh1"])  # the first draw collides with the loaded case
    monkeypatch.setattr(CaseStore, "_new_id", staticmethod(lambda: next(ids)))
    assert again.create(_card())["case_id"] == "c_fresh1"
    assert again.get(first) is not None


def test_memory_only_store_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = CaseStore(None)
    s.create(_card())
    assert os.listdir(tmp_path) == []


def test_unreadable_file_is_skipped_not_fatal(tmp_path):
    (tmp_path / "c_bad.json").write_text("{not json", encoding="utf-8")
    s = CaseStore(tmp_path)
    good = s.create(_card())
    assert s.get("c_bad") is None and s.get(good["case_id"]) is not None


def test_module_store_directory_comes_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RECOURSE_CASE_DIR", str(tmp_path / "cases"))
    from api.cases import store_from_env

    s = store_from_env()
    c = s.create(_card())
    assert (tmp_path / "cases" / f"{c['case_id']}.json").exists()

    monkeypatch.setenv("RECOURSE_CASE_DIR", "")
    assert store_from_env()._dir is None

"""deploy/modal_app.py imports without Modal credentials, and its names match the repo.

Run from the repo root: `python -m pytest deploy -q`. Nothing here calls the network.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parent.parent


def _fresh_import():
    sys.modules.pop("deploy.modal_app", None)
    return importlib.import_module("deploy.modal_app")


def test_imports_without_credentials_or_modal():
    m = _fresh_import()
    try:
        import modal  # noqa: F401 -- imported only to learn whether the package is installed
    except ImportError:
        assert m.app is None
        assert "pip install modal" in m.MODAL_IMPORT_ERROR
    else:
        assert m.MODAL_IMPORT_ERROR is None
        assert m.app is not None and m.app.name == m.APP_NAME


def test_module_level_modal_code_runs_against_a_stub():
    """Executes every image, volume, secret and decorator line with a permissive stand-in for `modal`.
    This catches errors in the definition code; it does not prove the Modal API accepts the arguments."""
    stub = mock.MagicMock(name="modal")
    stub.is_local.return_value = True
    with mock.patch.dict(sys.modules, {"modal": stub}):
        m = _fresh_import()
        assert m.app is stub.App.return_value
        stub.App.assert_called_once_with("recourse-api")
        stub.Volume.from_name.assert_called_once_with("recourse-data", create_if_missing=False)
        assert stub.Secret.from_name.call_args.args == ("recourse-muse-spark",)
        stub.Secret.from_dict.assert_called_once_with(m.RUNTIME_ENV)
        kwargs = [c.kwargs for c in stub.App.return_value.function.call_args_list]
        web = next(k for k in kwargs if "min_containers" in k)
        assert web["max_containers"] == 1
        assert web["volumes"] == {"/root/data": stub.Volume.from_name.return_value}
    _fresh_import()  # leave the real module (or the no-modal one) in sys.modules


def test_container_layout_matches_how_the_api_finds_its_data():
    m = _fresh_import()
    # api/main.py: ROOT = parent of api/, DATA = ROOT / "data"; the source goes to /root/api.
    assert m.DATA_MOUNT == m.REMOTE_ROOT + "/data"
    for key in ("RECOURSE_PDF_DIR", "RECOURSE_PAGE_CACHE", "RECOURSE_CASE_DIR"):
        assert m.RUNTIME_ENV[key].startswith(m.DATA_MOUNT + "/")
    for p in ("api/main.py", "policyqa/pages.py", "corpus/manifest.csv"):
        assert (m.REPO / p).is_file(), p
    main_src = (REPO / "api" / "main.py").read_text(encoding="utf-8")
    assert 'DATA = ROOT / "data"' in main_src
    assert "RECOURSE_CORS_ORIGINS" in main_src


def test_model_names_match_the_package():
    from policyqa.index import EMBED_MODEL
    from policyqa.retrieve import ANSWER_RERANK_MODEL

    m = _fresh_import()
    assert m.EMBED_MODEL == EMBED_MODEL
    assert m.ANSWER_RERANK_MODEL == ANSWER_RERANK_MODEL


def test_every_runtime_dependency_is_pinned():
    import tomllib

    m = _fresh_import()
    py = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    wanted = py["dependencies"] + py["optional-dependencies"]["api"]
    pinned = {re.split(r"[\[=<>]", p)[0].lower().replace("_", "-") for p in m.PIP_PINS + (m.TORCH_PIN,)}
    for dep in wanted:
        name = re.split(r"[\[=<>]", dep)[0].lower().replace("_", "-")
        assert name in pinned, f"{dep} from pyproject is not pinned in deploy/modal_app.py"


def test_secret_keys_are_the_env_names_the_code_reads():
    m = _fresh_import()
    example = (REPO / ".env.example").read_text(encoding="utf-8")
    for key in m.SECRET_KEYS:
        assert re.search(rf"^{key}=", example, re.M), key


def test_manifest_dry_parse_matches_fetch_script(tmp_path):
    m = _fresh_import()
    rows = m.manifest_rows(REPO / "corpus" / "manifest.csv")
    assert len(rows) == 64
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 64
    assert all(r["url"].startswith("https://") for r in rows)
    fetch = (REPO / "corpus" / "fetch.sh").read_text(encoding="utf-8")
    pairs = dict(re.findall(r'-o "\$D/([\w-]+)\.pdf" "([^"]+)"', fetch))
    assert pairs == {r["id"]: r["url"] for r in rows}
    # missing_pdfs: a stub under 10 KB counts as missing, a full file does not
    (tmp_path / f"{ids[0]}.pdf").write_bytes(b"%PDF" + b"0" * 20_000)
    (tmp_path / f"{ids[1]}.pdf").write_bytes(b"%PDF stub")
    missing = {r["id"] for r in m.missing_pdfs(rows, tmp_path)}
    assert ids[0] not in missing and ids[1] in missing and len(missing) == 63


def test_build_asgi_returns_the_fastapi_app(monkeypatch):
    monkeypatch.setenv("RECOURSE_WARM_RETRIEVER", "0")
    m = _fresh_import()
    app = m.build_asgi()
    assert "/health" in {getattr(r, "path", None) for r in app.routes}

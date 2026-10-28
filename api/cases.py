"""Case store: a dict behind a lock, mirrored to one JSON file per case when a directory is set.

Shape of a case (what every /case route returns):
  {case_id, source, raw_text, summary, card, status, model, cost_usd, latency_ms, created_at,
   route, investigation, verdict, letter, critique, second_opinion}
Statuses: intake -> investigating -> investigated -> deciding -> decided -> drafting -> drafted
-> reviewing -> reviewed, or failed at any step up to the letter (the stage that failed carries
`status: "failed"` and `error`). The critic never fails the case: a critic failure ends
`reviewed` with the letter as drafted. `route` and `investigation` are null until the
investigation starts; `verdict`, `letter` and `critique` are null until their stage starts.
`second_opinion` (policyqa/second_opinion.py) is written beside the letter and never sets the
status; a case stored before it existed has no such key.
Shapes: policyqa/investigate.py, policyqa/verdict.py, policyqa/letter.py, policyqa/critic.py.

The interface (create, get, patch, set_status, claim_for_investigation, set_investigation, set_stage)
is small on purpose so a SQLite store can replace it without touching the routes.
claim_for_investigation is the one compare-and-set: it checks that the case is in intake and
moves it to investigating under the lock, so two posts cannot both start it.

Persistence: CaseStore(directory) loads every `<case_id>.json` in the directory at start and
rewrites the case's file (atomically: temp file, then replace) after every mutation, so a
uvicorn reload or a cold start on a host keeps open cases. CaseStore(None) is memory only.
The module store reads RECOURSE_CASE_DIR (default `data/cases` under the repo; empty string
means memory only). A file that does not parse is skipped with a warning, never fatal. A loaded
case whose `second_opinion` is still "running" (its daemon thread died with the old process) is
rewritten as "failed" with SECOND_RESTARTED, every other field kept.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("recourse.cases")

DEFAULT_CASE_DIR = Path(__file__).resolve().parent.parent / "data" / "cases"
SECOND_RESTARTED = "the server restarted before the second opinion finished"


class CaseStore:
    def __init__(self, directory: str | os.PathLike | None = None):
        self._cases: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._dir = Path(directory) if directory else None
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        for f in sorted(self._dir.glob("*.json")):
            try:
                case = json.loads(f.read_text(encoding="utf-8"))
                cid = case["case_id"]
            except (OSError, ValueError, KeyError, TypeError) as e:
                log.warning("skipping unreadable case file %s: %s", f, e)
                continue
            self._cases[cid] = case
            so = case.get("second_opinion")
            if isinstance(so, dict) and so.get("status") == "running":
                # Its thread is a daemon and died with the old process; nothing else would ever finish it.
                case["second_opinion"] = {**so, "status": "failed", "error": SECOND_RESTARTED}
                self._save(case)

    def _save(self, case: dict) -> None:
        """Write the case's file; called under the lock. A write error is logged, not raised: the case stays in memory."""
        if self._dir is None:
            return
        final = self._dir / f"{case['case_id']}.json"
        tmp = final.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, final)
        except OSError as e:
            log.warning("could not write case file %s: %s", final, e)

    @staticmethod
    def _new_id() -> str:
        return "c_" + secrets.token_hex(3)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def create(self, data: dict) -> dict:
        with self._lock:
            cid = self._new_id()
            while cid in self._cases:
                cid = self._new_id()
            case = {"case_id": cid, **data, "status": "intake", "created_at": self._now(), "route": None, "investigation": None, "verdict": None, "letter": None, "critique": None, "second_opinion": None}
            self._cases[cid] = case
            self._save(case)
            return dict(case)

    def get(self, case_id: str) -> dict | None:
        with self._lock:
            c = self._cases.get(case_id)
            return dict(c) if c else None

    def patch(self, case_id: str, fields: dict) -> dict | None:
        """Replace card cells. `fields` maps field name -> {"value", "confidence", "edited"}."""
        with self._lock:
            c = self._cases.get(case_id)
            if c is None:
                return None
            card = dict(c["card"])
            card.update(fields)
            c["card"] = card
            self._save(c)
            return dict(c)

    def set_status(self, case_id: str, status: str) -> dict | None:
        with self._lock:
            c = self._cases.get(case_id)
            if c is None:
                return None
            c["status"] = status
            self._save(c)
            return dict(c)

    def claim_for_investigation(self, case_id: str) -> bool:
        """Move an `intake` case to `investigating` atomically. False when the case is missing or already past intake."""
        with self._lock:
            c = self._cases.get(case_id)
            if c is None or c["status"] != "intake":
                return False
            c["status"] = "investigating"
            self._save(c)
            return True

    def set_investigation(self, case_id: str, route: dict | None, investigation: dict | None, status: str) -> dict | None:
        """Store a snapshot of the route and the investigation (copied, so the running thread's dict can keep changing) and the case status."""
        with self._lock:
            c = self._cases.get(case_id)
            if c is None:
                return None
            c["route"] = copy.deepcopy(route)
            c["investigation"] = copy.deepcopy(investigation)
            c["status"] = status
            self._save(c)
            return dict(c)

    STAGES = ("investigation", "verdict", "letter", "critique", "second_opinion")

    def set_stage(self, case_id: str, field: str, value: dict | None, status: str | None = None) -> dict | None:
        """Store a copy of one stage (investigation, verdict, letter, or critique) and, when given, the case status."""
        if field not in self.STAGES:
            raise ValueError(f"{field} is not a stage")
        with self._lock:
            c = self._cases.get(case_id)
            if c is None:
                return None
            c[field] = copy.deepcopy(value)
            if status is not None:
                c["status"] = status
            self._save(c)
            return dict(c)


def store_from_env() -> CaseStore:
    """The store the API uses: RECOURSE_CASE_DIR, default data/cases; an empty value means memory only."""
    raw = os.environ.get("RECOURSE_CASE_DIR")
    if raw is None:
        return CaseStore(DEFAULT_CASE_DIR)
    return CaseStore(raw or None)


STORE = store_from_env()

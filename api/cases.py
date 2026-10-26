"""Case store: an in-memory dict behind a lock.

Shape of a case (what every /case route returns):
  {case_id, source, raw_text, summary, card, status, model, cost_usd, latency_ms, created_at}
Statuses: intake -> investigating (-> verdict -> letter, when those land).

The interface (create, get, patch, set_status) is small on purpose so a
file-backed or SQLite store can replace it without touching the routes.
"""
from __future__ import annotations

import secrets
import threading
from datetime import datetime, timezone


class CaseStore:
    def __init__(self):
        self._cases: dict[str, dict] = {}
        self._lock = threading.Lock()

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
            case = {"case_id": cid, **data, "status": "intake", "created_at": self._now()}
            self._cases[cid] = case
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
            return dict(c)

    def set_status(self, case_id: str, status: str) -> dict | None:
        with self._lock:
            c = self._cases.get(case_id)
            if c is None:
                return None
            c["status"] = status
            return dict(c)


STORE = CaseStore()

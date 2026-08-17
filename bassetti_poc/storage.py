"""Small local JSON session store with append-only audit events."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .schema import FIELD_ORDER, value_to_display


class SessionStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def create(self, result: dict) -> dict:
        session = {
            "id": uuid.uuid4().hex[:12],
            "created_at": self.now(),
            "updated_at": self.now(),
            "approved_at": None,
            "result": result,
            "audit": [],
        }
        self.save(session)
        return session

    def path(self, session_id: str) -> Path:
        if not session_id.isalnum() or len(session_id) > 32:
            raise KeyError("Invalid session id")
        return self.root / f"{session_id}.json"

    def get(self, session_id: str) -> dict:
        path = self.path(session_id)
        if not path.exists():
            raise KeyError("Session not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, session: dict) -> None:
        with self._lock:
            path = self.path(session["id"])
            fd, temp_name = tempfile.mkstemp(prefix="session_", suffix=".json", dir=self.root)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(session, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def update_field(self, session_id: str, field_path: str, value, action: str) -> dict:
        if field_path not in FIELD_ORDER:
            raise ValueError("Unknown schema field")
        if action not in {"save", "confirm", "follow_up"}:
            raise ValueError("Unsupported review action")
        with self._lock:
            session = self.get(session_id)
            field = session["result"]["fields"][field_path]
            old_value = field["value"]
            old_status = field["review_status"]
            field["value"] = value
            field["display"] = value_to_display(value)
            field["review_status"] = {"save": "unreviewed", "confirm": "confirmed", "follow_up": "follow_up"}[action]
            session["audit"].append({
                "timestamp": self.now(),
                "field": field_path,
                "old_value": old_value,
                "new_value": value,
                "old_status": old_status,
                "new_status": field["review_status"],
                "action": action,
            })
            session["updated_at"] = self.now()
            self.save(session)
            return session

    def reset_review(self, session_id: str) -> dict:
        with self._lock:
            session = self.get(session_id)
            for field_path, field in session["result"]["fields"].items():
                old_status = field["review_status"]
                if old_status != "unreviewed":
                    session["audit"].append({
                        "timestamp": self.now(), "field": field_path, "old_value": field["value"],
                        "new_value": field["value"], "old_status": old_status, "new_status": "unreviewed",
                        "action": "return_to_review",
                    })
                field["review_status"] = "unreviewed"
            session["approved_at"] = None
            session["updated_at"] = self.now()
            self.save(session)
            return session

    def stats(self) -> dict:
        corrections = sessions = 0
        durations = []
        for path in self.root.glob("*.json"):
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            sessions += 1
            durations.append(session.get("result", {}).get("processing_ms", 0))
            corrections += sum(1 for event in session.get("audit", []) if event["old_value"] != event["new_value"])
        return {"sessions": sessions, "corrections": corrections, "average_processing_ms": round(sum(durations) / len(durations)) if durations else 0}


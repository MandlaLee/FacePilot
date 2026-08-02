"""Local JSON persistence for FacePilot test-session history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SessionStore:
    """Persist completed session dictionaries in a local application folder."""

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, payload: dict[str, Any]) -> Path:
        session_id = str(payload.get("id", "unknown-session"))
        path = self.root / f"{session_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payload["_path"] = str(path)
            sessions.append(payload)
        return sessions

    def delete(self, session_id: str) -> bool:
        path = self.root / f"{session_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def purge_older_than(self, days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=max(days, 0))
        deleted = 0
        for payload in self.list_sessions():
            raw = payload.get("ended_at") or payload.get("created_at")
            if not isinstance(raw, str):
                continue
            try:
                timestamp = datetime.fromisoformat(raw)
            except ValueError:
                continue
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            if timestamp < cutoff and self.delete(str(payload.get("id", ""))):
                deleted += 1
        return deleted

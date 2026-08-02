"""Platform-appropriate local storage paths for FacePilot."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def application_data_root() -> Path:
    """Return and create FacePilot's writable application data directory."""
    raw = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    root = Path(raw) if raw else Path.home() / ".facepilot"
    root.mkdir(parents=True, exist_ok=True)
    return root


def session_history_root() -> Path:
    """Return the directory containing locally persisted test sessions."""
    root = application_data_root() / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root

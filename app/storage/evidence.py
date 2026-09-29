"""Local evidence snapshots for authorized FacePilot test sessions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage


class EvidenceStore:
    """Save explicit RGB preview snapshots locally as PNG evidence."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_frame(self, session_id: str, sequence: int, frame: np.ndarray) -> Path:
        if frame.ndim != 3 or frame.shape[2] < 3:
            raise ValueError("Expected an RGB frame")
        rgb = np.ascontiguousarray(frame[..., :3], dtype=np.uint8)
        height, width, _ = rgb.shape
        image = QImage(
            rgb.data,
            width,
            height,
            width * 3,
            QImage.Format.Format_RGB888,
        )
        if image.isNull():
            raise ValueError("Could not create an image from the frame")
        session_dir = self.root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / f"frame-{sequence:03d}.png"
        if not image.copy().save(str(path), "PNG"):
            raise OSError(f"Could not save evidence frame: {path}")
        return path

    def delete_session(self, session_id: str) -> int:
        session_dir = self.root / session_id
        if not session_dir.exists():
            return 0
        deleted = 0
        for path in session_dir.glob("*.png"):
            try:
                path.unlink()
                deleted += 1
            except OSError:
                continue
        try:
            session_dir.rmdir()
        except OSError:
            pass
        return deleted

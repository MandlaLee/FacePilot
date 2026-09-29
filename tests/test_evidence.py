import numpy as np
import pytest

from app.storage.evidence import EvidenceStore


def test_save_frame_creates_png(tmp_path) -> None:
    store = EvidenceStore(tmp_path)
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    path = store.save_frame("session-1", 1, frame)
    assert path.exists()
    assert path.name == "frame-001.png"
    assert path.read_bytes().startswith(b"\x89PNG")


def test_save_frame_rejects_non_rgb(tmp_path) -> None:
    store = EvidenceStore(tmp_path)
    with pytest.raises(ValueError):
        store.save_frame("session-1", 1, np.zeros((12, 16), dtype=np.uint8))

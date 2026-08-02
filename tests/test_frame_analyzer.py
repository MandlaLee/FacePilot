import numpy as np

from app.detection.frame_analyzer import FrameAnalyzer


def test_duplicate_frames_score_high() -> None:
    analyzer = FrameAnalyzer()
    frame = np.full((24, 24, 3), 128, dtype=np.uint8)
    analyzer.analyze(frame)
    metrics = analyzer.analyze(frame.copy())
    assert metrics.duplicate_score > 0.98
    assert metrics.motion_score == 0.0


def test_changed_frame_has_motion() -> None:
    analyzer = FrameAnalyzer()
    analyzer.analyze(np.zeros((20, 20), dtype=np.uint8))
    metrics = analyzer.analyze(np.full((20, 20), 255, dtype=np.uint8))
    assert metrics.motion_score == 1.0
    assert metrics.duplicate_score == 0.0

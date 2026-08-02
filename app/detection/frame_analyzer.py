"""Lightweight frame-level anomaly signals.

These detectors are deliberately transparent heuristics for controlled testing;
they are not represented as production biometric guarantees.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class FrameMetrics:
    duplicate_score: float
    brightness: float
    sharpness: float
    motion_score: float


class FrameAnalyzer:
    """Analyze consecutive RGB or grayscale NumPy frames locally."""

    def __init__(self, history_size: int = 12) -> None:
        if history_size < 2:
            raise ValueError("history_size must be at least 2")
        self._history: deque[np.ndarray] = deque(maxlen=history_size)

    @staticmethod
    def _gray(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            gray = frame
        elif frame.ndim == 3 and frame.shape[2] >= 3:
            rgb = frame[..., :3].astype(np.float32)
            gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        else:
            raise ValueError("Expected a grayscale or RGB frame")
        return np.clip(gray, 0, 255).astype(np.float32)

    @staticmethod
    def _sharpness(gray: np.ndarray) -> float:
        gx = np.diff(gray, axis=1)
        gy = np.diff(gray, axis=0)
        energy = float(np.mean(gx * gx) + np.mean(gy * gy))
        return max(0.0, min(energy / 3000.0, 1.0))

    def analyze(self, frame: np.ndarray) -> FrameMetrics:
        gray = self._gray(frame)
        brightness = float(np.mean(gray) / 255.0)
        sharpness = self._sharpness(gray)

        if not self._history:
            duplicate_score = 0.0
            motion_score = 0.0
        else:
            previous = self._history[-1]
            if previous.shape != gray.shape:
                duplicate_score = 0.0
                motion_score = 1.0
            else:
                mean_delta = float(np.mean(np.abs(gray - previous)) / 255.0)
                motion_score = max(0.0, min(mean_delta * 8.0, 1.0))
                duplicate_score = max(0.0, min(1.0 - mean_delta * 80.0, 1.0))

        self._history.append(gray.copy())
        return FrameMetrics(
            duplicate_score=duplicate_score,
            brightness=brightness,
            sharpness=sharpness,
            motion_score=motion_score,
        )

    def repeated_frame_ratio(self, threshold: float = 0.98) -> float:
        if len(self._history) < 2:
            return 0.0
        pairs = list(zip(list(self._history)[:-1], list(self._history)[1:]))
        repeated = 0
        valid = 0
        for first, second in pairs:
            if first.shape != second.shape:
                continue
            valid += 1
            delta = float(np.mean(np.abs(first - second)) / 255.0)
            similarity = 1.0 - min(delta, 1.0)
            repeated += similarity >= threshold
        return repeated / valid if valid else 0.0

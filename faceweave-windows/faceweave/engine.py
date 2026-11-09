"""FaceWeave Windows — offline ONNX live camera face-swap engine.

Models are provided by the user separately; this package never downloads or
redistributes pretrained identity models.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import onnxruntime as ort

MODELS = {
    "det_10g.onnx": "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
    "w600k_r50.onnx": "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
    "inswapper_128_fp16.onnx": "6d51a9278a1f650cffefc18ba53f38bf2769bf4bbff89267822cf72945f8a38b",
    "inswapper_emap.npy": "cee626bc81721d71c5d6cb1f76f830b9ae46f595514b0884dd8ae34785576764",
}

REFERENCE = np.array([
    [38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
    [41.5493, 92.3655], [70.7299, 92.2041],
], dtype=np.float32)


def verify_models(folder: Path, progress: Callable[[str], None] = lambda _s: None) -> None:
    for name, expected in MODELS.items():
        path = folder / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}. Copy the original model pack into {folder}")
        progress(f"Verifying {name}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest().lower() != expected:
            raise ValueError(f"{name} does not match the verified model pack")
    progress("All four original model files verified")


def bgr_chw(frame: np.ndarray, mean: float, scale: float) -> np.ndarray:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32)
    return np.ascontiguousarray(((rgb - mean) / scale).transpose(2, 0, 1)[None])


def scale_frame(frame: np.ndarray, maximum: int) -> np.ndarray:
    h, w = frame.shape[:2]
    scale = min(1.0, maximum / max(h, w))
    return cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale)))) if scale < 1 else frame


def _similarity(landmarks: np.ndarray, size: int) -> np.ndarray:
    if size not in (112, 128):
        raise ValueError("Only 112px and 128px aligned crops are supported")
    source = np.asarray(landmarks, dtype=np.float32).reshape(5, 2)
    destination = REFERENCE.copy()
    if size == 128:
        destination[:, 0] += 8.0
    sx, sy = source.mean(axis=0)
    dx, dy = destination.mean(axis=0)
    x, y = (source - (sx, sy)).T
    u, v = (destination - (dx, dy)).T
    denom = float(np.dot(x, x) + np.dot(y, y))
    if denom < 1e-4:
        raise ValueError("Degenerate face landmarks")
    a = float(np.dot(x, u) + np.dot(y, v)) / denom
    b = float(np.dot(x, v) - np.dot(y, u)) / denom
    return np.array([[a, -b, dx - a * sx + b * sy],
                     [b, a, dy - b * sx - a * sy]], dtype=np.float32)


def _aligned(frame: np.ndarray, landmarks: np.ndarray, size: int) -> tuple[np.ndarray, np.ndarray]:
    matrix = _similarity(landmarks, size)
    cropped = cv2.warpAffine(frame, matrix, (size, size), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT)
    return cropped, matrix


def _face_detection(session: ort.InferenceSession, frame: np.ndarray) -> np.ndarray:
    """Return landmarks for the highest-confidence large face (original SCRFD 10G)."""
    h, w = frame.shape[:2]
    scale = min(320.0 / w, 320.0 / h)
    sw = max(1, min(320, int(round(w * scale))))
    sh = max(1, min(320, int(round(h * scale))))
    canvas = np.zeros((320, 320, 3), np.uint8)
    canvas[:sh, :sw] = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_LINEAR)
    feeds = {session.get_inputs()[0].name: bgr_chw(canvas, 127.5, 128.0)}
    raw = session.run(None, feeds)
    if len(raw) != 9:
        raise RuntimeError(f"SCRFD expected 9 outputs, received {len(raw)}")
    candidates: list[tuple[float, np.ndarray]] = []
    for gi, stride in enumerate((8, 16, 32)):
        grid = 320 // stride
        count = grid * grid * 2
        scores = np.asarray(raw[gi]).reshape(-1)
        boxes = np.asarray(raw[gi + 3]).reshape(-1, 4)
        points = np.asarray(raw[gi + 6]).reshape(-1, 10)
        if scores.size < count or boxes.shape[0] < count or points.shape[0] < count:
            raise RuntimeError(f"Unexpected SCRFD output at stride {stride}")
        indices = np.flatnonzero(np.isfinite(scores[:count]) & (scores[:count] >= 0.48))
        for index in indices:
            cell = int(index) // 2
            cx, cy = (cell % grid) * stride, (cell // grid) * stride
            l, t, r, b = boxes[index] * stride
            left = np.clip((cx - l) / scale, 0, w)
            top = np.clip((cy - t) / scale, 0, h)
            right = np.clip((cx + r) / scale, 0, w)
            bottom = np.clip((cy + b) / scale, 0, h)
            fw, fh = right - left, bottom - top
            if fw < 20 or fh < 20:
                continue
            xy = points[index].reshape(5, 2) * stride
            xy += (cx, cy)
            xy = xy / scale
            xy[:, 0] = np.clip(xy[:, 0], 0, w)
            xy[:, 1] = np.clip(xy[:, 1], 0, h)
            rank = float(scores[index]) * float(fw * fh)
            candidates.append((rank, xy.astype(np.float32)))
    if not candidates:
        raise LookupError("No clear face visible; face the camera in good light")
    return max(candidates, key=lambda item: item[0])[1]


def _session(path: Path, threads: int = 2) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = max(1, threads)
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])


class LiveEngine:
    """Prepare a source identity once; reuse SCRFD and InSwapper for all live frames."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.detector: ort.InferenceSession | None = None
        self.swapper: ort.InferenceSession | None = None
        self.identity: np.ndarray | None = None

    def prepare(self, source: np.ndarray, status: Callable[[str], None] = lambda _s: None) -> None:
        self.close()
        verify_models(self.folder, status)
        status("Loading face detector")
        self.detector = _session(self.folder / "det_10g.onnx")
        source = scale_frame(source, 1200)
        status("Reading source face")
        landmarks = _face_detection(self.detector, source)
        status("Calculating identity once")
        recognizer = _session(self.folder / "w600k_r50.onnx")
        try:
            cropped, _ = _aligned(source, landmarks, 112)
            result = recognizer.run(None, {recognizer.get_inputs()[0].name: bgr_chw(cropped, 127.5, 127.5)})[0]
            embedding = np.asarray(result, dtype=np.float32).reshape(-1)
            if embedding.size != 512:
                raise RuntimeError("ArcFace returned an invalid identity vector")
        finally:
            del recognizer
        status("Mapping source identity")
        emap = np.load(self.folder / "inswapper_emap.npy", allow_pickle=False)
        if emap.shape != (512, 512) or emap.dtype != np.float32:
            raise RuntimeError("Invalid 512x512 identity mapping")
        embedding /= max(1e-9, np.linalg.norm(embedding))
        mapped = embedding @ emap
        mapped /= max(1e-9, np.linalg.norm(mapped))
        self.identity = np.ascontiguousarray(mapped.reshape(1, 512), dtype=np.float32)
        status("Loading neural face swapper")
        self.swapper = _session(self.folder / "inswapper_128_fp16.onnx")
        actual_inputs = {i.name for i in self.swapper.get_inputs()}
        if not {"source", "target"}.issubset(actual_inputs):
            raise RuntimeError("Unexpected InSwapper input names")
        status("Models ready — processing live webcam frames")

    def swap(self, frame: np.ndarray) -> np.ndarray:
        if self.detector is None or self.swapper is None or self.identity is None:
            raise RuntimeError("Engine not prepared")
        frame = scale_frame(frame, 640)
        landmarks = _face_detection(self.detector, frame)
        cropped, matrix = _aligned(frame, landmarks, 128)
        feeds = {
            "target": bgr_chw(cropped, 0.0, 255.0),
            "source": self.identity,
        }
        result = self.swapper.run(None, feeds)[0]
        result = np.asarray(result, dtype=np.float32).reshape(3, 128, 128)
        rgb = np.transpose(result, (1, 2, 0))
        fake = cv2.cvtColor(np.clip(rgb * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        yy, xx = np.mgrid[:128, :128]
        dx = (xx - 63.5) / (128.0 * 0.44)
        dy = (yy - 63.5) / (128.0 * 0.44)
        radius = np.sqrt(dx * dx + dy * dy)
        t = np.clip((radius - 0.70) / 0.30, 0.0, 1.0)
        mask = (1 - t * t * (3 - 2 * t)).astype(np.float32)
        inv = cv2.invertAffineTransform(matrix)
        height, width = frame.shape[:2]
        overlay = cv2.warpAffine(fake, inv, (width, height), flags=cv2.INTER_LINEAR)
        alpha = cv2.warpAffine(mask, inv, (width, height), flags=cv2.INTER_LINEAR)
        alpha = np.clip(alpha, 0.0, 1.0)[:, :, None]
        return np.clip(frame.astype(np.float32) * (1 - alpha) +
                       overlay.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    def close(self) -> None:
        self.detector = None
        self.swapper = None
        self.identity = None

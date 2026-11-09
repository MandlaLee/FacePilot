"""Native FaceWeave LIVE-only webcam interface for Windows."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import threading
import time

import cv2
import numpy as np
from PIL import Image as PILImage, ImageOps
from PySide6.QtCore import QObject, QSettings, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .engine import LiveEngine, MODELS


def resource_home() -> Path:
    # The distributed one-file EXE uses the directory beside FaceWeave.exe,
    # not PyInstaller's temporary extraction directory.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def load_source(path: Path) -> np.ndarray:
    with PILImage.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1600, 1600))
        rgb = np.array(image)
    return np.ascontiguousarray(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def pixmap(frame: np.ndarray) -> QPixmap:
    rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    h, w = rgb.shape[:2]
    return QPixmap.fromImage(
        QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888).copy()
    )


class CameraThread(QThread):
    picture = Signal(object)
    status = Signal(str)
    availability = Signal(bool)

    def __init__(self, index: int, forward, mirror: bool = True) -> None:
        super().__init__()
        self.index = index
        self.forward = forward
        self.mirror = mirror
        self._stop = threading.Event()

    def run(self) -> None:
        cap = None
        try:
            if sys.platform == "win32":
                cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(self.index, cv2.CAP_MSMF)
            else:
                cap = cv2.VideoCapture(self.index)
            if not cap.isOpened():
                raise RuntimeError(f"Camera {self.index} is unavailable or in use")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.availability.emit(True)
            self.status.emit("Camera connected. Select source identity to begin.")
            last_shown = 0.0
            missed = 0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    missed += 1
                    if missed >= 25:
                        raise RuntimeError("Camera stopped delivering frames")
                    self.msleep(30)
                    continue
                missed = 0
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self.forward(frame)
                now = time.monotonic()
                if now - last_shown >= 0.075:
                    self.picture.emit(frame)
                    last_shown = now
        except Exception as exc:
            self.status.emit(f"Camera: {exc}")
        finally:
            self.availability.emit(False)
            if cap is not None:
                cap.release()

    def stop(self) -> None:
        self._stop.set()


class LiveProcessor(QObject):
    status = Signal(str)
    result = Signal(object, int, int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, source: np.ndarray, model_folder: Path) -> None:
        super().__init__()
        self.source = source.copy()
        self.model_folder = model_folder
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._latest = None
        self._thread = threading.Thread(target=self._run, name="faceweave-neural-live", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def submit(self, frame: np.ndarray) -> None:
        if self._stop.is_set():
            return
        # Replace the old frame, never queue: only process the newest camera image.
        with self._lock:
            self._latest = frame.copy()
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def _run(self) -> None:
        engine = LiveEngine(self.model_folder)
        frame_count = 0
        try:
            engine.prepare(self.source, self.status.emit)
            if self._stop.is_set():
                return
            self.status.emit("Live face swap running. Processing latest webcam frames.")
            while not self._stop.is_set():
                if not self._wake.wait(timeout=0.2):
                    continue
                self._wake.clear()
                with self._lock:
                    frame = self._latest
                    self._latest = None
                if frame is None:
                    continue
                start = time.monotonic()
                try:
                    result = engine.swap(frame)
                except LookupError:
                    self.status.emit("Looking for a clear face in the camera…")
                    continue
                if self._stop.is_set():
                    break
                elapsed = max(1, int((time.monotonic() - start) * 1000))
                frame_count += 1
                self.result.emit(result, elapsed, frame_count)
        except MemoryError:
            self.error.emit("The computer ran out of memory while loading or swapping.")
        except Exception as exc:
            self.error.emit(f"Neural engine: {exc}")
        finally:
            engine.close()
            self.finished.emit()


STYLE = """
QMainWindow, QWidget#Root { background-color:#081815; color:#F2F6EC; }
QLabel { color:#F2F6EC; }
QLabel#Title {font-size:26px;font-weight:900;letter-spacing:2px;}
QLabel#Eyebrow {font-size:11px;color:#BCE9A5;font-weight:800;letter-spacing:1px;}
QLabel#Muted {color:#A3B8AE;font-size:12px;}
QLabel#Stat {color:#C9F2AB;font-weight:800;font-size:12px;}
QFrame#Panel {background:#112923;border:1px solid #335248;border-radius:14px;}
QLabel#Viewport {background:#07100F;color:#8DA99D;border:1px solid #335248;border-radius:10px;}
QPushButton {background:#C9F2AB;color:#081815;border:0;border-radius:10px;
            padding:11px 17px;font-weight:800;font-size:12px;}
QPushButton:hover {background:#E1FFC7;}
QPushButton:disabled {background:#2A4138;color:#829489;}
QPushButton#Secondary {background:#203D33;color:#F2F6EC;border:1px solid #36564A;}
QPushButton#Secondary:hover {background:#345648;}
QCheckBox {color:#DCE8DD;spacing:9px;font-size:12px;}
QCheckBox::indicator {width:18px;height:18px;}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FaceWeave — Live face swapping")
        self.setMinimumSize(910, 635)
        self.resize(1160, 760)
        self.settings = QSettings("Phala Digital", "FaceWeave Windows")
        self.model_folder = Path(self.settings.value("models", str(resource_home() / "models")))
        self.source = None
        self.source_path = None
        self.camera: CameraThread | None = None
        self.processor: LiveProcessor | None = None
        self.camera_available = False
        self._camera_idx = 0
        self._latest_raw: QPixmap | None = None
        self._latest_swapped: QPixmap | None = None
        self._build()
        self._refresh_controls()
        self._open_camera()

    def _text(self, value: str, role: str = "") -> QLabel:
        label = QLabel(value)
        if role:
            label.setObjectName(role)
        return label

    def _panel(self, heading: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.addWidget(self._text(heading, "Eyebrow"))
        viewport = QLabel()
        viewport.setObjectName("Viewport")
        viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewport.setMinimumHeight(300)
        viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viewport.setText("Waiting for camera…")
        layout.addWidget(viewport, 1)
        return panel, layout, viewport

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root.setStyleSheet(STYLE)
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 19, 24, 18)
        outer.setSpacing(14)

        head = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(self._text("FACEWEAVE", "Title"))
        heading.addWidget(self._text("WINDOWS  /  LIVE-ONLY FACE SWAP", "Eyebrow"))
        head.addLayout(heading, 1)
        head.addWidget(self._text("ON-DEVICE  •  NO CLOUD", "Stat"))
        outer.addLayout(head)

        previews = QHBoxLayout()
        previews.setSpacing(12)
        swapped_panel, swapped_layout, self.swapped_view = self._panel("AI LIVE OUTPUT  ·  MOST RECENT PROCESSED FRAME")
        self.swapped_view.setText("AI output will appear after you start live swapping")
        self.swap_rate = self._text("Not running  •  actual neural FPS: —", "Stat")
        swapped_layout.addWidget(self.swap_rate)
        raw_panel, raw_layout, self.raw_view = self._panel("CAMERA INPUT  ·  RESPONSIVE UNMODIFIED PREVIEW")
        self.camera_rate = self._text("Camera: starting…", "Muted")
        raw_layout.addWidget(self.camera_rate)
        previews.addWidget(swapped_panel, 3)
        previews.addWidget(raw_panel, 2)
        outer.addLayout(previews, 1)

        source_line = QHBoxLayout()
        source_text = QVBoxLayout()
        source_text.addWidget(self._text("SOURCE IDENTITY", "Eyebrow"))
        self.source_caption = self._text("Select the face to place into the live webcam feed", "Muted")
        source_text.addWidget(self.source_caption)
        source_line.addLayout(source_text, 1)
        self.source_button = QPushButton("CHOOSE SOURCE FACE")
        self.source_button.setObjectName("Secondary")
        self.source_button.clicked.connect(self._choose_source)
        source_line.addWidget(self.source_button)
        outer.addLayout(source_line)

        model_line = QHBoxLayout()
        model_text = QVBoxLayout()
        model_text.addWidget(self._text("NEURAL MODELS", "Eyebrow"))
        self.model_caption = self._text("Four external model files required in a local folder", "Muted")
        model_text.addWidget(self.model_caption)
        model_line.addLayout(model_text, 1)
        self.models_button = QPushButton("SELECT MODEL FOLDER")
        self.models_button.setObjectName("Secondary")
        self.models_button.clicked.connect(self._choose_models)
        model_line.addWidget(self.models_button)
        outer.addLayout(model_line)

        controls = QHBoxLayout()
        self.consent = QCheckBox("I have permission to use the source face and people on camera.")
        self.consent.stateChanged.connect(self._refresh_controls)
        controls.addWidget(self.consent, 1)
        self.mirror = QCheckBox("Mirror")
        self.mirror.setChecked(True)
        self.mirror.stateChanged.connect(self._restart_camera)
        controls.addWidget(self.mirror)
        self.flip = QPushButton("CAMERA 0 → 1")
        self.flip.setObjectName("Secondary")
        self.flip.clicked.connect(self._flip_camera)
        controls.addWidget(self.flip)
        self.start_button = QPushButton("START LIVE SWAP")
        self.start_button.clicked.connect(self._toggle)
        controls.addWidget(self.start_button)
        outer.addLayout(controls)

        self.status_line = self._text("Offline preview. The camera FPS is NOT AI face-swap FPS.", "Muted")
        self.status_line.setWordWrap(True)
        outer.addWidget(self.status_line)

    def _refresh_controls(self) -> None:
        for name in ("models", "source"):
            pass
        missing = [name for name in MODELS if not (self.model_folder / name).is_file()]
        self.model_caption.setText(
            "Ready: " + str(self.model_folder) if not missing else
            f"Missing {len(missing)} model files  •  " + str(self.model_folder)
        )
        busy = self.processor is not None
        self.start_button.setEnabled(busy or bool(self.source is not None and not missing
                                    and self.camera_available and self.consent.isChecked()))
        self.start_button.setText("STOP LIVE SWAP" if busy else "START LIVE SWAP")
        self.models_button.setEnabled(not busy)
        self.source_button.setEnabled(not busy)

    def _choose_source(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose source identity", "",
                    "Pictures (*.jpg *.jpeg *.png *.webp *.bmp)")
        if not name:
            return
        try:
            self.source = load_source(Path(name))
            self.source_path = Path(name)
            self.source_caption.setText("Selected: " + self.source_path.name)
            self._set_status("Source loaded. Face identity will be prepared once on Start.")
        except Exception as exc:
            QMessageBox.warning(self, "Cannot read source", str(exc))
        self._refresh_controls()

    def _choose_models(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Folder containing four original ONNX models",
                                                 str(self.model_folder.parent))
        if folder:
            self.model_folder = Path(folder)
            self.settings.setValue("models", folder)
            self._refresh_controls()

    def _set_status(self, message: str) -> None:
        self.status_line.setText(message)

    def _open_camera(self) -> None:
        self.camera_available = False
        self._refresh_controls()
        camera = CameraThread(self._camera_idx, self._submit_frame, self.mirror.isChecked())
        self.camera = camera
        camera.picture.connect(self._show_camera)
        camera.status.connect(self._set_status)
        camera.availability.connect(self._camera_status)
        camera.start()

    def _camera_status(self, ok: bool) -> None:
        self.camera_available = ok
        self.camera_rate.setText("Camera connected" if ok else "Camera unavailable")
        self._refresh_controls()

    def _submit_frame(self, frame: np.ndarray) -> None:
        processor = self.processor
        if processor is not None:
            processor.submit(frame)

    def _show_camera(self, frame: np.ndarray) -> None:
        self._latest_raw = pixmap(frame)
        self._update_view(self.raw_view, self._latest_raw)

    def _update_view(self, view: QLabel, value: QPixmap) -> None:
        view.setPixmap(value.scaled(view.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._latest_raw is not None:
            self._update_view(self.raw_view, self._latest_raw)
        if self._latest_swapped is not None:
            self._update_view(self.swapped_view, self._latest_swapped)

    def _restart_camera(self, *_args) -> None:
        self._stop_live()
        old = self.camera
        self.camera = None
        if old is not None:
            old.stop()
            old.wait(1700)
        self._latest_raw = None
        self.raw_view.setText("Connecting camera…")
        self._open_camera()

    def _flip_camera(self) -> None:
        self._camera_idx = 1 if self._camera_idx == 0 else 0
        self.flip.setText(f"CAMERA {self._camera_idx} → {1 - self._camera_idx}")
        self._restart_camera()

    def _toggle(self) -> None:
        if self.processor is not None:
            self._stop_live()
            return
        if self.source is None or not self.camera_available or not self.consent.isChecked():
            return
        processor = LiveProcessor(self.source, self.model_folder)
        self.processor = processor
        processor.status.connect(self._set_status)
        processor.result.connect(self._show_swapped)
        processor.error.connect(self._processor_error)
        processor.finished.connect(self._processor_finished)
        self.swapped_view.setText("Preparing models and source identity…")
        self.swap_rate.setText("Warming AI model · please wait")
        self._refresh_controls()
        processor.start()

    def _show_swapped(self, frame: np.ndarray, ms: int, count: int) -> None:
        if self.processor is None:
            return
        self._latest_swapped = pixmap(frame)
        self._update_view(self.swapped_view, self._latest_swapped)
        self.swap_rate.setText(
            f"Processed frames: {count}  •  {ms} ms  •  {1000 / max(1, ms):.2f} swapped FPS"
        )
        self._set_status("Displaying the latest processed frame, which may lag behind the camera.")

    def _processor_error(self, message: str) -> None:
        self._set_status(message)

    def _processor_finished(self) -> None:
        self.processor = None
        self._refresh_controls()
        self._set_status("Neural worker stopped. Camera preview remains live.")
        self.swap_rate.setText("Not running  •  actual neural FPS: —")

    def _stop_live(self) -> None:
        if self.processor is not None:
            self.processor.stop()
            self._set_status("Stopping neural inference…")
            self.start_button.setEnabled(False)
        self._latest_swapped = None
        self.swapped_view.clear()
        self.swapped_view.setText("Live swap stopped")

    def closeEvent(self, event) -> None:
        self._stop_live()
        if self.camera is not None:
            self.camera.stop()
            self.camera.wait(1500)
        super().closeEvent(event)


def self_test() -> int:
    print("FaceWeave Windows dependency self-test")
    print("Python:", sys.version.split()[0], "Windows:", sys.platform == "win32")
    print("NumPy:", np.__version__)
    print("OpenCV:", cv2.__version__)
    import onnxruntime as ort
    print("ONNX Runtime:", ort.__version__, "Providers:", ort.get_available_providers())
    print("Qt:", QImage.Format.Format_RGB888.name)
    print("Model names:", ", ".join(MODELS))
    assert "CPUExecutionProvider" in ort.get_available_providers()
    dummy = np.zeros((96, 128, 3), dtype=np.uint8)
    assert pixmap_testable(dummy)
    print("SELF-TEST PASS")
    return 0


def pixmap_testable(dummy: np.ndarray) -> bool:
    rgb = cv2.cvtColor(dummy, cv2.COLOR_BGR2RGB)
    return rgb.shape == dummy.shape and rgb.dtype == np.uint8


def main() -> int:
    parser = argparse.ArgumentParser(description="FaceWeave — live webcam face swapping only")
    parser.add_argument("--self-test", action="store_true", help="verify packaged runtime without webcam")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if sys.platform == "win32":
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("FaceWeave")
    app.setOrganizationName("Phala Digital")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

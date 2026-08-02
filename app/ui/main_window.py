"""Main FacePilot window and Phase 1 preview controls."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class PreviewCanvas(QWidget):
    """Render a user-supplied image with controlled movement and scaling."""

    WATERMARK = "AUTHORIZED TEST SIMULATION"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 420)
        self.setObjectName("previewCanvas")

        self._image = QImage()
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self._flipped = False

    @property
    def has_image(self) -> bool:
        return not self._image.isNull()

    def load_image(self, path: str) -> bool:
        image = QImage(path)
        if image.isNull():
            return False
        self._image = image
        self.reset_view()
        return True

    def set_zoom(self, value: float) -> None:
        self._zoom = max(0.25, min(value, 4.0))
        self.update()

    def move_image(self, dx: int, dy: int) -> None:
        self._offset += QPoint(dx, dy)
        self.update()

    def toggle_flip(self) -> None:
        self._flipped = not self._flipped
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self._flipped = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#07130f"))

        frame = self.rect().adjusted(18, 18, -18, -18)
        painter.setPen(QPen(QColor("#23443a"), 2))
        painter.drawRoundedRect(QRectF(frame), 12, 12)

        if self.has_image:
            pixmap = QPixmap.fromImage(self._image)
            if self._flipped:
                pixmap = pixmap.transformed(
                    __import__("PySide6.QtGui", fromlist=["QTransform"]).QTransform().scale(-1, 1)
                )

            available = frame.size()
            fitted = pixmap.scaled(
                available,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            target_size = fitted.size() * self._zoom
            scaled = pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = frame.center().x() - scaled.width() // 2 + self._offset.x()
            y = frame.center().y() - scaled.height() // 2 + self._offset.y()
            painter.save()
            painter.setClipRect(frame)
            painter.drawPixmap(x, y, scaled)
            painter.restore()
        else:
            painter.setPen(QColor("#88a39a"))
            painter.setFont(QFont("Arial", 16, QFont.Weight.DemiBold))
            painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, "Load a portrait to begin")

        watermark_rect = frame.adjusted(14, 14, -14, -14)
        painter.setPen(QColor(255, 255, 255, 175))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(
            watermark_rect,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            self.WATERMARK,
        )


class MainWindow(QMainWindow):
    """FacePilot Phase 1 application shell."""

    MOVE_STEP = 20

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FacePilot — Authorized Liveness Lab")
        self.resize(1180, 760)

        self.canvas = PreviewCanvas()
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 400)
        self.zoom_slider.setValue(100)
        self.zoom_value = QLabel("100%")
        self.file_label = QLabel("No image loaded")

        self._build_ui()
        self._apply_styles()
        self._build_menu()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        heading = QLabel("FACEPILOT")
        heading.setObjectName("heading")
        subheading = QLabel(
            "Controlled visual simulation for systems you own or are authorized to assess"
        )
        subheading.setObjectName("subheading")
        outer.addWidget(heading)
        outer.addWidget(subheading)

        body = QHBoxLayout()
        body.setSpacing(16)
        outer.addLayout(body, 1)

        body.addWidget(self.canvas, 1)
        controls = self._create_controls()
        body.addWidget(controls)

        status = QStatusBar()
        status.showMessage("Local-only Phase 1 preview ready")
        self.setStatusBar(status)

    def _create_controls(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("controlPanel")
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("MANUAL TEST CONTROLS")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        load_button = QPushButton("Load portrait")
        load_button.clicked.connect(self.open_image)
        layout.addWidget(load_button)
        self.file_label.setWordWrap(True)
        self.file_label.setObjectName("fileLabel")
        layout.addWidget(self.file_label)

        movement_label = QLabel("Frame movement")
        movement_label.setObjectName("sectionLabel")
        layout.addWidget(movement_label)

        movement = QGridLayout()
        up = QPushButton("↑")
        left = QPushButton("←")
        reset = QPushButton("Reset")
        right = QPushButton("→")
        down = QPushButton("↓")
        up.clicked.connect(lambda: self.canvas.move_image(0, -self.MOVE_STEP))
        down.clicked.connect(lambda: self.canvas.move_image(0, self.MOVE_STEP))
        left.clicked.connect(lambda: self.canvas.move_image(-self.MOVE_STEP, 0))
        right.clicked.connect(lambda: self.canvas.move_image(self.MOVE_STEP, 0))
        reset.clicked.connect(self.reset_scene)
        movement.addWidget(up, 0, 1)
        movement.addWidget(left, 1, 0)
        movement.addWidget(reset, 1, 1)
        movement.addWidget(right, 1, 2)
        movement.addWidget(down, 2, 1)
        layout.addLayout(movement)

        zoom_label = QLabel("Zoom")
        zoom_label.setObjectName("sectionLabel")
        layout.addWidget(zoom_label)
        zoom_row = QHBoxLayout()
        zoom_row.addWidget(self.zoom_slider, 1)
        zoom_row.addWidget(self.zoom_value)
        layout.addLayout(zoom_row)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)

        flip_button = QPushButton("Flip horizontally")
        flip_button.clicked.connect(self.canvas.toggle_flip)
        layout.addWidget(flip_button)

        notice = QLabel(
            "Test output stays inside FacePilot. No virtual camera or third-party injection is enabled."
        )
        notice.setWordWrap(True)
        notice.setObjectName("notice")
        layout.addStretch(1)
        layout.addWidget(notice)
        return panel

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        open_action = QAction("Open portrait…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a portrait",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        if not self.canvas.load_image(path):
            QMessageBox.critical(self, "Unable to load image", "The selected image could not be read.")
            return
        self.file_label.setText(Path(path).name)
        self.zoom_slider.setValue(100)
        self.statusBar().showMessage(f"Loaded {Path(path).name}")

    def reset_scene(self) -> None:
        self.canvas.reset_view()
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(100)
        self.zoom_slider.blockSignals(False)
        self.zoom_value.setText("100%")
        self.statusBar().showMessage("Preview reset")

    def _on_zoom_changed(self, value: int) -> None:
        self.canvas.set_zoom(value / 100)
        self.zoom_value.setText(f"{value}%")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0b1713;
                color: #e8f1ed;
                font-family: Arial;
            }
            QLabel#heading {
                color: #39d98a;
                font-size: 28px;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#subheading, QLabel#fileLabel {
                color: #91aaa0;
            }
            QFrame#controlPanel {
                background: #10231c;
                border: 1px solid #285142;
                border-radius: 12px;
            }
            QLabel#panelTitle, QLabel#sectionLabel {
                color: #bcebd5;
                font-weight: 700;
            }
            QLabel#notice {
                color: #7f9b90;
                background: #0c1b16;
                border: 1px solid #203e33;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                background: #17382c;
                color: #e9fff5;
                border: 1px solid #2b684f;
                border-radius: 7px;
                padding: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1f4c3b;
                border-color: #39d98a;
            }
            QPushButton:pressed {
                background: #102b21;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #23443a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #39d98a;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QMenuBar, QMenu, QStatusBar {
                background: #0d1d18;
                color: #dce9e3;
            }
            """
        )

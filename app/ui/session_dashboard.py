"""Interactive session dashboard for authorized FacePilot test runs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.challenges.engine import ChallengeEngine, default_sequence
from app.core.session import SessionStatus, SignalResult, TestSession
from app.reports.exporter import ReportExporter
from app.storage.paths import session_history_root
from app.storage.session_store import SessionStore


class SessionDashboard(QFrame):
    """Run a guided challenge sequence and export its local report."""

    session_changed = Signal(object)
    session_saved = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sessionDashboard")
        self._session: TestSession | None = None
        self._engine: ChallengeEngine | None = None
        self._elapsed_seconds = 0
        self._saved_session_ids: set[str] = set()
        self._store = SessionStore(session_history_root())

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("sessionStatus")
        self.elapsed_label = QLabel("00:00")
        self.challenge_label = QLabel("Load a portrait, then start an authorized test session.")
        self.challenge_label.setWordWrap(True)
        self.challenge_label.setObjectName("activeChallenge")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.queue = QListWidget()
        self.queue.setMinimumHeight(150)

        self.start_button = QPushButton("Start test session")
        self.pass_button = QPushButton("Mark challenge passed")
        self.fail_button = QPushButton("Mark challenge failed")
        self.cancel_button = QPushButton("Cancel session")
        self.export_button = QPushButton("Export reports")

        self.start_button.clicked.connect(self.start_session)
        self.pass_button.clicked.connect(lambda: self.submit_current(True))
        self.fail_button.clicked.connect(lambda: self.submit_current(False))
        self.cancel_button.clicked.connect(self.cancel_session)
        self.export_button.clicked.connect(self.export_reports)

        self._build_ui()
        self._set_running_controls(False)
        self.export_button.setEnabled(False)

    @property
    def session(self) -> TestSession | None:
        return self._session

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("AUTHORIZED TEST SESSION")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status"))
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        status_row.addWidget(QLabel("Elapsed"))
        status_row.addWidget(self.elapsed_label)
        layout.addLayout(status_row)

        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Active challenge"))
        layout.addWidget(self.challenge_label)
        layout.addWidget(QLabel("Challenge queue"))
        layout.addWidget(self.queue)

        layout.addWidget(self.start_button)
        decision_row = QHBoxLayout()
        decision_row.addWidget(self.pass_button)
        decision_row.addWidget(self.fail_button)
        layout.addLayout(decision_row)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.export_button)

        notice = QLabel(
            "Operator decisions are recorded as test annotations. Automated landmark verification "
            "will be added separately and must only be connected to authorized systems."
        )
        notice.setWordWrap(True)
        notice.setObjectName("notice")
        layout.addWidget(notice)

    def start_session(self) -> None:
        input_name = self.property("input_name") or "local-test-input"
        self._session = TestSession(input_name=str(input_name))
        self._session.start()
        self._engine = ChallengeEngine(default_sequence())
        self._elapsed_seconds = 0
        self.elapsed_label.setText("00:00")
        self.status_label.setText("RUNNING")
        self.export_button.setEnabled(False)
        self.queue.clear()
        for challenge in self._engine.challenges:
            self.queue.addItem(f"○ {challenge.instruction}")
        self._set_running_controls(True)
        self._timer.start()
        self._start_current_challenge()
        self.session_changed.emit(self._session)

    def _start_current_challenge(self) -> None:
        if self._engine is None:
            return
        if self._engine.finished:
            self._complete_session()
            return
        challenge = self._engine.start_current()
        self.challenge_label.setText(challenge.instruction)
        self.queue.setCurrentRow(self._engine.current_index)
        self._update_progress()

    def submit_current(self, passed: bool) -> None:
        if self._session is None or self._engine is None:
            return
        try:
            result = self._engine.submit(
                passed=passed,
                confidence=1.0 if passed else 0.0,
                note="Operator-confirmed result",
            )
        except RuntimeError as exc:
            QMessageBox.warning(self, "Challenge unavailable", str(exc))
            return

        anomaly_score = 0.0 if result.passed else 1.0
        self._session.add_signal(
            SignalResult(
                name=f"challenge:{result.challenge.kind.value}",
                score=anomaly_score,
                detail=(
                    f"{'Passed' if result.passed else 'Failed'} in "
                    f"{result.response_seconds:.2f}s; confidence {result.confidence:.0%}"
                ),
            )
        )
        row = self._engine.current_index - 1
        marker = "✓" if result.passed else "✕"
        item = self.queue.item(row)
        if item is not None:
            item.setText(f"{marker} {result.challenge.instruction}")
        self._start_current_challenge()
        self.session_changed.emit(self._session)

    def cancel_session(self) -> None:
        if self._session is None:
            return
        self._session.cancel()
        self._timer.stop()
        self.status_label.setText("CANCELLED")
        self.challenge_label.setText("Session cancelled by operator.")
        self._set_running_controls(False)
        self.export_button.setEnabled(True)
        self._persist_session()
        self.session_changed.emit(self._session)

    def _complete_session(self) -> None:
        if self._session is None:
            return
        self._session.complete()
        self._timer.stop()
        self.status_label.setText("COMPLETED")
        self.challenge_label.setText(
            f"Sequence complete — {self._session.classification()} "
            f"({self._session.risk_score():.0%} anomaly score)."
        )
        self.progress.setValue(100)
        self._set_running_controls(False)
        self.export_button.setEnabled(True)
        self._persist_session()
        self.session_changed.emit(self._session)

    def _persist_session(self) -> None:
        if self._session is None or self._session.id in self._saved_session_ids:
            return
        try:
            self._store.save(self._session.to_dict())
        except OSError as exc:
            QMessageBox.warning(
                self,
                "History save failed",
                f"The session finished, but its local history file could not be saved:\n{exc}",
            )
            return
        self._saved_session_ids.add(self._session.id)
        self.session_saved.emit(self._session)

    def export_reports(self) -> None:
        if self._session is None or self._session.status is SessionStatus.RUNNING:
            return
        directory = QFileDialog.getExistingDirectory(self, "Choose report folder")
        if not directory:
            return
        exporter = ReportExporter(Path(directory))
        paths = [
            exporter.json_report(self._session),
            exporter.csv_report(self._session),
            exporter.html_report(self._session),
        ]
        QMessageBox.information(
            self,
            "Reports exported",
            "Created:\n" + "\n".join(path.name for path in paths),
        )

    def _tick(self) -> None:
        self._elapsed_seconds += 1
        minutes, seconds = divmod(self._elapsed_seconds, 60)
        self.elapsed_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _update_progress(self) -> None:
        if self._engine is None or not self._engine.challenges:
            self.progress.setValue(0)
            return
        self.progress.setValue(
            round(100 * len(self._engine.results) / len(self._engine.challenges))
        )

    def _set_running_controls(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.pass_button.setEnabled(running)
        self.fail_button.setEnabled(running)
        self.cancel_button.setEnabled(running)

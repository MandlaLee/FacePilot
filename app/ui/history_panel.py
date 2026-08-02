"""Session history browser for locally stored FacePilot reports."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.storage.paths import session_history_root
from app.storage.session_store import SessionStore


class HistoryPanel(QFrame):
    """Browse and delete completed local sessions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self.store = SessionStore(session_history_root())
        self._payloads: list[dict[str, object]] = []

        self.list_widget = QListWidget()
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.refresh_button = QPushButton("Refresh history")
        self.delete_button = QPushButton("Delete selected")
        self.purge_button = QPushButton("Delete sessions older than 30 days")

        self.refresh_button.clicked.connect(self.refresh)
        self.delete_button.clicked.connect(self.delete_selected)
        self.purge_button.clicked.connect(self.purge_old)
        self.list_widget.currentRowChanged.connect(self.show_details)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("LOCAL SESSION HISTORY")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        content = QHBoxLayout()
        content.addWidget(self.list_widget, 1)
        content.addWidget(self.details, 2)
        layout.addLayout(content, 1)

        controls = QHBoxLayout()
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.delete_button)
        controls.addWidget(self.purge_button)
        layout.addLayout(controls)

        note = QLabel("History remains on this device and can be deleted at any time.")
        note.setObjectName("notice")
        layout.addWidget(note)

    def refresh(self) -> None:
        self._payloads = self.store.list_sessions()
        self.list_widget.clear()
        for payload in self._payloads:
            session_id = str(payload.get("id", "unknown"))[:8]
            status = str(payload.get("status", "unknown"))
            created = str(payload.get("created_at", ""))[:19].replace("T", " ")
            classification = str(payload.get("classification", "unclassified"))
            self.list_widget.addItem(
                f"{created}  •  {status.upper()}  •  {classification}  •  {session_id}"
            )
        if self._payloads:
            self.list_widget.setCurrentRow(0)
        else:
            self.details.setPlainText("No saved sessions yet.")

    def show_details(self, row: int) -> None:
        if row < 0 or row >= len(self._payloads):
            return
        payload = self._payloads[row]
        signals = payload.get("signals", [])
        lines = [
            f"Session: {payload.get('id', '')}",
            f"Status: {payload.get('status', '')}",
            f"Input: {payload.get('input_name', '')}",
            f"Created: {payload.get('created_at', '')}",
            f"Started: {payload.get('started_at', '')}",
            f"Ended: {payload.get('ended_at', '')}",
            f"Anomaly score: {float(payload.get('risk_score', 0) or 0):.0%}",
            f"Classification: {payload.get('classification', '')}",
            "",
            f"Signals recorded: {len(signals) if isinstance(signals, list) else 0}",
        ]
        if isinstance(signals, list):
            for signal in signals:
                if not isinstance(signal, dict):
                    continue
                lines.append(
                    f"• {signal.get('name', 'signal')}: "
                    f"{float(signal.get('score', 0) or 0):.0%} — {signal.get('detail', '')}"
                )
        self.details.setPlainText("\n".join(lines))

    def delete_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._payloads):
            return
        session_id = str(self._payloads[row].get("id", ""))
        answer = QMessageBox.question(
            self,
            "Delete session",
            f"Delete local session {session_id[:8]} permanently?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.store.delete(session_id)
            self.refresh()

    def purge_old(self) -> None:
        deleted = self.store.purge_older_than(30)
        self.refresh()
        QMessageBox.information(self, "Retention cleanup", f"Deleted {deleted} old session(s).")

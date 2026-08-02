"""Persistent authorization consent for FacePilot."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


CONSENT_VERSION = "1"
CONSENT_KEY = "authorization/consent_version"


class AuthorizationDialog(QDialog):
    """Require an explicit acknowledgement before FacePilot can start."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FacePilot Authorization")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        title = QLabel("AUTHORIZED TESTING ONLY")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #39d98a;")
        layout.addWidget(title)

        message = QLabel(
            "FacePilot is a controlled liveness-testing laboratory. Use it only on "
            "systems you own or are explicitly authorized to assess. It must not be "
            "used to bypass identity verification, KYC, age checks, access controls, "
            "or third-party security systems."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        self.confirmation = QCheckBox(
            "I confirm that I will use FacePilot only within an authorized test scope."
        )
        self.confirmation.setWordWrap(True)
        layout.addWidget(self.confirmation)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Accept | QDialogButtonBox.StandardButton.Cancel
        )
        self.accept_button = buttons.button(QDialogButtonBox.StandardButton.Accept)
        self.accept_button.setText("Accept and continue")
        self.accept_button.setEnabled(False)
        self.confirmation.toggled.connect(self.accept_button.setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.confirmation.isChecked():
            return
        QSettings().setValue(CONSENT_KEY, CONSENT_VERSION)
        super().accept()


def has_current_consent() -> bool:
    """Return whether the current authorization notice has been accepted."""
    return QSettings().value(CONSENT_KEY, "") == CONSENT_VERSION

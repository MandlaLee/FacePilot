"""FacePilot application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.security.consent import AuthorizationDialog, has_current_consent
from app.ui.main_window import MainWindow


def main() -> int:
    """Start the FacePilot desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("FacePilot")
    app.setOrganizationName("FacePilot")
    app.setOrganizationDomain("facepilot.local")

    if not has_current_consent():
        dialog = AuthorizationDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

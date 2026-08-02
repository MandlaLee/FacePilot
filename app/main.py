"""FacePilot application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    """Start the FacePilot desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("FacePilot")
    app.setOrganizationName("FacePilot")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

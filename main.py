#!/usr/bin/env python3
"""La Mia Scribe — Local AI Transcription & Caption Studio.

By Tech Inclusion Pro (Dr. Rocco G. Catrone, CPACC).
Privacy-first, locally-run transcription and caption studio.
All AI runs on-device — no data leaves the machine.
"""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.login_window import LoginWindow
from app.main_window import MainWindow
from app.accessibility_panel import load_initial_settings, apply_accessibility_settings


class AppController:
    """Controls the login -> dashboard flow and logout cycling."""

    def __init__(self, app: QApplication):
        self.app = app
        self.login_window = None
        self.main_window = None
        self._first_launch = True

    def start(self):
        self._show_login()

    def _show_login(self):
        # Close main window if open
        if self.main_window:
            self.main_window.close()
            self.main_window = None

        auto = self._first_launch
        self._first_launch = False
        self.login_window = LoginWindow(auto_login=auto)
        self.login_window.login_success.connect(self._on_login_success)
        self.login_window.show()

    def _on_login_success(self, display_name: str):
        if self.login_window:
            self.login_window.close()
            self.login_window = None

        self.main_window = MainWindow(display_name=display_name)
        self.main_window.logout_requested.connect(self._show_login)
        self.main_window.show()


def main():
    # Filter out macOS -psn_* argument passed when launched from .app bundle
    argv = [a for a in sys.argv if not a.startswith("-psn")]
    app = QApplication(argv)
    app.setApplicationName("La Mia Scribe")
    app.setOrganizationName("TechInclusionPro")
    app.setOrganizationDomain("techinclusion.pro")

    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Load and apply accessibility/theme settings
    a11y_settings = load_initial_settings()
    apply_accessibility_settings(a11y_settings)

    controller = AppController(app)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

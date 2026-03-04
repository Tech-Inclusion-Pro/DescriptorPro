#!/usr/bin/env python3
"""Wrapper that catches and logs any startup errors for the .app bundle."""

import sys
import os
import traceback

LOG_PATH = "/tmp/lamiascribe.log"

def main():
    try:
        # Ensure we're in the right directory
        app_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(app_dir)
        sys.path.insert(0, app_dir)

        with open(LOG_PATH, "a") as f:
            f.write(f"Python {sys.version}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"CWD: {os.getcwd()}\n")
            f.write(f"argv: {sys.argv}\n")
            f.flush()

        # Filter macOS -psn_* args
        sys.argv = [a for a in sys.argv if not a.startswith("-psn")]

        # Import and run the real app
        with open(LOG_PATH, "a") as f:
            f.write("Importing PyQt6...\n")
            f.flush()

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon

        with open(LOG_PATH, "a") as f:
            f.write("PyQt6 imported OK\n")
            f.write("Creating QApplication...\n")
            f.flush()

        app = QApplication(sys.argv)
        app.setApplicationName("La Mia Scribe")
        app.setOrganizationName("TechInclusionPro")
        app.setOrganizationDomain("techinclusion.pro")

        # Set application icon
        icon_path = os.path.join(app_dir, "assets", "logo.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        with open(LOG_PATH, "a") as f:
            f.write("Importing app modules...\n")
            f.flush()

        from app.login_window import LoginWindow
        from app.main_window import MainWindow
        from app.accessibility_panel import load_initial_settings, apply_accessibility_settings

        # Load and apply accessibility/theme settings
        a11y_settings = load_initial_settings()
        apply_accessibility_settings(a11y_settings)

        with open(LOG_PATH, "a") as f:
            f.write("All imports OK, launching UI...\n")
            f.flush()

        # App controller inline
        state = {"login": None, "main": None, "first_launch": True}

        def show_login():
            if state["main"]:
                state["main"].close()
                state["main"] = None
            auto = state["first_launch"]
            state["first_launch"] = False
            state["login"] = LoginWindow(auto_login=auto)
            state["login"].login_success.connect(on_login_success)
            state["login"].show()

        def on_login_success(display_name):
            if state["login"]:
                state["login"].close()
                state["login"] = None
            state["main"] = MainWindow(display_name=display_name)
            state["main"].logout_requested.connect(show_login)
            state["main"].show()

        show_login()

        # Activate the app so it appears in the foreground when launched from .app bundle
        try:
            from AppKit import NSApplication, NSApp
            NSApplication.sharedApplication()
            NSApp.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular
            NSApp.activateIgnoringOtherApps_(True)
        except ImportError:
            pass

        # Ensure the login window is raised and focused
        if state["login"]:
            state["login"].raise_()
            state["login"].activateWindow()

        with open(LOG_PATH, "a") as f:
            f.write("Entering event loop...\n")
            f.flush()

        sys.exit(app.exec())

    except Exception:
        with open(LOG_PATH, "a") as f:
            f.write("FATAL ERROR:\n")
            traceback.print_exc(file=f)
            f.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()

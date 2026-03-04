"""App preferences dialog using QSettings for persistence."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QCheckBox
)
from PyQt6.QtCore import QSettings


SETTINGS_ORG = "TechInclusionPro"
SETTINGS_APP = "LaMiaScribe"


def get_settings() -> QSettings:
    return QSettings(SETTINGS_ORG, SETTINGS_APP)


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("La Mia Scribe — Settings")
        self.setMinimumWidth(400)
        self.setAccessibleName("Application settings dialog")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Settings are automatically saved when you close the application.\n"
            "Changes here are applied immediately."
        )
        info_label.setWordWrap(True)
        info_label.setAccessibleName("Settings information")
        layout.addWidget(info_label)

        # Default Whisper settings group
        whisper_group = QGroupBox("Default Whisper Settings")
        whisper_group.setAccessibleName("Default Whisper settings")
        wl = QVBoxLayout(whisper_group)

        lbl = QLabel("These defaults are loaded when the application starts.")
        lbl.setWordWrap(True)
        wl.addWidget(lbl)

        layout.addWidget(whisper_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setMinimumSize(44, 44)
        close_btn.setAccessibleName("Close settings dialog")
        close_btn.setToolTip("Close this dialog")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

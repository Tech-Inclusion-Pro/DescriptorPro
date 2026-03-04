"""Progress bar + collapsible status log widget."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton,
    QTextEdit
)
from PyQt6.QtCore import Qt

from app.accessibility_panel import announce
from core.i18n import tr


class ProgressWidget(QWidget):
    """Progress bar with step label, time estimate, and collapsible log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAccessibleName("Transcription progress")
        self.progress_bar.setAccessibleDescription("Shows the progress of the current transcription task")
        self.progress_bar.setToolTip("Transcription progress")
        layout.addWidget(self.progress_bar)

        self.step_label = QLabel("")
        self.step_label.setObjectName("stepLabel")
        self.step_label.setAccessibleName("Current processing step")
        self.step_label.setToolTip("Current processing step")
        layout.addWidget(self.step_label)

        self.time_label = QLabel("")
        self.time_label.setObjectName("stepLabel")
        self.time_label.setAccessibleName("Estimated time remaining")
        self.time_label.setToolTip("Estimated time remaining")
        layout.addWidget(self.time_label)

        self.log_toggle = QPushButton(tr("show_log"))
        self.log_toggle.setObjectName("logToggleButton")
        self.log_toggle.setMinimumSize(44, 44)
        self.log_toggle.setAccessibleName(tr("show_log"))
        self.log_toggle.setToolTip(tr("show_log"))
        self.log_toggle.clicked.connect(self._toggle_log)
        layout.addWidget(self.log_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("logPanel")
        self.log_panel.setReadOnly(True)
        self.log_panel.setMaximumHeight(150)
        self.log_panel.setVisible(False)
        self.log_panel.setAccessibleName("Processing log")
        self.log_panel.setAccessibleDescription("Detailed log of transcription processing steps")
        self.log_panel.setToolTip("Detailed processing log")
        layout.addWidget(self.log_panel)

    def _toggle_log(self):
        visible = not self.log_panel.isVisible()
        self.log_panel.setVisible(visible)
        self.log_toggle.setText(tr("hide_log") if visible else tr("show_log"))

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)
        if value in (0, 25, 50, 75, 100):
            announce(self.progress_bar, f"Transcription progress: {value} percent")

    def set_step(self, text: str):
        self.step_label.setText(text)
        announce(self.step_label, text)

    def set_time_remaining(self, text: str):
        self.time_label.setText(text)

    def append_log(self, text: str):
        self.log_panel.append(text)
        # Auto-show log panel on errors so the user sees what went wrong
        if "error" in text.lower() and not self.log_panel.isVisible():
            self._toggle_log()
        self.log_panel.verticalScrollBar().setValue(
            self.log_panel.verticalScrollBar().maximum()
        )

    def retranslateUi(self):
        """Refresh all translatable text."""
        if self.log_panel.isVisible():
            self.log_toggle.setText(tr("hide_log"))
        else:
            self.log_toggle.setText(tr("show_log"))

    def reset(self):
        self.progress_bar.setValue(0)
        self.step_label.setText("")
        self.time_label.setText("")
        self.log_panel.clear()

"""Export format checkboxes + Save button widget."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QLabel, QRadioButton, QButtonGroup, QFileDialog, QMessageBox,
    QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt

from core.i18n import tr


class ExportPanel(QWidget):
    """Panel with export format checkboxes, language selection, and save/copy buttons."""

    save_requested = pyqtSignal(str, list, str)  # directory, formats, language

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("exportPanel")
        self._has_spanish = False
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        self._title = QLabel(tr("export_formats"))
        self._title.setObjectName("exportPanelTitle")
        self._title.setAccessibleName(tr("export_formats"))
        layout.addWidget(self._title)

        # Format checkboxes
        formats_layout = QHBoxLayout()
        self.srt_cb = QCheckBox("SRT")
        self.srt_cb.setChecked(True)
        self.srt_cb.setAccessibleName("Export SRT format")
        self.srt_cb.setToolTip("Export as SubRip subtitle file")
        formats_layout.addWidget(self.srt_cb)

        self.vtt_cb = QCheckBox("VTT")
        self.vtt_cb.setChecked(True)
        self.vtt_cb.setAccessibleName("Export VTT format")
        self.vtt_cb.setToolTip("Export as WebVTT subtitle file")
        formats_layout.addWidget(self.vtt_cb)

        self.pdf_cb = QCheckBox("PDF")
        self.pdf_cb.setChecked(True)
        self.pdf_cb.setAccessibleName("Export PDF format")
        self.pdf_cb.setToolTip("Export as branded PDF document")
        formats_layout.addWidget(self.pdf_cb)

        self.docx_cb = QCheckBox("DOCX")
        self.docx_cb.setChecked(True)
        self.docx_cb.setAccessibleName("Export DOCX format")
        self.docx_cb.setToolTip("Export as accessible Word document")
        formats_layout.addWidget(self.docx_cb)

        self.txt_cb = QCheckBox("TXT")
        self.txt_cb.setChecked(True)
        self.txt_cb.setAccessibleName("Export TXT format")
        self.txt_cb.setToolTip("Export as plain text file")
        formats_layout.addWidget(self.txt_cb)

        formats_layout.addStretch()
        layout.addLayout(formats_layout)

        # Language radio buttons (hidden until Spanish available)
        self.lang_widget = QWidget()
        lang_layout = QHBoxLayout(self.lang_widget)
        lang_layout.setContentsMargins(0, 4, 0, 4)

        self._lang_label = QLabel(tr("export_lang"))
        self._lang_label.setAccessibleName(tr("export_lang"))
        lang_layout.addWidget(self._lang_label)

        self.lang_group = QButtonGroup(self)
        self.english_radio = QRadioButton(tr("english_only"))
        self.english_radio.setChecked(True)
        self.english_radio.setAccessibleName(tr("english_only"))
        self.lang_group.addButton(self.english_radio)
        lang_layout.addWidget(self.english_radio)

        self.spanish_radio = QRadioButton(tr("spanish_only"))
        self.spanish_radio.setAccessibleName(tr("spanish_only"))
        self.lang_group.addButton(self.spanish_radio)
        lang_layout.addWidget(self.spanish_radio)

        self.both_radio = QRadioButton(tr("both_lang"))
        self.both_radio.setAccessibleName(tr("both_lang"))
        self.lang_group.addButton(self.both_radio)
        lang_layout.addWidget(self.both_radio)

        lang_layout.addStretch()
        self.lang_widget.setVisible(False)
        layout.addWidget(self.lang_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton(tr("save_selected"))
        self.save_btn.setMinimumSize(44, 44)
        self.save_btn.setAccessibleName(tr("save_selected"))
        self.save_btn.setToolTip("Ctrl+S")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        self.copy_btn = QPushButton(tr("copy_transcript"))
        self.copy_btn.setMinimumSize(44, 44)
        self.copy_btn.setAccessibleName(tr("copy_transcript"))
        self.copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(self.copy_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def show_panel(self, has_spanish: bool = False):
        self._has_spanish = has_spanish
        self.lang_widget.setVisible(has_spanish)
        self.setVisible(True)

    def hide_panel(self):
        self.setVisible(False)

    def _get_selected_formats(self) -> list[str]:
        formats = []
        if self.srt_cb.isChecked():
            formats.append("srt")
        if self.vtt_cb.isChecked():
            formats.append("vtt")
        if self.pdf_cb.isChecked():
            formats.append("pdf")
        if self.docx_cb.isChecked():
            formats.append("docx")
        if self.txt_cb.isChecked():
            formats.append("txt")
        return formats

    def _get_language_choice(self) -> str:
        if self.spanish_radio.isChecked():
            return "spanish"
        elif self.both_radio.isChecked():
            return "both"
        return "english"

    def _on_save(self):
        formats = self._get_selected_formats()
        if not formats:
            QMessageBox.information(
                self, tr("no_formats"),
                tr("select_one_format")
            )
            return

        directory = QFileDialog.getExistingDirectory(
            self, tr("select_export_dir")
        )
        if directory:
            lang = self._get_language_choice()
            self.save_requested.emit(directory, formats, lang)

    def _on_copy(self):
        clipboard = QApplication.clipboard()
        if clipboard and self.parent():
            # The main window will connect this to get the text
            pass

    def get_format_states(self) -> dict:
        """Return dict of format checkbox states for settings persistence."""
        return {
            "srt": self.srt_cb.isChecked(),
            "vtt": self.vtt_cb.isChecked(),
            "pdf": self.pdf_cb.isChecked(),
            "docx": self.docx_cb.isChecked(),
            "txt": self.txt_cb.isChecked(),
        }

    def retranslateUi(self):
        """Refresh all translatable text."""
        self._title.setText(tr("export_formats"))
        self._lang_label.setText(tr("export_lang"))
        self.english_radio.setText(tr("english_only"))
        self.spanish_radio.setText(tr("spanish_only"))
        self.both_radio.setText(tr("both_lang"))
        self.save_btn.setText(tr("save_selected"))
        self.copy_btn.setText(tr("copy_transcript"))

    def set_format_states(self, states: dict):
        """Restore format checkbox states from settings."""
        if "srt" in states:
            self.srt_cb.setChecked(states["srt"])
        if "vtt" in states:
            self.vtt_cb.setChecked(states["vtt"])
        if "pdf" in states:
            self.pdf_cb.setChecked(states["pdf"])
        if "docx" in states:
            self.docx_cb.setChecked(states["docx"])
        if "txt" in states:
            self.txt_cb.setChecked(states["txt"])

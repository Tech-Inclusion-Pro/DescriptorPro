"""Controls sidebar widget — file input, Whisper config, Ollama options, Transcribe button."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QGroupBox, QFileDialog,
    QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from app.accessibility_panel import announce
from core.i18n import tr, available_languages, whisper_language_code


ACCEPTED_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv",
    ".mp3", ".wav", ".m4a", ".ogg"
}

ACCEPTED_FILTER = (
    "Media Files (*.mp4 *.mov *.avi *.mkv *.mp3 *.wav *.m4a *.ogg);;"
    "Video Files (*.mp4 *.mov *.avi *.mkv);;"
    "Audio Files (*.mp3 *.wav *.m4a *.ogg);;"
    "All Files (*)"
)


class DropZone(QLabel):
    """Drag-and-drop zone for media files."""

    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setText("Drag & drop media file here\nor use Browse below")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setWordWrap(True)
        self.setAccessibleName("File drop zone")
        self.setAccessibleDescription("Drag and drop a media file here to load it for transcription")
        self.setToolTip("Drop a media file here (MP4, MOV, AVI, MKV, MP3, WAV, M4A, OGG)")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in ACCEPTED_EXTENSIONS:
                event.acceptProposedAction()
                self.setProperty("dragActive", True)
                self.style().unpolish(self)
                self.style().polish(self)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in ACCEPTED_EXTENSIONS:
                event.acceptProposedAction()
                self.file_dropped.emit(path)
                return
        event.ignore()


class LeftPanel(QWidget):
    """Left sidebar with all input controls."""

    transcribe_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    file_loaded = pyqtSignal(str)  # emits file path
    youtube_requested = pyqtSignal(str)  # emits URL
    clear_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("leftPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(380)
        self._is_processing = False
        self._loaded_file = None
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ---- File / URL Input Section ----
        self._file_group = QGroupBox(tr("file_url_input"))
        self._file_group.setAccessibleName(tr("file_url_input"))
        file_layout = QVBoxLayout(self._file_group)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        file_layout.addWidget(self.drop_zone)

        self._browse_label = QLabel(tr("local_file"))
        self._browse_label.setAccessibleName(tr("local_file"))
        file_layout.addWidget(self._browse_label)

        self.browse_btn = QPushButton(tr("browse_file"))
        self.browse_btn.setMinimumSize(44, 44)
        self.browse_btn.setAccessibleName(tr("browse_file"))
        self.browse_btn.setAccessibleDescription("Open file dialog to select a media file for transcription")
        self.browse_btn.setToolTip(tr("browse_file"))
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        self._yt_label = QLabel(tr("youtube_url"))
        self._yt_label.setAccessibleName(tr("youtube_url"))
        file_layout.addWidget(self._yt_label)

        yt_row = QHBoxLayout()
        self.youtube_input = QLineEdit()
        self.youtube_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self.youtube_input.setAccessibleName("YouTube URL input")
        self.youtube_input.setAccessibleDescription("Enter a YouTube video URL to download and transcribe")
        self.youtube_input.setToolTip("Paste a YouTube video URL here")
        yt_row.addWidget(self.youtube_input)

        self.fetch_btn = QPushButton(tr("fetch"))
        self.fetch_btn.setMinimumSize(44, 44)
        self.fetch_btn.setAccessibleName(tr("fetch"))
        self.fetch_btn.setToolTip(tr("fetch"))
        self.fetch_btn.clicked.connect(self._fetch_youtube)
        yt_row.addWidget(self.fetch_btn)
        file_layout.addLayout(yt_row)

        self.file_info_label = QLabel("")
        self.file_info_label.setObjectName("fileInfoLabel")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setAccessibleName("Loaded file information")
        file_layout.addWidget(self.file_info_label)

        self.clear_btn = QPushButton(tr("clear"))
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.setMinimumSize(44, 44)
        self.clear_btn.setAccessibleName(tr("clear"))
        self.clear_btn.setToolTip(tr("clear"))
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setVisible(False)
        file_layout.addWidget(self.clear_btn)

        layout.addWidget(self._file_group)

        # ---- Whisper Settings Section ----
        self._whisper_group = QGroupBox(tr("whisper_settings"))
        self._whisper_group.setAccessibleName(tr("whisper_settings"))
        whisper_layout = QVBoxLayout(self._whisper_group)

        self._model_label = QLabel(tr("model_size"))
        whisper_layout.addWidget(self._model_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v2", "large-v3"])
        self.model_combo.setCurrentText("medium")
        self.model_combo.setAccessibleName(tr("model_size"))
        self.model_combo.setToolTip(tr("model_size"))
        whisper_layout.addWidget(self.model_combo)

        self._lang_label = QLabel(tr("language"))
        whisper_layout.addWidget(self._lang_label)
        self.language_combo = QComboBox()
        self.language_combo.addItem(tr("auto_detect"), "auto")
        for code, display in available_languages():
            self.language_combo.addItem(display, code)
        self.language_combo.setAccessibleName(tr("language"))
        self.language_combo.setToolTip(tr("language"))
        whisper_layout.addWidget(self.language_combo)

        self._device_label = QLabel(tr("device"))
        whisper_layout.addWidget(self._device_label)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        self.device_combo.setAccessibleName(tr("device"))
        self.device_combo.setToolTip(tr("device"))
        whisper_layout.addWidget(self.device_combo)

        self._compute_label = QLabel(tr("compute_type"))
        whisper_layout.addWidget(self._compute_label)
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "float16", "float32"])
        self.compute_combo.setAccessibleName(tr("compute_type"))
        self.compute_combo.setToolTip(tr("compute_type"))
        whisper_layout.addWidget(self.compute_combo)

        layout.addWidget(self._whisper_group)

        # ---- Ollama Post-Processing Section ----
        self._ollama_group = QGroupBox(tr("ollama_optional"))
        self._ollama_group.setAccessibleName(tr("ollama_optional"))
        ollama_layout = QVBoxLayout(self._ollama_group)

        self.clean_fillers_cb = QCheckBox(tr("clean_fillers"))
        self.clean_fillers_cb.setAccessibleName(tr("clean_fillers"))
        ollama_layout.addWidget(self.clean_fillers_cb)

        self.summary_cb = QCheckBox(tr("generate_summary"))
        self.summary_cb.setAccessibleName(tr("generate_summary"))
        ollama_layout.addWidget(self.summary_cb)

        self.translate_cb = QCheckBox(tr("translate_spanish"))
        self.translate_cb.setAccessibleName(tr("translate_spanish"))
        ollama_layout.addWidget(self.translate_cb)

        self.speakers_cb = QCheckBox(tr("label_speakers"))
        self.speakers_cb.setAccessibleName(tr("label_speakers"))
        ollama_layout.addWidget(self.speakers_cb)

        self._ollama_model_label = QLabel(tr("ollama_model"))
        ollama_layout.addWidget(self._ollama_model_label)
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setAccessibleName(tr("ollama_model"))
        self.ollama_model_combo.setToolTip(tr("ollama_model"))
        ollama_layout.addWidget(self.ollama_model_combo)

        self.ollama_status_label = QLabel("Ollama: Checking...")
        self.ollama_status_label.setAccessibleName("Ollama server status")
        self.ollama_status_label.setWordWrap(True)
        ollama_layout.addWidget(self.ollama_status_label)

        layout.addWidget(self._ollama_group)

        # ---- Transcribe Button ----
        self.transcribe_btn = QPushButton(tr("transcribe"))
        self.transcribe_btn.setObjectName("transcribeButton")
        self.transcribe_btn.setMinimumSize(44, 48)
        self.transcribe_btn.setAccessibleName(tr("transcribe"))
        self.transcribe_btn.setToolTip("Ctrl+T")
        self.transcribe_btn.clicked.connect(self._on_transcribe_clicked)
        layout.addWidget(self.transcribe_btn)

        layout.addStretch()

        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Media File", "", ACCEPTED_FILTER
        )
        if path:
            self._set_file(path)

    def _on_file_dropped(self, path: str):
        self._set_file(path)

    def _set_file(self, path: str):
        self._loaded_file = path
        filename = os.path.basename(path)
        self.file_info_label.setText(f"File: {filename}")
        self.clear_btn.setVisible(True)
        self.youtube_input.clear()
        self.file_loaded.emit(path)
        announce(self.file_info_label, f"File loaded: {filename}")

    def _fetch_youtube(self):
        url = self.youtube_input.text().strip()
        if url:
            self.youtube_requested.emit(url)

    def _clear(self):
        self._loaded_file = None
        self.file_info_label.setText("")
        self.youtube_input.clear()
        self.clear_btn.setVisible(False)
        self.clear_requested.emit()

    def _on_transcribe_clicked(self):
        if self._is_processing:
            self.cancel_requested.emit()
        else:
            self.transcribe_requested.emit()

    def set_processing(self, processing: bool):
        """Update button state for processing/idle."""
        self._is_processing = processing
        if processing:
            self.transcribe_btn.setText(tr("cancel"))
            self.transcribe_btn.setAccessibleName(tr("cancel"))
            self.browse_btn.setEnabled(False)
            self.fetch_btn.setEnabled(False)
        else:
            self.transcribe_btn.setText(tr("transcribe"))
            self.transcribe_btn.setAccessibleName(tr("transcribe"))
            self.browse_btn.setEnabled(True)
            self.fetch_btn.setEnabled(True)

    def set_ollama_status(self, running: bool, models: list[str] | None = None):
        """Update Ollama status indicator and model list."""
        if running:
            self.ollama_status_label.setText("Ollama: Running \u2713")
            self.ollama_status_label.setObjectName("ollamaStatusRunning")
            announce(self.ollama_status_label, "Ollama is running")
        else:
            self.ollama_status_label.setText("Ollama: Not found \u2717")
            self.ollama_status_label.setObjectName("ollamaStatusStopped")
            announce(self.ollama_status_label, "Ollama is not found")
        self.ollama_status_label.style().unpolish(self.ollama_status_label)
        self.ollama_status_label.style().polish(self.ollama_status_label)

        if models:
            self.ollama_model_combo.clear()
            self.ollama_model_combo.addItems(models)

    def get_loaded_file(self) -> str | None:
        return self._loaded_file

    def get_whisper_settings(self) -> dict:
        lang_code = self.language_combo.currentData()
        if lang_code == "auto":
            whisper_lang = None
        else:
            whisper_lang = whisper_language_code(lang_code)
        return {
            "model_size": self.model_combo.currentText(),
            "language": whisper_lang,
            "device": self.device_combo.currentText(),
            "compute_type": self.compute_combo.currentText(),
        }

    def get_ollama_settings(self) -> dict:
        return {
            "clean_fillers": self.clean_fillers_cb.isChecked(),
            "generate_summary": self.summary_cb.isChecked(),
            "translate_spanish": self.translate_cb.isChecked(),
            "label_speakers": self.speakers_cb.isChecked(),
            "model": self.ollama_model_combo.currentText(),
        }

    def has_ollama_tasks(self) -> bool:
        return any([
            self.clean_fillers_cb.isChecked(),
            self.summary_cb.isChecked(),
            self.translate_cb.isChecked(),
            self.speakers_cb.isChecked(),
        ])

    def retranslateUi(self):
        """Refresh all translatable text."""
        self._file_group.setTitle(tr("file_url_input"))
        self._browse_label.setText(tr("local_file"))
        self.browse_btn.setText(tr("browse_file"))
        self._yt_label.setText(tr("youtube_url"))
        self.fetch_btn.setText(tr("fetch"))
        self.clear_btn.setText(tr("clear"))
        self.drop_zone.setText(tr("drop_zone"))

        self._whisper_group.setTitle(tr("whisper_settings"))
        self._model_label.setText(tr("model_size"))
        self._lang_label.setText(tr("language"))
        self._device_label.setText(tr("device"))
        self._compute_label.setText(tr("compute_type"))

        # Update auto-detect item text
        self.language_combo.setItemText(0, tr("auto_detect"))

        self._ollama_group.setTitle(tr("ollama_optional"))
        self.clean_fillers_cb.setText(tr("clean_fillers"))
        self.summary_cb.setText(tr("generate_summary"))
        self.translate_cb.setText(tr("translate_spanish"))
        self.speakers_cb.setText(tr("label_speakers"))
        self._ollama_model_label.setText(tr("ollama_model"))

        if self._is_processing:
            self.transcribe_btn.setText(tr("cancel"))
        else:
            self.transcribe_btn.setText(tr("transcribe"))

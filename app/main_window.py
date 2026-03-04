"""PyQt6 MainWindow — central hub for La Mia Scribe."""

import os
import time
import json

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStatusBar, QMessageBox, QApplication, QSplitter, QPushButton,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QPixmap

from app.left_panel import LeftPanel
from app.transcript_viewer import TranscriptViewer
from app.progress_widget import ProgressWidget
from app.export_panel import ExportPanel
from app.settings_dialog import SettingsDialog, get_settings
from core.models import TranscriptModel, TranscriptSegment
from core.audio_extractor import AudioExtractionWorker
from core.transcriber import TranscriptionWorker
from core.ollama_processor import OllamaProcessor, OllamaWorker, check_ollama_status
from core.youtube_handler import YouTubeWorker
from utils.time_utils import format_duration
from app.accessibility_panel import (
    AccessibilityPanel, FloatingAccessibilityButton, apply_accessibility_settings,
    CursorTrailOverlay,
)
from app.dashboard_widget import DashboardWidget
from app.tutorial_dialog import TutorialDialog
from core.project_store import add_project, load_transcript
from core.i18n import tr, get_language, on_language_change, is_rtl


def _get_logo_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")


class MainWindow(QMainWindow):
    """Main application window for La Mia Scribe."""

    logout_requested = pyqtSignal()

    def __init__(self, display_name: str = ""):
        super().__init__()
        self._display_name = display_name
        self.setWindowTitle("La Mia Scribe — Tech Inclusion Pro")
        self.setMinimumSize(900, 600)
        self.setAccessibleName("La Mia Scribe main window")

        self._transcript_model = None
        self._audio_path = None
        self._temp_audio_path = None
        self._audio_extraction_worker = None
        self._transcription_worker = None
        self._ollama_worker = None
        self._youtube_worker = None
        self._start_time = 0
        self._cursor_trail = None

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_status_bar()
        self._load_settings()
        self._check_ollama()
        # Apply initial a11y settings (bionic mode, cursor trail)
        self._apply_accessibility()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 20, 6)

        # Logo in header
        logo_label = QLabel()
        logo_path = _get_logo_path()
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(
                40, 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
        logo_label.setAccessibleName("La Mia Scribe logo")
        logo_label.setToolTip("La Mia Scribe")
        logo_label.setStyleSheet("background: transparent;")
        header_layout.addWidget(logo_label)

        header_title = QLabel("La Mia Scribe")
        header_title.setObjectName("headerLabel")
        header_title.setAccessibleName("La Mia Scribe application title")
        header_layout.addWidget(header_title)

        header_sub = QLabel("Tech Inclusion Pro")
        header_sub.setObjectName("headerSubLabel")
        header_sub.setAccessibleName("By Tech Inclusion Pro")
        header_layout.addWidget(header_sub)

        header_layout.addStretch()

        # Welcome greeting — centered
        self._user_label = None
        if self._display_name:
            self._user_label = QLabel(tr("welcome", name=self._display_name))
            self._user_label.setObjectName("userLabel")
            self._user_label.setAccessibleName(f"Logged in as {self._display_name}")
            self._user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(self._user_label)

        header_layout.addStretch()

        # Right-side buttons: Dashboard, Tutorial, Sign Out
        self._dashboard_btn = QPushButton(tr("dashboard"))
        self._dashboard_btn.setObjectName("dashboardBtn")
        self._dashboard_btn.setMinimumSize(44, 32)
        self._dashboard_btn.setAccessibleName(tr("dashboard"))
        self._dashboard_btn.setToolTip(tr("dashboard"))
        self._dashboard_btn.clicked.connect(self._show_dashboard)
        header_layout.addWidget(self._dashboard_btn)

        self._tutorial_btn = QPushButton(tr("tutorial"))
        self._tutorial_btn.setObjectName("tutorialBtn")
        self._tutorial_btn.setMinimumSize(44, 32)
        self._tutorial_btn.setAccessibleName(tr("tutorial"))
        self._tutorial_btn.setToolTip(tr("tutorial"))
        self._tutorial_btn.clicked.connect(self._show_tutorial)
        header_layout.addWidget(self._tutorial_btn)

        self._logout_btn = None
        if self._display_name:
            logout_btn = QPushButton(tr("sign_out"))
            logout_btn.setObjectName("logoutBtn")
            logout_btn.setMinimumSize(44, 32)
            logout_btn.setAccessibleName("Sign out")
            logout_btn.setAccessibleDescription("Sign out and return to the login screen")
            logout_btn.setToolTip("Sign out of your account")
            logout_btn.clicked.connect(self.logout_requested.emit)
            header_layout.addWidget(logout_btn)
            self._logout_btn = logout_btn

        main_layout.addWidget(header)

        # Body: left panel + content area
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left panel
        self.left_panel = LeftPanel()
        self.left_panel.transcribe_requested.connect(self._on_transcribe)
        self.left_panel.cancel_requested.connect(self._on_cancel)
        self.left_panel.file_loaded.connect(self._on_file_loaded)
        self.left_panel.youtube_requested.connect(self._on_youtube_fetch)
        self.left_panel.clear_requested.connect(self._on_clear)
        body_layout.addWidget(self.left_panel)

        # Content area — stacked: dashboard (0) and transcription (1)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentArea")

        # Page 0: Dashboard
        self._dashboard = DashboardWidget()
        self._dashboard.project_opened.connect(self._on_project_opened)
        self._content_stack.addWidget(self._dashboard)

        # Page 1: Transcription view
        transcription_page = QWidget()
        transcription_layout = QVBoxLayout(transcription_page)
        transcription_layout.setContentsMargins(24, 20, 24, 20)
        transcription_layout.setSpacing(16)

        self.transcript_viewer = TranscriptViewer()
        transcription_layout.addWidget(self.transcript_viewer, 1)

        self.progress_widget = ProgressWidget()
        transcription_layout.addWidget(self.progress_widget)

        self.export_panel = ExportPanel()
        self.export_panel.save_requested.connect(self._on_export)
        self.export_panel.copy_btn.clicked.connect(self._copy_transcript)
        transcription_layout.addWidget(self.export_panel)

        self._content_stack.addWidget(transcription_page)

        # Start on dashboard
        self._content_stack.setCurrentIndex(0)

        body_layout.addWidget(self._content_stack, 1)
        main_layout.addWidget(body, 1)

        # Floating accessibility button + panel
        self._a11y_button = FloatingAccessibilityButton(self)
        self._a11y_button.clicked.connect(self._toggle_accessibility)

        self._a11y_panel = AccessibilityPanel(self)
        self._a11y_panel.settings_changed.connect(self._apply_accessibility)
        self._a11y_panel.panel_closed.connect(lambda: self._a11y_button.setFocus())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition floating accessibility button
        self._a11y_button.move(
            self.width() - self._a11y_button.width() - 20,
            self.height() - self._a11y_button.height() - 50
        )
        # Reposition accessibility panel if open
        if self._a11y_panel.isVisible():
            self._a11y_panel.move(
                self.width() - self._a11y_panel.width() - 10, 60
            )
            self._a11y_panel.setFixedHeight(self.height() - 120)
        # Resize cursor trail overlay
        if self._cursor_trail is not None:
            self._cursor_trail.setGeometry(self.rect())

    def _toggle_accessibility(self):
        self._a11y_panel.toggle()
        if self._a11y_panel.isVisible():
            self._a11y_panel.move(
                self.width() - self._a11y_panel.width() - 10, 60
            )
            self._a11y_panel.setFixedHeight(self.height() - 120)
            self._a11y_panel.raise_()

    def _apply_accessibility(self):
        settings = self._a11y_panel.get_current_settings()
        apply_accessibility_settings(settings)
        self.retranslateUi()

        # Adjust left panel width for wider fonts
        font_type = settings.get("font_type", "default")
        if font_type == "dyslexic":
            self.left_panel.setFixedWidth(360)
        else:
            self.left_panel.setMinimumWidth(280)
            self.left_panel.setMaximumWidth(380)

        # Update bionic reading mode on transcript viewer
        self.transcript_viewer.set_bionic_mode(font_type == "bionic")

        # Handle cursor trail
        cursor_style = settings.get("cursor", "default")
        if cursor_style == "trail":
            if self._cursor_trail is None:
                self._cursor_trail = CursorTrailOverlay(self)
            self._cursor_trail.setGeometry(self.rect())
            self._cursor_trail.start()
            self._cursor_trail.raise_()
        else:
            if self._cursor_trail is not None:
                self._cursor_trail.stop()
                self._cursor_trail.deleteLater()
                self._cursor_trail = None

    def _show_dashboard(self):
        self._dashboard.refresh()
        self._content_stack.setCurrentIndex(0)

    def _show_tutorial(self):
        dlg = TutorialDialog(self)
        dlg.exec()

    def retranslateUi(self):
        """Refresh all translatable text in the main window and children."""
        self._dashboard_btn.setText(tr("dashboard"))
        self._tutorial_btn.setText(tr("tutorial"))
        if self._user_label:
            self._user_label.setText(tr("welcome", name=self._display_name))
        if self._logout_btn:
            self._logout_btn.setText(tr("sign_out"))

        # Retranslate child widgets that have the method
        for child in (self.left_panel, self.transcript_viewer, self.export_panel,
                      self.progress_widget, self._dashboard):
            if hasattr(child, 'retranslateUi'):
                child.retranslateUi()

        # Handle RTL layout direction
        direction = Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight
        QApplication.setLayoutDirection(direction)

    def _show_transcription(self):
        self._content_stack.setCurrentIndex(1)

    def _on_project_opened(self, project: dict):
        """Load a saved project's transcript and display it."""
        project_id = project.get("id", "")
        segments_data = load_transcript(project_id)

        if not segments_data:
            QMessageBox.information(
                self, tr("transcript_not_available"),
                tr("transcript_not_saved_msg")
            )
            return

        # Reconstruct TranscriptSegment objects
        segments = [
            TranscriptSegment(
                index=s.get("index", i),
                start_time=s.get("start_time", 0.0),
                end_time=s.get("end_time", 0.0),
                text=s.get("text", ""),
                text_es=s.get("text_es"),
                speaker=s.get("speaker"),
                cleaned=s.get("cleaned", False),
            )
            for i, s in enumerate(segments_data)
        ]

        # Build a TranscriptModel for the loaded project
        self._transcript_model = TranscriptModel(
            segments=segments,
            source_file=project.get("source_file", ""),
            duration_seconds=project.get("duration_seconds", 0.0),
            language_detected=project.get("language", ""),
            whisper_model_used=project.get("model_used", ""),
        )

        # Display the transcript
        self.transcript_viewer.set_segments(segments)

        # Update status bar
        filename = project.get("filename", "Unknown")
        self.status_file_label.setText(f"File: {filename}")
        self.status_model_label.setText(f"Model: {project.get('model_used', '—')}")
        self.status_lang_label.setText(f"Language: {project.get('language', '—')}")
        self.status_time_label.setText("Time: —")

        # Show export panel and switch to transcription view
        has_spanish = any(s.text_es for s in segments)
        self.export_panel.show_panel(has_spanish)
        self.progress_widget.reset()
        self._show_transcription()

    def _setup_shortcuts(self):
        # Ctrl+T = Transcribe
        transcribe_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        transcribe_shortcut.activated.connect(self._on_transcribe)
        transcribe_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        # Ctrl+S = Save
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(lambda: self.export_panel.save_btn.click()
                                        if self.export_panel.isVisible() else None)
        save_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

        # Ctrl+F = Find
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(self.transcript_viewer.show_find_bar)
        find_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_model_label = QLabel("Model: —")
        self.status_model_label.setAccessibleName("Current Whisper model")
        self.status_bar.addPermanentWidget(self.status_model_label)

        self.status_lang_label = QLabel("Language: —")
        self.status_lang_label.setAccessibleName("Detected language")
        self.status_bar.addPermanentWidget(self.status_lang_label)

        self.status_time_label = QLabel("Time: —")
        self.status_time_label.setAccessibleName("Processing time")
        self.status_bar.addPermanentWidget(self.status_time_label)

        self.status_file_label = QLabel("File: —")
        self.status_file_label.setAccessibleName("Current file")
        self.status_bar.addPermanentWidget(self.status_file_label)

    def _load_settings(self):
        settings = get_settings()

        # Restore window geometry
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Restore Whisper settings
        model = settings.value("whisper/model", "medium")
        self.left_panel.model_combo.setCurrentText(model)

        lang = settings.value("whisper/language", "auto")
        idx = self.left_panel.language_combo.findData(lang)
        if idx >= 0:
            self.left_panel.language_combo.setCurrentIndex(idx)

        device = settings.value("whisper/device", "auto")
        self.left_panel.device_combo.setCurrentText(device)

        compute = settings.value("whisper/compute_type", "int8")
        self.left_panel.compute_combo.setCurrentText(compute)

        # Restore export format states
        export_states = settings.value("export/formats")
        if export_states:
            try:
                states = json.loads(export_states)
                self.export_panel.set_format_states(states)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_settings(self):
        settings = get_settings()

        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("whisper/model", self.left_panel.model_combo.currentText())
        settings.setValue("whisper/language", self.left_panel.language_combo.currentData() or "auto")
        settings.setValue("whisper/device", self.left_panel.device_combo.currentText())
        settings.setValue("whisper/compute_type", self.left_panel.compute_combo.currentText())

        ollama_model = self.left_panel.ollama_model_combo.currentText()
        if ollama_model:
            settings.setValue("ollama/model", ollama_model)

        settings.setValue("export/formats", json.dumps(self.export_panel.get_format_states()))

    def closeEvent(self, event):
        self._save_settings()
        self._cleanup_temp()
        if self._cursor_trail is not None:
            self._cursor_trail.stop()
        super().closeEvent(event)

    def _cleanup_temp(self):
        if self._temp_audio_path and os.path.exists(self._temp_audio_path):
            try:
                os.unlink(self._temp_audio_path)
            except OSError:
                pass

    def _check_ollama(self):
        """Check Ollama availability and populate model list."""
        running, models = check_ollama_status()
        self.left_panel.set_ollama_status(running, models)

        # Restore last used Ollama model
        settings = get_settings()
        last_model = settings.value("ollama/model")
        if last_model and self.left_panel.ollama_model_combo.findText(last_model) >= 0:
            self.left_panel.ollama_model_combo.setCurrentText(last_model)

    def _on_file_loaded(self, path: str):
        self._audio_path = path
        filename = os.path.basename(path)
        self.status_file_label.setText(f"File: {filename}")
        self.status_bar.showMessage(f"Loaded: {filename}", 3000)

    def _on_youtube_fetch(self, url: str):
        self.left_panel.set_processing(True)
        self.progress_widget.reset()
        self.progress_widget.set_step("Downloading YouTube audio...")
        self.progress_widget.append_log(f"Fetching: {url}")

        self._youtube_worker = YouTubeWorker(url)
        self._youtube_worker.status_update.connect(self.progress_widget.append_log)
        self._youtube_worker.finished.connect(self._on_youtube_done)
        self._youtube_worker.error.connect(self._on_youtube_error)
        self._youtube_worker.start()

    def _on_youtube_done(self, path: str):
        self._audio_path = path
        self._temp_audio_path = path
        filename = os.path.basename(path)
        self.left_panel._set_file(path)
        self.left_panel.set_processing(False)
        self.progress_widget.set_step("YouTube audio downloaded.")
        self.progress_widget.append_log(f"Downloaded: {filename}")
        self.status_bar.showMessage("YouTube audio downloaded successfully.", 3000)

    def _on_youtube_error(self, msg: str):
        self.left_panel.set_processing(False)
        self.progress_widget.set_step("YouTube download failed.")
        self.progress_widget.append_log(f"ERROR: {msg}")
        QMessageBox.critical(
            self, "YouTube Download Error",
            f"Could not download this YouTube URL.\n\n{msg}\n\n"
            "The video may be private or unavailable.\nTry: pip install -U yt-dlp"
        )

    def _on_clear(self):
        self._audio_path = None
        self._transcript_model = None
        self._cleanup_temp()
        self._temp_audio_path = None
        self.transcript_viewer.clear()
        self.export_panel.hide_panel()
        self.progress_widget.reset()
        self.status_file_label.setText("File: —")
        self.status_model_label.setText("Model: —")
        self.status_lang_label.setText("Language: —")
        self.status_time_label.setText("Time: —")
        self.status_bar.showMessage("Cleared.", 2000)

    def _on_transcribe(self):
        if not self._audio_path:
            QMessageBox.information(
                self, tr("no_file_loaded"),
                tr("load_file_message")
            )
            return

        self._show_transcription()
        self.progress_widget.reset()
        self.export_panel.hide_panel()
        self.left_panel.set_processing(True)
        self._start_time = time.time()

        self.progress_widget.set_step("Extracting audio...")
        self.progress_widget.append_log("Starting audio extraction...")

        # Non-blocking audio extraction via QThread
        self._audio_extraction_worker = AudioExtractionWorker(self._audio_path)
        self._audio_extraction_worker.status_update.connect(self.progress_widget.append_log)
        self._audio_extraction_worker.finished.connect(self._on_audio_extracted)
        self._audio_extraction_worker.error.connect(self._on_audio_extraction_error)
        self._audio_extraction_worker.start()

    def _on_audio_extracted(self, audio_path: str):
        """Audio extraction completed — start transcription."""
        self._temp_audio_path = audio_path
        self.progress_widget.append_log(f"Audio extracted: {audio_path}")
        self.progress_widget.set_step("Loading Whisper model...")

        whisper_settings = self.left_panel.get_whisper_settings()
        self.status_model_label.setText(f"Model: {whisper_settings['model_size']}")

        self._transcription_worker = TranscriptionWorker(
            audio_path=audio_path,
            model_size=whisper_settings["model_size"],
            language=whisper_settings["language"],
            device=whisper_settings["device"],
            compute_type=whisper_settings["compute_type"],
        )
        self._transcription_worker.progress_update.connect(self.progress_widget.set_progress)
        self._transcription_worker.status_update.connect(self._on_transcription_status)
        self._transcription_worker.segment_ready.connect(self._on_segment_ready)
        self._transcription_worker.finished.connect(self._on_transcription_done)
        self._transcription_worker.error.connect(self._on_transcription_error)
        self._transcription_worker.start()

    def _on_audio_extraction_error(self, msg: str):
        """Handle audio extraction failure."""
        self.left_panel.set_processing(False)
        self.progress_widget.set_step("Audio extraction failed.")
        self.progress_widget.append_log(f"ERROR: {msg}")

        if "ffmpeg" in msg.lower() and "not installed" in msg.lower():
            QMessageBox.critical(
                self, "FFmpeg Not Found",
                "FFmpeg is not installed. Please install FFmpeg and add it to your PATH.\n"
                "Visit ffmpeg.org for instructions."
            )
        elif "no audio" in msg.lower():
            QMessageBox.critical(
                self, "No Audio Track",
                "No audio track found in this file. Please check the file and try again."
            )
        else:
            QMessageBox.critical(
                self, "Audio Extraction Error",
                f"Failed to extract audio:\n{msg}"
            )

    def _on_transcription_status(self, msg: str):
        self.progress_widget.set_step(msg)
        self.progress_widget.append_log(msg)

    def _on_segment_ready(self, seg_dict: dict):
        """Handle individual segment as it arrives."""
        pass  # Segments accumulated in worker; viewer refreshes on finish

    def _on_transcription_done(self, model: TranscriptModel):
        self._transcript_model = model
        elapsed = time.time() - self._start_time

        # Update status
        lang = model.language_detected or "Unknown"
        self.status_lang_label.setText(f"Language: {lang}")
        self.status_time_label.setText(f"Time: {format_duration(elapsed)}")

        self.progress_widget.set_progress(100)
        self.progress_widget.set_step("Transcription complete.")
        self.progress_widget.append_log(
            f"Transcription complete. {len(model.segments)} segments, "
            f"duration: {format_duration(model.duration_seconds)}"
        )

        # Show transcript
        self.transcript_viewer.set_segments(model.segments)

        # Check for Ollama post-processing
        if self.left_panel.has_ollama_tasks():
            self._run_ollama_processing()
        else:
            self._finalize()

    def _on_transcription_error(self, msg: str):
        self.left_panel.set_processing(False)
        self.progress_widget.set_step("Transcription failed.")
        self.progress_widget.append_log(f"ERROR: {msg}")

        if "model" in msg.lower() and ("download" in msg.lower() or "not found" in msg.lower()):
            QMessageBox.warning(
                self, "Whisper Model",
                "The selected Whisper model is not downloaded.\n"
                "It will be downloaded automatically (~1-3GB).\n"
                "This may take several minutes."
            )
        else:
            QMessageBox.critical(
                self, "Transcription Error",
                f"An error occurred during transcription:\n{msg}"
            )

    def _on_cancel(self):
        if self._audio_extraction_worker and self._audio_extraction_worker.isRunning():
            self._audio_extraction_worker.cancel()
            self._audio_extraction_worker.wait(3000)

        if self._transcription_worker and self._transcription_worker.isRunning():
            self._transcription_worker.cancel()
            self._transcription_worker.wait(3000)

        if self._ollama_worker and self._ollama_worker.isRunning():
            self._ollama_worker.cancel()
            self._ollama_worker.wait(3000)

        self.progress_widget.set_step("Cancelled.")
        self.progress_widget.append_log("Operation cancelled by user.")
        self.status_bar.showMessage("Cancelled.", 3000)
        self.left_panel.set_processing(False)

    def _run_ollama_processing(self):
        """Run Ollama post-processing on completed transcript."""
        ollama_settings = self.left_panel.get_ollama_settings()
        if not ollama_settings["model"]:
            self.progress_widget.append_log("No Ollama model selected. Skipping post-processing.")
            self._finalize()
            return

        self.progress_widget.set_step("Running Ollama post-processing...")
        self.progress_widget.append_log(f"Ollama model: {ollama_settings['model']}")

        self._ollama_worker = OllamaWorker(
            transcript_model=self._transcript_model,
            ollama_model=ollama_settings["model"],
            clean_fillers=ollama_settings["clean_fillers"],
            generate_summary=ollama_settings["generate_summary"],
            translate_spanish=ollama_settings["translate_spanish"],
            label_speakers=ollama_settings["label_speakers"],
        )
        self._ollama_worker.progress_update.connect(self.progress_widget.set_progress)
        self._ollama_worker.status_update.connect(self._on_transcription_status)
        self._ollama_worker.finished.connect(self._on_ollama_done)
        self._ollama_worker.error.connect(self._on_ollama_error)
        self._ollama_worker.start()

    def _on_ollama_done(self, model: TranscriptModel):
        self._transcript_model = model
        self.transcript_viewer.set_segments(model.segments)
        self.progress_widget.set_step("Post-processing complete.")
        self.progress_widget.append_log("Ollama post-processing finished.")
        self._finalize()

    def _on_ollama_error(self, msg: str):
        self.progress_widget.append_log(f"Ollama error: {msg}")
        if "not running" in msg.lower() or "connection" in msg.lower():
            QMessageBox.warning(
                self, "Ollama Not Running",
                "Ollama is not running. Start it with: ollama serve\n"
                "Then restart the app. Visit ollama.ai for setup help.\n\n"
                "Transcription is still available without post-processing."
            )
        else:
            QMessageBox.warning(
                self, "Ollama Error",
                f"Post-processing encountered an error:\n{msg}\n\n"
                "The transcript is still available without post-processing."
            )
        self._finalize()

    def _finalize(self):
        """Show export panel, save project, and finalize processing."""
        elapsed = time.time() - self._start_time
        self.status_time_label.setText(f"Time: {format_duration(elapsed)}")
        self.left_panel.set_processing(False)

        has_spanish = any(s.text_es for s in self._transcript_model.segments)
        self.export_panel.show_panel(has_spanish)

        self.progress_widget.set_progress(100)
        self.status_bar.showMessage("Ready to export.", 5000)

        # Save project to dashboard history (including full transcript)
        try:
            preview = " ".join(
                s.text for s in self._transcript_model.segments[:10]
            )
            segments_data = [
                {
                    "index": s.index,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "text": s.text,
                    "text_es": s.text_es,
                    "speaker": s.speaker,
                    "cleaned": s.cleaned,
                }
                for s in self._transcript_model.segments
            ]
            add_project(
                source_file=self._transcript_model.source_file or self._audio_path or "",
                model_used=self._transcript_model.whisper_model_used,
                language=self._transcript_model.language_detected or "",
                segments_count=len(self._transcript_model.segments),
                duration_seconds=self._transcript_model.duration_seconds,
                transcript_preview=preview,
                segments=segments_data,
            )
        except Exception:
            pass  # Don't block export on save failure

    def _on_export(self, directory: str, formats: list[str], language: str):
        """Export transcript in selected formats."""
        if not self._transcript_model:
            return

        source = self._transcript_model.source_file
        base_name = os.path.splitext(os.path.basename(source))[0] if source else "transcript"

        exported = []
        errors = []

        for fmt in formats:
            try:
                if fmt == "srt":
                    from exporters.srt_exporter import export_srt
                    if language in ("english", "both"):
                        path = os.path.join(directory, f"{base_name}_transcript.srt")
                        export_srt(self._transcript_model, path, spanish=False)
                        exported.append(path)
                    if language in ("spanish", "both") and any(s.text_es for s in self._transcript_model.segments):
                        path = os.path.join(directory, f"{base_name}_transcript_es.srt")
                        export_srt(self._transcript_model, path, spanish=True)
                        exported.append(path)

                elif fmt == "vtt":
                    from exporters.vtt_exporter import export_vtt
                    if language in ("english", "both"):
                        path = os.path.join(directory, f"{base_name}_transcript.vtt")
                        export_vtt(self._transcript_model, path, spanish=False)
                        exported.append(path)
                    if language in ("spanish", "both") and any(s.text_es for s in self._transcript_model.segments):
                        path = os.path.join(directory, f"{base_name}_transcript_es.vtt")
                        export_vtt(self._transcript_model, path, spanish=True)
                        exported.append(path)

                elif fmt == "txt":
                    from exporters.txt_exporter import export_txt
                    if language in ("english", "both"):
                        path = os.path.join(directory, f"{base_name}_transcript.txt")
                        export_txt(self._transcript_model, path, spanish=False)
                        exported.append(path)
                    if language in ("spanish", "both") and any(s.text_es for s in self._transcript_model.segments):
                        path = os.path.join(directory, f"{base_name}_transcript_es.txt")
                        export_txt(self._transcript_model, path, spanish=True)
                        exported.append(path)

                elif fmt == "pdf":
                    from exporters.pdf_exporter import export_pdf
                    if language in ("english", "both"):
                        path = os.path.join(directory, f"{base_name}_transcript.pdf")
                        export_pdf(self._transcript_model, path, spanish=False)
                        exported.append(path)
                    if language in ("spanish", "both") and any(s.text_es for s in self._transcript_model.segments):
                        path = os.path.join(directory, f"{base_name}_transcript_es.pdf")
                        export_pdf(self._transcript_model, path, spanish=True)
                        exported.append(path)

                elif fmt == "docx":
                    from exporters.docx_exporter import export_docx
                    if language in ("english", "both"):
                        path = os.path.join(directory, f"{base_name}_transcript.docx")
                        export_docx(self._transcript_model, path, spanish=False)
                        exported.append(path)
                    if language in ("spanish", "both") and any(s.text_es for s in self._transcript_model.segments):
                        path = os.path.join(directory, f"{base_name}_transcript_es.docx")
                        export_docx(self._transcript_model, path, spanish=True)
                        exported.append(path)

            except Exception as e:
                errors.append(f"{fmt.upper()}: {e}")

        # Save last export directory
        settings = get_settings()
        settings.setValue("export/last_directory", directory)

        if exported:
            file_list = "\n".join(f"  - {os.path.basename(f)}" for f in exported)
            msg = f"Exported {len(exported)} file(s) to:\n{directory}\n\n{file_list}"
            if errors:
                msg += f"\n\nErrors:\n" + "\n".join(errors)
            QMessageBox.information(self, "Export Complete", msg)
        elif errors:
            QMessageBox.critical(
                self, "Export Failed",
                "All exports failed:\n" + "\n".join(errors)
            )

    def _copy_transcript(self):
        text = self.transcript_viewer.get_plain_text()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.status_bar.showMessage("Transcript copied to clipboard.", 3000)

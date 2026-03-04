"""Step-by-step tutorial dialog for La Mia Scribe."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.i18n import tr


TUTORIAL_STEPS = [
    {
        "title_key": "tut_welcome_title",
        "title": "Welcome to La Mia Scribe",
        "body": (
            "La Mia Scribe is an accessible transcription tool built by "
            "Tech Inclusion Pro.\n\n"
            "This tutorial will walk you through all the features of the "
            "application so you can get the most out of it.\n\n"
            "Use the Next and Previous buttons below to navigate, or press "
            "Escape to close at any time."
        ),
    },
    {
        "title_key": "tut_load_title",
        "title": "Step 1: Load a Media File",
        "body": (
            "On the left panel you'll find the file input area.\n\n"
            "\u2022  Drag & drop a media file onto the drop zone, or\n"
            "\u2022  Click \"Browse\" to choose a file from your computer, or\n"
            "\u2022  Paste a YouTube URL and click \"Fetch\" to download audio\n\n"
            "Supported formats: MP4, MOV, AVI, MKV, MP3, WAV, M4A, OGG."
        ),
    },
    {
        "title_key": "tut_whisper_title",
        "title": "Step 2: Configure Whisper Settings",
        "body": (
            "Below the file input, you can adjust your transcription settings:\n\n"
            "\u2022  Model \u2014 Choose from tiny, base, small, medium, or large. "
            "Larger models are more accurate but slower.\n"
            "\u2022  Language \u2014 Select a language or leave on Auto-detect.\n"
            "\u2022  Device \u2014 Choose auto, CPU, or GPU (if available).\n"
            "\u2022  Compute Type \u2014 int8 is fastest, float16 for better quality.\n\n"
            "Your settings are saved automatically between sessions."
        ),
    },
    {
        "title_key": "tut_ollama_title",
        "title": "Step 3: Ollama Post-Processing (Optional)",
        "body": (
            "If you have Ollama running locally, you can enable AI-powered "
            "post-processing:\n\n"
            "\u2022  Clean Fillers \u2014 Remove \"um\", \"uh\", and other filler words\n"
            "\u2022  Generate Summary \u2014 Get a summary of the transcript\n"
            "\u2022  Translate to Spanish \u2014 Add a Spanish translation\n"
            "\u2022  Label Speakers \u2014 Identify different speakers\n\n"
            "Ollama is optional. Transcription works without it."
        ),
    },
    {
        "title_key": "tut_transcribe_title",
        "title": "Step 4: Transcribe",
        "body": (
            "Click the \"Transcribe\" button (or press Ctrl+T) to start.\n\n"
            "You'll see a progress bar and log showing each step:\n"
            "1. Audio extraction from your media file\n"
            "2. Whisper model loading\n"
            "3. Transcription with real-time progress\n"
            "4. Ollama post-processing (if enabled)\n\n"
            "You can cancel at any time with the Cancel button."
        ),
    },
    {
        "title_key": "tut_review_title",
        "title": "Step 5: Review & Edit the Transcript",
        "body": (
            "Once transcription is complete, the transcript appears in the "
            "main viewer with timestamps and speaker labels.\n\n"
            "\u2022  The text is fully editable \u2014 click and type to make changes\n"
            "\u2022  Use Ctrl+F to open the Find & Replace bar\n"
            "\u2022  If Spanish translation is available, toggle between English "
            "and Spanish with the language buttons\n"
            "\u2022  Word and character counts appear at the bottom"
        ),
    },
    {
        "title_key": "tut_export_title",
        "title": "Step 6: Export Your Transcript",
        "body": (
            "After transcription, the export panel appears at the bottom.\n\n"
            "Available export formats:\n"
            "\u2022  SRT \u2014 Subtitles for video players\n"
            "\u2022  VTT \u2014 Web Video Text Tracks\n"
            "\u2022  TXT \u2014 Plain text\n"
            "\u2022  PDF \u2014 Formatted document\n"
            "\u2022  DOCX \u2014 Microsoft Word\n\n"
            "Select one or more formats, choose a save location, and click "
            "Save. You can also use \"Copy\" to copy text to clipboard."
        ),
    },
    {
        "title_key": "tut_dashboard_title",
        "title": "Step 7: Dashboard & Project History",
        "body": (
            "Click \"Dashboard\" in the top right to view all your past "
            "transcription projects.\n\n"
            "\u2022  Each project card shows the file name, date, model used, "
            "language, segment count, and duration\n"
            "\u2022  Click \"Open Transcript\" to reload a saved transcript\n"
            "\u2022  Add notes to any project for your reference\n"
            "\u2022  Use the trash icon to delete projects you no longer need"
        ),
    },
    {
        "title_key": "tut_a11y_title",
        "title": "Step 8: Accessibility Features",
        "body": (
            "Click the floating accessibility button (bottom-right corner) "
            "to open the accessibility panel.\n\n"
            "\u2022  Themes \u2014 Light, Dark, Forest, and colorblind-safe options\n"
            "\u2022  Font Size \u2014 Small, Default, Large, XL, XXL\n"
            "\u2022  Font Type \u2014 Default, OpenDyslexic (dyslexia-friendly), "
            "or Bionic Reading (ADHD-friendly)\n"
            "\u2022  Cursor \u2014 Default, Large, Crosshair, or Trail\n\n"
            "All accessibility settings are saved and persist across sessions."
        ),
    },
    {
        "title_key": "tut_shortcuts_title",
        "title": "Keyboard Shortcuts",
        "body": (
            "La Mia Scribe supports these keyboard shortcuts:\n\n"
            "\u2022  Ctrl+T \u2014 Start transcription\n"
            "\u2022  Ctrl+S \u2014 Save / Export\n"
            "\u2022  Ctrl+F \u2014 Find & Replace in transcript\n"
            "\u2022  Escape \u2014 Close dialogs and panels\n\n"
            "The app is fully navigable with keyboard using Tab and "
            "Shift+Tab, and works with VoiceOver on macOS."
        ),
    },
    {
        "title_key": "tut_done_title",
        "title": "You're All Set!",
        "body": (
            "That's everything you need to know to use La Mia Scribe.\n\n"
            "Tips for best results:\n"
            "\u2022  Use the \"medium\" or \"large\" Whisper model for best accuracy\n"
            "\u2022  Clear audio with minimal background noise transcribes best\n"
            "\u2022  Enable Ollama post-processing to clean up filler words "
            "and add speaker labels\n\n"
            "You can revisit this tutorial anytime from the Tutorial button "
            "in the header bar.\n\n"
            "Happy transcribing!"
        ),
    },
]


class TutorialDialog(QDialog):
    """Multi-step tutorial walkthrough dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("La Mia Scribe \u2014 Tutorial")
        self.setMinimumSize(560, 420)
        self.setMaximumSize(700, 600)
        self.setAccessibleName("Application tutorial")
        self.setObjectName("tutorialDialog")
        self._step = 0
        self._setup_ui()
        self._show_step(0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        # Step indicator
        self._step_label = QLabel()
        self._step_label.setObjectName("tutorialStepLabel")
        self._step_label.setAccessibleName("Tutorial step indicator")
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._step_label)

        # Title
        self._title_label = QLabel()
        self._title_label.setObjectName("tutorialTitle")
        self._title_label.setWordWrap(True)
        title_font = self._title_label.font()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        self._title_label.setFont(title_font)
        layout.addWidget(self._title_label)

        # Body
        self._body_label = QLabel()
        self._body_label.setObjectName("tutorialBody")
        self._body_label.setWordWrap(True)
        self._body_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        body_font = self._body_label.font()
        body_font.setPointSize(13)
        self._body_label.setFont(body_font)
        layout.addWidget(self._body_label, 1)

        # Progress dots
        self._dots_widget = QWidget()
        self._dots_layout = QHBoxLayout(self._dots_widget)
        self._dots_layout.setContentsMargins(0, 0, 0, 0)
        self._dots_layout.setSpacing(6)
        self._dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dots = []
        for i in range(len(TUTORIAL_STEPS)):
            dot = QLabel("\u25cf")
            dot.setObjectName("tutorialDot")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(16, 16)
            self._dots_layout.addWidget(dot)
            self._dots.append(dot)
        layout.addWidget(self._dots_widget)

        # Navigation buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._prev_btn = QPushButton(tr("previous"))
        self._prev_btn.setObjectName("tutorialPrevBtn")
        self._prev_btn.setMinimumSize(100, 44)
        self._prev_btn.setAccessibleName(tr("previous"))
        self._prev_btn.clicked.connect(self._go_prev)
        btn_row.addWidget(self._prev_btn)

        btn_row.addStretch()

        self._close_btn = QPushButton(tr("close"))
        self._close_btn.setObjectName("tutorialCloseBtn")
        self._close_btn.setMinimumSize(80, 44)
        self._close_btn.setAccessibleName(tr("close"))
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)

        btn_row.addStretch()

        self._next_btn = QPushButton(tr("next_btn"))
        self._next_btn.setObjectName("tutorialNextBtn")
        self._next_btn.setMinimumSize(100, 44)
        self._next_btn.setAccessibleName(tr("next_btn"))
        self._next_btn.clicked.connect(self._go_next)
        self._next_btn.setDefault(True)
        btn_row.addWidget(self._next_btn)

        layout.addLayout(btn_row)

    def _show_step(self, index):
        self._step = max(0, min(index, len(TUTORIAL_STEPS) - 1))
        step = TUTORIAL_STEPS[self._step]
        total = len(TUTORIAL_STEPS)

        self._step_label.setText(tr("step_of", n=self._step + 1, total=total))
        # Use translated title if available, fall back to English
        title_key = step.get("title_key")
        title_text = tr(title_key) if title_key else step["title"]
        self._title_label.setText(title_text)
        self._body_label.setText(step["body"])

        self._prev_btn.setEnabled(self._step > 0)
        is_last = self._step == total - 1
        self._next_btn.setText(tr("finish") if is_last else tr("next_btn"))
        self._next_btn.setAccessibleName(tr("finish") if is_last else tr("next_btn"))

        # Update dots
        for i, dot in enumerate(self._dots):
            if i == self._step:
                dot.setStyleSheet("color: palette(highlight); font-size: 14px;")
            else:
                dot.setStyleSheet("color: palette(mid); font-size: 10px;")

        # Announce for screen readers
        self._title_label.setAccessibleName(
            f"Step {self._step + 1} of {total}: {step['title']}"
        )

    def _go_next(self):
        if self._step >= len(TUTORIAL_STEPS) - 1:
            self.accept()
        else:
            self._show_step(self._step + 1)

    def _go_prev(self):
        self._show_step(self._step - 1)

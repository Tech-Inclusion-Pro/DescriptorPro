"""Editable transcript display widget with find/replace and language toggle."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QTextCharFormat, QColor, QTextCursor, QFont, QKeySequence, QShortcut,
    QPalette
)

from utils.time_utils import seconds_to_display_time
from core.i18n import tr


class FindBar(QWidget):
    """Inline find/replace bar."""

    def __init__(self, text_edit: QTextEdit, parent=None):
        super().__init__(parent)
        self.setObjectName("findBar")
        self.text_edit = text_edit
        self.setVisible(False)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._find_label = QLabel(tr("find"))
        layout.addWidget(self._find_label)

        self.find_input = QLineEdit()
        self.find_input.setAccessibleName(tr("find"))
        self.find_input.setToolTip(tr("find"))
        self.find_input.returnPressed.connect(self.find_next)
        layout.addWidget(self.find_input)

        self.find_next_btn = QPushButton(tr("next_btn"))
        self.find_next_btn.setMinimumSize(44, 44)
        self.find_next_btn.setAccessibleName(tr("next_btn"))
        self.find_next_btn.clicked.connect(self.find_next)
        layout.addWidget(self.find_next_btn)

        self.find_prev_btn = QPushButton(tr("prev_btn"))
        self.find_prev_btn.setMinimumSize(44, 44)
        self.find_prev_btn.setAccessibleName(tr("prev_btn"))
        self.find_prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(self.find_prev_btn)

        self._replace_label = QLabel(tr("replace_label"))
        layout.addWidget(self._replace_label)

        self.replace_input = QLineEdit()
        self.replace_input.setAccessibleName(tr("replace_label"))
        self.replace_input.setToolTip(tr("replace_label"))
        layout.addWidget(self.replace_input)

        self.replace_btn = QPushButton(tr("replace_btn"))
        self.replace_btn.setMinimumSize(44, 44)
        self.replace_btn.setAccessibleName(tr("replace_btn"))
        self.replace_btn.clicked.connect(self.replace_current)
        layout.addWidget(self.replace_btn)

        self.close_btn = QPushButton("\u00d7")
        self.close_btn.setMinimumSize(44, 44)
        self.close_btn.setAccessibleName(tr("close"))
        self.close_btn.setToolTip(tr("close"))
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

    def show_bar(self):
        self.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def find_next(self):
        text = self.find_input.text()
        if text:
            self.text_edit.find(text)

    def find_prev(self):
        text = self.find_input.text()
        if text:
            self.text_edit.find(text, QTextEdit.FindFlag(1))  # FindBackward

    def replace_current(self):
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_input.text())
            self.find_next()


class TranscriptViewer(QWidget):
    """Transcript display widget with editing, find/replace, and language toggle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments = []
        self._show_spanish = False
        self._has_spanish = False
        self._bionic_mode = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Language toggle (hidden until translation available)
        self.language_toggle = QWidget()
        self.language_toggle.setObjectName("languageToggle")
        toggle_layout = QHBoxLayout(self.language_toggle)
        toggle_layout.setContentsMargins(0, 0, 0, 4)

        self.english_btn = QPushButton(tr("show_english"))
        self.english_btn.setCheckable(True)
        self.english_btn.setChecked(True)
        self.english_btn.setMinimumSize(44, 32)
        self.english_btn.setAccessibleName(tr("show_english"))
        self.english_btn.clicked.connect(lambda: self._set_language(False))
        toggle_layout.addWidget(self.english_btn)

        self.spanish_btn = QPushButton(tr("show_spanish"))
        self.spanish_btn.setCheckable(True)
        self.spanish_btn.setMinimumSize(44, 32)
        self.spanish_btn.setAccessibleName(tr("show_spanish"))
        self.spanish_btn.clicked.connect(lambda: self._set_language(True))
        toggle_layout.addWidget(self.spanish_btn)

        toggle_layout.addStretch()
        self.language_toggle.setVisible(False)
        layout.addWidget(self.language_toggle)

        # Find bar
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("transcriptViewer")
        self.text_edit.setAccessibleName("Transcript viewer")
        self.text_edit.setAccessibleDescription(
            "Editable transcript with timestamps and speaker labels. "
            "Use Ctrl+F to find text."
        )
        self.text_edit.setToolTip("Editable transcript text")

        self.find_bar = FindBar(self.text_edit)
        layout.addWidget(self.find_bar)

        layout.addWidget(self.text_edit, 1)

        # Word count
        self.word_count_label = QLabel("")
        self.word_count_label.setObjectName("wordCountLabel")
        self.word_count_label.setAccessibleName("Word and character count")
        layout.addWidget(self.word_count_label)

        self.text_edit.textChanged.connect(self._update_word_count)

    def _set_language(self, spanish: bool):
        self._show_spanish = spanish
        self.english_btn.setChecked(not spanish)
        self.spanish_btn.setChecked(spanish)
        self.refresh_display()

    def set_segments(self, segments: list):
        """Set transcript segments and refresh display."""
        self._segments = segments
        self._has_spanish = any(s.text_es for s in segments)
        self.language_toggle.setVisible(self._has_spanish)
        self.refresh_display()

    def refresh_display(self):
        """Rebuild the transcript display from segments."""
        scroll_pos = self.text_edit.verticalScrollBar().value()
        self.text_edit.clear()
        cursor = self.text_edit.textCursor()

        # Use palette-aware colors so text is readable on both dark and light themes
        base_text_color = self.text_edit.palette().color(QPalette.ColorRole.Text)
        is_dark = self.text_edit.palette().color(QPalette.ColorRole.Base).lightness() < 128

        timestamp_color = QColor("#c9a0e8") if is_dark else QColor("#7b5ea0")
        speaker_color = QColor("#e090cc") if is_dark else QColor("#6f2fa6")

        timestamp_fmt = QTextCharFormat()
        timestamp_fmt.setForeground(timestamp_color)

        speaker_fmt = QTextCharFormat()
        speaker_fmt.setForeground(speaker_color)
        speaker_fmt.setFontWeight(QFont.Weight.Bold)

        text_fmt = QTextCharFormat()
        text_fmt.setForeground(base_text_color)

        # Bionic bold format — first portion of each word is bold
        bionic_bold_fmt = QTextCharFormat(text_fmt)
        bionic_bold_fmt.setFontWeight(QFont.Weight.Bold)

        for i, seg in enumerate(self._segments):
            if i > 0:
                cursor.insertText("\n\n", text_fmt)

            start = seconds_to_display_time(seg.start_time)
            end = seconds_to_display_time(seg.end_time)
            cursor.insertText(f"[{start} \u2192 {end}]  ", timestamp_fmt)

            if seg.speaker:
                cursor.insertText(f"{seg.speaker}:  ", speaker_fmt)

            text = seg.text_es if (self._show_spanish and seg.text_es) else seg.text
            if self._bionic_mode:
                self._insert_bionic_text(cursor, text, bionic_bold_fmt, text_fmt)
            else:
                cursor.insertText(text, text_fmt)

        self.text_edit.verticalScrollBar().setValue(scroll_pos)
        self._update_word_count()

    def _update_word_count(self):
        text = self.text_edit.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self.word_count_label.setText(tr("words_count", w=words, c=chars))

    def set_bionic_mode(self, enabled: bool):
        """Enable or disable bionic reading mode."""
        if self._bionic_mode != enabled:
            self._bionic_mode = enabled
            if self._segments:
                self.refresh_display()

    @staticmethod
    def _bionic_fixation_len(word_len):
        """Calculate how many characters to bold for bionic reading.

        Matches the Bionic Reading fixation style: bold a short prefix
        of each word to create an eye-guiding fixation point.
        """
        if word_len <= 1:
            return 1
        if word_len <= 3:
            return 1
        if word_len == 4:
            return 2
        if word_len <= 6:
            return 2
        if word_len <= 9:
            return 3
        if word_len <= 12:
            return 4
        return max(4, round(word_len * 0.35))

    def _insert_bionic_text(self, cursor, text, bold_fmt, normal_fmt):
        """Insert text with Bionic Reading formatting.

        Bolds the first few characters of each word to create fixation
        points that guide the eye across text, improving reading flow
        for ADHD and other readers.
        """
        import re
        tokens = re.split(r'(\s+)', text)
        for token in tokens:
            if not token or token.isspace():
                cursor.insertText(token, normal_fmt)
            else:
                bold_len = self._bionic_fixation_len(len(token))
                cursor.insertText(token[:bold_len], bold_fmt)
                if bold_len < len(token):
                    cursor.insertText(token[bold_len:], normal_fmt)

    def show_find_bar(self):
        self.find_bar.show_bar()

    def get_plain_text(self) -> str:
        return self.text_edit.toPlainText()

    def retranslateUi(self):
        """Refresh all translatable text."""
        self.english_btn.setText(tr("show_english"))
        self.spanish_btn.setText(tr("show_spanish"))
        self.find_bar._find_label.setText(tr("find"))
        self.find_bar.find_next_btn.setText(tr("next_btn"))
        self.find_bar.find_prev_btn.setText(tr("prev_btn"))
        self.find_bar._replace_label.setText(tr("replace_label"))
        self.find_bar.replace_btn.setText(tr("replace_btn"))
        self._update_word_count()

    def clear(self):
        self._segments = []
        self._has_spanish = False
        self._show_spanish = False
        self.language_toggle.setVisible(False)
        self.text_edit.clear()
        self.word_count_label.setText("")

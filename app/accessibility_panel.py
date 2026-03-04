"""Floating accessibility button and settings panel for La Mia Scribe.

Matches the TIP Business Tools accessibility feature set:
- Font size (small/default/large/xl/xxl)
- Font type (default/OpenDyslexic/Bionic)
- Color theme (8 themes including system)
- Colorblind support (protanopia/deuteranopia/tritanopia/achromatopsia)
- Cursor style (default/large/crosshair/trail)
- Reduced motion toggle
- Enhanced text spacing toggle
- Enhanced focus indicators toggle
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QCursor, QPixmap, QPainter, QColor, QFont, QFontDatabase, QPolygonF,
)

from app.settings_dialog import get_settings
from app.theme_manager import generate_stylesheet, FONT_SIZES, get_effective_theme

import os
import platform

from core.i18n import tr, set_language, get_language, available_languages, on_language_change


def announce(widget, message):
    """Fire a screen reader announcement.

    On macOS, uses NSAccessibility to post a notification that VoiceOver reads.
    On other platforms, sets the accessible name (picked up on focus).
    """
    widget.setAccessibleName(message)
    if platform.system() == "Darwin":
        try:
            import AppKit
            nsview = None
            # Get the native NSView for the widget
            win_id = int(widget.winId()) if hasattr(widget, 'winId') else 0
            if win_id:
                from Cocoa import NSApp
                # Post an announcement notification
                info = {AppKit.NSAccessibilityAnnouncementKey: message}
                AppKit.NSAccessibilityPostNotificationWithUserInfo(
                    NSApp, AppKit.NSAccessibilityAnnouncementRequestedNotification, info
                )
        except Exception:
            pass  # Silently fall back to accessible name only


THEME_OPTIONS = [
    ("system", "System"),
    ("light", "Light"),
    ("dark", "Dark"),
    ("high-contrast", "High Contrast"),
    ("sepia", "Sepia"),
    ("blue-light", "Blue Light"),
    ("pastel", "Pastel"),
    ("forest", "Forest"),
]

COLORBLIND_OPTIONS = [
    ("none", "None", ""),
    ("protanopia", "Protanopia", "(Red-blind)"),
    ("deuteranopia", "Deuteranopia", "(Green-blind)"),
    ("tritanopia", "Tritanopia", "(Blue-blind)"),
    ("achromatopsia", "Grayscale", ""),
]

CURSOR_OPTIONS = [
    ("default", "Default"),
    ("large", "Large"),
    ("crosshair", "Crosshair"),
    ("trail", "Trail"),
]

FONT_SIZE_OPTIONS = [
    ("small", "S"),
    ("default", "M"),
    ("large", "L"),
    ("xl", "XL"),
    ("xxl", "XXL"),
]

FONT_TYPE_OPTIONS = [
    ("default", "Default"),
    ("dyslexic", "OpenDyslexic"),
    ("bionic", "Bionic"),
]


_fonts_loaded = set()


def _load_bundled_fonts():
    """Load bundled font files from assets/. Only loads each font once."""
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    font_files = [
        "OpenDyslexic-Regular.otf",
        "OpenDyslexic-Bold.otf",
    ]
    for fname in font_files:
        if fname in _fonts_loaded:
            continue
        font_path = os.path.join(assets_dir, fname)
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id >= 0:
                _fonts_loaded.add(fname)


def _is_font_available(family_name):
    """Check if a font family is available after loading."""
    return family_name in QFontDatabase.families()


class AccessibilityPanel(QWidget):
    """Slide-out accessibility settings panel."""

    settings_changed = pyqtSignal()
    panel_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("accessibilityPanel")
        self.setFixedWidth(340)

        self._settings = get_settings()
        self._language = self._settings.value("a11y/language", "en")
        set_language(self._language)
        self._font_size = self._settings.value("a11y/font_size", "default")
        self._font_type = self._settings.value("a11y/font_type", "default")
        self._theme = self._settings.value("a11y/theme", "dark")
        self._colorblind = self._settings.value("a11y/colorblind", "none")
        self._cursor = self._settings.value("a11y/cursor", "default")
        self._reduced_motion = self._settings.value("a11y/reduced_motion", "false") == "true"
        self._text_spacing = self._settings.value("a11y/text_spacing", "false") == "true"
        self._enhanced_focus = self._settings.value("a11y/enhanced_focus", "false") == "true"

        _load_bundled_fonts()
        self._dyslexic_available = _is_font_available("OpenDyslexic")
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("a11yHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Accessibility")
        title.setAccessibleName("Accessibility settings panel")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("\u00d7")
        close_btn.setObjectName("a11yCloseBtn")
        close_btn.setAccessibleName("Close accessibility panel")
        close_btn.setToolTip("Close (Esc)")
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(4)

        # ---- App Language ----
        self._add_section_label(content_layout, tr("app_language"))
        from PyQt6.QtWidgets import QComboBox
        self._language_combo = QComboBox()
        self._language_combo.setMinimumHeight(44)
        self._language_combo.setAccessibleName("App language selector")
        langs = available_languages()
        for code, display in langs:
            self._language_combo.addItem(display, code)
        # Set current
        idx = self._language_combo.findData(self._language)
        if idx >= 0:
            self._language_combo.setCurrentIndex(idx)
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        content_layout.addWidget(self._language_combo)

        # ---- Font Size ----
        self._add_section_label(content_layout, "Font Size")
        self._font_size_btns = {}
        row = QHBoxLayout()
        row.setSpacing(4)
        for key, label in FONT_SIZE_OPTIONS:
            btn = QPushButton(label)
            btn.setMinimumSize(44, 44)
            btn.setAccessibleName(f"Font size: {label}")
            btn.setToolTip(f"Set font size to {label}")
            btn.clicked.connect(lambda checked, k=key: self._set_font_size(k))
            self._font_size_btns[key] = btn
            row.addWidget(btn)
        content_layout.addLayout(row)

        # ---- Font Type ----
        self._add_section_label(content_layout, "Font Type")
        self._font_type_btns = {}
        row = QHBoxLayout()
        row.setSpacing(4)
        for key, label in FONT_TYPE_OPTIONS:
            btn = QPushButton(label)
            btn.setMinimumSize(44, 44)
            btn.setAccessibleName(f"Font type: {label}")
            if key == "dyslexic" and not self._dyslexic_available:
                btn.setToolTip("OpenDyslexic font not found in assets/")
            btn.clicked.connect(lambda checked, k=key: self._set_font_type(k))
            self._font_type_btns[key] = btn
            row.addWidget(btn)
        content_layout.addLayout(row)

        # ---- Color Theme ----
        self._add_section_label(content_layout, "Color Theme")
        self._theme_btns = {}
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (key, label) in enumerate(THEME_OPTIONS):
            btn = QPushButton(label)
            btn.setMinimumSize(44, 44)
            btn.setAccessibleName(f"Theme: {label}")
            btn.setToolTip(f"Switch to {label} theme")
            btn.clicked.connect(lambda checked, k=key: self._set_theme(k))
            self._theme_btns[key] = btn
            grid.addWidget(btn, i // 2, i % 2)
        content_layout.addLayout(grid)

        # ---- Colorblind Support ----
        self._add_section_label(content_layout, "Colorblind Support")
        self._colorblind_btns = {}
        for key, label, desc in COLORBLIND_OPTIONS:
            text = f"{label} {desc}".strip()
            btn = QPushButton(text)
            btn.setMinimumSize(44, 44)
            btn.setAccessibleName(f"Colorblind mode: {label}")
            btn.clicked.connect(lambda checked, k=key: self._set_colorblind(k))
            self._colorblind_btns[key] = btn
            content_layout.addWidget(btn)

        # ---- Cursor Style ----
        self._add_section_label(content_layout, "Cursor Style")
        self._cursor_btns = {}
        row = QHBoxLayout()
        row.setSpacing(4)
        for key, label in CURSOR_OPTIONS:
            btn = QPushButton(label)
            btn.setMinimumSize(44, 44)
            btn.setAccessibleName(f"Cursor style: {label}")
            btn.clicked.connect(lambda checked, k=key: self._set_cursor(k))
            self._cursor_btns[key] = btn
            row.addWidget(btn)
        content_layout.addLayout(row)

        # ---- Toggle options ----
        self._add_section_label(content_layout, "More Options")

        # Reduced Motion
        self._reduced_motion_toggle = self._add_toggle_row(
            content_layout, "Reduced Motion", self._reduced_motion,
            self._on_reduced_motion_toggled
        )

        # Text Spacing
        self._text_spacing_toggle = self._add_toggle_row(
            content_layout, "Enhanced Text Spacing", self._text_spacing,
            self._on_text_spacing_toggled
        )

        # Enhanced Focus
        self._enhanced_focus_toggle = self._add_toggle_row(
            content_layout, "Enhanced Focus Indicators", self._enhanced_focus,
            self._on_enhanced_focus_toggled
        )

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._update_button_states()

    def _add_section_label(self, layout, text):
        label = QLabel(text)
        label.setObjectName("a11ySectionLabel")
        label.setAccessibleName(f"{text} section")
        layout.addWidget(label)

    def _add_toggle_row(self, layout, label_text, initial_state, callback):
        row_widget = QWidget()
        row_widget.setObjectName("a11yToggleRow")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 4)

        label = QLabel(label_text)
        label.setAccessibleName(f"{label_text} toggle")
        row_layout.addWidget(label)
        row_layout.addStretch()

        toggle = QPushButton("ON" if initial_state else "OFF")
        toggle.setCheckable(True)
        toggle.setChecked(initial_state)
        toggle.setFixedSize(52, 44)
        toggle.setAccessibleName(f"Toggle {label_text.lower()}")
        toggle.setToolTip(f"Enable/disable {label_text.lower()}")
        self._style_toggle(toggle, initial_state)
        toggle.clicked.connect(callback)
        row_layout.addWidget(toggle)

        layout.addWidget(row_widget)
        return toggle

    def _style_toggle(self, toggle, checked):
        # Find the label text from the parent row
        label_text = ""
        parent = toggle.parent()
        if parent:
            for child in parent.findChildren(QLabel):
                label_text = child.text()
                break
        if checked:
            toggle.setText("ON")
            toggle.setAccessibleName(f"Toggle {label_text.lower()}, currently ON")
            toggle.setStyleSheet(
                "QPushButton { background-color: #a23b84; color: white; "
                "border: none; border-radius: 22px; font-weight: bold; font-size: 11px; }"
                "QPushButton:focus { border: 3px solid #6f2fa6; }"
            )
        else:
            toggle.setText("OFF")
            toggle.setAccessibleName(f"Toggle {label_text.lower()}, currently OFF")
            toggle.setStyleSheet(
                "QPushButton { background-color: #9590a6; color: white; "
                "border: none; border-radius: 22px; font-weight: bold; font-size: 11px; }"
                "QPushButton:focus { border: 3px solid #6f2fa6; }"
            )

    def _update_button_states(self):
        """Update all button active/inactive objectNames to match QSS."""
        # Font size buttons
        for key, btn in self._font_size_btns.items():
            active = key == self._font_size
            btn.setObjectName("a11yPillActive" if active else "a11yPill")
            label = dict(FONT_SIZE_OPTIONS)[key]
            btn.setText(f"\u2713 {label}" if active else label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Font type buttons
        for key, btn in self._font_type_btns.items():
            active = key == self._font_type
            btn.setObjectName("a11yPillActive" if active else "a11yPill")
            label = dict(FONT_TYPE_OPTIONS)[key]
            btn.setText(f"\u2713 {label}" if active else label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Theme buttons
        for key, btn in self._theme_btns.items():
            active = key == self._theme
            btn.setObjectName("a11yThemeCardActive" if active else "a11yThemeCard")
            label = dict(THEME_OPTIONS)[key]
            btn.setText(f"\u2713 {label}" if active else label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Colorblind buttons
        colorblind_labels = {key: f"{label} {desc}".strip() for key, label, desc in COLORBLIND_OPTIONS}
        for key, btn in self._colorblind_btns.items():
            active = key == self._colorblind
            btn.setObjectName("a11yPillActive" if active else "a11yPill")
            label = colorblind_labels[key]
            btn.setText(f"\u2713 {label}" if active else label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Cursor buttons
        for key, btn in self._cursor_btns.items():
            active = key == self._cursor
            btn.setObjectName("a11yPillActive" if active else "a11yPill")
            label = dict(CURSOR_OPTIONS)[key]
            btn.setText(f"\u2713 {label}" if active else label)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_language_changed(self, index):
        code = self._language_combo.itemData(index)
        if code and code != self._language:
            self._language = code
            set_language(code)
            self._save_and_apply()

    def _save_and_apply(self):
        self._settings.setValue("a11y/language", self._language)
        self._settings.setValue("a11y/font_size", self._font_size)
        self._settings.setValue("a11y/font_type", self._font_type)
        self._settings.setValue("a11y/theme", self._theme)
        self._settings.setValue("a11y/colorblind", self._colorblind)
        self._settings.setValue("a11y/cursor", self._cursor)
        self._settings.setValue("a11y/reduced_motion", "true" if self._reduced_motion else "false")
        self._settings.setValue("a11y/text_spacing", "true" if self._text_spacing else "false")
        self._settings.setValue("a11y/enhanced_focus", "true" if self._enhanced_focus else "false")
        self._update_button_states()
        self.settings_changed.emit()

    def _set_font_size(self, size):
        self._font_size = size
        self._save_and_apply()

    def _set_font_type(self, font_type):
        self._font_type = font_type
        self._save_and_apply()

    def _set_theme(self, theme):
        self._theme = theme
        self._save_and_apply()

    def _set_colorblind(self, mode):
        self._colorblind = mode
        self._save_and_apply()

    def _set_cursor(self, style):
        self._cursor = style
        self._save_and_apply()

    def _on_reduced_motion_toggled(self):
        self._reduced_motion = self._reduced_motion_toggle.isChecked()
        self._style_toggle(self._reduced_motion_toggle, self._reduced_motion)
        self._save_and_apply()

    def _on_text_spacing_toggled(self):
        self._text_spacing = self._text_spacing_toggle.isChecked()
        self._style_toggle(self._text_spacing_toggle, self._text_spacing)
        self._save_and_apply()

    def _on_enhanced_focus_toggled(self):
        self._enhanced_focus = self._enhanced_focus_toggle.isChecked()
        self._style_toggle(self._enhanced_focus_toggle, self._enhanced_focus)
        self._save_and_apply()

    def get_current_settings(self):
        return {
            "language": self._language,
            "font_size": self._font_size,
            "font_type": self._font_type,
            "theme": self._theme,
            "colorblind": self._colorblind,
            "cursor": self._cursor,
            "reduced_motion": self._reduced_motion,
            "text_spacing": self._text_spacing,
            "enhanced_focus": self._enhanced_focus,
        }

    def toggle(self):
        self.setVisible(not self.isVisible())
        if self.isVisible():
            self.setFocus()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.panel_closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class FloatingAccessibilityButton(QPushButton):
    """Floating button that opens the accessibility panel — outline icon."""

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setObjectName("accessibilityButton")
        self.setAccessibleName("Open accessibility settings")
        self.setAccessibleDescription("Opens the accessibility options panel")
        self.setToolTip("Accessibility Settings")
        self.setFixedSize(48, 48)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor(255, 255, 255))
        pen.setWidthF(1.8)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = 24, 24
        # Head (outline circle)
        painter.drawEllipse(int(cx - 3), int(cy - 14), 7, 7)
        # Body line
        painter.drawLine(int(cx), int(cy - 7), int(cx), int(cy + 2))
        # Arms (outstretched)
        painter.drawLine(int(cx - 8), int(cy - 4), int(cx + 8), int(cy - 4))
        # Left leg
        painter.drawLine(int(cx), int(cy + 2), int(cx - 6), int(cy + 12))
        # Right leg
        painter.drawLine(int(cx), int(cy + 2), int(cx + 6), int(cy + 12))
        painter.end()


class CursorTrailOverlay(QWidget):
    """Transparent overlay that draws a fading trail behind the cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._trail_points = []  # list of (x, y, opacity)
        self._max_points = 18
        self._timer_id = None

    def start(self):
        """Start tracking and drawing the trail."""
        self.show()
        self.raise_()
        if self._timer_id is None:
            self._timer_id = self.startTimer(25)  # ~40 fps
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def stop(self):
        """Stop and hide the trail overlay."""
        if self._timer_id is not None:
            self.killTimer(self._timer_id)
            self._timer_id = None
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        self._trail_points.clear()
        self.hide()

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseMove:
            pos = event.globalPosition().toPoint()
            local = self.mapFromGlobal(pos)
            self._trail_points.append((local.x(), local.y(), 1.0))
            if len(self._trail_points) > self._max_points:
                self._trail_points = self._trail_points[-self._max_points:]
        return False

    def timerEvent(self, event):
        # Fade out old points
        self._trail_points = [
            (x, y, o - 0.06) for x, y, o in self._trail_points if o > 0.06
        ]
        self.update()

    def paintEvent(self, event):
        if not self._trail_points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for x, y, opacity in self._trail_points:
            radius = max(3, int(opacity * 8))
            color = QColor(162, 59, 132)  # primary purple
            color.setAlphaF(opacity * 0.6)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
        painter.end()


# Singleton reference for the cursor trail overlay
_cursor_trail = None


def apply_accessibility_settings(settings_dict):
    """Apply accessibility settings to the running QApplication."""
    app = QApplication.instance()
    if not app:
        return

    # Ensure bundled fonts are loaded (needed at startup before panel exists)
    _load_bundled_fonts()

    font_type = settings_dict.get("font_type", "default")
    font_family = "Arial, Helvetica, sans-serif"
    if font_type == "dyslexic":
        font_family = '"OpenDyslexic", Arial, Helvetica, sans-serif'
    elif font_type == "bionic":
        font_family = "Arial, Helvetica, sans-serif"

    font_size = FONT_SIZES.get(settings_dict.get("font_size", "default"), 13)
    theme = settings_dict.get("theme", "light")

    qss = generate_stylesheet(
        theme_name=theme,
        font_size=font_size,
        font_family=font_family,
        enhanced_focus=settings_dict.get("enhanced_focus", False),
        text_spacing=settings_dict.get("text_spacing", False),
        colorblind_mode=settings_dict.get("colorblind", "none"),
        font_type=font_type,
    )
    app.setStyleSheet(qss)

    # Apply cursor
    global _cursor_trail
    cursor_style = settings_dict.get("cursor", "default")
    while app.overrideCursor() is not None:
        app.restoreOverrideCursor()

    # Stop any existing cursor trail
    if _cursor_trail is not None:
        _cursor_trail.stop()
        _cursor_trail.deleteLater()
        _cursor_trail = None

    if cursor_style == "crosshair":
        app.setOverrideCursor(QCursor(Qt.CursorShape.CrossCursor))
    elif cursor_style == "large":
        # Create a large arrow cursor
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0))
        painter.setPen(QColor(255, 255, 255))
        arrow = QPolygonF([
            QPointF(2, 2), QPointF(2, 26), QPointF(10, 20),
            QPointF(18, 28), QPointF(22, 24), QPointF(14, 16), QPointF(22, 14),
        ])
        painter.drawPolygon(arrow)
        painter.end()
        app.setOverrideCursor(QCursor(pixmap, 2, 2))
    elif cursor_style == "trail":
        # Cursor trail is attached to the active window later via main_window
        pass

    # Apply font
    font = QFont(font_family.split(",")[0].strip().strip('"'), font_size)
    app.setFont(font)


def load_initial_settings():
    """Load accessibility settings from QSettings and return as dict."""
    settings = get_settings()
    lang = settings.value("a11y/language", "en")
    set_language(lang)
    return {
        "language": lang,
        "font_size": settings.value("a11y/font_size", "default"),
        "font_type": settings.value("a11y/font_type", "default"),
        "theme": settings.value("a11y/theme", "dark"),
        "colorblind": settings.value("a11y/colorblind", "none"),
        "cursor": settings.value("a11y/cursor", "default"),
        "reduced_motion": settings.value("a11y/reduced_motion", "false") == "true",
        "text_spacing": settings.value("a11y/text_spacing", "false") == "true",
        "enhanced_focus": settings.value("a11y/enhanced_focus", "false") == "true",
    }

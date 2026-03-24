"""Theme manager for La Mia Scribe — matching TIP Business Tools themes."""

import subprocess


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r, g, b):
    return f"#{max(0,min(255,int(r))):02x}{max(0,min(255,int(g))):02x}{max(0,min(255,int(b))):02x}"


def _lighten(hex_color, amount=0.15):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount)


def _darken(hex_color, amount=0.15):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(r * (1 - amount), g * (1 - amount), b * (1 - amount))


def _desaturate(hex_color):
    r, g, b = _hex_to_rgb(hex_color)
    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
    return _rgb_to_hex(gray, gray, gray)


def _rgba(hex_color, alpha):
    """Convert hex + alpha (0-255) to rgba() string for QSS."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


# Font size presets (px)
FONT_SIZES = {
    "small": 11,
    "default": 13,
    "large": 15,
    "xl": 17,
    "xxl": 19,
}


# Theme definitions matching TIP Business Tools tokens.css
THEMES = {
    "light": {
        "bg": "#f8f7fa", "surface": "#ffffff", "surface_alt": "#f0f0fa",
        "border": "#e2dfe8", "text": "#1a1625", "text_secondary": "#5c5672",
        "text_muted": "#9590a6", "text_inverse": "#ffffff",
        "primary": "#a23b84", "secondary": "#3a2b95", "accent": "#6f2fa6",
        "success": "#2d8a4e", "warning": "#c47f17", "error": "#c53030", "info": "#2b6cb0",
        "sidebar_bg": "#1e1e2e", "sidebar_text": "#e0e0f0", "sidebar_border": "#3a3a5e",
        "sidebar_input": "#2a2a42", "sidebar_input_border": "#4a4a6e",
    },
    "dark": {
        "bg": "#1a1625", "surface": "#2a2640", "surface_alt": "#352f50",
        "border": "#3d3660", "text": "#ffffff", "text_secondary": "#d0cce0",
        "text_muted": "#a8a0c0", "text_inverse": "#1a1625",
        "primary": "#8e3572", "secondary": "#5a4bb5", "accent": "#9055c0",
        "success": "#4caf6a", "warning": "#e0a030", "error": "#f07070", "info": "#4a90d0",
        "sidebar_bg": "#14101f", "sidebar_text": "#ffffff", "sidebar_border": "#2a2640",
        "sidebar_input": "#1e1a30", "sidebar_input_border": "#3d3660",
    },
    "high-contrast": {
        "bg": "#ffffff", "surface": "#ffffff", "surface_alt": "#f0f0f0",
        "border": "#000000", "text": "#000000", "text_secondary": "#1a1a1a",
        "text_muted": "#333333", "text_inverse": "#ffffff",
        "primary": "#7a2d64", "secondary": "#2a1d70", "accent": "#52207d",
        "success": "#1a6b32", "warning": "#8a5a00", "error": "#a12020", "info": "#1a4e8a",
        "sidebar_bg": "#000000", "sidebar_text": "#ffffff", "sidebar_border": "#333333",
        "sidebar_input": "#1a1a1a", "sidebar_input_border": "#666666",
    },
    "sepia": {
        "bg": "#f4ecd8", "surface": "#faf3e0", "surface_alt": "#efe6cc",
        "border": "#d4c5a0", "text": "#3d3222", "text_secondary": "#6b5d46",
        "text_muted": "#8d7e63", "text_inverse": "#faf3e0",
        "primary": "#8b6914", "secondary": "#5a4a20", "accent": "#7a5a30",
        "success": "#4a7a30", "warning": "#9a7a10", "error": "#a03020", "info": "#4a6a8a",
        "sidebar_bg": "#2e2818", "sidebar_text": "#f4ecd8", "sidebar_border": "#4a4030",
        "sidebar_input": "#3a3020", "sidebar_input_border": "#5a5040",
    },
    "blue-light": {
        "bg": "#f5f0e0", "surface": "#fdfaf0", "surface_alt": "#f0ebd8",
        "border": "#d8d0b8", "text": "#2e2a1e", "text_secondary": "#5c5545",
        "text_muted": "#8a826e", "text_inverse": "#fdfaf0",
        "primary": "#8a7a40", "secondary": "#6a5a80", "accent": "#6a5a80",
        "success": "#4a7a30", "warning": "#9a7a10", "error": "#a03020", "info": "#4a6a7a",
        "sidebar_bg": "#2a2518", "sidebar_text": "#f5f0e0", "sidebar_border": "#4a4530",
        "sidebar_input": "#352f20", "sidebar_input_border": "#5a5540",
    },
    "pastel": {
        "bg": "#f8f0f8", "surface": "#fff5ff", "surface_alt": "#f0e8f2",
        "border": "#e0d0e0", "text": "#2a1a2e", "text_secondary": "#5c4c60",
        "text_muted": "#8a7a90", "text_inverse": "#fff5ff",
        "primary": "#9a60b0", "secondary": "#b080c0", "accent": "#9a60b0",
        "success": "#60a070", "warning": "#c0a040", "error": "#c06070", "info": "#6090c0",
        "sidebar_bg": "#2a1a2e", "sidebar_text": "#f8f0f8", "sidebar_border": "#4a3a50",
        "sidebar_input": "#352838", "sidebar_input_border": "#5a4a60",
    },
    "forest": {
        "bg": "#1a2e1f", "surface": "#243828", "surface_alt": "#2e4232",
        "border": "#3d5040", "text": "#e8f0ea", "text_secondary": "#b0c8b4",
        "text_muted": "#7a9a7e", "text_inverse": "#1a2e1f",
        "primary": "#3d6d44", "secondary": "#508858", "accent": "#3d6d44",
        "success": "#60b068", "warning": "#c0a840", "error": "#c06050", "info": "#60a0c0",
        "sidebar_bg": "#12201a", "sidebar_text": "#e8f0ea", "sidebar_border": "#2e4232",
        "sidebar_input": "#1a2e22", "sidebar_input_border": "#3d5040",
        "header_primary": "#3d6840", "header_secondary": "#1a2e1f",
    },
}


def _apply_colorblind(theme, mode):
    """Return a copy of theme with colors adjusted for colorblind mode."""
    if mode == "none":
        return theme
    adjusted = dict(theme)
    if mode == "achromatopsia":
        for key in adjusted:
            if isinstance(adjusted[key], str) and adjusted[key].startswith("#") and len(adjusted[key]) == 7:
                adjusted[key] = _desaturate(adjusted[key])
        return adjusted
    if mode in ("protanopia", "deuteranopia"):
        adjusted["primary"] = "#4a6aa0"
        adjusted["error"] = "#cc8800"
        adjusted["success"] = "#0066cc"
    elif mode == "tritanopia":
        adjusted["secondary"] = "#cc4488"
        adjusted["info"] = "#cc6600"
    return adjusted


def generate_stylesheet(theme_name="light", font_size=13,
                        font_family="Arial, Helvetica, sans-serif",
                        enhanced_focus=False, text_spacing=False,
                        colorblind_mode="none", font_type="default"):
    """Generate the full QSS stylesheet for the given settings."""
    if theme_name == "system":
        theme_name = "dark" if is_system_dark_mode() else "light"

    theme = THEMES.get(theme_name, THEMES["light"])
    theme = _apply_colorblind(theme, colorblind_mode)
    t = theme

    # Derived colors
    primary_hover = _lighten(t["primary"], 0.15)
    primary_pressed = _darken(t["primary"], 0.15)
    sidebar_btn_bg = _lighten(t["sidebar_bg"], 0.12)
    sidebar_btn_border = _lighten(t["sidebar_bg"], 0.22)
    sidebar_btn_hover = _lighten(t["sidebar_bg"], 0.18)
    sidebar_checkbox_border = _lighten(t["sidebar_bg"], 0.3)
    sidebar_group_title = _lighten(t["sidebar_text"], 0.1)
    drop_zone_border = _lighten(t["sidebar_bg"], 0.3)
    drop_zone_text = _lighten(t["sidebar_bg"], 0.45)
    progress_bg = _lighten(t["border"], 0.3) if theme_name not in ("dark", "forest") else t["surface_alt"]
    header_primary = t.get("header_primary", t["primary"])
    header_secondary = t.get("header_secondary", t["secondary"])

    # Focus width
    fw = "4px" if enhanced_focus else "3px"
    fc = "#000000" if enhanced_focus and theme_name == "high-contrast" else t["primary"]

    # Font sizes
    fs = font_size
    fs_sm = max(9, fs - 2)
    fs_lg = fs + 1
    fs_xxl = fs + 9

    # Text spacing — bionic mode also benefits from slight extra spacing
    if text_spacing:
        ts_letter = "letter-spacing: 1.5px;"
        ts_word = "word-spacing: 2px;"
    elif font_type == "bionic":
        ts_letter = "letter-spacing: 0.5px;"
        ts_word = "word-spacing: 1px;"
    else:
        ts_letter = ""
        ts_word = ""

    er, eg, eb = _hex_to_rgb(t["error"])

    qss = f"""
/* La Mia Scribe — Theme: {theme_name} */

QWidget {{
    font-family: {font_family};
    font-size: {fs}px;
    color: {t["text"]};
    {ts_letter}
    {ts_word}
}}

QMainWindow {{
    background-color: {t["bg"]};
}}

/* ---- Header Bar ---- */
#headerBar {{
    background-color: {t["sidebar_bg"]};
    border-bottom: 1px solid {t["sidebar_border"]};
    min-height: 50px;
    padding: 0 12px;
}}

#headerLabel {{
    color: white;
    font-size: {fs_xxl}px;
    font-weight: bold;
    background: transparent;
}}

#headerSubLabel {{
    color: rgba(255, 255, 255, 0.85);
    font-size: {fs_sm}px;
    background: transparent;
}}

#userLabel {{
    color: rgba(255, 255, 255, 0.9);
    font-size: {fs_sm}px;
    background: transparent;
}}

#logoutBtn {{
    background: rgba(255,255,255,0.15);
    color: white;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px;
    padding: 4px 14px;
    font-size: {fs_sm}px;
}}

#logoutBtn:hover {{
    background: rgba(255,255,255,0.25);
}}

#logoutBtn:focus {{
    border: {fw} solid white;
}}

/* ---- Left Panel (Sidebar) ---- */
#leftPanel {{
    background-color: {t["sidebar_bg"]};
    border-right: 1px solid {t["sidebar_border"]};
}}

#leftPanel QLabel {{
    color: {t["sidebar_text"]};
    font-size: {fs}px;
}}

#leftPanel QGroupBox {{
    color: {t["sidebar_text"]};
    font-weight: bold;
    font-size: {fs}px;
    border: 1px solid {t["sidebar_border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 14px;
}}

#leftPanel QGroupBox QLabel {{
    font-weight: normal;
}}

#leftPanel QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {sidebar_group_title};
}}

#leftPanel QComboBox {{
    background-color: {t["sidebar_input"]};
    color: {t["sidebar_text"]};
    border: 1px solid {t["sidebar_input_border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 28px;
}}

#leftPanel QComboBox:focus {{
    border: {fw} solid {fc};
}}

#leftPanel QComboBox::drop-down {{
    border-left: 1px solid {t["sidebar_input_border"]};
    width: 24px;
}}

#leftPanel QComboBox QAbstractItemView {{
    background-color: {t["sidebar_input"]};
    color: {t["sidebar_text"]};
    selection-background-color: {t["primary"]};
    selection-color: white;
    border: 1px solid {t["sidebar_input_border"]};
}}

#leftPanel QCheckBox {{
    color: {t["sidebar_text"]};
    spacing: 8px;
    min-height: 44px;
}}

#leftPanel QCheckBox::indicator {{
    width: 24px;
    height: 24px;
    border: 2px solid {sidebar_checkbox_border};
    border-radius: 3px;
    background-color: {t["sidebar_input"]};
}}

#leftPanel QCheckBox::indicator:checked {{
    background-color: {t["primary"]};
    border-color: {t["primary"]};
}}

#leftPanel QCheckBox::indicator:focus {{
    border: {fw} solid {fc};
}}

#leftPanel QLineEdit {{
    background-color: {t["sidebar_input"]};
    color: {t["sidebar_text"]};
    border: 1px solid {t["sidebar_input_border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 28px;
}}

#leftPanel QLineEdit:focus {{
    border: {fw} solid {fc};
}}

#leftPanel QPushButton {{
    background-color: {sidebar_btn_bg};
    color: {t["sidebar_text"]};
    border: 1px solid {sidebar_btn_border};
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 32px;
    min-width: 44px;
}}

#leftPanel QPushButton:hover {{
    background-color: {sidebar_btn_hover};
}}

#leftPanel QPushButton:pressed {{
    background-color: {sidebar_btn_border};
}}

#leftPanel QPushButton:focus {{
    border: {fw} solid {fc};
}}

/* ---- Transcribe Button ---- */
#transcribeButton {{
    background-color: {t["primary"]};
    color: white;
    font-size: {fs_lg}px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    min-height: 48px;
    padding: 8px 20px;
}}

#transcribeButton:hover {{
    background-color: {primary_hover};
}}

#transcribeButton:pressed {{
    background-color: {primary_pressed};
}}

#transcribeButton:focus {{
    border: {fw} solid {t["accent"]};
    outline: none;
}}

#transcribeButton:disabled {{
    background-color: {_lighten(t["sidebar_bg"], 0.25)};
    color: {t["text_muted"]};
}}

/* ---- Drag-Drop Zone ---- */
#dropZone {{
    background-color: {t["sidebar_input"]};
    border: 2px dashed {drop_zone_border};
    border-radius: 8px;
    min-height: 80px;
    color: {drop_zone_text};
}}

#dropZone[dragActive="true"] {{
    border-color: {t["primary"]};
    background-color: {_lighten(t["sidebar_input"], 0.08)};
}}

/* ---- Content Area ---- */
#contentArea {{
    background-color: {t["bg"]};
    padding: 8px;
}}

/* ---- Transcript Viewer ---- */
#transcriptViewer {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 8px;
    padding: 20px;
    font-size: {fs}px;
    line-height: 1.6;
    selection-background-color: {t["primary"]};
    selection-color: white;
}}

#transcriptViewer:focus {{
    border: {fw} solid {fc};
}}

/* ---- Word Count Label ---- */
#wordCountLabel {{
    color: {t["text_muted"]};
    font-size: {fs_sm}px;
    padding: 8px 8px;
    margin-top: 4px;
}}

/* ---- Find Bar ---- */
#findBar {{
    background-color: {t["surface_alt"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    padding: 4px;
}}

#findBar QLineEdit {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 28px;
}}

#findBar QLineEdit:focus {{
    border: {fw} solid {fc};
}}

#findBar QPushButton {{
    background-color: {t["primary"]};
    color: white;
    border: none;
    border-radius: 3px;
    padding: 4px 12px;
    min-height: 44px;
    min-width: 44px;
}}

#findBar QPushButton:hover {{
    background-color: {primary_hover};
}}

#findBar QPushButton:focus {{
    border: {fw} solid {t["accent"]};
}}

/* ---- Progress Widget ---- */
QProgressBar {{
    background-color: {progress_bg};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    min-height: 20px;
    text-align: center;
    color: {t["text"]};
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t["primary"]}, stop:1 {t["accent"]});
    border-radius: 3px;
}}

#stepLabel {{
    color: {t["text_secondary"]};
    font-size: {fs_sm}px;
    padding: 6px 4px;
}}

#logToggleButton {{
    background: none;
    border: none;
    color: {t["accent"]};
    font-size: {fs_sm}px;
    padding: 8px 4px;
    min-height: 44px;
}}

#logToggleButton:hover {{
    color: {t["primary"]};
}}

#logToggleButton:focus {{
    border: {fw} solid {fc};
    border-radius: 3px;
}}

#logPanel {{
    background-color: {t["sidebar_bg"]};
    color: #a0f0a0;
    font-family: "Courier New", Courier, monospace;
    font-size: {fs_sm}px;
    border: 1px solid {t["sidebar_border"]};
    border-radius: 4px;
    padding: 8px;
}}

/* ---- Export Panel ---- */
#exportPanel {{
    background-color: {t["surface_alt"]};
    border: 1px solid {t["border"]};
    border-radius: 8px;
    padding: 20px;
    margin-top: 12px;
}}

#exportPanelTitle {{
    color: {t["text"]};
    font-weight: bold;
    font-size: {fs_lg}px;
    margin-bottom: 4px;
}}

#exportPanel QCheckBox {{
    color: {t["text"]};
    spacing: 10px;
    min-height: 44px;
    font-size: {fs}px;
    margin-right: 12px;
}}

#exportPanel QCheckBox::indicator {{
    width: 24px;
    height: 24px;
    border: 2px solid {t["text_muted"]};
    border-radius: 3px;
    background-color: {t["surface"]};
}}

#exportPanel QCheckBox::indicator:checked {{
    background-color: {t["primary"]};
    border-color: {t["primary"]};
}}

#exportPanel QCheckBox::indicator:focus {{
    border: {fw} solid {fc};
}}

#exportPanel QPushButton {{
    background-color: {t["primary"]};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    min-height: 44px;
    min-width: 44px;
    margin-right: 10px;
}}

#exportPanel QPushButton:hover {{
    background-color: {primary_hover};
}}

#exportPanel QPushButton:pressed {{
    background-color: {primary_pressed};
}}

#exportPanel QPushButton:focus {{
    border: {fw} solid {t["accent"]};
}}

#exportPanel QRadioButton {{
    color: {t["text"]};
    spacing: 8px;
    min-height: 44px;
}}

#exportPanel QRadioButton:focus {{
    border: {fw} solid {fc};
    border-radius: 3px;
}}

/* ---- Language Toggle ---- */
#languageToggle QPushButton {{
    background-color: {t["surface_alt"]};
    color: {t["secondary"]};
    border: 1px solid {t["border"]};
    border-radius: 3px;
    padding: 4px 14px;
    min-height: 28px;
    min-width: 44px;
    font-weight: bold;
}}

#languageToggle QPushButton:checked {{
    background-color: {t["secondary"]};
    color: white;
    border-color: {t["secondary"]};
}}

#languageToggle QPushButton:focus {{
    border: {fw} solid {fc};
}}

/* ---- Status Bar ---- */
QStatusBar {{
    background-color: {t["sidebar_bg"]};
    color: {t["sidebar_text"]};
    font-size: {fs_sm}px;
    border-top: 1px solid {t["sidebar_border"]};
    min-height: 28px;
    padding: 0 10px;
}}

QStatusBar QLabel {{
    color: {t["sidebar_text"]};
    padding: 0 8px;
}}

/* ---- Scroll Bars ---- */
QScrollBar:vertical {{
    background-color: {t["surface_alt"]};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {t["text_muted"]};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {t["text_secondary"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {t["surface_alt"]};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {t["text_muted"]};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {t["text_secondary"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---- Tooltips ---- */
QToolTip {{
    background-color: {t["sidebar_input"]};
    color: {t["sidebar_text"]};
    border: 1px solid {t["sidebar_input_border"]};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: {fs_sm}px;
}}

/* ---- General Focus Ring ---- */
QPushButton:focus,
QComboBox:focus,
QLineEdit:focus,
QTextEdit:focus,
QCheckBox:focus,
QRadioButton:focus {{
    outline: none;
}}

/* ---- Settings Dialog ---- */
#settingsDialog QGroupBox {{
    font-weight: bold;
    border: 1px solid {t["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
}}

#settingsDialog QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {t["secondary"]};
}}

/* ---- Ollama Status ---- */
#ollamaStatusRunning {{
    color: {t["success"]};
    font-weight: bold;
}}

#ollamaStatusStopped {{
    color: {t["error"]};
    font-weight: bold;
}}

/* ---- File Info Label ---- */
#fileInfoLabel {{
    color: {t["text_muted"]};
    font-size: {fs_sm}px;
    padding: 4px 0;
}}

/* ---- Clear Button ---- */
#clearButton {{
    background-color: transparent;
    color: {t["error"]};
    border: 1px solid {t["error"]};
    border-radius: 4px;
    font-size: {fs_sm}px;
    min-height: 44px;
    padding: 2px 12px;
}}

#clearButton:hover {{
    background-color: rgba({er}, {eg}, {eb}, 25);
}}

#clearButton:focus {{
    border: {fw} solid {fc};
}}

/* ---- Accessibility Button ---- */
#accessibilityButton {{
    background-color: {t["primary"]};
    color: white;
    border: 2px solid {_lighten(t["primary"], 0.2)};
    border-radius: 24px;
    font-size: 18px;
    font-weight: bold;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
}}

#accessibilityButton:hover {{
    background-color: {primary_hover};
    border-color: {_lighten(t["primary"], 0.3)};
}}

#accessibilityButton:focus {{
    border: {fw} solid {t["accent"]};
}}

/* ---- Accessibility Panel ---- */
#accessibilityPanel {{
    background-color: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 12px;
}}

#accessibilityPanel QLabel {{
    color: {t["text"]};
}}

#a11yHeader {{
    background-color: {t["sidebar_bg"]};
    border-bottom: 1px solid {t["sidebar_border"]};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    padding: 12px 16px;
}}

#a11yHeader QLabel {{
    color: white;
    font-size: {fs_lg}px;
    font-weight: bold;
    background: transparent;
}}

#a11yCloseBtn {{
    background: rgba(255,255,255,0.3);
    color: white;
    border: none;
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 14px;
    font-weight: bold;
}}

#a11yCloseBtn:hover {{
    background: rgba(255,255,255,0.45);
}}

#a11yCloseBtn:focus {{
    border: 2px solid white;
}}

#a11ySectionLabel {{
    color: {t["text_secondary"]};
    font-size: {fs_sm}px;
    font-weight: bold;
    padding: 8px 0 4px 0;
}}

/* ---- Accessibility Pill Buttons ---- */
#a11yPill {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 14px;
    padding: 4px 6px;
    min-height: 44px;
    font-size: {fs_sm}px;
}}

#a11yPill:hover {{
    border-color: {t["primary"]};
}}

#a11yPillActive {{
    background-color: {t["primary"]};
    color: white;
    border: 1px solid {t["primary"]};
    border-radius: 14px;
    padding: 4px 6px;
    min-height: 44px;
    font-size: {fs_sm}px;
}}

#a11yPillActive:hover {{
    background-color: {primary_hover};
}}

/* ---- Theme Card Buttons ---- */
#a11yThemeCard {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
    border: 2px solid {t["border"]};
    border-radius: 8px;
    padding: 6px;
    min-height: 44px;
    font-size: {fs_sm}px;
}}

#a11yThemeCard:hover {{
    border-color: {t["primary"]};
}}

#a11yThemeCardActive {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
    border: 2px solid {t["primary"]};
    border-radius: 8px;
    padding: 6px;
    min-height: 44px;
    font-size: {fs_sm}px;
}}

/* ---- Toggle Row ---- */
#a11yToggleRow {{
    padding: 4px 0;
}}

#a11yToggleRow QLabel {{
    color: {t["text"]};
    font-size: {fs}px;
}}

/* ---- Login Window ---- */
#loginTopArea {{
    background-color: {t["sidebar_bg"]};
}}

#loginFormArea {{
    background-color: {t["bg"]};
}}

#loginTitle {{
    color: {t["secondary"]};
    font-size: 20px;
    font-weight: bold;
}}

#loginSubtitle {{
    color: {t["text_muted"]};
    font-size: {fs}px;
}}

#loginFieldLabel {{
    color: {t["text"]};
    font-weight: bold;
}}

#loginInput {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 44px;
}}

#loginInput:focus {{
    border: {fw} solid {fc};
}}

#loginPrimaryBtn {{
    background-color: {t["primary"]};
    color: white;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    min-height: 48px;
}}

#loginPrimaryBtn:hover {{
    background-color: {primary_hover};
}}

#loginPrimaryBtn:focus {{
    border: {fw} solid {t["accent"]};
}}

#loginErrorLabel {{
    color: {t["error"]};
    font-size: {fs_sm}px;
}}

#loginSwitchLabel {{
    color: {t["text_muted"]};
}}

#loginSwitchBtn {{
    background: none;
    border: none;
    color: {t["primary"]};
    font-weight: bold;
    text-decoration: underline;
}}

#loginSwitchBtn:hover {{
    color: {t["accent"]};
}}

#loginCheckbox {{
    color: {t["text"]};
    spacing: 8px;
    min-height: 44px;
    font-size: {fs}px;
}}

#loginCheckbox::indicator {{
    width: 24px;
    height: 24px;
    border: 2px solid {t["border"]};
    border-radius: 3px;
    background-color: {t["surface"]};
}}

#loginCheckbox::indicator:checked {{
    background-color: {t["primary"]};
    border-color: {t["primary"]};
}}

#loginCheckbox::indicator:focus {{
    border: {fw} solid {fc};
}}

#loginSwitchBtn:focus {{
    border: {fw} solid {fc};
    border-radius: 3px;
}}

#loginAppTitle {{
    color: white;
    font-size: 22px;
    font-weight: bold;
    background: transparent;
}}

#loginTagline {{
    color: rgba(255, 255, 255, 0.85);
    font-size: 12px;
    background: transparent;
}}

/* ---- QMessageBox ---- */
QMessageBox {{
    background-color: {t["surface"]};
}}

QMessageBox QLabel {{
    color: {t["text"]};
    font-size: {fs}px;
}}

QMessageBox QPushButton {{
    background-color: {t["primary"]};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 20px;
    min-height: 32px;
    min-width: 80px;
}}

QMessageBox QPushButton:hover {{
    background-color: {primary_hover};
}}

QMessageBox QPushButton:focus {{
    border: {fw} solid {t["accent"]};
}}

/* ---- Dashboard ---- */
#dashboardBtn {{
    background: rgba(255,255,255,0.15);
    color: white;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px;
    padding: 4px 14px;
    font-size: {fs_sm}px;
}}

#dashboardBtn:hover {{
    background: rgba(255,255,255,0.25);
}}

#dashboardBtn:focus {{
    border: {fw} solid white;
}}

#tutorialBtn {{
    background: rgba(255,255,255,0.15);
    color: white;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px;
    padding: 4px 14px;
    font-size: {fs_sm}px;
}}

#tutorialBtn:hover {{
    background: rgba(255,255,255,0.25);
}}

#tutorialBtn:focus {{
    border: {fw} solid white;
}}

/* ---- Tutorial Dialog ---- */
#tutorialDialog {{
    background: {t["surface"]};
}}

#tutorialStepLabel {{
    color: {t["text_secondary"]};
    font-size: {fs_sm}px;
}}

#tutorialTitle {{
    color: {t["text"]};
}}

#tutorialBody {{
    color: {t["text"]};
    line-height: 1.5;
}}

#tutorialPrevBtn, #tutorialNextBtn {{
    background: {t["primary"]};
    color: {t["bg"]};
    border: none;
    border-radius: 6px;
    padding: 6px 20px;
    font-size: {fs}px;
    font-weight: bold;
}}

#tutorialPrevBtn:hover, #tutorialNextBtn:hover {{
    background: {_lighten(t["primary"], 0.12)};
}}

#tutorialPrevBtn:disabled {{
    background: {t["border"]};
    color: {t["text_secondary"]};
}}

#tutorialPrevBtn:focus, #tutorialNextBtn:focus, #tutorialCloseBtn:focus {{
    border: {fw} solid {fc};
}}

#tutorialCloseBtn {{
    background: transparent;
    color: {t["text_secondary"]};
    border: 1px solid {t["border"]};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: {fs}px;
}}

#tutorialCloseBtn:hover {{
    background: {t["surface_alt"]};
}}

#dashboardTitle {{
    color: {t["text"]};
    font-size: {fs_lg}px;
    font-weight: bold;
    padding: 8px 4px;
}}

#dashboardRefreshBtn {{
    background-color: {t["surface_alt"]};
    color: {t["text_secondary"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    padding: 4px 14px;
    font-size: {fs_sm}px;
}}

#dashboardRefreshBtn:hover {{
    border-color: {t["primary"]};
}}

#dashboardEmpty {{
    color: {t["text_muted"]};
    font-size: {fs_lg}px;
    padding: 40px;
}}

#projectCard {{
    background-color: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 8px;
    padding: 4px;
}}

#projectCard:hover {{
    border-color: {t["primary"]};
}}

#projectCardTitle {{
    color: {t["text"]};
    font-size: {fs_lg}px;
    font-weight: bold;
}}

#projectCardDate {{
    color: {t["text_muted"]};
    font-size: {fs_sm}px;
}}

#projectCardInfo {{
    color: {t["text_secondary"]};
    font-size: {fs_sm}px;
}}

#projectCardPreview {{
    color: {t["text_muted"]};
    font-size: {fs_sm}px;
    padding: 4px 0;
}}

#projectCardNoteLabel {{
    color: {t["text_secondary"]};
    font-size: {fs_sm}px;
    font-weight: bold;
}}

#projectCardNote {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    padding: 6px;
    font-size: {fs_sm}px;
}}

#projectCardNote:focus {{
    border: {fw} solid {fc};
}}

#projectOpenBtn {{
    background: {t["primary"]};
    color: {t["bg"]};
    border: none;
    border-radius: 6px;
    min-width: 120px;
    min-height: 44px;
    padding: 4px 16px;
    font-size: {fs}px;
    font-weight: bold;
}}

#projectOpenBtn:hover {{
    background: {_lighten(t["primary"], 0.12)};
}}

#projectOpenBtn:focus {{
    border: {fw} solid {fc};
}}

#projectDeleteBtn {{
    background: transparent;
    color: {t["error"]};
    border: 1px solid {t["error"]};
    border-radius: 22px;
    min-width: 44px;
    min-height: 44px;
    font-size: 16px;
    font-weight: bold;
}}

#projectDeleteBtn:hover {{
    background-color: rgba({er}, {eg}, {eb}, 25);
}}

#projectDeleteBtn:focus {{
    border: {fw} solid {fc};
}}

/* ---- Dashboard Folder Sidebar ---- */
#folderSidebar {{
    background-color: {t["surface"]};
    border-right: 1px solid {t["border"]};
    border-radius: 8px 0 0 8px;
}}

#folderItemBtn {{
    background-color: transparent;
    color: {t["text"]};
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    text-align: left;
    font-size: {fs}px;
    min-height: 36px;
}}

#folderItemBtn:hover {{
    background-color: {t["surface_alt"]};
}}

#folderItemBtn[active="true"] {{
    background-color: {_rgba(t["primary"], 30)};
    color: {t["primary"]};
    border-left: 3px solid {t["primary"]};
    font-weight: bold;
}}

#folderItemBtn:focus {{
    border: {fw} solid {fc};
}}

#newFolderBtn {{
    background-color: transparent;
    color: {t["primary"]};
    border: 1px dashed {t["primary"]};
    border-radius: 4px;
    padding: 6px 12px;
    text-align: left;
    font-size: {fs}px;
    min-height: 36px;
}}

#newFolderBtn:hover {{
    background-color: {_rgba(t["primary"], 20)};
}}

#newFolderBtn:focus {{
    border: {fw} solid {fc};
}}

/* ---- Dashboard Search Bar ---- */
#dashboardSearchBar {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: {fs}px;
}}

#dashboardSearchBar:focus {{
    border: {fw} solid {fc};
}}

/* ---- Project Folder Button ---- */
#projectFolderBtn {{
    background-color: {t["surface_alt"]};
    color: {t["text_secondary"]};
    border: 1px solid {t["border"]};
    border-radius: 6px;
    min-width: 120px;
    min-height: 44px;
    padding: 4px 16px;
    font-size: {fs}px;
}}

#projectFolderBtn:hover {{
    border-color: {t["primary"]};
    color: {t["primary"]};
}}

#projectFolderBtn:focus {{
    border: {fw} solid {fc};
}}

/* ---- Password Toggle ---- */
#loginPasswordToggle {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    min-width: 44px;
    min-height: 44px;
    max-width: 60px;
    font-size: {fs_sm}px;
    font-weight: bold;
    padding: 4px 8px;
}}

#loginPasswordToggle:hover {{
    border-color: {t["primary"]};
}}

#loginPasswordToggle:focus {{
    border: {fw} solid {fc};
}}
"""
    return qss


def is_system_dark_mode():
    """Check if macOS is in dark mode."""
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True
        )
        return "dark" in result.stdout.lower()
    except Exception:
        return False


def get_effective_theme(theme_name):
    """Resolve 'system' to actual theme."""
    if theme_name == "system":
        return "dark" if is_system_dark_mode() else "light"
    return theme_name

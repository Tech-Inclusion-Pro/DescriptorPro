"""Login and Register window for La Mia Scribe."""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QMessageBox, QFrame, QSizePolicy,
    QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

from core.user_db import authenticate_user, register_user
from app.settings_dialog import get_settings
from app.accessibility_panel import announce
from core.i18n import tr


def _get_logo_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")


class LoginPage(QWidget):
    """Login form."""

    login_success = pyqtSignal(str)  # emits display name
    switch_to_register = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = get_settings()
        self._setup_ui()
        self._load_saved_credentials()

    def _load_saved_credentials(self):
        """Pre-fill username/password if 'Save login info' was checked."""
        saved = self._settings.value("login/save_credentials", "false") == "true"
        if saved:
            username = self._settings.value("login/username", "")
            password = self._settings.value("login/password", "")
            if username:
                self.username_input.setText(username)
            if password:
                self.password_input.setText(password)
            self.save_login_cb.setChecked(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 20, 40, 20)

        title = QLabel(tr("sign_in"))
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setAccessibleName(tr("sign_in"))
        layout.addWidget(title)

        subtitle = QLabel(tr("welcome_back"))
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # Username
        username_label = QLabel(tr("username"))
        username_label.setObjectName("loginFieldLabel")
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText(tr("enter_username"))
        self.username_input.setMinimumHeight(44)
        self.username_input.setAccessibleName(tr("username"))
        self.username_input.setToolTip(tr("username"))
        layout.addWidget(self.username_input)
        username_label.setBuddy(self.username_input)

        # Password
        password_label = QLabel(tr("password"))
        password_label.setObjectName("loginFieldLabel")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText(tr("enter_password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.setAccessibleName(tr("password"))
        self.password_input.setToolTip(tr("password"))
        self.password_input.returnPressed.connect(self._on_login)
        password_label.setBuddy(self.password_input)

        # Password row with toggle
        password_row = QHBoxLayout()
        password_row.setSpacing(4)
        password_row.addWidget(self.password_input)

        self.password_toggle = QPushButton(tr("show"))
        self.password_toggle.setObjectName("loginPasswordToggle")
        self.password_toggle.setFixedSize(60, 44)
        self.password_toggle.setAccessibleName(tr("show"))
        self.password_toggle.clicked.connect(self._toggle_password_visibility)
        password_row.addWidget(self.password_toggle)

        layout.addLayout(password_row)

        # Save login info checkbox
        self.save_login_cb = QCheckBox(tr("save_login"))
        self.save_login_cb.setObjectName("loginCheckbox")
        self.save_login_cb.setMinimumHeight(44)
        self.save_login_cb.setAccessibleName(tr("save_login"))
        layout.addWidget(self.save_login_cb)

        layout.addSpacing(8)

        # Login button
        self.login_btn = QPushButton(tr("sign_in"))
        self.login_btn.setObjectName("loginPrimaryBtn")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.setAccessibleName(tr("sign_in"))
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("loginErrorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setAccessibleName("Error message")
        self.error_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        layout.addSpacing(16)

        # Switch to register
        switch_row = QHBoxLayout()
        switch_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        switch_label = QLabel(tr("dont_have_account"))
        switch_label.setObjectName("loginSwitchLabel")
        switch_row.addWidget(switch_label)

        self.register_link = QPushButton(tr("create_account"))
        self.register_link.setObjectName("loginSwitchBtn")
        self.register_link.setMinimumSize(44, 44)
        self.register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_link.setAccessibleName(tr("create_account"))
        self.register_link.clicked.connect(self.switch_to_register.emit)
        switch_row.addWidget(self.register_link)

        layout.addLayout(switch_row)

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error(tr("enter_both"))
            return

        success, result = authenticate_user(username, password)
        if success:
            self.error_label.setVisible(False)
            # Save or clear credentials based on checkbox
            if self.save_login_cb.isChecked():
                self._settings.setValue("login/save_credentials", "true")
                self._settings.setValue("login/username", username)
                self._settings.setValue("login/password", password)
            else:
                self._settings.setValue("login/save_credentials", "false")
                self._settings.remove("login/username")
                self._settings.remove("login/password")
            self.login_success.emit(result)  # result is display_name
        else:
            self._show_error(result)

    def _toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.password_toggle.setText(tr("hide"))
            self.password_toggle.setAccessibleName(tr("hide"))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_toggle.setText(tr("show"))
            self.password_toggle.setAccessibleName(tr("show"))

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.setVisible(True)
        self.error_label.setFocus()
        announce(self.error_label, f"Error: {msg}")

    def clear_fields(self):
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.setVisible(False)


class RegisterPage(QWidget):
    """Registration form."""

    register_success = pyqtSignal()
    switch_to_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 20, 40, 20)

        title = QLabel(tr("create_account"))
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setAccessibleName(tr("create_account"))
        layout.addWidget(title)

        subtitle = QLabel(tr("join_app"))
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # Display Name
        name_label = QLabel(tr("display_name"))
        name_label.setObjectName("loginFieldLabel")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("loginInput")
        self.name_input.setPlaceholderText(tr("your_full_name"))
        self.name_input.setMinimumHeight(44)
        self.name_input.setAccessibleName(tr("display_name"))
        self.name_input.setToolTip(tr("display_name"))
        layout.addWidget(self.name_input)
        name_label.setBuddy(self.name_input)

        # Username
        username_label = QLabel(tr("username"))
        username_label.setObjectName("loginFieldLabel")
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText(tr("enter_username"))
        self.username_input.setMinimumHeight(44)
        self.username_input.setAccessibleName(tr("username"))
        self.username_input.setToolTip(tr("username"))
        layout.addWidget(self.username_input)
        username_label.setBuddy(self.username_input)

        # Password
        password_label = QLabel(tr("password"))
        password_label.setObjectName("loginFieldLabel")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText(tr("enter_password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.setAccessibleName(tr("password"))
        self.password_input.setToolTip(tr("password"))
        password_label.setBuddy(self.password_input)

        # Password row with toggle
        password_row = QHBoxLayout()
        password_row.setSpacing(4)
        password_row.addWidget(self.password_input)

        self.password_toggle = QPushButton(tr("show"))
        self.password_toggle.setObjectName("loginPasswordToggle")
        self.password_toggle.setFixedSize(60, 44)
        self.password_toggle.setAccessibleName(tr("show"))
        self.password_toggle.clicked.connect(self._toggle_password_visibility)
        password_row.addWidget(self.password_toggle)

        layout.addLayout(password_row)

        # Confirm password
        confirm_label = QLabel(tr("confirm_password"))
        confirm_label.setObjectName("loginFieldLabel")
        layout.addWidget(confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setObjectName("loginInput")
        self.confirm_input.setPlaceholderText(tr("confirm_password"))
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setMinimumHeight(44)
        self.confirm_input.setAccessibleName(tr("confirm_password"))
        self.confirm_input.setToolTip(tr("confirm_password"))
        self.confirm_input.returnPressed.connect(self._on_register)
        confirm_label.setBuddy(self.confirm_input)

        # Confirm password row with toggle
        confirm_row = QHBoxLayout()
        confirm_row.setSpacing(4)
        confirm_row.addWidget(self.confirm_input)

        self.confirm_toggle = QPushButton(tr("show"))
        self.confirm_toggle.setObjectName("loginPasswordToggle")
        self.confirm_toggle.setFixedSize(60, 44)
        self.confirm_toggle.setAccessibleName(tr("show"))
        self.confirm_toggle.clicked.connect(self._toggle_confirm_visibility)
        confirm_row.addWidget(self.confirm_toggle)

        layout.addLayout(confirm_row)

        layout.addSpacing(8)

        # Register button
        self.register_btn = QPushButton(tr("create_account"))
        self.register_btn.setObjectName("loginPrimaryBtn")
        self.register_btn.setMinimumHeight(48)
        self.register_btn.setAccessibleName(tr("create_account"))
        self.register_btn.clicked.connect(self._on_register)
        layout.addWidget(self.register_btn)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("loginErrorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setAccessibleName("Error message")
        self.error_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        layout.addSpacing(16)

        # Switch to login
        switch_row = QHBoxLayout()
        switch_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        switch_label = QLabel(tr("already_have_account"))
        switch_label.setObjectName("loginSwitchLabel")
        switch_row.addWidget(switch_label)

        self.login_link = QPushButton(tr("sign_in"))
        self.login_link.setObjectName("loginSwitchBtn")
        self.login_link.setMinimumSize(44, 44)
        self.login_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_link.setAccessibleName(tr("sign_in"))
        self.login_link.clicked.connect(self.switch_to_login.emit)
        switch_row.addWidget(self.login_link)

        layout.addLayout(switch_row)

    def _toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.password_toggle.setText(tr("hide"))
            self.password_toggle.setAccessibleName(tr("hide"))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_toggle.setText(tr("show"))
            self.password_toggle.setAccessibleName(tr("show"))

    def _toggle_confirm_visibility(self):
        if self.confirm_input.echoMode() == QLineEdit.EchoMode.Password:
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.confirm_toggle.setText(tr("hide"))
            self.confirm_toggle.setAccessibleName(tr("hide"))
        else:
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_toggle.setText(tr("show"))
            self.confirm_toggle.setAccessibleName(tr("show"))

    def _on_register(self):
        name = self.name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not name or not username or not password:
            self._show_error(tr("all_fields_required"))
            return

        if password != confirm:
            self._show_error(tr("passwords_no_match"))
            return

        success, msg = register_user(username, name, password)
        if success:
            self.error_label.setVisible(False)
            QMessageBox.information(self, tr("account_created"), msg)
            self.register_success.emit()
        else:
            self._show_error(msg)

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.setVisible(True)
        self.error_label.setFocus()
        announce(self.error_label, f"Error: {msg}")

    def clear_fields(self):
        self.name_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.error_label.setVisible(False)


class LoginWindow(QWidget):
    """Combined login/register window with logo and brand styling."""

    login_success = pyqtSignal(str)  # emits display name

    def __init__(self, auto_login=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("La Mia Scribe — Sign In")
        self.setFixedSize(480, 720)
        self.setAccessibleName("La Mia Scribe sign in window")
        self._auto_logged_in = False
        self._setup_ui()
        if auto_login:
            self._try_auto_login()

    def _try_auto_login(self):
        """If saved credentials exist, attempt auto-login."""
        settings = get_settings()
        if settings.value("login/save_credentials", "false") == "true":
            username = settings.value("login/username", "")
            password = settings.value("login/password", "")
            if username and password:
                success, result = authenticate_user(username, password)
                if success:
                    self._auto_logged_in = True
                    # Use a single-shot timer so the window can finish init first
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.login_success.emit(result))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top area with gradient background and logo
        top_area = QWidget()
        top_area.setObjectName("loginTopArea")
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(0, 24, 0, 24)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo_label = QLabel()
        logo_path = _get_logo_path()
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(
                100, 100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setAccessibleName("La Mia Scribe logo")
        logo_label.setToolTip("La Mia Scribe")
        top_layout.addWidget(logo_label)

        app_title = QLabel("La Mia Scribe")
        app_title.setObjectName("loginAppTitle")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_title.setAccessibleName("La Mia Scribe")
        top_layout.addWidget(app_title)

        tagline = QLabel("Tech Inclusion Pro")
        tagline.setObjectName("loginTagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setAccessibleName("By Tech Inclusion Pro")
        top_layout.addWidget(tagline)

        layout.addWidget(top_area)

        # Form area
        form_area = QWidget()
        form_area.setObjectName("loginFormArea")
        form_layout = QVBoxLayout(form_area)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        self.login_page = LoginPage()
        self.login_page.login_success.connect(self._on_login_success)
        self.login_page.switch_to_register.connect(self._show_register)
        self.stack.addWidget(self.login_page)

        self.register_page = RegisterPage()
        self.register_page.register_success.connect(self._show_login)
        self.register_page.switch_to_login.connect(self._show_login)
        self.stack.addWidget(self.register_page)

        form_layout.addWidget(self.stack)
        layout.addWidget(form_area, 1)

    def _show_register(self):
        self.register_page.clear_fields()
        self.stack.setCurrentWidget(self.register_page)
        self.setWindowTitle("La Mia Scribe — Create Account")
        self.register_page.name_input.setFocus()

    def _show_login(self):
        self.login_page.clear_fields()
        self.stack.setCurrentWidget(self.login_page)
        self.setWindowTitle("La Mia Scribe — Sign In")
        self.login_page.username_input.setFocus()

    def _on_login_success(self, display_name: str):
        self.login_success.emit(display_name)

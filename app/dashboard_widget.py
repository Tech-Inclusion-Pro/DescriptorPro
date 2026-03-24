"""Dashboard widget showing saved transcription projects."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QMessageBox, QSizePolicy,
    QLineEdit, QInputDialog, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath, QAction

from core.project_store import (
    list_projects, update_note, update_title, delete_project,
    list_folders, create_folder, rename_folder, delete_folder,
    assign_project_folder,
)
from utils.time_utils import format_duration
from app.accessibility_panel import announce
from core.i18n import tr


def _make_trash_icon(size=24, color="#e05050"):
    """Paint a minimal trash-can line icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    m = size * 0.15  # margin
    w = size - 2 * m
    # Lid line
    lid_y = m + w * 0.18
    p.drawLine(int(m), int(lid_y), int(size - m), int(lid_y))
    # Handle nub on lid
    handle_w = w * 0.28
    handle_h = w * 0.12
    hx = size / 2 - handle_w / 2
    p.drawRect(QRectF(hx, lid_y - handle_h, handle_w, handle_h))
    # Can body (trapezoid)
    body_top = lid_y + 1
    body_bot = size - m
    inset = w * 0.08
    path = QPainterPath()
    path.moveTo(m + inset, body_top)
    path.lineTo(size - m - inset, body_top)
    path.lineTo(size - m - inset * 2.5, body_bot)
    path.lineTo(m + inset * 2.5, body_bot)
    path.closeSubpath()
    p.drawPath(path)
    # Vertical lines inside can
    for frac in (0.38, 0.5, 0.62):
        x = m + w * frac
        p.drawLine(int(x), int(body_top + 3), int(x), int(body_bot - 3))
    p.end()
    return QIcon(pixmap)


def _make_edit_icon(size=20, color="#b0b0d0"):
    """Paint a minimal pencil / edit line icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    # Pencil body (diagonal line with a rectangle body)
    m = size * 0.15
    # Pencil shaft from top-right to bottom-left
    path = QPainterPath()
    # Tip
    path.moveTo(m + 1, size - m - 1)
    # Left edge of shaft
    path.lineTo(size * 0.30, size * 0.55)
    # Top of shaft
    path.lineTo(size * 0.45, size * 0.40)
    path.lineTo(size - m - 1, size * 0.08)
    # Right edge
    path.lineTo(size - m + 1, size * 0.20)
    path.lineTo(size * 0.57, size * 0.52)
    path.lineTo(size * 0.42, size * 0.67)
    path.closeSubpath()
    p.drawPath(path)
    # Small line across the tip
    p.drawLine(int(size * 0.30), int(size * 0.55), int(size * 0.42), int(size * 0.67))
    p.end()
    return QIcon(pixmap)


class ProjectCard(QFrame):
    """A single project card in the dashboard."""

    deleted = pyqtSignal(str)  # project id
    opened = pyqtSignal(dict)  # project dict
    folder_changed = pyqtSignal(str, str)  # project_id, folder_id

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self._project = project
        self.setObjectName("projectCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row: filename + date
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        display_title = self._project.get("title") or self._project.get("filename", "Unknown")
        self._title_label = QLabel(display_title)
        self._title_label.setObjectName("projectCardTitle")
        self._title_label.setAccessibleName(f"Project: {display_title}")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._title_label.setWordWrap(True)
        top_row.addWidget(self._title_label)

        self._title_edit = QLineEdit(display_title)
        self._title_edit.setObjectName("projectCardTitleEdit")
        self._title_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._title_edit.setAccessibleName("Edit project title")
        self._title_edit.editingFinished.connect(self._finish_title_edit)
        self._title_edit.hide()
        top_row.addWidget(self._title_edit)

        edit_btn = QPushButton()
        edit_btn.setIcon(_make_edit_icon())
        edit_btn.setIconSize(QSize(20, 20))
        edit_btn.setObjectName("projectEditTitleBtn")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setAccessibleName(f"Edit title of {display_title}")
        edit_btn.setToolTip("Edit project title")
        edit_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        edit_btn.clicked.connect(self._start_title_edit)
        top_row.addWidget(edit_btn)

        date_str = self._project.get("created_at", "")
        if date_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_str)
                date_str = dt.strftime("%b %d, %Y  %H:%M")
            except (ValueError, TypeError):
                pass
        date_label = QLabel(date_str)
        date_label.setObjectName("projectCardDate")
        date_label.setAccessibleName(f"Created {date_str}")
        top_row.addWidget(date_label)

        layout.addLayout(top_row)

        # Info row: model, language, segments, duration
        info_parts = []
        model = self._project.get("model_used", "")
        if model:
            info_parts.append(f"Model: {model}")
        lang = self._project.get("language", "")
        if lang:
            info_parts.append(f"Lang: {lang}")
        segs = self._project.get("segments_count", 0)
        if segs:
            info_parts.append(f"{segs} segments")
        dur = self._project.get("duration_seconds", 0)
        if dur:
            info_parts.append(format_duration(dur))

        if info_parts:
            info_label = QLabel("  |  ".join(info_parts))
            info_label.setObjectName("projectCardInfo")
            info_label.setAccessibleName(", ".join(info_parts))
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

        # Transcript preview
        preview = self._project.get("transcript_preview", "")
        if preview:
            preview_label = QLabel(preview[:200] + ("..." if len(preview) > 200 else ""))
            preview_label.setObjectName("projectCardPreview")
            preview_label.setWordWrap(True)
            preview_label.setAccessibleName("Transcript preview")
            layout.addWidget(preview_label)

        # Note area
        note_label = QLabel(tr("note"))
        note_label.setObjectName("projectCardNoteLabel")
        layout.addWidget(note_label)

        self._note_edit = QTextEdit()
        self._note_edit.setObjectName("projectCardNote")
        self._note_edit.setPlaceholderText("Add a note about this project...")
        self._note_edit.setMinimumHeight(50)
        self._note_edit.setMaximumHeight(80)
        self._note_edit.setAccessibleName("Project note")
        self._note_edit.setAccessibleDescription("Add or edit a note for this transcription project")
        self._note_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        existing_note = self._project.get("note", "")
        if existing_note:
            self._note_edit.setPlainText(existing_note)
        self._note_edit.textChanged.connect(self._on_note_changed)
        layout.addWidget(self._note_edit)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        open_btn = QPushButton(tr("open_transcript"))
        open_btn.setObjectName("projectOpenBtn")
        open_btn.setMinimumSize(120, 44)
        open_btn.setAccessibleName(f"{tr('open_transcript')}: {self._project.get('filename', '')}")
        open_btn.setToolTip(tr("open_transcript"))
        open_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        open_btn.clicked.connect(lambda: self.opened.emit(self._project))
        btn_row.addWidget(open_btn)

        # Move to Folder button
        self._folder_btn = QPushButton(tr("move_to_folder"))
        self._folder_btn.setObjectName("projectFolderBtn")
        self._folder_btn.setMinimumSize(120, 44)
        self._folder_btn.setAccessibleName(tr("move_to_folder"))
        self._folder_btn.setToolTip(tr("move_to_folder"))
        self._folder_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._folder_btn.clicked.connect(self._on_move_to_folder)
        btn_row.addWidget(self._folder_btn)

        btn_row.addStretch()

        delete_btn = QPushButton()
        delete_btn.setIcon(_make_trash_icon())
        delete_btn.setIconSize(QSize(24, 24))
        delete_btn.setObjectName("projectDeleteBtn")
        delete_btn.setFixedSize(44, 44)
        delete_btn.setAccessibleName(f"Delete project {self._project.get('filename', '')}")
        delete_btn.setToolTip("Delete this project from history")
        delete_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(delete_btn)

        layout.addLayout(btn_row)

    def _start_title_edit(self):
        self._title_edit.setText(self._title_label.text())
        self._title_label.hide()
        self._title_edit.show()
        self._title_edit.setFocus()
        self._title_edit.selectAll()

    def _finish_title_edit(self):
        new_title = self._title_edit.text().strip()
        if not new_title:
            new_title = self._project.get("title") or self._project.get("filename", "Unknown")
        self._title_label.setText(new_title)
        self._title_label.setAccessibleName(f"Project: {new_title}")
        self._title_edit.hide()
        self._title_label.show()
        self._project["title"] = new_title
        update_title(self._project["id"], new_title)

    def _on_note_changed(self):
        update_note(self._project["id"], self._note_edit.toPlainText())

    def _on_move_to_folder(self):
        menu = QMenu(self)
        # Uncategorized option
        uncat_action = QAction(tr("uncategorized"), menu)
        uncat_action.triggered.connect(lambda: self._set_folder(""))
        menu.addAction(uncat_action)
        menu.addSeparator()
        # User folders
        for folder in list_folders():
            action = QAction(folder["name"], menu)
            fid = folder["id"]
            action.triggered.connect(lambda checked, f=fid: self._set_folder(f))
            menu.addAction(action)
        menu.exec(self._folder_btn.mapToGlobal(self._folder_btn.rect().bottomLeft()))

    def _set_folder(self, folder_id: str):
        assign_project_folder(self._project["id"], folder_id)
        self._project["folder_id"] = folder_id
        self.folder_changed.emit(self._project["id"], folder_id)

    def _on_delete(self):
        reply = QMessageBox.question(
            self, tr("delete_project"),
            tr("delete_confirm", name=self._project.get('filename', '')),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_project(self._project["id"])
            self.deleted.emit(self._project["id"])

    def matches_filter(self, search_text: str) -> bool:
        """Return True if this card matches the search text."""
        if not search_text:
            return True
        s = search_text.lower()
        title = (self._project.get("title") or self._project.get("filename", "")).lower()
        filename = self._project.get("filename", "").lower()
        preview = self._project.get("transcript_preview", "").lower()
        note = self._project.get("note", "").lower()
        return s in title or s in filename or s in preview or s in note


class DashboardWidget(QWidget):
    """Scrollable dashboard showing all saved projects with folder sidebar."""

    project_opened = pyqtSignal(dict)  # emitted when user clicks Open on a card

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardWidget")
        self._active_folder = None  # None = All Projects, "" = Uncategorized, str = folder id
        self._cards: list[ProjectCard] = []
        self._folder_buttons: list[QPushButton] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(8, 8, 8, 8)

        self._title = QLabel(tr("recent_projects"))
        self._title.setObjectName("dashboardTitle")
        self._title.setAccessibleName(tr("recent_projects"))
        header.addWidget(self._title)

        header.addStretch()

        self._refresh_btn = QPushButton(tr("refresh"))
        self._refresh_btn.setObjectName("dashboardRefreshBtn")
        self._refresh_btn.setMinimumSize(80, 44)
        self._refresh_btn.setAccessibleName(tr("refresh"))
        self._refresh_btn.setToolTip(tr("refresh"))
        self._refresh_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)

        layout.addLayout(header)

        # Body: sidebar + right area
        body = QHBoxLayout()
        body.setSpacing(12)

        # ── Folder sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("folderSidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(4)

        # "All Projects" button
        self._all_btn = QPushButton(tr("all_projects"))
        self._all_btn.setObjectName("folderItemBtn")
        self._all_btn.setProperty("active", True)
        self._all_btn.setMinimumHeight(36)
        self._all_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._all_btn.setAccessibleName(tr("all_projects"))
        self._all_btn.clicked.connect(lambda: self._select_folder(None))
        sidebar_layout.addWidget(self._all_btn)

        # "Uncategorized" button
        self._uncat_btn = QPushButton(tr("uncategorized"))
        self._uncat_btn.setObjectName("folderItemBtn")
        self._uncat_btn.setProperty("active", False)
        self._uncat_btn.setMinimumHeight(36)
        self._uncat_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._uncat_btn.setAccessibleName(tr("uncategorized"))
        self._uncat_btn.clicked.connect(lambda: self._select_folder(""))
        sidebar_layout.addWidget(self._uncat_btn)

        # Scrollable folder list
        self._folder_scroll = QScrollArea()
        self._folder_scroll.setWidgetResizable(True)
        self._folder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._folder_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._folder_scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._folder_container = QWidget()
        self._folder_list_layout = QVBoxLayout(self._folder_container)
        self._folder_list_layout.setContentsMargins(0, 0, 0, 0)
        self._folder_list_layout.setSpacing(4)
        self._folder_list_layout.addStretch()
        self._folder_scroll.setWidget(self._folder_container)
        sidebar_layout.addWidget(self._folder_scroll, 1)

        # "+ New Folder" button
        self._new_folder_btn = QPushButton(tr("new_folder"))
        self._new_folder_btn.setObjectName("newFolderBtn")
        self._new_folder_btn.setMinimumHeight(36)
        self._new_folder_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._new_folder_btn.setAccessibleName(tr("new_folder"))
        self._new_folder_btn.clicked.connect(self._on_create_folder)
        sidebar_layout.addWidget(self._new_folder_btn)

        body.addWidget(sidebar)

        # ── Right area ──
        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Search bar
        self._search_bar = QLineEdit()
        self._search_bar.setObjectName("dashboardSearchBar")
        self._search_bar.setPlaceholderText(tr("search_projects"))
        self._search_bar.setMinimumHeight(40)
        self._search_bar.setAccessibleName(tr("search_projects"))
        self._search_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._search_bar.textChanged.connect(self._on_search_changed)
        right_layout.addWidget(self._search_bar)

        # Scroll area for project cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        right_layout.addWidget(self._scroll)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()
        self._scroll.setWidget(self._cards_container)

        body.addWidget(right_area, 1)

        layout.addLayout(body, 1)

        self.refresh()

    # ── Folder sidebar ──

    def _rebuild_folder_list(self):
        """Rebuild the scrollable folder buttons from disk."""
        # Clear existing folder buttons
        for btn in self._folder_buttons:
            btn.deleteLater()
        self._folder_buttons.clear()

        for folder in list_folders():
            btn = QPushButton(folder["name"])
            btn.setObjectName("folderItemBtn")
            btn.setProperty("active", False)
            btn.setProperty("folder_id", folder["id"])
            btn.setMinimumHeight(36)
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setAccessibleName(folder["name"])
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            fid = folder["id"]
            btn.clicked.connect(lambda checked, f=fid: self._select_folder(f))
            btn.customContextMenuRequested.connect(
                lambda pos, f=fid, b=btn: self._folder_context_menu(f, b, pos)
            )
            self._folder_list_layout.insertWidget(
                self._folder_list_layout.count() - 1, btn
            )
            self._folder_buttons.append(btn)

        self._update_folder_active_state()

    def _update_folder_active_state(self):
        """Update the 'active' property on all folder buttons."""
        self._all_btn.setProperty("active", self._active_folder is None)
        self._all_btn.style().unpolish(self._all_btn)
        self._all_btn.style().polish(self._all_btn)

        self._uncat_btn.setProperty("active", self._active_folder == "")
        self._uncat_btn.style().unpolish(self._uncat_btn)
        self._uncat_btn.style().polish(self._uncat_btn)

        for btn in self._folder_buttons:
            is_active = btn.property("folder_id") == self._active_folder
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _select_folder(self, folder_id):
        """Set active folder filter and re-filter cards."""
        self._active_folder = folder_id
        self._update_folder_active_state()
        self._apply_filters()

    def _on_create_folder(self):
        name, ok = QInputDialog.getText(
            self, tr("new_folder"), tr("folder_name")
        )
        if ok and name.strip():
            create_folder(name.strip())
            self._rebuild_folder_list()

    def _folder_context_menu(self, folder_id: str, btn: QPushButton, pos):
        menu = QMenu(btn)
        rename_action = QAction(tr("rename_folder"), menu)
        rename_action.triggered.connect(lambda: self._on_rename_folder(folder_id))
        menu.addAction(rename_action)

        delete_action = QAction(tr("delete_folder"), menu)
        delete_action.triggered.connect(lambda: self._on_delete_folder(folder_id))
        menu.addAction(delete_action)

        menu.exec(btn.mapToGlobal(pos))

    def _on_rename_folder(self, folder_id: str):
        # Find current name
        current_name = ""
        for f in list_folders():
            if f["id"] == folder_id:
                current_name = f["name"]
                break
        name, ok = QInputDialog.getText(
            self, tr("rename_folder"), tr("folder_name"), text=current_name
        )
        if ok and name.strip():
            rename_folder(folder_id, name.strip())
            self._rebuild_folder_list()

    def _on_delete_folder(self, folder_id: str):
        # Find folder name
        folder_name = ""
        for f in list_folders():
            if f["id"] == folder_id:
                folder_name = f["name"]
                break
        reply = QMessageBox.question(
            self, tr("delete_folder"),
            tr("delete_folder_confirm", name=folder_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_folder(folder_id)
            if self._active_folder == folder_id:
                self._active_folder = None
            self.refresh()

    # ── Search / Filter ──

    def _on_search_changed(self):
        self._apply_filters()

    def _apply_filters(self):
        """Show/hide cards based on active folder + search text."""
        search_text = self._search_bar.text().strip()
        visible_count = 0

        for card in self._cards:
            folder_id = card._project.get("folder_id", "")

            # Folder filter
            if self._active_folder is None:
                folder_match = True
            elif self._active_folder == "":
                folder_match = (folder_id == "")
            else:
                folder_match = (folder_id == self._active_folder)

            # Search filter
            search_match = card.matches_filter(search_text)

            visible = folder_match and search_match
            card.setVisible(visible)
            if visible:
                visible_count += 1

        # Show/hide empty label
        if hasattr(self, '_empty_label'):
            self._empty_label.setVisible(visible_count == 0 and len(self._cards) > 0)

    # ── Refresh ──

    def refresh(self):
        """Reload projects from disk and rebuild cards + folder sidebar."""
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        # Remove empty label if present
        if hasattr(self, '_empty_label') and self._empty_label:
            self._empty_label.deleteLater()
            self._empty_label = None

        # Remove all widgets from cards layout except the stretch
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Rebuild folder sidebar
        self._rebuild_folder_list()

        projects = list_projects()

        if not projects:
            empty = QLabel(tr("no_projects"))
            empty.setObjectName("dashboardEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            empty.setAccessibleName(tr("no_projects"))
            self._cards_layout.insertWidget(0, empty)
            announce(self._refresh_btn, "No projects found")
            return

        for project in projects:
            card = ProjectCard(project)
            card.deleted.connect(self._on_project_deleted)
            card.opened.connect(self.project_opened)
            card.folder_changed.connect(self._on_folder_changed)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            self._cards.append(card)

        # Empty search/filter label (hidden by default)
        self._empty_label = QLabel(tr("no_projects"))
        self._empty_label.setObjectName("dashboardEmpty")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.hide()
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, self._empty_label)

        self._apply_filters()
        announce(self._refresh_btn, f"{len(projects)} projects loaded")

    def _on_project_deleted(self, project_id: str):
        announce(self._refresh_btn, tr("project_deleted"))
        self.refresh()

    def _on_folder_changed(self, project_id: str, folder_id: str):
        self._apply_filters()

    def retranslateUi(self):
        """Refresh all translatable text."""
        self._title.setText(tr("recent_projects"))
        self._refresh_btn.setText(tr("refresh"))
        self._all_btn.setText(tr("all_projects"))
        self._uncat_btn.setText(tr("uncategorized"))
        self._new_folder_btn.setText(tr("new_folder"))
        self._search_bar.setPlaceholderText(tr("search_projects"))
        self.refresh()

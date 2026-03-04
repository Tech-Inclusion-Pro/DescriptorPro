"""Dashboard widget showing saved transcription projects."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath

from core.project_store import list_projects, update_note, delete_project
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


class ProjectCard(QFrame):
    """A single project card in the dashboard."""

    deleted = pyqtSignal(str)  # project id
    opened = pyqtSignal(dict)  # project dict

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

        filename = QLabel(self._project.get("filename", "Unknown"))
        filename.setObjectName("projectCardTitle")
        filename.setAccessibleName(f"Project: {self._project.get('filename', 'Unknown')}")
        filename.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        filename.setWordWrap(True)
        top_row.addWidget(filename)

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

    def _on_note_changed(self):
        update_note(self._project["id"], self._note_edit.toPlainText())

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


class DashboardWidget(QWidget):
    """Scrollable dashboard showing all saved projects."""

    project_opened = pyqtSignal(dict)  # emitted when user clicks Open on a card

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardWidget")
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

        # Scroll area for project cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._scroll)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()
        self._scroll.setWidget(self._cards_container)

        self.refresh()

    def refresh(self):
        """Reload projects from disk and rebuild cards."""
        # Clear existing cards
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        projects = list_projects()

        if not projects:
            empty = QLabel(tr("no_projects"))
            empty.setObjectName("dashboardEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            empty.setAccessibleName(tr("no_projects"))
            self._cards_layout.insertWidget(0, empty)
            announce(empty, "No projects found")
            return

        for project in projects:
            card = ProjectCard(project)
            card.deleted.connect(self._on_project_deleted)
            card.opened.connect(self.project_opened)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        announce(self._refresh_btn, f"{len(projects)} projects loaded")

    def _on_project_deleted(self, project_id: str):
        announce(self._refresh_btn, tr("project_deleted"))
        self.refresh()

    def retranslateUi(self):
        """Refresh all translatable text."""
        self._title.setText(tr("recent_projects"))
        self._refresh_btn.setText(tr("refresh"))
        self.refresh()

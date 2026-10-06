"""Project storage: one folder per project; SQLite only as a rebuildable index.

Folder layout (spec §3.4):
    <library>/<project-id>/
        project.json     # source of truth
        media/           # reference or copy of the source
        frames/  audio/  exports/  jobs/
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from service.paths import index_db_file

SUBDIRS = ("media", "frames", "audio", "exports", "jobs")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class ProjectStore:
    def __init__(self, library: Path) -> None:
        self.library = library
        self._db = sqlite3.connect(index_db_file())
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, title TEXT, path TEXT,
                status TEXT, created TEXT, updated TEXT)"""
        )
        self._db.commit()

    # -- index ------------------------------------------------------------

    def _index_upsert(self, project: dict, path: Path) -> None:
        self._db.execute(
            """INSERT INTO projects (id, title, path, status, created, updated)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, status=excluded.status, updated=excluded.updated""",
            (
                project["id"],
                project["title"],
                str(path),
                project.get("status", "new"),
                project["created"],
                _now_iso(),
            ),
        )
        self._db.commit()

    def rebuild_index(self) -> int:
        """Rescan the library; the folders are the source of truth."""
        self._db.execute("DELETE FROM projects")
        count = 0
        for project_file in self.library.glob("*/project.json"):
            try:
                project = json.loads(project_file.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            self._index_upsert(project, project_file.parent)
            count += 1
        self._db.commit()
        return count

    # -- CRUD -------------------------------------------------------------

    def create(self, title: str, source_path: str, outputs: dict, copy_media: bool = False) -> dict:
        source = Path(source_path).expanduser()
        if not source.is_file():
            raise FileNotFoundError(f"Source file not found: {source}")

        project_id = str(uuid.uuid4())
        folder = self.library / project_id
        for sub in SUBDIRS:
            (folder / sub).mkdir(parents=True, exist_ok=True)

        media_path = source
        if copy_media:
            media_path = folder / "media" / source.name
            shutil.copy2(source, media_path)

        project = {
            "schema": 1,
            "id": project_id,
            "title": title or source.stem,
            "source": {
                "path": str(media_path),
                "kind": _kind_for(source),
                "sha256": None,  # filled by the ingest/hash job
            },
            "outputs": outputs,
            "status": "new",
            "created": _now_iso(),
            "segments": [],
            "caption_cues": [],
            "description_cues": [],
            "images": [],
            "provenance": {},
        }
        self.save(project)
        return project

    def folder(self, project_id: str) -> Path:
        return self.library / project_id

    def load(self, project_id: str) -> dict | None:
        path = self.folder(project_id) / "project.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save(self, project: dict) -> None:
        folder = self.folder(project["id"])
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "project.json").write_text(json.dumps(project, indent=2))
        self._index_upsert(project, folder)

    def list(self) -> list[dict]:
        rows = self._db.execute(
            "SELECT id, title, status, created, updated FROM projects ORDER BY updated DESC"
        ).fetchall()
        return [
            {"id": r[0], "title": r[1], "status": r[2], "created": r[3], "updated": r[4]}
            for r in rows
        ]

    def delete(self, project_id: str, keep_exports: bool = False) -> bool:
        folder = self.folder(project_id)
        if not folder.is_dir():
            return False
        if keep_exports:
            # Working files (frames, audio, media copies) are removed; exports stay.
            for sub in ("media", "frames", "audio", "jobs"):
                shutil.rmtree(folder / sub, ignore_errors=True)
            (folder / "project.json").unlink(missing_ok=True)
        else:
            shutil.rmtree(folder, ignore_errors=True)
        self._db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self._db.commit()
        return True

    def close(self) -> None:
        self._db.close()


def _kind_for(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in {".mp4", ".mov", ".mkv", ".avi"}:
        return "video"
    if suffix in {".mp3", ".wav", ".m4a", ".ogg"}:
        return "audio"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return "image"
    if suffix in {".pdf", ".pptx"}:
        return "slides"
    return "video"

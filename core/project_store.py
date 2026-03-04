"""Persistent project history store for La Mia Scribe.

Stores completed transcription projects as JSON records so the user
can browse, annotate, and delete past work from the dashboard.
"""

import json
import os
import uuid
from datetime import datetime


def _store_path() -> str:
    """Return the path to the projects JSON file."""
    data_dir = os.path.expanduser("~/Library/Application Support/TechInclusionPro/LaMiaScribe")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "projects.json")


def _load_all() -> list[dict]:
    path = _store_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_all(projects: list[dict]):
    path = _store_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)


def list_projects() -> list[dict]:
    """Return all projects, most recent first."""
    projects = _load_all()
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return projects


def _transcripts_dir() -> str:
    """Return the directory where full transcript JSON files are stored."""
    data_dir = os.path.expanduser("~/Library/Application Support/TechInclusionPro/LaMiaScribe/transcripts")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def add_project(
    source_file: str,
    model_used: str,
    language: str,
    segments_count: int,
    duration_seconds: float,
    transcript_preview: str,
    segments: list | None = None,
) -> dict:
    """Add a new project record and return it."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "source_file": source_file,
        "filename": os.path.basename(source_file) if source_file else "Unknown",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model_used": model_used,
        "language": language,
        "segments_count": segments_count,
        "duration_seconds": duration_seconds,
        "transcript_preview": transcript_preview[:300],
        "note": "",
    }
    projects = _load_all()
    projects.append(project)
    _save_all(projects)

    # Save full transcript segments to a separate file
    if segments:
        transcript_path = os.path.join(_transcripts_dir(), f"{project_id}.json")
        try:
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    return project


def load_transcript(project_id: str) -> list[dict] | None:
    """Load saved transcript segments for a project. Returns list of segment dicts or None."""
    transcript_path = os.path.join(_transcripts_dir(), f"{project_id}.json")
    if not os.path.exists(transcript_path):
        return None
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def update_note(project_id: str, note: str):
    """Update the note for a project."""
    projects = _load_all()
    for p in projects:
        if p["id"] == project_id:
            p["note"] = note
            break
    _save_all(projects)


def delete_project(project_id: str):
    """Delete a project by ID, including its saved transcript."""
    projects = _load_all()
    projects = [p for p in projects if p["id"] != project_id]
    _save_all(projects)
    # Remove transcript file if it exists
    transcript_path = os.path.join(_transcripts_dir(), f"{project_id}.json")
    try:
        if os.path.exists(transcript_path):
            os.unlink(transcript_path)
    except OSError:
        pass

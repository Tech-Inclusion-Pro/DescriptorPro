"""Service-side settings: library location and UI language.

Stored as settings.json in the app support directory. Display settings
(palette, text size, and so on) live in the browser's localStorage, not here.
"""

from __future__ import annotations

import json
from pathlib import Path

from service.paths import app_support_dir, default_library_dir

_ALLOWED_KEYS = {"library_dir", "language"}


def _settings_file() -> Path:
    return app_support_dir() / "settings.json"


def load_settings() -> dict:
    path = _settings_file()
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            data = {}
    data.setdefault("library_dir", str(default_library_dir()))
    data.setdefault("language", "en")
    return data


def save_settings(patch: dict) -> dict:
    current = load_settings()
    for key, value in patch.items():
        if key in _ALLOWED_KEYS:
            current[key] = value
    _settings_file().write_text(json.dumps(current, indent=2))
    return current


def library_dir() -> Path:
    path = Path(load_settings()["library_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path

"""Filesystem locations for the Describe Studio service."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_support_dir() -> Path:
    """Per-user application data directory (created on first use).

    DESCRIBE_STUDIO_DATA_DIR overrides the location (tests, portable installs).
    """
    override = os.environ.get("DESCRIBE_STUDIO_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    path = base / "TechInclusionPro" / "DescriptorPro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def handshake_file() -> Path:
    return app_support_dir() / "service.json"


def index_db_file() -> Path:
    return app_support_dir() / "index.sqlite"


def default_library_dir() -> Path:
    """Default project library until the user chooses one in settings."""
    path = app_support_dir() / "library"
    path.mkdir(parents=True, exist_ok=True)
    return path

"""Handshake file + stdout line so the shell (or dev scripts) can find the service."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from core.branding import APP_VERSION
from service.paths import handshake_file


def write_handshake(port: int, token: str, started_iso: str) -> Path:
    """Write the port/token handshake file with owner-only permissions and
    print a DS_READY line on stdout for process supervisors."""
    payload = {
        "port": port,
        "token": token,
        "pid": os.getpid(),
        "started": started_iso,
        "version": APP_VERSION,
    }
    path = handshake_file()
    path.write_text(json.dumps(payload))
    os.chmod(path, 0o600)

    print(f"DS_READY {json.dumps(payload)}", flush=True)
    return path


def remove_handshake() -> None:
    try:
        handshake_file().unlink(missing_ok=True)
    except OSError:
        pass


def read_handshake() -> dict | None:
    """Used by dev tooling; returns None when the service is not running."""
    path = handshake_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


if __name__ == "__main__":  # tiny helper: print the running service's port
    data = read_handshake()
    sys.exit(0 if data and print(data["port"]) is None else 1)

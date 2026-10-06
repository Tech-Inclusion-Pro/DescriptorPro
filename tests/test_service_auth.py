"""Auth and handshake behavior (spec §3.3)."""

from __future__ import annotations

import json
import stat


def test_health_is_open(anon_client):
    response = anon_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_requires_token(anon_client):
    assert anon_client.get("/api/settings").status_code == 401
    assert anon_client.get("/api/projects").status_code == 401
    assert anon_client.post("/api/shutdown").status_code == 401


def test_wrong_token_rejected(anon_client):
    response = anon_client.get(
        "/api/settings", headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401


def test_right_token_accepted(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert "library_dir" in response.json()


def test_handshake_file_permissions(tmp_path, monkeypatch):
    from service.handshake import read_handshake, remove_handshake, write_handshake
    from service.paths import handshake_file

    path = write_handshake(12345, "secret-token", "2026-10-06T00:00:00Z")
    try:
        assert path == handshake_file()
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

        data = read_handshake()
        assert data["port"] == 12345
        assert data["token"] == "secret-token"
        assert json.loads(path.read_text())["pid"] > 0
    finally:
        remove_handshake()
    assert read_handshake() is None

"""Cloud BYOK routes: keychain storage (mocked) + send preview."""

from __future__ import annotations


class FakeKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, service, name, value):
        self.store[(service, name)] = value

    def get_password(self, service, name):
        return self.store.get((service, name))

    def delete_password(self, service, name):
        self.store.pop((service, name), None)

    class errors:
        class PasswordDeleteError(Exception):
            pass


def test_key_lifecycle_never_returns_key(client, monkeypatch):
    import sys

    fake = FakeKeyring()
    fake.errors = __import__("keyring").errors
    monkeypatch.setitem(sys.modules, "keyring", fake)

    assert client.get("/api/cloud/keys").json()["providers"] == []
    assert client.put("/api/cloud/keys", json={"provider": "anthropic", "key": "sk-test"}).status_code == 200
    data = client.get("/api/cloud/keys").json()
    assert data["providers"] == ["anthropic"]
    assert "sk-test" not in str(data)
    client.delete("/api/cloud/keys/anthropic")
    assert client.get("/api/cloud/keys").json()["providers"] == []


def test_bad_provider_rejected(client):
    assert client.put("/api/cloud/keys", json={"provider": "weird", "key": "x"}).status_code == 400


def test_preview_sends_nothing_and_describes_payload(client, tmp_path):
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()

    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        full = store.load(project["id"])
        full["segments"] = [
            {"id": "seg-0001", "start": 0, "end": 8, "keyframes": [],
             "ocr_text": [], "visual_facts": [{"id": "vf-1", "text": "Six roles shown", "kind": "diagram", "essential": True}],
             "transcript_window": "", "need": None,
             "decision": {"value": "describe", "by": "R", "at": "now"}},
        ]
        store.save(full)
    finally:
        store.close()

    preview = client.get(f"/api/projects/{project['id']}/cloud-preview?stage=describe").json()
    assert preview["segments"] == 1
    assert "never leave this computer" in preview["never_sent"]
    assert "Nothing has been sent" in preview["note"]
    assert "Six roles shown" in preview["sample_text"]

"""Project folder CRUD and index behavior (spec §3.4)."""

from __future__ import annotations

import json
from pathlib import Path


def _make_source(tmp_path: Path) -> Path:
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"not really a video, fine for storage tests")
    return source


def test_create_list_get_delete(client, tmp_path):
    source = _make_source(tmp_path)

    created = client.post(
        "/api/projects",
        json={"title": "Week 7", "source_path": str(source), "outputs": {"captions": True}},
    ).json()
    assert created["title"] == "Week 7"
    assert created["schema"] == 1
    assert created["source"]["kind"] == "video"

    listed = client.get("/api/projects").json()
    assert [p["id"] for p in listed] == [created["id"]]

    fetched = client.get(f"/api/projects/{created['id']}").json()
    assert fetched["id"] == created["id"]

    deleted = client.delete(f"/api/projects/{created['id']}").json()
    assert deleted["deleted"] is True
    assert client.get(f"/api/projects/{created['id']}").status_code == 404


def test_project_folder_layout(client, tmp_path):
    from service.settings_store import library_dir

    source = _make_source(tmp_path)
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()

    folder = library_dir() / project["id"]
    assert (folder / "project.json").is_file()
    for sub in ("media", "frames", "audio", "exports", "jobs"):
        assert (folder / sub).is_dir()

    on_disk = json.loads((folder / "project.json").read_text())
    assert on_disk["id"] == project["id"]


def test_missing_source_rejected(client):
    response = client.post(
        "/api/projects", json={"source_path": "/nowhere/missing.mp4", "outputs": {}}
    )
    assert response.status_code == 400


def test_hash_endpoint(client, tmp_path):
    import hashlib

    source = _make_source(tmp_path)
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()

    result = client.post(f"/api/projects/{project['id']}/hash").json()
    assert result["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_keep_exports_delete(client, tmp_path):
    from service.settings_store import library_dir

    source = _make_source(tmp_path)
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()
    folder = library_dir() / project["id"]
    (folder / "exports" / "captions.vtt").write_text("WEBVTT\n")

    client.delete(f"/api/projects/{project['id']}", params={"keep_exports": "true"})
    assert (folder / "exports" / "captions.vtt").is_file()
    assert not (folder / "media").exists()
    assert not (folder / "project.json").exists()


def test_index_rebuild(client, tmp_path):
    from service.projects import ProjectStore
    from service.settings_store import library_dir

    source = _make_source(tmp_path)
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()

    store = ProjectStore(library_dir())
    try:
        count = store.rebuild_index()
        assert count == 1
        assert store.list()[0]["id"] == project["id"]
    finally:
        store.close()

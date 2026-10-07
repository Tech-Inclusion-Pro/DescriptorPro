"""Description review + standards routes."""

from __future__ import annotations


def _project_with_descriptions(client, tmp_path) -> dict:
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media bytes")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {"audio_description": True}}
    ).json()

    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        full = store.load(project["id"])
        full["ad_style"] = "standard"
        full["description_cues"] = [
            {
                "id": "ad-0001", "segment": "seg-0002", "start": 52.0, "gap": 8.0,
                "text": "A diagram shows six roles. The roles are printed in red.",
                "full_text": "A diagram shows six roles. The roles are printed in red.",
                "short_text": "Six roles shown.",
                "suggested_text": "A diagram shows six roles.",
                "est_duration": 4.1, "mode": "inline", "placement": "in_gap",
                "voice": {"kind": "synthetic", "clip": None},
                "flags": [{"type": "contradicted", "detail": "The roles are printed in red", "span": None}],
                "criteria": ["DS-3"], "status": "draft",
                "approved_by": None, "approved_at": None, "lang": "en",
            },
        ]
        store.save(full)
    finally:
        store.close()
    return project


def test_standards_served_with_notice(client):
    data = client.get("/api/standards").json()
    assert len(data["criteria"]) == 10
    assert data["quotes_verified"] is False
    assert data["verification_notice"]
    ds3 = next(c for c in data["criteria"] if c["id"] == "DS-3")
    assert "unverified_claim" in ds3["flag_types"]
    assert {s["led_by"] for s in data["sources"]} >= {"blind-led", "deaf-led"}


def test_get_descriptions(client, tmp_path):
    project = _project_with_descriptions(client, tmp_path)
    data = client.get(f"/api/projects/{project['id']}/descriptions").json()
    assert len(data["cues"]) == 1
    assert data["ad_style"] == "standard"


def test_take_suggested_text_returns_to_draft(client, tmp_path):
    project = _project_with_descriptions(client, tmp_path)
    url = f"/api/projects/{project['id']}/descriptions/ad-0001"

    cue = client.patch(url, json={"use": "suggested"}).json()
    assert cue["text"] == "A diagram shows six roles."
    assert cue["status"] == "draft"
    # flags survive the edit — only approval clears them
    assert any(f["type"] == "contradicted" for f in cue["flags"])


def test_approve_requires_name_and_clears_flags(client, tmp_path):
    project = _project_with_descriptions(client, tmp_path)
    url = f"/api/projects/{project['id']}/descriptions/ad-0001"

    assert client.patch(url, json={"approve": True}).status_code == 400
    cue = client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"}).json()
    assert cue["status"] == "approved"
    assert cue["flags"] == []


def test_short_version_updates_duration(client, tmp_path):
    project = _project_with_descriptions(client, tmp_path)
    url = f"/api/projects/{project['id']}/descriptions/ad-0001"
    cue = client.patch(url, json={"use": "short"}).json()
    assert cue["text"] == "Six roles shown."
    assert cue["est_duration"] < 4.1

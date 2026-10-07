"""Caption review + export routes, with fabricated cues (no model runs)."""

from __future__ import annotations

from pathlib import Path


def _project_with_cues(client, tmp_path) -> dict:
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media bytes")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {"captions": True}}
    ).json()

    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        full = store.load(project["id"])
        full["caption_cues"] = [
            {
                "id": "cap-0001", "start": 0.5, "end": 3.2, "speaker": None,
                "text": "Welcome to week seven.", "kind": "speech",
                "words": [], "flags": [], "status": "draft",
                "approved_by": None, "approved_at": None,
            },
            {
                "id": "cap-0002", "start": 4.0, "end": 7.9, "speaker": "Dr. Catrone",
                "text": "This is the eligibility form.", "kind": "speech",
                "words": [],
                "flags": [{"type": "low_confidence", "detail": "eligibility", "span": [12, 23]}],
                "status": "draft", "approved_by": None, "approved_at": None,
            },
        ]
        store.save(full)
    finally:
        store.close()
    return project


def test_get_captions(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    data = client.get(f"/api/projects/{project['id']}/captions").json()
    assert len(data["cues"]) == 2
    assert data["cues"][1]["flags"][0]["type"] == "low_confidence"


def test_edit_returns_cue_to_draft(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    url = f"/api/projects/{project['id']}/captions/cap-0001"

    client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"})
    edited = client.patch(url, json={"text": "Welcome to week 7."}).json()
    assert edited["status"] == "draft"
    assert edited["approved_by"] is None


def test_speaker_edit_returns_cue_to_draft(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    url = f"/api/projects/{project['id']}/captions/cap-0001"

    client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"})
    relabelled = client.patch(url, json={"speaker": "Dr. Catrone"}).json()
    assert relabelled["speaker"] == "Dr. Catrone"
    assert relabelled["status"] == "draft"

    cleared = client.patch(url, json={"speaker": ""}).json()
    assert cleared["speaker"] is None


def test_approve_requires_name_and_clears_flags(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    url = f"/api/projects/{project['id']}/captions/cap-0002"

    assert client.patch(url, json={"approve": True}).status_code == 400
    cue = client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"}).json()
    assert cue["status"] == "approved"
    assert cue["approved_by"] == "Rocco Catrone"
    assert cue["flags"] == []


def test_export_vtt_carries_provenance_status(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    result = client.post(
        f"/api/projects/{project['id']}/export", json={"formats": ["vtt", "srt"]}
    ).json()
    assert result["status"] == "draft_not_reviewed"

    vtt = Path(result["written"][0]).read_text()
    assert vtt.startswith("WEBVTT")
    assert "NOTE" in vtt
    assert "DRAFT. Not yet reviewed by a person." in vtt
    assert "Dr. Catrone: This is the eligibility form." in vtt
    assert "00:00:00.500 --> 00:00:03.200" in vtt

    sidecar = [p for p in result["written"] if p.endswith("provenance.txt")]
    assert sidecar and "DRAFT" in Path(sidecar[0]).read_text()


def test_export_reviewed_when_all_approved(client, tmp_path):
    project = _project_with_cues(client, tmp_path)
    for cue_id in ("cap-0001", "cap-0002"):
        client.patch(
            f"/api/projects/{project['id']}/captions/{cue_id}",
            json={"approve": True, "reviewer": "Rocco Catrone"},
        )
    result = client.post(
        f"/api/projects/{project['id']}/export", json={"formats": ["vtt"]}
    ).json()
    assert result["status"] == "reviewed"
    vtt = Path(result["written"][0]).read_text()
    assert "reviewed by Rocco Catrone." in vtt


def test_upload_creates_project_with_hash(client):
    import hashlib

    files = {"file": ("clip.mp3", b"fake-mp3-bytes", "audio/mpeg")}
    data = {"title": "Upload test", "outputs": '{"captions": true}'}
    project = client.post("/api/projects/upload", files=files, data=data).json()
    assert project["title"] == "Upload test"
    assert project["source"]["kind"] == "audio"
    assert project["source"]["sha256"] == hashlib.sha256(b"fake-mp3-bytes").hexdigest()
    assert Path(project["source"]["path"]).read_bytes() == b"fake-mp3-bytes"

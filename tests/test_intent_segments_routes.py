"""Intent + segment routes (service/routes/intent.py, segments.py)."""

from __future__ import annotations


def _project(client, tmp_path) -> dict:
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media bytes")
    return client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {"captions": True}}
    ).json()


def _with_segments(client, tmp_path) -> dict:
    project = _project(client, tmp_path)
    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        full = store.load(project["id"])
        full["segments"] = [
            {
                "id": "seg-0001", "start": 0.0, "end": 10.0, "keyframes": [],
                "ocr_text": [], "visual_facts": [], "transcript_window": "",
                "need": {"verdict": "needed", "reason": "Shown but never said aloud: a chart",
                         "uncovered_facts": ["vf-1"], "criteria": ["WCAG-1.2.5"],
                         "deictic": [], "coach": None},
                "decision": {"value": "undecided", "by": None, "at": None},
            },
        ]
        store.save(full)
    finally:
        store.close()
    return project


def test_questions_listed(client):
    data = client.get("/api/intent/questions").json()
    assert len(data["questions"]) == 6
    assert data["questions"][0]["id"] == "audience"


def test_intent_defaults_and_put_sanitizes(client, tmp_path):
    project = _project(client, tmp_path)
    url = f"/api/projects/{project['id']}/intent"

    data = client.get(url).json()
    assert data["intent"]["detail_level"] == "concise"

    saved = client.put(
        url,
        json={"intent": {"audience": "Undergrads", "content_type": "nonsense",
                          "people": [{"label": "Dr. Catrone"}]}},
    ).json()
    assert saved["intent"]["content_type"] == "other"
    assert saved["intent"]["people"][0]["source"] == "user"

    assert client.get(url).json()["intent"]["audience"] == "Undergrads"


def test_segments_report_shape(client, tmp_path):
    project = _with_segments(client, tmp_path)
    data = client.get(f"/api/projects/{project['id']}/segments").json()
    assert data["tally"]["needed"] == 1
    assert any("WCAG" in s for s in data["standards_checked"])
    assert "does not give legal advice" in data["notice"]


def test_decision_requires_name_and_records_time(client, tmp_path):
    project = _with_segments(client, tmp_path)
    url = f"/api/projects/{project['id']}/segments/seg-0001/decision"

    assert client.patch(url, json={"value": "describe"}).status_code == 400
    assert client.patch(url, json={"value": "nonsense", "by": "R"}).status_code == 400

    decision = client.patch(url, json={"value": "describe", "by": "Rocco Catrone"}).json()
    assert decision["value"] == "describe"
    assert decision["by"] == "Rocco Catrone"
    assert decision["at"]

    undone = client.patch(url, json={"value": "undecided"}).json()
    assert undone["by"] is None and undone["at"] is None

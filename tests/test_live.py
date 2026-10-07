"""Live mode logic: slide watcher (model-free) and live routes."""

from __future__ import annotations

import numpy as np


def slide_jpeg(title: str, bullets: list[str], busy: bool = False) -> bytes:
    import cv2

    img = np.full((360, 640, 3), 245, dtype=np.uint8)
    cv2.putText(img, title, (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 20, 90), 2, cv2.LINE_AA)
    for j, b in enumerate(bullets):
        cv2.putText(img, f"- {b}", (60, 130 + j * 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
    if busy:
        # mostly-pictorial slide: noise instead of text
        noise = np.random.default_rng(7).integers(0, 255, (360, 640, 3), dtype=np.uint8)
        img = cv2.addWeighted(img, 0.2, noise.astype(np.uint8), 0.8, 0)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


class TestSlideWatcher:
    def test_first_frame_announces(self):
        from core.live.announcer import SlideWatcher

        watcher = SlideWatcher()
        change = watcher.feed(slide_jpeg("Who is on the team?", ["Parent", "Educator"]))
        assert change is not None
        assert change["slide_number"] == 1
        assert "team" in change["title"].lower() or change["lines"]

    def test_same_slide_silent_changed_slide_announces(self):
        from core.live.announcer import SlideWatcher

        watcher = SlideWatcher()
        a = slide_jpeg("Slide one title here", ["alpha", "beta"])
        b = slide_jpeg("Completely different slide", ["gamma", "delta"])
        assert watcher.feed(a) is not None
        assert watcher.feed(a) is None  # unchanged → silent
        change = watcher.feed(b)
        assert change is not None and change["slide_number"] == 2
        assert len(watcher.log) == 2  # logged for the recorded pass

    def test_graphical_slide_gets_not_described_note(self):
        from core.live.announcer import GRAPHICS_NOTE, SlideWatcher

        watcher = SlideWatcher()
        change = watcher.feed(slide_jpeg("", [], busy=True))
        assert change is not None
        assert change["graphics_note"] == GRAPHICS_NOTE


class TestLiveRoutes:
    def test_frame_endpoint_requires_session(self, client):
        response = client.post("/api/live/nope/frame", content=b"xx")
        assert response.status_code == 404

    def test_project_endpoint_requires_session(self, client):
        assert client.post("/api/live/nope/project", json={}).status_code == 404

    def test_transcript_only_session_saves_project(self, client, tmp_path):
        from core.live.announcer import SlideWatcher
        from service.routes.live import _SESSIONS

        _SESSIONS["t1"] = {
            "sentences": [
                {"text": "Welcome back everyone.", "start": 0.0, "end": 1.4},
                {"text": "Today we talk about captions.", "start": 1.8, "end": 3.9},
            ],
            "wav_path": None,
            "wav": None,
            "watcher": SlideWatcher(),
            "started": 0,
            "model": "mlx-community/parakeet-tdt-0.6b-v3",
        }
        try:
            data = client.post("/api/live/t1/project", json={"title": "Live test"}).json()
            assert data["cues"] == 2
            assert data["recorded"] is False

            captions = client.get(f"/api/projects/{data['project_id']}/captions").json()
            assert captions["cues"][0]["text"] == "Welcome back everyone."
            assert captions["provenance"]["captions"]["drafted_by"] == "model (live session)"
            assert captions["provenance"]["status"] == "draft_not_reviewed"
        finally:
            _SESSIONS.pop("t1", None)

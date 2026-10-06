"""Job runner: lifecycle, resume, cancel, websocket protocol."""

from __future__ import annotations

import time
from pathlib import Path


def _project(client, tmp_path) -> dict:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"bytes")
    return client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()


def _wait_terminal(client, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in ("succeeded", "failed", "cancelled"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not finish: {job}")


def test_noop_job_succeeds_and_persists(client, tmp_path):
    from service.settings_store import library_dir

    project = _project(client, tmp_path)
    job_id = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={"type": "noop", "params": {"steps": 2, "delay": 0.05}},
    ).json()["job_id"]

    job = _wait_terminal(client, job_id)
    assert job["state"] == "succeeded"
    assert job["result"] == {"steps": 2, "ran": 2, "skipped": 0}
    assert job["percent"] == 100

    job_file = library_dir() / project["id"] / "jobs" / f"{job_id}.json"
    assert job_file.is_file()


def test_noop_job_resumes_from_stage_files(client, tmp_path):
    project = _project(client, tmp_path)
    params = {"steps": 3, "delay": 0.05}

    first = client.post(
        f"/api/projects/{project['id']}/jobs", json={"type": "noop", "params": params}
    ).json()["job_id"]
    assert _wait_terminal(client, first)["result"]["ran"] == 3

    # Same job type again: every stage output exists, so everything is skipped.
    second = client.post(
        f"/api/projects/{project['id']}/jobs", json={"type": "noop", "params": params}
    ).json()["job_id"]
    result = _wait_terminal(client, second)["result"]
    assert result["ran"] == 0
    assert result["skipped"] == 3


def test_cancel_running_job(client, tmp_path):
    project = _project(client, tmp_path)
    job_id = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={"type": "noop", "params": {"steps": 50, "delay": 0.2}},
    ).json()["job_id"]

    time.sleep(0.3)  # let it start
    assert client.post(f"/api/jobs/{job_id}/cancel").json()["cancelling"] is True
    job = _wait_terminal(client, job_id)
    assert job["state"] == "cancelled"


def test_unknown_job_type_fails(client, tmp_path):
    project = _project(client, tmp_path)
    job_id = client.post(
        f"/api/projects/{project['id']}/jobs", json={"type": "mystery"}
    ).json()["job_id"]
    job = _wait_terminal(client, job_id)
    assert job["state"] == "failed"
    assert "Unknown job type" in job["error"]


def test_websocket_streams_progress(client, token, tmp_path):
    project = _project(client, tmp_path)
    job_id = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={"type": "noop", "params": {"steps": 2, "delay": 0.1}},
    ).json()["job_id"]

    messages = []
    with client.websocket_connect(f"/ws/jobs/{job_id}?token={token}") as ws:
        while True:
            message = ws.receive_json()
            messages.append(message)
            if message["type"] in ("done", "error"):
                break

    types = {m["type"] for m in messages}
    assert "state" in types
    assert "status" in types
    assert messages[-1]["type"] == "done"
    assert messages[-1]["result"]["steps"] == 2


def test_websocket_rejects_bad_token(client, tmp_path):
    project = _project(client, tmp_path)
    job_id = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={"type": "noop", "params": {"steps": 1, "delay": 0.05}},
    ).json()["job_id"]

    from starlette.websockets import WebSocketDisconnect

    import pytest

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/jobs/{job_id}?token=nope") as ws:
            ws.receive_json()

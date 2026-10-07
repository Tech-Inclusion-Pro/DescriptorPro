"""Image routes (service/routes/images.py)."""

from __future__ import annotations


def _project_with_images(client, tmp_path) -> dict:
    source = tmp_path / "deck.pdf.mp4"  # any media source; images attach to projects
    source.write_bytes(b"media")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {"image_description": True}}
    ).json()

    from service.projects import ProjectStore
    from service.settings_store import library_dir

    store = ProjectStore(library_dir())
    try:
        full = store.load(project["id"])
        full["images"] = [
            {
                "id": "img-0001", "path": "images/0001-roles.png", "name": "roles.png",
                "kind": "diagram", "ocr_text": [], "alt": "Six roles around a student.",
                "long_description": "", "flags": [],
                "decorative": {"suggested": True, "reason": "test", "confirmed": None},
                "status": "draft", "approved_by": None, "approved_at": None, "lang": "en",
            },
        ]
        store.save(full)
    finally:
        store.close()
    return project


def test_upload_batch_of_images(client, tmp_path):
    import cv2
    import numpy as np

    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {"image_description": True}}
    ).json()

    img = np.full((40, 60, 3), 250, dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "one.png"), img)
    cv2.imwrite(str(tmp_path / "two.png"), img)
    with open(tmp_path / "one.png", "rb") as f1, open(tmp_path / "two.png", "rb") as f2:
        response = client.post(
            f"/api/projects/{project['id']}/images",
            files=[("files", ("one.png", f1, "image/png")), ("files", ("two.png", f2, "image/png"))],
        )
    assert response.status_code == 200
    images = response.json()["images"]
    assert [i["id"] for i in images] == ["img-0001", "img-0002"]


def test_pptx_rejected_with_guidance(client, tmp_path):
    source = tmp_path / "lecture.mp4"
    source.write_bytes(b"media")
    project = client.post(
        "/api/projects", json={"source_path": str(source), "outputs": {}}
    ).json()
    response = client.post(
        f"/api/projects/{project['id']}/images",
        files=[("files", ("deck.pptx", b"zipbytes", "application/octet-stream"))],
    )
    assert response.status_code == 400
    assert "export the deck to PDF" in response.json()["detail"]


def test_approve_blocked_until_decorative_confirmed(client, tmp_path):
    project = _project_with_images(client, tmp_path)
    url = f"/api/projects/{project['id']}/images/img-0001"

    blocked = client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"})
    assert blocked.status_code == 400
    assert "never decides it alone" in blocked.json()["detail"]

    client.patch(url, json={"decorative_confirmed": False})
    approved = client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"}).json()
    assert approved["status"] == "approved"
    assert approved["flags"] == []


def test_edit_returns_to_draft(client, tmp_path):
    project = _project_with_images(client, tmp_path)
    url = f"/api/projects/{project['id']}/images/img-0001"
    client.patch(url, json={"decorative_confirmed": False})
    client.patch(url, json={"approve": True, "reviewer": "Rocco Catrone"})
    edited = client.patch(url, json={"alt": "Six team roles shown around a student."}).json()
    assert edited["status"] == "draft"
    assert edited["approved_by"] is None

"""Image-description routes (spec §7.11): batch upload, review table
edits, decorative confirmation (a person decides, never the tool), and
CSV/JSON/DOCX exports. Same review rules as every other cue type."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from service.projects import ProjectStore
from service.settings_store import library_dir

router = APIRouter(tags=["images"])


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


def _load(store: ProjectStore, project_id: str) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.post("/projects/{project_id}/images")
async def upload_images(project_id: str, request: Request) -> dict:
    """Multipart batch: image files and/or PDF slide decks. PowerPoint is
    rejected with export-to-PDF guidance (core/images.py)."""
    from core.images import ingest_images

    form = await request.form()
    uploads = [v for v in form.getlist("files") if not isinstance(v, str)]
    if not uploads:
        raise HTTPException(status_code=400, detail="No files in the upload.")

    store = _store()
    try:
        project = _load(store, project_id)
        folder = store.folder(project_id)
        incoming = folder / "images" / "_incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        paths = []
        for upload in uploads:
            data = await upload.read()
            if not data:
                continue
            target = incoming / (upload.filename or "image")
            target.write_bytes(data)
            paths.append(target)
        try:
            items = ingest_images(paths, folder / "images")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        finally:
            for p in paths:
                p.unlink(missing_ok=True)

        existing = project.get("images", [])
        for i, item in enumerate(items):
            item["id"] = f"img-{len(existing) + i + 1:04d}"
        project["images"] = existing + items
        store.save(project)
        return {"images": project["images"]}
    finally:
        store.close()


@router.get("/projects/{project_id}/images")
def get_images(project_id: str) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        return {"images": project.get("images", [])}
    finally:
        store.close()


class ImagePatch(BaseModel):
    alt: str | None = None
    long_description: str | None = None
    decorative_confirmed: bool | None = None
    approve: bool | None = None
    reviewer: str | None = None


@router.patch("/projects/{project_id}/images/{image_id}")
def patch_image(project_id: str, image_id: str, body: ImagePatch) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        item = next((i for i in project.get("images", []) if i["id"] == image_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="Image not found.")

        edited = False
        if body.alt is not None and body.alt != item.get("alt"):
            item["alt"] = body.alt
            edited = True
        if body.long_description is not None and body.long_description != item.get("long_description"):
            item["long_description"] = body.long_description
            edited = True
        if body.decorative_confirmed is not None:
            item.setdefault("decorative", {})["confirmed"] = body.decorative_confirmed
            edited = True
        if edited:
            item["status"] = "draft"
            item["approved_by"] = None
            item["approved_at"] = None

        if body.approve is True:
            if not body.reviewer or not body.reviewer.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Approving needs your name, so the record says who reviewed it.",
                )
            decorative = item.get("decorative") or {}
            if decorative.get("suggested") and decorative.get("confirmed") is None:
                raise HTTPException(
                    status_code=400,
                    detail="This image is suggested as decorative. Confirm or reject that first — the tool never decides it alone.",
                )
            item["status"] = "approved"
            item["approved_by"] = body.reviewer.strip()
            item["approved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            item["flags"] = []
        elif body.approve is False:
            item["status"] = "draft"
            item["approved_by"] = None
            item["approved_at"] = None

        store.save(project)
        return item
    finally:
        store.close()

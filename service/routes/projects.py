"""Project CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from service.projects import ProjectStore, sha256_file
from service.settings_store import library_dir

router = APIRouter(tags=["projects"])


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


class CreateProject(BaseModel):
    title: str = ""
    source_path: str
    outputs: dict = {}
    copy_media: bool = False


@router.post("/projects")
def create_project(body: CreateProject) -> dict:
    store = _store()
    try:
        project = store.create(body.title, body.source_path, body.outputs, body.copy_media)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        store.close()
    return project


@router.post("/projects/upload")
async def upload_project(request: Request) -> dict:
    """Multipart create: fields `file` (the media), `title`, `outputs` (JSON)."""
    import json as json_mod

    form = await request.form()
    upload = form.get("file")
    if upload is None or isinstance(upload, str):
        raise HTTPException(status_code=400, detail="No file in the upload.")
    try:
        outputs = json_mod.loads(str(form.get("outputs") or "{}"))
    except json_mod.JSONDecodeError:
        outputs = {}

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    store = _store()
    try:
        return store.create_from_upload(
            str(form.get("title") or ""), upload.filename or "media", data, outputs
        )
    finally:
        store.close()


media_router = APIRouter()


@media_router.get("/media/{project_id}")
def stream_media(project_id: str, token: str, request: Request):
    """Media playback for the review editor. Token comes as a query param
    because media elements cannot send headers; checked in constant time."""
    from pathlib import Path

    from fastapi.responses import FileResponse

    from service.auth import check_ws_token

    if not check_ws_token(token, request.app.state.token):
        raise HTTPException(status_code=401, detail="Missing or invalid service token.")

    store = _store()
    try:
        project = store.load(project_id)
    finally:
        store.close()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    media = Path(project["source"]["path"])
    if not media.is_file():
        raise HTTPException(status_code=404, detail="Media file is missing.")
    return FileResponse(media)


@router.get("/projects")
def list_projects() -> list[dict]:
    store = _store()
    try:
        return store.list()
    finally:
        store.close()


@router.get("/projects/{project_id}")
def get_project(project_id: str) -> dict:
    store = _store()
    try:
        project = store.load(project_id)
    finally:
        store.close()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.post("/projects/{project_id}/hash")
def hash_source(project_id: str) -> dict:
    """Compute and store the source sha256 (provenance). Small files only in
    Phase 0; big files move into the ingest job in Phase 1."""
    from pathlib import Path

    store = _store()
    try:
        project = store.load(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        source = Path(project["source"]["path"])
        if not source.is_file():
            raise HTTPException(status_code=400, detail="Source file is missing.")
        project["source"]["sha256"] = sha256_file(source)
        store.save(project)
        return {"sha256": project["source"]["sha256"]}
    finally:
        store.close()


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, keep_exports: bool = False) -> dict:
    store = _store()
    try:
        deleted = store.delete(project_id, keep_exports=keep_exports)
    finally:
        store.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"deleted": True, "kept_exports": keep_exports}

"""Caption review and export routes.

Review rules (spec §8.1, §11): edits keep a cue in draft; approving records
the reviewer's name and time; flags clear only when a person approves the cue;
export status is draft_not_reviewed unless every cue is approved.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.projects import ProjectStore
from service.settings_store import library_dir

router = APIRouter(tags=["captions"])


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load(store: ProjectStore, project_id: str) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _refresh_provenance(project: dict) -> None:
    cues = project.get("caption_cues", [])
    approved = sum(1 for c in cues if c.get("status") == "approved")
    prov = project.setdefault("provenance", {})
    cap = prov.setdefault("captions", {"drafted_by": "model", "style": "verbatim"})
    cap["cues"] = len(cues)
    cap["approved"] = approved
    cap["flagged_open"] = sum(1 for c in cues if c.get("flags") and c.get("status") != "approved")
    prov["status"] = "reviewed" if cues and approved == len(cues) else "draft_not_reviewed"


@router.get("/projects/{project_id}/captions")
def get_captions(project_id: str) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        return {
            "cues": project.get("caption_cues", []),
            "provenance": project.get("provenance", {}),
            "source": project.get("source", {}),
            "status": project.get("status"),
        }
    finally:
        store.close()


class CuePatch(BaseModel):
    text: str | None = None
    approve: bool | None = None
    reviewer: str | None = None


@router.patch("/projects/{project_id}/captions/{cue_id}")
def patch_cue(project_id: str, cue_id: str, body: CuePatch) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        cue = next((c for c in project.get("caption_cues", []) if c["id"] == cue_id), None)
        if cue is None:
            raise HTTPException(status_code=404, detail="Cue not found.")

        if body.text is not None and body.text != cue["text"]:
            cue["text"] = body.text
            # An edited cue goes back to draft; a person re-approves it.
            cue["status"] = "draft"
            cue["approved_by"] = None
            cue["approved_at"] = None

        if body.approve is True:
            if not body.reviewer or not body.reviewer.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Approving needs your name, so the record says who reviewed it.",
                )
            cue["status"] = "approved"
            cue["approved_by"] = body.reviewer.strip()
            cue["approved_at"] = _now_iso()
            # Flags clear only on human approval (spec §7.9).
            cue["flags"] = []
        elif body.approve is False:
            cue["status"] = "draft"
            cue["approved_by"] = None
            cue["approved_at"] = None

        _refresh_provenance(project)
        store.save(project)
        return cue
    finally:
        store.close()


class ExportRequest(BaseModel):
    formats: list[str] = ["vtt"]


@router.post("/projects/{project_id}/export")
def export_captions(project_id: str, body: ExportRequest) -> dict:
    from exporters.caption_cue_exporter import export_cues_srt, export_cues_vtt

    store = _store()
    try:
        project = _load(store, project_id)
        if not project.get("caption_cues"):
            raise HTTPException(status_code=400, detail="There are no caption cues to export yet.")

        _refresh_provenance(project)
        exports_dir = store.folder(project_id) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        lang = project.get("provenance", {}).get("language") or "en"
        stem = f"captions.{lang}"

        written: list[str] = []
        for fmt in body.formats:
            if fmt == "vtt":
                written.append(str(export_cues_vtt(project, exports_dir / f"{stem}.vtt")))
            elif fmt == "srt":
                path = export_cues_srt(project, exports_dir / f"{stem}.srt")
                written.append(str(path))
                written.append(str(path.with_suffix(".provenance.txt")))
            else:
                raise HTTPException(status_code=400, detail=f"Unknown export format: {fmt}")

        project["status"] = "exported"
        store.save(project)
        return {
            "written": written,
            "status": project["provenance"]["status"],
        }
    finally:
        store.close()

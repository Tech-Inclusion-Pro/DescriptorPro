"""Description review routes (spec §8.1) + the standards view data.

Same review rules as captions: edits return a cue to draft; approving
records who and when; flags clear only on human approval (§7.9). The
reviewer can take the verification pass's suggested text (contradicted
claims struck) or the full/short drafts.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.projects import ProjectStore
from service.settings_store import library_dir

router = APIRouter(tags=["descriptions"])

_STANDARDS_FILE = Path(__file__).resolve().parent.parent.parent / "standards" / "description_criteria.json"


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


def _load(store: ProjectStore, project_id: str) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _refresh_provenance(project: dict) -> None:
    cues = project.get("description_cues", [])
    prov = project.setdefault("provenance", {})
    desc = prov.setdefault("descriptions", {"drafted_by": "model", "style": project.get("ad_style") or "standard"})
    desc["cues"] = len(cues)
    desc["approved"] = sum(1 for c in cues if c.get("status") == "approved")
    desc["flagged_open"] = sum(1 for c in cues if c.get("flags") and c.get("status") != "approved")


@router.get("/standards")
def get_standards() -> dict:
    return json.loads(_STANDARDS_FILE.read_text(encoding="utf-8"))


@router.get("/projects/{project_id}/descriptions")
def get_descriptions(project_id: str) -> dict:
    from core.gapfit import added_running_time

    store = _store()
    try:
        project = _load(store, project_id)
        cues = project.get("description_cues", [])
        return {
            "cues": cues,
            "ad_style": project.get("ad_style") or "standard",
            "added_running_time": added_running_time(cues),
            "provenance": project.get("provenance", {}),
        }
    finally:
        store.close()


class DescriptionPatch(BaseModel):
    text: str | None = None
    use: str | None = None  # "suggested" | "full" | "short"
    approve: bool | None = None
    reviewer: str | None = None


@router.patch("/projects/{project_id}/descriptions/{cue_id}")
def patch_description(project_id: str, cue_id: str, body: DescriptionPatch) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        cue = next((c for c in project.get("description_cues", []) if c["id"] == cue_id), None)
        if cue is None:
            raise HTTPException(status_code=404, detail="Description not found.")

        new_text = None
        if body.use == "suggested":
            new_text = cue.get("suggested_text") or cue["text"]
        elif body.use == "full":
            new_text = cue.get("full_text") or cue["text"]
        elif body.use == "short":
            new_text = cue.get("short_text") or cue["text"]
        elif body.text is not None:
            new_text = body.text

        if new_text is not None and new_text != cue["text"]:
            from core.gapfit import estimate_duration

            cue["text"] = new_text
            cue["est_duration"] = estimate_duration(new_text)
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
            cue["approved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cue["flags"] = []  # flags clear only on human approval (§7.9)
        elif body.approve is False:
            cue["status"] = "draft"
            cue["approved_by"] = None
            cue["approved_at"] = None

        _refresh_provenance(project)
        store.save(project)
        return cue
    finally:
        store.close()

"""Segment + need-check routes (spec §7.6 output rules).

Never a whole-video verdict: the UI gets the tally and the per-segment
table. `needed` and `uncertain` segments require a recorded decision before
export in full review mode; each decision stores who and when.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.need_check import STANDARDS_CHECKED, tally
from service.projects import ProjectStore
from service.settings_store import library_dir

router = APIRouter(tags=["segments"])


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


def _load(store: ProjectStore, project_id: str) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.get("/projects/{project_id}/segments")
def get_segments(project_id: str) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        segments = project.get("segments", [])
        return {
            "segments": segments,
            "tally": tally(segments),
            "standards_checked": STANDARDS_CHECKED,
            # Spec §7.6: report against WCAG, never legal advice — the UI
            # must show this sentence.
            "notice": (
                "This tool reports against WCAG criteria. It does not give legal advice."
            ),
        }
    finally:
        store.close()


class DecisionPatch(BaseModel):
    value: str  # describe | skip | undecided
    by: str | None = None


@router.patch("/projects/{project_id}/segments/{segment_id}/decision")
def patch_decision(project_id: str, segment_id: str, body: DecisionPatch) -> dict:
    if body.value not in ("describe", "skip", "undecided"):
        raise HTTPException(status_code=400, detail="Decision must be describe, skip, or undecided.")
    if body.value != "undecided" and not (body.by or "").strip():
        raise HTTPException(
            status_code=400,
            detail="A decision needs your name, so the record says who made it.",
        )
    store = _store()
    try:
        project = _load(store, project_id)
        segment = next((s for s in project.get("segments", []) if s["id"] == segment_id), None)
        if segment is None:
            raise HTTPException(status_code=404, detail="Segment not found.")
        segment["decision"] = {
            "value": body.value,
            "by": body.by.strip() if body.value != "undecided" and body.by else None,
            "at": (
                datetime.datetime.now(datetime.timezone.utc).isoformat()
                if body.value != "undecided"
                else None
            ),
        }
        store.save(project)
        return segment["decision"]
    finally:
        store.close()

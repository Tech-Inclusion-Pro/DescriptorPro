"""Cloud BYOK (spec §13): off by default, per project and per stage, with
the user's own key, and a preview of exactly what would be sent before the
first call.

Keys live in the OS keychain (python-keyring → macOS Keychain), never in
project files, never in settings.json, and never returned by any route —
GET only reports which providers have a stored key.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from service.projects import ProjectStore
from service.settings_store import library_dir

router = APIRouter(tags=["cloud"])

_SERVICE = "DescriptorPro"
_PROVIDERS = ("anthropic", "openai")


@router.get("/cloud/keys")
def list_keys() -> dict:
    import keyring

    stored = [p for p in _PROVIDERS if keyring.get_password(_SERVICE, p)]
    return {"providers": stored, "available": list(_PROVIDERS)}


class KeyPut(BaseModel):
    provider: str
    key: str


@router.put("/cloud/keys")
def put_key(body: KeyPut) -> dict:
    import keyring

    if body.provider not in _PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")
    if not body.key.strip():
        raise HTTPException(status_code=400, detail="The key is empty.")
    keyring.set_password(_SERVICE, body.provider, body.key.strip())
    return {"stored": body.provider}


@router.delete("/cloud/keys/{provider}")
def delete_key(provider: str) -> dict:
    import keyring

    try:
        keyring.delete_password(_SERVICE, provider)
    except keyring.errors.PasswordDeleteError:
        pass
    return {"removed": provider}


_STAGE_PAYLOADS = {
    "describe": "The uncovered visual facts, the OCR text, the transcript window, and your intent profile for each segment marked describe — plus one keyframe image per segment.",
    "need_check": "Each essential visual fact and the transcript words around it.",
    "visual_facts": "One keyframe image per segment, its OCR text, and your intent profile.",
}


@router.get("/projects/{project_id}/cloud-preview")
def cloud_preview(project_id: str, stage: str = "describe") -> dict:
    """Spec §13: before the first cloud call you see exactly what would be
    sent and to whom. Nothing is sent by this route."""
    if stage not in _STAGE_PAYLOADS:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")
    store = ProjectStore(library_dir())
    try:
        project = store.load(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")

        segments = project.get("segments", [])
        to_describe = [s for s in segments if (s.get("decision") or {}).get("value") == "describe"]
        keyframes = [k for s in to_describe for k in s.get("keyframes", [])]
        folder = store.folder(project_id)
        frame_bytes = sum(
            (folder / k).stat().st_size for k in keyframes if (folder / k).exists()
        )
        sample_facts = [
            f["text"] for s in to_describe[:2] for f in s.get("visual_facts", [])[:2]
        ]
        return {
            "stage": stage,
            "would_send": _STAGE_PAYLOADS[stage],
            "segments": len(to_describe),
            "keyframe_images": len(keyframes),
            "keyframe_bytes": frame_bytes,
            "sample_text": sample_facts,
            "never_sent": "The media file itself, the full video, and your library never leave this computer.",
            "note": "Nothing has been sent. Cloud stays off until you confirm on a specific run.",
        }
    finally:
        store.close()

"""Intent conversation routes (spec §7.2).

The UI runs the conversation (six fixed questions, each skippable) and
posts the answers; the text model converts them to an IntentProfile; the
profile is stored on the project and the user can edit every field via PUT.
The profile, not the conversation, drives later stages.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.intent import QUESTIONS, default_profile, profile_from_answers, sanitize_profile
from service.projects import ProjectStore
from service.settings_store import library_dir, load_settings

router = APIRouter(tags=["intent"])


def _store() -> ProjectStore:
    return ProjectStore(library_dir())


def _load(store: ProjectStore, project_id: str) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.get("/intent/questions")
def get_questions() -> dict:
    return {"questions": QUESTIONS}


@router.get("/projects/{project_id}/intent")
def get_intent(project_id: str) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        return {"intent": project.get("intent") or default_profile()}
    finally:
        store.close()


class IntentPut(BaseModel):
    intent: dict


@router.put("/projects/{project_id}/intent")
def put_intent(project_id: str, body: IntentPut) -> dict:
    store = _store()
    try:
        project = _load(store, project_id)
        project["intent"] = sanitize_profile(body.intent)
        store.save(project)
        return {"intent": project["intent"]}
    finally:
        store.close()


class ConverseRequest(BaseModel):
    answers: dict[str, str]


@router.post("/projects/{project_id}/intent/converse")
async def converse(project_id: str, body: ConverseRequest) -> dict:
    """Turn conversation answers into a draft profile. The caller shows the
    result for editing — nothing downstream runs off the raw answers."""
    from core.engine.llm import LlmClient

    settings = load_settings()
    model = settings["text_model"]
    client = LlmClient()

    def generate(prompt: str) -> str:
        return client.generate_json(model, prompt, keep_alive=0)

    try:
        profile = await asyncio.to_thread(profile_from_answers, body.answers, generate)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The local text model could not build the profile ({exc}). "
            "Check that Ollama is running, then try again — or fill the profile in by hand.",
        ) from None

    store = _store()
    try:
        project = _load(store, project_id)
        project["intent"] = profile
        store.save(project)
        return {"intent": profile}
    finally:
        store.close()

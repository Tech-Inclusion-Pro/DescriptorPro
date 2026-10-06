"""Service settings routes (library location, UI language)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from service.settings_store import load_settings, save_settings

router = APIRouter(tags=["settings"])


class SettingsPatch(BaseModel):
    library_dir: str | None = None
    language: str | None = None


@router.get("/settings")
def get_settings() -> dict:
    return load_settings()


@router.put("/settings")
def put_settings(body: SettingsPatch) -> dict:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    return save_settings(patch)

"""Job record and persistence (spec §3.3: every stage resumable from saved output)."""

from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class Job:
    type: str
    project_id: str
    params: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: JobState = JobState.QUEUED
    stage: str = ""
    percent: int = 0
    status_text: str = ""
    created: str = field(default_factory=_now_iso)
    started: str | None = None
    finished: str | None = None
    error: str | None = None
    result: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    def persist(self, project_folder: Path) -> None:
        jobs_dir = project_folder / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        (jobs_dir / f"{self.id}.json").write_text(json.dumps(self.to_dict(), indent=2))

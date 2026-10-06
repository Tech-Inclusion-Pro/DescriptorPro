"""Job-type registry. Phase 0 ships only `noop`, which exercises the whole
pipeline contract: stages, progress, resume-from-saved-output, cancellation.
Phase 1 adds `ingest` and `captions` here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

JobHandler = Callable[..., Awaitable[dict]]


async def noop_job(ctx, model_manager) -> dict:
    """Test job: three stages, each writes a stage file and resume-skips it."""
    params = ctx.job.params
    steps = int(params.get("steps", 3))
    delay = float(params.get("delay", 0.4))
    stage_dir = ctx.project_folder / "jobs"
    stage_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    for step in range(1, steps + 1):
        ctx.cancel.raise_if_cancelled()
        stage_name = f"noop-{step}"
        ctx.stage(stage_name)
        stage_file = stage_dir / f"{ctx.job.type}-stage-{step}.json"

        if stage_file.exists():
            ctx.status(f"Stage {step} already complete. Skipping.")
        else:
            ctx.status(f"Working on stage {step} of {steps}...")
            await asyncio.sleep(delay)
            ctx.cancel.raise_if_cancelled()
            stage_file.write_text(json.dumps({"stage": step, "done": True}))
            completed += 1

        ctx.percent(min(int(step / steps * 100), 100))

    ctx.status("Test job complete.")
    return {"steps": steps, "ran": completed, "skipped": steps - completed}


_HANDLERS: dict[str, JobHandler] = {
    "noop": noop_job,
}


def get_job_handler(job_type: str) -> JobHandler:
    try:
        return _HANDLERS[job_type]
    except KeyError:
        raise ValueError(f"Unknown job type: {job_type}") from None


def register_job(job_type: str, handler: JobHandler) -> None:
    _HANDLERS[job_type] = handler

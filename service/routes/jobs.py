"""Job submission and inspection routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from service.jobs.models import Job

router = APIRouter(tags=["jobs"])


class SubmitJob(BaseModel):
    type: str
    params: dict = {}


@router.post("/projects/{project_id}/jobs")
async def submit_job(project_id: str, body: SubmitJob, request: Request) -> dict:
    runner = request.app.state.job_runner
    job = Job(type=body.type, project_id=project_id, params=body.params)
    runner.submit(job)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    job = request.app.state.job_runner.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict()


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request) -> dict:
    ok = request.app.state.job_runner.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Job is not running or queued.")
    return {"cancelling": True}

"""Single-worker job runner.

One asyncio consumer task executes jobs strictly in sequence, so the memory
rule "one model loaded at a time" (spec §5.3) is structural. Blocking engine
work runs in a thread via asyncio.to_thread; progress events cross back into
the loop with call_soon_threadsafe and fan out to websocket subscribers.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import time
from pathlib import Path

from core.engine.progress import CancelToken, Cancelled
from service.jobs.models import Job, JobState
from service.jobs.registry import get_job_handler
from service.settings_store import library_dir

PROGRESS_MIN_INTERVAL = 0.5  # seconds; ≤2 progress messages per second


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class JobContext:
    """Passed to job handlers: progress sink + cancel token + project folder."""

    def __init__(self, runner: "JobRunner", job: Job, loop: asyncio.AbstractEventLoop) -> None:
        self.job = job
        self.cancel = CancelToken()
        self.project_folder: Path = library_dir() / job.project_id
        self._runner = runner
        self._loop = loop
        self._started_monotonic = time.monotonic()
        self._last_progress = 0.0

    # ProgressReporter protocol (callable from worker threads)

    def percent(self, value: int) -> None:
        now = time.monotonic()
        if value < 100 and now - self._last_progress < PROGRESS_MIN_INTERVAL:
            return
        self._last_progress = now
        self.job.percent = value
        eta = self._eta(value)
        self._emit({"type": "progress", "percent": value, "stage": self.job.stage, "eta_seconds": eta})

    def status(self, message: str) -> None:
        self.job.status_text = message
        self._emit({"type": "status", "message": message})

    def partial(self, payload: dict) -> None:
        self._emit({"type": "partial", "payload": payload})

    def stage(self, name: str) -> None:
        self.job.stage = name
        self._persist()
        self._emit({"type": "state", "state": self.job.state.value, "stage": name})

    def _eta(self, percent: int) -> int | None:
        """Honest estimate from measured speed; None until one minute has passed."""
        elapsed = time.monotonic() - self._started_monotonic
        if elapsed < 60 or percent <= 0:
            return None
        return int(elapsed * (100 - percent) / percent)

    def _persist(self) -> None:
        if self.project_folder.is_dir():
            self.job.persist(self.project_folder)

    def _emit(self, message: dict) -> None:
        self._loop.call_soon_threadsafe(self._runner.publish, self.job.id, message)


class JobRunner:
    def __init__(self, model_manager) -> None:
        self.model_manager = model_manager
        self.jobs: dict[str, Job] = {}
        self.contexts: dict[str, JobContext] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._worker: asyncio.Task | None = None

    async def start(self) -> None:
        self._worker = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker

    # -- public API ---------------------------------------------------------

    def submit(self, job: Job) -> Job:
        self.jobs[job.id] = job
        ctx = JobContext(self, job, asyncio.get_running_loop())
        self.contexts[job.id] = ctx
        ctx._persist()
        self._queue.put_nowait(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.state not in (JobState.QUEUED, JobState.RUNNING):
            return False
        self.contexts[job_id].cancel.cancel()
        if job.state is JobState.QUEUED:
            self._finish(job, JobState.CANCELLED)
        return True

    # -- pub/sub for websockets ----------------------------------------------

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(job_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    def publish(self, job_id: str, message: dict) -> None:
        for queue in self._subscribers.get(job_id, []):
            queue.put_nowait(message)

    # -- worker ---------------------------------------------------------------

    async def _run_forever(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self.jobs[job_id]
            if job.state is not JobState.QUEUED:
                continue  # cancelled while queued
            ctx = self.contexts[job_id]

            job.state = JobState.RUNNING
            job.started = _now_iso()
            ctx._persist()
            self.publish(job.id, {"type": "state", "state": "running", "stage": job.stage})

            try:
                handler = get_job_handler(job.type)
                result = await handler(ctx, self.model_manager)
                job.result = result
                self._finish(job, JobState.SUCCEEDED)
            except Cancelled:
                self._finish(job, JobState.CANCELLED)
            except Exception as exc:  # report, never crash the worker
                job.error = str(exc)
                self._finish(job, JobState.FAILED)

    def _finish(self, job: Job, state: JobState) -> None:
        job.state = state
        job.finished = _now_iso()
        ctx = self.contexts.get(job.id)
        if ctx:
            ctx._persist()
        if state is JobState.SUCCEEDED:
            self.publish(job.id, {"type": "done", "result": job.result or {}})
        elif state is JobState.FAILED:
            self.publish(job.id, {"type": "error", "message": job.error or "Job failed."})
        else:
            self.publish(job.id, {"type": "state", "state": state.value, "stage": job.stage})

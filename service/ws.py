"""Websocket progress endpoint: /ws/jobs/{job_id}?token=...

Sends the job's current state on connect, then streams runner events:
state | progress | status | partial | done | error.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from service.auth import check_ws_token


def register_ws(app: FastAPI) -> None:
    @app.websocket("/ws/jobs/{job_id}")
    async def job_progress(websocket: WebSocket, job_id: str) -> None:
        token = websocket.query_params.get("token")
        if not check_ws_token(token, app.state.token):
            await websocket.close(code=4401)
            return

        runner = app.state.job_runner
        job = runner.get(job_id)
        if job is None:
            await websocket.close(code=4404)
            return

        await websocket.accept()
        await websocket.send_json(
            {
                "type": "state",
                "state": job.state.value,
                "stage": job.stage,
                "percent": job.percent,
            }
        )

        queue = runner.subscribe(job_id)
        try:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
                if message["type"] in ("done", "error"):
                    break
                if message["type"] == "state" and message.get("state") == "cancelled":
                    break
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            runner.unsubscribe(job_id, queue)
            with contextlib.suppress(Exception):
                await websocket.close()

"""Live session routes (spec §10).

- WS /ws/live: binary frames of mono float32 PCM at 16 kHz in; caption
  JSON out ({text, sentences, lag_ms}). Text frames carry control:
  {"type":"record","on":bool} (default OFF — the app does not record
  unless the user turns it on) and {"type":"stop"}.
- POST /api/live/{session_id}/frame: one slide frame; returns the change
  announcement or {"changed": false}.
- POST /api/live/{session_id}/project: after stop — saves the transcript
  (and the recording when one exists) as a project so the full recorded
  pipeline can run on it.

Sessions live in memory keyed by a server-issued id; stopping the ws
keeps the session for saving, closing the app drops it.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
import wave

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from service.settings_store import library_dir, load_settings

router = APIRouter(tags=["live"])

_SESSIONS: dict[str, dict] = {}


def register_live_ws(app) -> None:
    @app.websocket("/ws/live")
    async def live_captions(websocket: WebSocket) -> None:
        from service.auth import check_ws_token

        token = websocket.query_params.get("token")
        if not check_ws_token(token, app.state.token):
            await websocket.close(code=4401)
            return
        await websocket.accept()

        import numpy as np

        from core.live.announcer import SlideWatcher
        from core.live.captions import LiveCaptioner

        settings = load_settings()
        model_name = settings["parakeet_model"]
        session_id = secrets.token_urlsafe(8)
        session: dict = {
            "sentences": [],
            "wav_path": None,
            "wav": None,
            "watcher": SlideWatcher(),
            "started": time.time(),
            "model": model_name,
        }
        _SESSIONS[session_id] = session

        manager = app.state.model_manager
        async with manager.use("parakeet", model_name):
            captioner = await asyncio.to_thread(LiveCaptioner, model_name)
            await websocket.send_json({"type": "ready", "session_id": session_id})
            try:
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        break
                    if (data := message.get("bytes")) is not None:
                        pcm = np.frombuffer(data, dtype=np.float32)
                        if session["wav"] is not None:
                            session["wav"].writeframes(
                                (np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes()
                            )
                        update = await asyncio.to_thread(captioner.feed, pcm)
                        session["sentences"] = update["sentences"]
                        await websocket.send_json({"type": "caption", **update})
                    elif (text := message.get("text")) is not None:
                        control = json.loads(text)
                        if control.get("type") == "record":
                            if control.get("on") and session["wav"] is None:
                                path = library_dir() / f"live-{session_id}.wav"
                                handle = wave.open(str(path), "wb")
                                handle.setnchannels(1)
                                handle.setsampwidth(2)
                                handle.setframerate(16000)
                                session["wav"] = handle
                                session["wav_path"] = str(path)
                            elif not control.get("on") and session["wav"] is not None:
                                session["wav"].close()
                                session["wav"] = None
                            await websocket.send_json(
                                {"type": "recording", "on": session["wav"] is not None}
                            )
                        elif control.get("type") == "stop":
                            final = await asyncio.to_thread(captioner.close)
                            session["sentences"] = final["sentences"]
                            await websocket.send_json(
                                {"type": "final", "session_id": session_id, **final}
                            )
                            break
            except WebSocketDisconnect:
                pass
            finally:
                if session["wav"] is not None:
                    session["wav"].close()
                    session["wav"] = None


@router.post("/live/{session_id}/frame")
async def live_frame(session_id: str, request: Request) -> dict:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No live session with that id.")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty frame.")
    change = await asyncio.to_thread(session["watcher"].feed, body)
    if change is None:
        return {"changed": False}
    return {"changed": True, **change}


@router.post("/live/{session_id}/project")
def live_to_project(session_id: str, body: dict | None = None) -> dict:
    """Spec §10.1: save the transcript (+ recording) and offer the full
    recorded pipeline. Creates a project whose caption cues are the live
    sentences, marked as live drafts."""
    from service.projects import ProjectStore

    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No live session with that id.")
    sentences = session["sentences"]
    if not sentences and not session["wav_path"]:
        raise HTTPException(status_code=400, detail="Nothing was captured in this session.")

    title = (body or {}).get("title") or f"Live session {time.strftime('%Y-%m-%d %H:%M')}"
    store = ProjectStore(library_dir())
    try:
        if session["wav_path"]:
            project = store.create(title, session["wav_path"], {"captions": True}, copy_media=True)
        else:
            # Transcript-only: a placeholder text source keeps the project
            # shape; the cues below carry the content.
            placeholder = library_dir() / f"live-{session_id}-transcript.txt"
            placeholder.write_text(
                "\n".join(s["text"] for s in sentences), encoding="utf-8"
            )
            project = store.create(title, str(placeholder), {"captions": True}, copy_media=True)

        project["caption_cues"] = [
            {
                "id": f"cap-{i + 1:04d}",
                "start": s["start"],
                "end": s["end"],
                "speaker": None,
                "text": s["text"],
                "kind": "speech",
                "words": [],
                "flags": [],
                "status": "draft",
                "approved_by": None,
                "approved_at": None,
            }
            for i, s in enumerate(sentences)
        ]
        prov = project.setdefault("provenance", {})
        prov.setdefault("models", []).append(
            {"role": "asr_live", "name": f"parakeet-mlx {session['model']} (streaming)", "location": "local"}
        )
        prov["captions"] = {
            "drafted_by": "model (live session)",
            "cues": len(project["caption_cues"]),
            "approved": 0,
            "flagged_open": 0,
            "style": "verbatim",
        }
        prov["status"] = "draft_not_reviewed"
        prov["slide_log"] = session["watcher"].log
        store.save(project)
        return {
            "project_id": project["id"],
            "recorded": bool(session["wav_path"]),
            "cues": len(project["caption_cues"]),
        }
    finally:
        store.close()

"""Describe Studio service entry point.

Run: python -m service.main [--dev] [--port N]
Binds 127.0.0.1 only. Port 0 (default) lets the OS pick a free port; the
chosen port and the per-launch token are written to the handshake file and
printed as a DS_READY line on stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.branding import APP_NAME, APP_VERSION
from service.auth import TokenAuthMiddleware, new_token
from service.handshake import remove_handshake, write_handshake

UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist"


def create_app(token: str, dev: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from service.jobs.runner import JobRunner
        from service.model_manager import ModelManager

        app.state.model_manager = ModelManager()
        app.state.job_runner = JobRunner(app.state.model_manager)
        await app.state.job_runner.start()
        yield
        await app.state.job_runner.stop()
        remove_handshake()

    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.state.token = token
    app.state.shutdown_event = asyncio.Event()

    if dev:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(TokenAuthMiddleware, token=token)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}

    @app.post("/api/shutdown")
    async def shutdown() -> dict:
        app.state.shutdown_event.set()
        return {"stopping": True}

    from service.routes.captions import router as captions_router
    from service.routes.descriptions import router as descriptions_router
    from service.routes.intent import router as intent_router
    from service.routes.jobs import router as jobs_router
    from service.routes.projects import media_router
    from service.routes.projects import router as projects_router
    from service.routes.segments import router as segments_router
    from service.routes.settings import router as settings_router

    app.include_router(media_router)

    app.include_router(projects_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(captions_router, prefix="/api")
    app.include_router(descriptions_router, prefix="/api")
    app.include_router(intent_router, prefix="/api")
    app.include_router(segments_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")

    from service.ws import register_ws

    register_ws(app)

    if UI_DIST.is_dir():
        app.mount("/ui", StaticFiles(directory=UI_DIST, html=True), name="ui")

    return app


async def _serve(app: FastAPI, port: int) -> None:
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    serve_task = asyncio.create_task(server.serve())
    while not server.started and not serve_task.done():
        await asyncio.sleep(0.02)
    if serve_task.done():
        await serve_task  # surface startup errors
        return

    actual_port = server.servers[0].sockets[0].getsockname()[1]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_handshake(actual_port, app.state.token, started)

    await app.state.shutdown_event.wait()
    server.should_exit = True
    await serve_task


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} local service")
    parser.add_argument("--port", type=int, default=0, help="0 = OS-assigned")
    parser.add_argument("--dev", action="store_true", help="enable Vite dev CORS")
    args = parser.parse_args()

    token = new_token()
    app = create_app(token, dev=args.dev)
    try:
        asyncio.run(_serve(app, args.port))
    finally:
        remove_handshake()


if __name__ == "__main__":
    main()

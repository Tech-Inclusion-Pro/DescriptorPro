"""Per-launch bearer-token auth (spec §3.3).

Every HTTP request except GET /health must carry `Authorization: Bearer <token>`.
Websocket connections authenticate with a `?token=` query parameter checked at
the endpoint (middleware here covers HTTP only). The token is random per launch
so other local processes and web pages cannot drive the service.
"""

from __future__ import annotations

import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

OPEN_PATHS = {"/health"}
OPEN_PREFIXES = ("/ui",)


def new_token() -> str:
    return secrets.token_urlsafe(32)


class TokenAuthMiddleware:
    """Pure ASGI middleware: rejects HTTP requests without the launch token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in OPEN_PATHS or path.startswith(OPEN_PREFIXES):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        header = request.headers.get("authorization", "")
        expected = f"Bearer {self.token}"
        if not secrets.compare_digest(header, expected):
            response = JSONResponse(
                {"detail": "Missing or invalid service token."}, status_code=401
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def check_ws_token(provided: str | None, token: str) -> bool:
    """Constant-time websocket token check."""
    return provided is not None and secrets.compare_digest(provided, token)

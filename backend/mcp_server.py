from __future__ import annotations

import hmac
import json
import logging
from typing import Any

import uvicorn
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.config import settings
from backend.tools import create_mcp_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("campusflow.audit")


class BearerTokenMiddleware:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token.encode("utf-8")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"authorization", b"")
        scheme, separator, credentials = supplied.partition(b" ")
        if (
            not separator
            or scheme.lower() != b"bearer"
            or not hmac.compare_digest(credentials, self.token)
        ):
            logger.warning("audit event=mcp_access actor=unknown outcome=denied")
            body = json.dumps({"error": "Unauthorized"}).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)


def create_app() -> ASGIApp:
    server = create_mcp_server()
    streamable_app: Any = server.streamable_http_app()
    return BearerTokenMiddleware(streamable_app, settings.mcp_bearer_token)


if __name__ == "__main__":
    uvicorn.run(create_app(), host=settings.mcp_host, port=settings.mcp_port, log_level="info")

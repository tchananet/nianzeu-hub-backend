import json
import logging
from time import perf_counter
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.requests")


class RequestContext:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id, started = str(uuid4()), perf_counter()
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_context(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                message["headers"] = [*headers, (b"x-request-id", request_id.encode())]
                route = getattr(scope.get("route"), "path", "unmatched")
                logger.info(
                    json.dumps(
                        {
                            "request_id": request_id,
                            "route": route,
                            "status": message["status"],
                            "duration_ms": round((perf_counter() - started) * 1000, 2),
                        }
                    )
                )
            await send(message)

        await self.app(scope, receive, send_context)

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.shared.http_errors import error_response


class JsonTransport:
    """Bound JSON request bodies, including chunked bodies, before parsing/routes."""

    def __init__(self, app: ASGIApp, max_bytes: int = 65536) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return
        request, body = Request(scope), bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                response = error_response(request, "BODY_TOO_LARGE", 413, "Body too large")
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if body and media_type != "application/json":
            response = error_response(request, "UNSUPPORTED_MEDIA_TYPE", 415, "JSON required")
            await response(scope, receive, send)
            return

        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)

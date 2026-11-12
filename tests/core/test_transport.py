import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.json_transport import JsonTransport
from app.core.request_context import RequestContext
from app.shared.http_errors import install_error_handlers


def test_body_size_media_type_and_request_id():
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(JsonTransport)
    app.add_middleware(RequestContext)

    @app.post("/")
    def route(body: dict):
        return body

    with TestClient(app) as client:
        for content, headers, status in [
            ("{}", {}, 415),
            ("x" * 65537, {"content-type": "application/json"}, 413),
            ("{}", {"content-type": "application/json"}, 200),
        ]:
            response = client.post("/", content=content, headers=headers)
            assert response.status_code == status
            assert "x-request-id" in response.headers


def test_chunked_size_enforced_before_downstream():
    async def run():
        async def downstream(scope, receive, send):
            pytest.fail("oversize body reached downstream")

        messages = iter(
            [
                {"type": "http.request", "body": b"a" * 40000, "more_body": True},
                {"type": "http.request", "body": b"b" * 40000, "more_body": False},
            ]
        )
        sent = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        await JsonTransport(downstream)(
            {"type": "http", "method": "POST", "headers": []},
            receive,
            send,
        )
        assert sent[0]["status"] == 413

    asyncio.run(run())

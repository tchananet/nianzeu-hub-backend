from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.json_transport import JsonTransport
from app.core.request_context import RequestContext
from app.shared.http_errors import install_error_handlers


@pytest.mark.parametrize("transport", [False, True])
@pytest.mark.parametrize("body", [b"\xff", b'{"private":"\xff"}', b'{"private":"\xc3"}'])
def test_invalid_utf8_is_invalid_json(transport, body, caplog):
    app = FastAPI()
    install_error_handlers(app)
    if transport:
        app.add_middleware(JsonTransport)
    app.add_middleware(RequestContext)

    @app.post("/probe")
    def probe(payload: dict):
        pytest.fail("Invalid UTF-8 must not reach the route")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/probe", content=body, headers={"content-type": "application/json"}
        )
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "INVALID_JSON",
        "message": "Invalid JSON",
        "details": [],
    }
    assert str(UUID(response.json()["request_id"])) == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    assert "private" not in response.text + caplog.text

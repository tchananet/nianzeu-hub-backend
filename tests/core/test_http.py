from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_context import RequestContext
from app.shared.dto import Pagination
from app.shared.errors import EmailUnavailable, RateLimited
from app.shared.http_errors import install_error_handlers


@pytest.fixture
def client():
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(RequestContext)

    @app.post("/dto")
    def dto(data: Pagination):
        return data

    @app.get("/email")
    def email():
        raise EmailUnavailable()

    @app.get("/quota")
    def quota():
        raise RateLimited(17)

    @app.get("/boom")
    def boom():
        raise RuntimeError("password=must-not-leak")

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/missing", 404, "NOT_FOUND"),
        ("/dto", 405, "METHOD_NOT_ALLOWED"),
        ("/email", 503, "EMAIL_UNAVAILABLE"),
        ("/boom", 500, "INTERNAL_ERROR"),
        ("/quota", 429, "RATE_LIMITED"),
    ],
)
def test_error_envelopes(client, path, status, code, caplog):
    response = client.get(path, headers={"X-Request-ID": "untrusted"})
    body = response.json()
    assert response.status_code == status and body["error"]["code"] == code
    assert body["error"]["details"] == []
    assert str(UUID(body["request_id"])) == response.headers["x-request-id"]
    assert "must-not-leak" not in response.text + caplog.text
    if status == 405:
        assert "POST" in response.headers["allow"]
    if status == 429:
        assert response.headers["retry-after"] == "17"


def test_validation_and_success_ids(client):
    response = client.post("/dto", json={"page": "secret-value"})
    assert response.status_code == 422 and "secret-value" not in response.text
    assert response.json()["error"]["details"] == [{"field": "body.page", "code": "invalid"}]
    assert (
        client.post("/dto", content="{", headers={"Content-Type": "application/json"}).status_code
        == 400
    )
    success = client.post("/dto", json={"page": 1})
    assert success.status_code == 200
    assert UUID(success.headers["x-request-id"])

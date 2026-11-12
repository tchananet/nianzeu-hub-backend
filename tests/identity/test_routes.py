from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.json_transport import JsonTransport
from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.modules.identity.routes import create_router
from app.modules.identity.service import IdentityService
from app.shared.http_errors import install_error_handlers


@pytest.fixture
def client():
    service, limits = Mock(spec=IdentityService), Mock(spec=IdentityLimits)
    settings = Settings.model_construct(environment="test", session_cross_site_enabled=True,
                                        secure_cookies=True)
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(JsonTransport)
    app.include_router(create_router(service, limits, BrowserPolicy(settings)))
    with TestClient(app) as client:
        yield client, service, limits


def test_reset_uniform_and_never_calls_service(client):
    http, service, limits = client
    headers = {"Origin": "https://netatroniks.xyz"}
    for email in ["known@example.com", "unknown@example.com"]:
        response = http.post("/api/v1/auth/password/forgot",
                             json={"email": email}, headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "EMAIL_UNAVAILABLE"
    assert not service.mock_calls
    assert limits.ip.call_count == 2
    assert http.post("/api/v1/auth/password/reset", headers=headers,
                     json={"token": "a" * 43, "password": "a" * 12}).status_code == 503
    assert http.post("/api/v1/auth/password/forgot", headers=headers,
                     json={"email": "bad"}).status_code == 422


def test_origin_intent_and_content_type_before_side_effects(client):
    http, service, _ = client
    body = {"email": "a@example.com", "password": "a" * 12}
    assert http.post("/api/v1/auth/login", json=body).status_code == 403
    headers = {"Origin": "https://diddifree.com"}
    assert http.post("/api/v1/auth/login", json=body, headers=headers).status_code == 403
    headers["X-Auth-Intent"] = "session"
    assert http.post("/api/v1/auth/login", data=body, headers=headers).status_code == 415
    assert http.get("/api/v1/auth/me").status_code == 403
    assert not service.mock_calls

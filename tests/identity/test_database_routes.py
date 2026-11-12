from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.json_transport import JsonTransport
from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.modules.identity.routes import create_router
from app.shared.http_errors import install_error_handlers

pytestmark = pytest.mark.integration


def test_browser_flow_and_private_payload(identity_db):
    service, _, data = identity_db
    settings = Settings.model_construct(environment="test", session_cross_site_enabled=True,
                                        secure_cookies=True)
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(JsonTransport)
    app.include_router(create_router(service, Mock(spec=IdentityLimits), BrowserPolicy(settings)))
    headers = {"Origin": "http://localhost:5173", "X-Auth-Intent": "session"}
    with TestClient(app, base_url="https://api.diddifree.com", headers=headers) as http:
        body = data.model_dump()
        assert http.post("/api/v1/auth/register", json=body).status_code == 201
        assert not http.cookies
        response = http.post("/api/v1/auth/login", json=body)
        assert response.status_code == 200
        assert set(response.json()) == {"user", "csrf_token"}
        assert set(response.json()["user"]) == {"id", "email", "role", "created_at"}
        csrf = response.json()["csrf_token"]
        assert http.get("/api/v1/auth/me").status_code == 200
        assert http.get("/api/v1/auth/me?user_id=other").status_code == 422
        recovered = http.get("/api/v1/auth/csrf")
        assert recovered.json() == {"csrf_token": csrf}
        assert recovered.headers["cache-control"] == "no-store"
        assert http.post("/api/v1/auth/logout").status_code == 403
        assert http.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert http.get("/api/v1/auth/me").status_code == 401

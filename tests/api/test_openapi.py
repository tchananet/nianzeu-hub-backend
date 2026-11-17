"""The schema is served only when asked for, and describes the real route table."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from tests.api.conftest import SETTINGS


def client(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> TestClient:
    for key, value in (SETTINGS | overrides).items():
        monkeypatch.setenv(key, value)
    return TestClient(create_app(), base_url="https://api.diddifree.com",
                      client=("203.0.113.7", 44321), raise_server_exceptions=False)


def test_the_schema_is_absent_in_production_unless_enabled(monkeypatch) -> None:
    with client(monkeypatch, APP_ENVIRONMENT="production", APP_SECURE_COOKIES="true") as http:
        assert http.get("/api/v1/openapi.json").status_code == 404
        assert http.get("/api/v1/docs").status_code == 404


def test_enabling_it_serves_swagger_and_the_schema(monkeypatch) -> None:
    with client(monkeypatch, APP_ENVIRONMENT="production", APP_SECURE_COOKIES="true",
                APP_DOCS_ENABLED="true") as http:
        page = http.get("/api/v1/docs")
        assert page.status_code == 200
        assert "swagger" in page.text.lower()
        schema = http.get("/api/v1/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["title"] == "nianzeuhub backend"


def test_the_schema_covers_the_contract_route_table(monkeypatch) -> None:
    with client(monkeypatch) as http:          # test environment: docs on by default
        paths = http.get("/api/v1/openapi.json").json()["paths"]
    for path in [
        "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/logout",
        "/api/v1/auth/me", "/api/v1/auth/csrf", "/api/v1/auth/password/forgot",
        "/api/v1/auth/password/reset", "/api/v1/profiles/me", "/api/v1/profiles/me/contacts",
        "/api/v1/profiles/me/portfolio", "/api/v1/profiles/me/portfolio/upload-url",
        "/api/v1/profiles/{item_id}", "/api/v1/search/profiles", "/api/v1/skills",
        "/api/v1/portfolio/{item_id}/content",
    ]:
        assert path in paths or path.replace("{item_id}", "{profile_id}") in paths, path


def test_a_strict_boolean_is_required_for_the_flag(monkeypatch) -> None:
    # Settings rejects loose truthiness everywhere; this flag is no exception.
    with pytest.raises(ValidationError):
        client(monkeypatch, APP_DOCS_ENABLED="yes")


def header_names(operation: dict) -> list[str]:
    return [p["name"] for p in operation.get("parameters", []) if p.get("in") == "header"]


def test_the_schema_publishes_the_headers_the_policy_demands(monkeypatch) -> None:
    # BrowserPolicy refuses a mutation without these, but FastAPI only documents a
    # header a route declares. Undeclared, Swagger offered no field for them, so
    # "Try it out" on register answered 403 with no way to fix it from the page.
    with client(monkeypatch) as http:
        paths = http.get("/api/v1/openapi.json").json()["paths"]
    for path in ("/api/v1/auth/register", "/api/v1/auth/login"):
        assert header_names(paths[path]["post"]) == ["X-Auth-Intent"], path
    for path, method in (
        ("/api/v1/auth/logout", "post"), ("/api/v1/profiles/me", "put"),
        ("/api/v1/profiles/me", "delete"), ("/api/v1/profiles/me/contacts", "put"),
        ("/api/v1/profiles/me/portfolio", "post"),
        ("/api/v1/profiles/me/portfolio/upload-url", "post"),
        ("/api/v1/profiles/me/portfolio/{item_id}/validate", "post"),
        ("/api/v1/profiles/me/portfolio/{item_id}/publish", "post"),
        ("/api/v1/profiles/me/portfolio/{item_id}/unpublish", "post"),
        ("/api/v1/profiles/me/portfolio/{item_id}", "delete"),
    ):
        assert "X-CSRF-Token" in header_names(paths[path][method]), f"{method} {path}"


def test_the_declared_headers_stay_optional_in_the_schema(monkeypatch) -> None:
    # Required in the schema would make FastAPI answer 422 before the policy runs,
    # which would reject direct clients in open mode -- where neither is demanded.
    with client(monkeypatch) as http:
        paths = http.get("/api/v1/openapi.json").json()["paths"]
    for path, method in (("/api/v1/auth/register", "post"), ("/api/v1/profiles/me", "put")):
        for parameter in paths[path][method].get("parameters", []):
            if parameter.get("in") == "header":
                assert parameter.get("required") is not True, f"{method} {path}"

"""Open mode: no configured origin, plain HTTP, reachable directly on an address.

It exists so the API can be used without a proxy or a frontend. It must be
impossible in production, which is what most of these tests assert.
"""

import pytest
from fastapi import Request

from app.core.config import Settings
from app.modules.identity.browser import BrowserPolicy
from app.shared.errors import AppError

BASE = dict(
    environment="test",
    database_url="postgresql+psycopg://u:p@localhost/open_test",
    storage_endpoint="http://storage:8333",
    storage_public_endpoint="http://203.0.113.7:21848",
    storage_access_key="a", storage_secret_key="b",
    quarantine_bucket="quarantine", validated_bucket="validated",
    quota_hmac_secret="x" * 32, secure_cookies=False,
)


def settings(**changes: object) -> Settings:
    return Settings.model_validate(BASE | changes)


def test_no_origin_configured_is_legal_outside_production() -> None:
    assert settings().frontend_origin is None


@pytest.mark.parametrize("blank", ["", "   "])
def test_an_empty_value_reads_as_absent_not_as_a_value(blank: str) -> None:
    # Compose passes an unset variable through as an empty string.
    assert settings(frontend_origin=blank).frontend_origin is None


def test_plain_http_storage_is_accepted_on_any_host_outside_production() -> None:
    assert settings().storage_public_endpoint == "http://203.0.113.7:21848"


def test_insecure_cookies_no_longer_demand_a_localhost_api() -> None:
    assert settings(api_public_origin=None).secure_cookies is False


@pytest.mark.parametrize("environment", ["production"])
def test_production_still_demands_an_origin(environment: str) -> None:
    with pytest.raises(ValueError, match="frontend origin is required"):
        settings(environment=environment, secure_cookies=True,
                 storage_public_endpoint="https://files.example.com")


def test_production_still_demands_secure_cookies() -> None:
    with pytest.raises(ValueError):
        settings(environment="production", frontend_origin="https://app.example.com",
                 storage_public_endpoint="https://files.example.com")


def test_production_still_demands_https_storage() -> None:
    with pytest.raises(ValueError):
        settings(environment="production", secure_cookies=True,
                 frontend_origin="https://app.example.com")


def request_without_origin() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/v1/auth/login",
                    "headers": [(b"content-type", b"application/json")]})


def test_without_a_configured_origin_a_mutation_needs_no_origin_header() -> None:
    BrowserPolicy(settings()).validate_mutation(request_without_origin())


def test_without_a_configured_origin_login_needs_no_intent_header() -> None:
    # Demanding it would break curl and the Swagger page for no security gain.
    BrowserPolicy(settings()).validate_mutation(request_without_origin())


def test_with_a_configured_origin_both_are_enforced_again() -> None:
    policy = BrowserPolicy(settings(frontend_origin="https://app.example.com"))
    with pytest.raises(AppError) as raised:
        policy.validate_mutation(request_without_origin())
    assert raised.value.code == "ORIGIN_FORBIDDEN"

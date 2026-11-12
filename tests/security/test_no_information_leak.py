"""No error response may carry SQL, connection detail, configuration or a stack trace.

The fixture's database failure raises an OperationalError whose text contains both the
statement and the driver message, so any handler that echoed the cause would be caught
here. Secrets come from the same settings the fixture installs.
"""

from uuid import uuid4

import pytest

from tests.api.conftest import SETTINGS

GOOD = "https://diddifree.com"
FORBIDDEN_FRAGMENTS = [
    "SELECT 1", "connection refused", "OperationalError", "Traceback",
    "psycopg", "sqlalchemy", "rate_limit_windows", "INSERT INTO",
    SETTINGS["APP_QUOTA_HMAC_SECRET"], SETTINGS["APP_STORAGE_SECRET_KEY"],
    SETTINGS["APP_STORAGE_ACCESS_KEY"], SETTINGS["APP_DATABASE_URL"],
]
PROBES = [
    ("get", "/api/v1/skills"),
    ("get", "/api/v1/search/profiles?q=alpha"),
    ("get", f"/api/v1/profiles/{uuid4()}"),
    ("get", f"/api/v1/portfolio/{uuid4()}/content"),
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/profiles/me"),
    ("get", "/api/v1/does-not-exist"),
]


@pytest.mark.parametrize(("method", "path"), PROBES)
def test_error_bodies_stay_opaque(assembled, method, path):
    response = getattr(assembled, method)(path, headers={"Origin": GOOD})
    assert response.status_code >= 400
    body = response.text
    for fragment in FORBIDDEN_FRAGMENTS:
        assert fragment not in body, f"{path} leaked {fragment!r}"


@pytest.mark.parametrize(("method", "path"), PROBES)
def test_every_error_carries_the_contract_envelope(assembled, method, path):
    response = getattr(assembled, method)(path, headers={"Origin": GOOD})
    payload = response.json()
    assert set(payload) == {"error", "request_id"}
    assert set(payload["error"]) == {"code", "message", "details"}
    # details is always an array and empty outside validation errors.
    assert isinstance(payload["error"]["details"], list)
    assert payload["error"]["details"] == []
    assert payload["request_id"] == response.headers["x-request-id"]


def test_request_id_is_served_even_on_health(assembled):
    assert assembled.get("/health/live").headers["x-request-id"]


def test_private_reads_are_never_cacheable(assembled):
    response = assembled.get("/api/v1/profiles/me", headers={"Origin": GOOD})
    assert response.headers.get("cache-control") == "no-store"

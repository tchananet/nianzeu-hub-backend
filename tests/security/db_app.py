"""Assembled application bound to a real PostgreSQL test database.

Q01 must prove the cross-session guarantees of http.md end to end, which no module
suite can do on its own. SQLite is never substituted: without the variable the suite
blocks loudly rather than reporting a pass.
"""

import os
from collections.abc import Iterator
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import make_url

from app.main import create_app

ORIGIN = "https://diddifree.com"
# Each test is a distinct visitor: the register quota is 5/hour/IP, so sharing one
# address across tests would exhaust it and mask what is being verified.
_VISITORS = count(11)
INTENT = {"Origin": ORIGIN, "X-Auth-Intent": "session", "Content-Type": "application/json"}


def database_url() -> str:
    raw = os.environ.get("SECURITY_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BLOCKED: SECURITY_TEST_DATABASE_URL with migrations applied required",
                    pytrace=False)
    url = make_url(raw)
    if (url.drivername != "postgresql+psycopg"
            or url.host not in {"localhost", "127.0.0.1", "::1"}
            or not (url.database or "").endswith("_test")):
        pytest.fail("BLOCKED: loopback PostgreSQL _test database required", pytrace=False)
    return raw


def environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "APP_ENVIRONMENT": "test",
        "APP_DATABASE_URL": database_url(),
        "APP_STORAGE_ENDPOINT": "http://localhost:9000",
        "APP_STORAGE_PUBLIC_ENDPOINT": "https://files.diddifree.com",
        "APP_STORAGE_ACCESS_KEY": "q01-access",
        "APP_STORAGE_SECRET_KEY": "q01-secret",
        "APP_QUARANTINE_BUCKET": "quarantine",
        "APP_VALIDATED_BUCKET": "validated",
        "APP_FRONTEND_ORIGIN": ORIGIN,
        "APP_QUOTA_HMAC_SECRET": "q" * 32,
    }.items():
        monkeypatch.setenv(key, value)


def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    environment(monkeypatch)
    visitor = f"203.0.113.{next(_VISITORS) % 240 + 11}"
    with TestClient(create_app(), base_url="https://api.diddifree.com",
                    client=(visitor, 51000), raise_server_exceptions=False) as http:
        yield http

"""Q01 reuses the assembled application fixture: the control order it verifies is a
property of the whole wired app, not of any single module."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import assembled as assembled
from tests.security.db_app import INTENT, client, purge


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Assembled app on real PostgreSQL. Blocks explicitly when none is supplied."""
    yield from client(monkeypatch)


@pytest.fixture
def two_sessions(live: TestClient) -> Iterator[list[dict[str, object]]]:
    """Two registered, logged-in talents with independent cookies and CSRF tokens."""
    accounts: list[dict[str, object]] = []
    for _ in range(2):
        email = f"q01-{uuid4().hex}@example.com"
        body = {"email": email, "password": "a sufficiently long secret"}
        created = live.post("/api/v1/auth/register", json=body, headers=INTENT)
        assert created.status_code == 201, created.text
        logged = live.post("/api/v1/auth/login", json=body, headers=INTENT)
        assert logged.status_code == 200, logged.text
        accounts.append({"email": email, "csrf": logged.json()["csrf_token"],
                         "cookies": dict(live.cookies)})
        live.cookies.clear()
    try:
        yield accounts
    finally:
        purge([str(account["email"]) for account in accounts])

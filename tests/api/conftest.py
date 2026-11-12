import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.main import create_app

SETTINGS = {
    "APP_ENVIRONMENT": "test",
    "APP_DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:1/assembly_test",
    "APP_STORAGE_ENDPOINT": "http://localhost:9000",
    "APP_STORAGE_PUBLIC_ENDPOINT": "https://files.diddifree.com",
    "APP_STORAGE_ACCESS_KEY": "assembly-access",
    "APP_STORAGE_SECRET_KEY": "assembly-secret",
    "APP_QUARANTINE_BUCKET": "quarantine",
    "APP_VALIDATED_BUCKET": "validated",
    "APP_FRONTEND_ORIGIN": "https://diddifree.com",
    "APP_QUOTA_HMAC_SECRET": "x" * 32,
}


@pytest.fixture
def assembled(monkeypatch):
    """The real application factory with the database refusing every connection.

    Routing, middleware, the error envelope and the control order are all genuine;
    only the database is unavailable, which is what makes the probes instant.
    """
    for key, value in SETTINGS.items():
        monkeypatch.setenv(key, value)

    def refuse(*_: object, **__: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(Engine, "connect", refuse)
    # A real address: the quota key is an HMAC of the normalised client IP, and the
    # default "testclient" host is not an address at all.
    with TestClient(create_app(), base_url="https://api.diddifree.com",
                    client=("203.0.113.7", 44321),
                    raise_server_exceptions=False) as client:
        yield client

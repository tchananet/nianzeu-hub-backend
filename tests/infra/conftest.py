from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def health_client(monkeypatch):
    settings = Settings.model_validate(dict(
        environment="test", database_url="postgresql+psycopg://test:test@localhost/f02",
        storage_endpoint="http://localhost:9000",
        storage_public_endpoint="https://files.test",
        storage_access_key="test-access", storage_secret_key="test-secret",
        quarantine_bucket="quarantine", validated_bucket="validated",
        frontend_origin="https://frontend.test", quota_hmac_secret="x" * 32,
    ))
    monkeypatch.setattr("app.main.Settings", lambda: settings)
    engine, storage = MagicMock(), Mock()
    monkeypatch.setattr("app.main.build_engine", lambda _: engine)
    monkeypatch.setattr("app.main.storage_client", lambda _: storage)
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client, engine, storage
    engine.dispose.assert_called_once()

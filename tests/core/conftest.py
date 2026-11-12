import pytest

from app.core.config import Settings


@pytest.fixture
def config_data() -> dict[str, object]:
    return dict(
        environment="test",
        database_url="postgresql+psycopg://test:test@localhost/f01_test",
        storage_endpoint="http://localhost:9000",
        storage_public_endpoint="https://files.test",
        storage_access_key="test-access",
        storage_secret_key="test-secret",
        quarantine_bucket="quarantine",
        validated_bucket="validated",
        frontend_origin="https://diddifree.com",
        quota_hmac_secret="x" * 32,
    )


@pytest.fixture
def settings(config_data: dict[str, object]) -> Settings:
    return Settings.model_validate(config_data)

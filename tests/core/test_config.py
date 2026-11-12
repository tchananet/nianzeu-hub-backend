import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import Base, build_engine


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_url", "sqlite://"),
        ("database_url", "postgresql+psycopg://bad"),
        ("frontend_origin", "https://user:password@test"),
        ("frontend_origin", "http://remote.test"),
        ("frontend_origin", "https://test/path"),
        ("storage_public_endpoint", "http://remote.test"),
        ("quota_hmac_secret", "short"),
        ("pool_size", 6),
        ("environment", "unknown"),
        ("validated_bucket", "quarantine"),
        ("storage_secret_key", ""),
    ],
)
def test_invalid(config_data, field, value):
    config_data[field] = value
    with pytest.raises(ValidationError):
        Settings.model_validate(config_data)


def test_missing_and_secret_redaction(config_data):
    del config_data["environment"]
    with pytest.raises(ValidationError) as error:
        Settings.model_validate(config_data)
    assert "test-secret" not in str(error.value)


def test_secure_cookie_policy(config_data):
    config_data.update(environment="production", secure_cookies=False)
    with pytest.raises(ValidationError):
        Settings.model_validate(config_data)


def test_pool_without_network(settings):
    engine = build_engine(settings)
    assert engine.pool.size() == 5
    assert engine.pool.timeout() == 3
    assert engine.hide_parameters
    assert "test-secret" not in repr(settings)
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    engine.dispose()

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_explicit_cross_site(config_data):
    config_data.update(frontend_origin="http://localhost:4321", environment="test",
                       session_cross_site_enabled=True, api_public_origin="https://api.diddifree.com")
    settings = Settings.model_validate(config_data)
    assert settings.session_cross_site_enabled and settings.secure_cookies


@pytest.mark.parametrize("changes", [
    {"secure_cookies": False}, {"api_public_origin": None},
    {"api_public_origin": "http://localhost"}, {"session_cross_site_enabled": 1},
    {"session_cross_site_enabled": "yes"}, {"api_public_origin": "https://api.diddifree.com/"},
])
def test_invalid_cross_site(config_data, changes):
    config_data.update(frontend_origin="https://diddifree.com", session_cross_site_enabled=True,
                       api_public_origin="https://api.diddifree.com")
    config_data.update(changes)
    with pytest.raises(ValidationError):
        Settings.model_validate(config_data)

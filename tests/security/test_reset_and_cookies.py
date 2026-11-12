"""Password reset stays explicitly unavailable, and session cookies stay hostile to theft."""

import pytest

from app.core.config import Settings
from app.modules.identity.accounts import unavailable_reset
from app.modules.identity.browser import BrowserPolicy
from app.shared.errors import EmailUnavailable

BASE = dict(
    environment="test", database_url="postgresql+psycopg://u:p@localhost/q01_test",
    storage_endpoint="http://localhost:9000", storage_public_endpoint="https://files.test",
    storage_access_key="a", storage_secret_key="b", quarantine_bucket="quarantine",
    validated_bucket="validated", frontend_origin="https://diddifree.com",
    quota_hmac_secret="x" * 32,
)


def policy(**changes: object) -> BrowserPolicy:
    return BrowserPolicy(Settings.model_validate(BASE | changes))


def test_reset_fails_loudly_instead_of_pretending_to_send() -> None:
    with pytest.raises(EmailUnavailable) as raised:
        unavailable_reset()
    assert raised.value.status == 503
    assert raised.value.code == "EMAIL_UNAVAILABLE"


def test_secure_sessions_use_a_host_locked_cookie() -> None:
    assert policy().cookie_name == "__Host-session"


def test_insecure_local_sessions_cannot_borrow_the_host_prefix() -> None:
    # __Host- requires Secure; reusing the name without it would be rejected anyway.
    assert policy(secure_cookies=False, api_public_origin="http://localhost").cookie_name == (
        "session_local"
    )


def test_same_site_defaults_to_lax_and_only_relaxes_for_declared_cross_site() -> None:
    assert policy().same_site == "lax"
    cross = policy(session_cross_site_enabled=True, api_public_origin="https://api.diddifree.com")
    assert cross.same_site == "none"

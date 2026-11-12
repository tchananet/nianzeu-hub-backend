from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.identity.models import LoginSession
from app.modules.identity.sessions import active, check_csrf, token_digest
from app.shared.errors import AppError


def test_expiration_boundaries_and_revocation() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = LoginSession(id=uuid4(), user_id=uuid4(), token_hash="a" * 64,
                       csrf_token="b" * 43, created_at=now, last_seen_at=now,
                       expires_at=now + timedelta(days=7), revoked_at=None)
    assert active(row, now + timedelta(hours=23))
    assert not active(row, now + timedelta(hours=24))
    row.last_seen_at = now + timedelta(days=6, hours=23)
    assert not active(row, now + timedelta(days=7))
    row.revoked_at = now
    assert not active(row, now)


@pytest.mark.parametrize("token", [None, "", "a" * 42, "é" * 43, "=" * 43, "a" * 44])
def test_invalid_cookie_is_not_hashed(token: str | None) -> None:
    assert token_digest(token) is None


def test_csrf_constant_time_comparison_handles_non_ascii() -> None:
    row = LoginSession(csrf_token="b" * 43)
    check_csrf(row, "b" * 43)
    for token in [None, "", "é" * 43, "c" * 43]:
        with pytest.raises(AppError) as error:
            check_csrf(row, token)
        assert error.value.code == "CSRF_FAILED"

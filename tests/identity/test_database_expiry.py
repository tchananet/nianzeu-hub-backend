from datetime import UTC, datetime, timedelta

import pytest

from app.shared.errors import AppError

pytestmark = pytest.mark.integration


def test_idle_and_absolute_expiration(identity_db):
    service, _, data = identity_db
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    service.clock = lambda: now[0]
    service.register(data)
    login = service.login(data)
    now[0] += timedelta(hours=24)
    with pytest.raises(AppError) as error:
        service.authenticate(login.token)
    assert error.value.code == "AUTH_REQUIRED"
    login = service.login(data)
    for _ in range(7):
        now[0] += timedelta(hours=23)
        service.authenticate(login.token)
    now[0] += timedelta(hours=7)
    with pytest.raises(AppError) as error:
        service.authenticate(login.token)
    assert error.value.code == "AUTH_REQUIRED"


def test_csrf_failure_preserves_session(identity_db):
    service, _, data = identity_db
    service.register(data)
    login = service.login(data)
    with pytest.raises(AppError) as error:
        service.logout(login.token, "incorrect")
    assert error.value.code == "CSRF_FAILED"
    assert service.authenticate(login.token).user == login.identity.user

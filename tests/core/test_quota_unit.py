from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.core.quotas import consume
from app.shared.errors import DependencyUnavailable, RateLimited


def test_clock_and_refusal_after_commit():
    factory = MagicMock()
    context = factory.begin.return_value
    context.__enter__.return_value.execute.return_value.scalar_one.return_value = 6
    clock = lambda: datetime(2026, 1, 1, 0, 0, 59, 500000, tzinfo=UTC)  # noqa: E731
    with pytest.raises(RateLimited) as error:
        consume(factory, "login", "a" * 64, 5, 60, clock)
    assert error.value.retry_after == 1
    context.__exit__.assert_called_once_with(None, None, None)


def test_dependency_failure_is_not_bypassed():
    factory = MagicMock()
    factory.begin.side_effect = OperationalError("secret SQL", {}, Exception("password"))
    with pytest.raises(DependencyUnavailable) as error:
        consume(factory, "login", "a" * 64, 5, 60)
    assert "secret" not in str(error.value) and "password" not in str(error.value)


def test_invalid_clock_and_key_do_not_connect():
    factory = MagicMock()
    with pytest.raises(ValueError):
        consume(factory, "login", "a" * 64, 5, 60, lambda: datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        consume(factory, "login", "raw-email", 5, 60)
    factory.begin.assert_not_called()

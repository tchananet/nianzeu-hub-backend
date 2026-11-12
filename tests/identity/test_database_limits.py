from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.primitives import quota_key
from app.modules.identity.limits import IdentityLimits
from app.shared.errors import RateLimited

pytestmark = pytest.mark.integration


def test_email_limit_shared_between_connections(identity_db):
    _, factory, data = identity_db
    secret = uuid4().hex
    now = datetime(2026, 1, 1, tzinfo=UTC)
    limits = IdentityLimits(factory, secret, lambda: now)

    def attempt(_):
        try:
            limits.login_email(data.email)
            return True
        except RateLimited as error:
            assert error.retry_after == 900
            return False

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(12)))
        assert sum(results) == 10
    finally:
        with factory.begin() as db:
            db.execute(text("DELETE FROM rate_limit_windows WHERE key_hash = :key"),
                       {"key": quota_key(secret, data.email)})

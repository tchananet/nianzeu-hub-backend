from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.quotas import consume, purge_expired
from app.shared.errors import RateLimited
from tests.migrations.identity.helpers import NOW

pytestmark = pytest.mark.integration


def test_f01_quota_operations_on_migrated_schema(migrated):
    factory = sessionmaker(bind=migrated)
    consume(factory, "login", "a" * 64, 1, 60, lambda: NOW)
    with pytest.raises(RateLimited):
        consume(factory, "login", "a" * 64, 1, 60, lambda: NOW)
    assert migrated.execute(text("SELECT count FROM rate_limit_windows")).scalar_one() == 2
    migrated.commit()
    assert purge_expired(factory, lambda: NOW + timedelta(days=2)) == 1

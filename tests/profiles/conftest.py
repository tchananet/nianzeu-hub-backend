import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, make_url, select
from sqlalchemy.orm import sessionmaker

from app.core.primitives import utc_now
from app.modules.identity.models import User
from app.modules.profiles.models import Skill


@pytest.fixture
def profile_db():
    raw = os.environ.get("PROFILES_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BLOCKED: PROFILES_TEST_DATABASE_URL with M02 applied required")
    url = make_url(raw)
    if (url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or not (url.database or "").endswith("_test")):
        pytest.fail("BLOCKED: isolated loopback PostgreSQL _test database required")
    engine = create_engine(url, hide_parameters=True)
    factory = sessionmaker(engine, expire_on_commit=False)
    users = [uuid4(), uuid4()]
    try:
        with factory.begin() as db:
            assert db.scalar(select(Skill.id).limit(1)) is not None
            for user_id in users:
                db.add(User(id=user_id, email=f"p01-{user_id}@example.com", role="talent",
                            is_active=True, created_at=utc_now(), updated_at=utc_now()))
        yield factory, users
    finally:
        with factory.begin() as db:
            db.execute(delete(User).where(User.id.in_(users)))
        engine.dispose()

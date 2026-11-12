import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, make_url, select
from sqlalchemy.orm import sessionmaker

from app.core.primitives import utc_now
from app.modules.identity.models import User
from app.modules.profiles.models import Skill
from tests.discovery.seeds import SEEDS, seed_profiles

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture
def discovery_db():
    """Real PostgreSQL with M01..M03 already applied by the parent; never created here."""
    raw = os.environ.get("DISCOVERY_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BLOQUE: DISCOVERY_TEST_DATABASE_URL with M03 applied required",
                    pytrace=False)
    url = make_url(raw)
    if (url.drivername != "postgresql+psycopg" or url.host not in LOOPBACK
            or not (url.database or "").endswith("_test")):
        pytest.fail("BLOQUE: isolated loopback PostgreSQL _test database required", pytrace=False)
    engine = create_engine(url, hide_parameters=True)
    factory = sessionmaker(engine, expire_on_commit=False)
    users = [uuid4() for _ in SEEDS]
    try:
        with factory.begin() as db:
            assert db.scalar(select(Skill.id).limit(1)) is not None
            for user_id in users:
                db.add(User(id=user_id, email=f"r01-{user_id}@example.com", role="talent",
                            is_active=True, created_at=utc_now(), updated_at=utc_now()))
        yield factory, seed_profiles(factory, users)
    finally:
        with factory.begin() as db:
            db.execute(delete(User).where(User.id.in_(users)))
        engine.dispose()

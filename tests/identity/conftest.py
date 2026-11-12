import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, make_url, text
from sqlalchemy.orm import sessionmaker

from app.modules.identity.models import User
from app.modules.identity.passwords import Passwords
from app.modules.identity.schemas import CredentialsInput
from app.modules.identity.service import IdentityService


@pytest.fixture(scope="session")
def passwords():
    return Passwords()


@pytest.fixture
def identity_db(passwords):
    raw = os.environ.get("IDENTITY_TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BLOCKED: IDENTITY_TEST_DATABASE_URL with M01 already applied required")
    url = make_url(raw)
    if (url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or not (url.database or "").endswith("_test")):
        pytest.fail("BLOCKED: identity tests require a loopback PostgreSQL _test database")
    engine = create_engine(url, hide_parameters=True)
    factory = sessionmaker(engine, expire_on_commit=False)
    prefix = "i01-" + uuid4().hex
    try:
        with engine.connect() as connection:
            table = connection.execute(text("SELECT to_regclass('sessions')")).scalar_one()
            assert table is not None
        data = CredentialsInput(email=prefix + "@example.com",
                                password="a sufficiently long secret")
        yield IdentityService(factory, passwords), factory, data
    finally:
        with factory.begin() as db:
            db.execute(delete(User).where(User.email.like(prefix + "%")))
        engine.dispose()

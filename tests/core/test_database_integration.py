import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import make_url, text

from app.core.config import Settings
from app.core.database import build_engine, check_database, session_factory, transaction
from app.core.quotas import consume, purge_expired
from app.shared.errors import RateLimited
from tests.core.db_schema import DDL

pytestmark = pytest.mark.integration


@pytest.fixture
def db(config_data):
    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.fail("BLOQUE: TEST_DATABASE_URL local test PostgreSQL required", pytrace=False)
    url = make_url(raw)
    if url.host not in {"localhost", "127.0.0.1", "::1"} or not (url.database or "").endswith(
        "_test"
    ):
        pytest.fail("BLOQUE: only loopback database with _test suffix permitted", pytrace=False)
    config_data["database_url"] = raw
    engine = build_engine(Settings.model_validate(config_data))
    schema = "f01_" + uuid4().hex
    created = False
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            for statement in DDL.split(";"):
                if statement.strip():
                    connection.execute(text(statement))
        from sqlalchemy import event

        @event.listens_for(engine, "checkout")
        def set_schema(connection, record, proxy):
            # SET within transactions would be rolled back on pool return.
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
            connection.autocommit = False

        yield engine, session_factory(engine)
    finally:
        if created:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_transaction_commit_rollback_and_connection_reuse(db):
    engine, factory = db
    check_database(engine)
    with transaction(factory) as session:
        session.execute(text("INSERT INTO transaction_probe VALUES (1)"))
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "3s"
    with pytest.raises(RuntimeError), transaction(factory) as session:
        session.execute(text("INSERT INTO transaction_probe VALUES (2)"))
        raise RuntimeError("rollback")
    with transaction(factory) as session:
        assert session.execute(text("SELECT id FROM transaction_probe")).scalars().all() == [1]
    assert engine.pool.checkedout() == 0


def test_atomic_quota_multiple_connections_and_clock(db):
    _, factory = db
    now = datetime(2026, 1, 1, tzinfo=UTC)

    def attempt(_):
        try:
            consume(factory, "login", "a" * 64, 5, 60, lambda: now)
            return True
        except RateLimited as error:
            assert error.retry_after == 60
            return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        assert sum(executor.map(attempt, range(20))) == 5
    with transaction(factory) as session:
        assert session.execute(text("SELECT count FROM rate_limit_windows")).scalar_one() == 20
    consume(factory, "login", "a" * 64, 5, 60, lambda: now + timedelta(minutes=1))
    assert purge_expired(factory, lambda: now + timedelta(days=2)) == 2

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


@pytest.fixture
def migration_db():
    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.fail("TEST_DATABASE_URL PostgreSQL loopback _test required", pytrace=False)
    url = make_url(raw)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not (url.database or "").endswith("_test")
        or url.query
    ):
        pytest.fail("Only PostgreSQL loopback _test without URL options allowed", pytrace=False)
    engine = create_engine(
        url, poolclass=NullPool, hide_parameters=True,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=10000"},
    )
    schema = "m01_" + uuid4().hex
    created = False
    try:
        with engine.connect() as connection:
            try:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.commit()
                created = True
                connection.execute(text(f'SET search_path TO "{schema}"'))
                connection.commit()
                config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
                config.attributes.update(connection=connection, version_table_schema=schema)
                yield connection, config, schema
            finally:
                connection.rollback()
                if created:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                    connection.commit()
    finally:
        engine.dispose()


@pytest.fixture
def migrated(migration_db):
    connection, config, _ = migration_db
    command.upgrade(config, "head")
    return connection

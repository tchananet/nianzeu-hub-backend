import pytest
from alembic import command

from tests.migrations.identity.conftest import migration_db as migration_db


@pytest.fixture
def profiles_db(migration_db):
    connection, config, _ = migration_db
    command.upgrade(config, "0002_profiles")
    return connection

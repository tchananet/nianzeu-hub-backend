import pytest
from alembic import command

from tests.migrations.identity.conftest import migration_db as migration_db
from tests.migrations.profiles.helpers import profile


@pytest.fixture
def portfolio_db(migration_db):
    connection, config, _ = migration_db
    command.upgrade(config, "0003_portfolio_search")
    return connection


@pytest.fixture
def owned_profile(portfolio_db):
    return profile(portfolio_db)

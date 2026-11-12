from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.migrations.identity.helpers import child, user

TABLES = {"users", "credentials", "sessions", "password_reset_tokens", "rate_limit_windows"}
pytestmark = pytest.mark.integration


def test_single_root_revision():
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["0001_identity"]
    assert scripts.get_revision("0001_identity").down_revision is None


def test_upgrade_downgrade_upgrade(migration_db, monkeypatch):
    connection, config, schema = migration_db
    assert inspect(connection).get_table_names(schema=schema) == []
    connection.commit()
    command.upgrade(config, "head")
    assert set(inspect(connection).get_table_names(schema=schema)) == TABLES | {"alembic_version"}
    owner = user(connection)
    child(connection, "sessions", owner)
    connection.commit()
    command.upgrade(config, "head")
    assert connection.execute(text("SELECT id FROM users")).scalar_one() == owner
    assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 1
    connection.commit()
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "1")
    command.downgrade(config, "base")
    assert inspect(connection).get_table_names(schema=schema) == ["alembic_version"]
    connection.commit()
    command.upgrade(config, "head")
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
        "0001_identity"
    )
    assert set(inspect(connection).get_table_names(schema=schema)) == TABLES | {"alembic_version"}
    assert connection.execute(text("SELECT count(*) FROM users")).scalar_one() == 0
    assert connection.execute(text("SELECT count(*) FROM password_reset_tokens")).scalar_one() == 0


def test_downgrade_requires_opt_in(migration_db, monkeypatch):
    connection, config, schema = migration_db
    command.upgrade(config, "head")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DOWNGRADE", raising=False)
    with pytest.raises(RuntimeError, match="explicit opt-in"):
        command.downgrade(config, "base")
    assert set(inspect(connection).get_table_names(schema=schema)) == TABLES | {"alembic_version"}


def test_indexes_and_timestamp_types(migrated):
    inspector = inspect(migrated)
    expected = {
        "sessions": {("user_id", "created_at"), ("expires_at",)},
        "rate_limit_windows": {("expires_at",)},
    }
    for table, indexes in expected.items():
        actual = {tuple(index["column_names"]) for index in inspector.get_indexes(table)}
        assert indexes <= actual
    for table in TABLES:
        for column in inspector.get_columns(table):
            if column["name"].endswith("_at") or column["name"] == "window_start":
                assert column["type"].timezone is True
    assert inspector.get_pk_constraint("rate_limit_windows")["constrained_columns"] == [
        "scope", "key_hash", "window_start"
    ]

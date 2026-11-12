import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.migrations.identity.helpers import NOW, child, insert, user
from tests.migrations.portfolio.helpers import SEARCH_INDEXES, TABLES, validated_item
from tests.migrations.profiles.helpers import SKILL_ID, profile

pytestmark = pytest.mark.integration
REVISION = "0003_portfolio_search"


def seed_previous_revisions(connection):
    owner = user(connection)
    child(connection, "sessions", owner)
    ident = profile(connection, user_id=owner)
    insert(connection, "contact_settings", profile_id=ident,
           email="talent@example.test", email_visible=True)
    insert(connection, "profile_skills", profile_id=ident, skill_id=SKILL_ID)
    return owner, ident


def assert_previous_revisions_intact(connection, owner, ident):
    assert connection.execute(text("SELECT id FROM users")).scalar_one() == owner
    assert connection.execute(text("SELECT user_id FROM sessions")).scalar_one() == owner
    assert connection.execute(text("SELECT id FROM talent_profiles")).scalar_one() == ident
    contact = connection.execute(text("SELECT email, email_visible FROM contact_settings"))
    assert contact.one() == ("talent@example.test", True)
    assert connection.execute(text("SELECT skill_id FROM profile_skills")).scalar_one() == SKILL_ID


def test_single_head_and_linear_chain(migration_db):
    _, config, _ = migration_db
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == "0002_profiles"
    assert scripts.get_bases() == ["0001_identity"]


def test_cycle_preserves_identity_profiles_and_contacts(migration_db, monkeypatch):
    connection, config, schema = migration_db
    command.upgrade(config, "0002_profiles")
    owner, ident = seed_previous_revisions(connection)
    connection.commit()
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "1")
    for _ in range(2):
        command.upgrade(config, REVISION)
        assert TABLES <= set(inspect(connection).get_table_names(schema=schema))
        validated_item(connection, ident, state="published", published_at=NOW)
        connection.commit()
        command.downgrade(config, "0002_profiles")
        assert TABLES.isdisjoint(inspect(connection).get_table_names(schema=schema))
        assert_previous_revisions_intact(connection, owner, ident)
        for table in ("talent_profiles", "profile_skills"):
            names = {index["name"] for index in inspect(connection).get_indexes(table)}
            assert SEARCH_INDEXES[table].isdisjoint(names)
        connection.commit()
    command.upgrade(config, REVISION)
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
        REVISION
    )
    assert connection.execute(text("SELECT count(*) FROM portfolio_items")).scalar_one() == 0
    assert_previous_revisions_intact(connection, owner, ident)


def test_downgrade_requires_explicit_permission(migration_db, monkeypatch):
    connection, config, schema = migration_db
    command.upgrade(config, REVISION)
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DOWNGRADE", raising=False)
    with pytest.raises(RuntimeError, match="explicit opt-in"):
        command.downgrade(config, "0002_profiles")
    assert TABLES <= set(inspect(connection).get_table_names(schema=schema))

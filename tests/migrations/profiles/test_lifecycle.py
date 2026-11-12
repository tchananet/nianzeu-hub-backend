import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.migrations.identity.helpers import child, user
from tests.migrations.profiles.helpers import profile

pytestmark = pytest.mark.integration
TABLES = {"talent_profiles", "skills", "profile_skills", "experiences", "certifications",
          "contact_settings", "profile_views", "profile_view_dedup"}
NAMES = ["Python", "JavaScript", "TypeScript", "React", "Design graphique", "Marketing digital"]


def test_cycle_preserves_identity_and_reseeds(migration_db, monkeypatch):
    connection, config, schema = migration_db
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_revision("0002_profiles").down_revision == "0001_identity"
    assert len(scripts.get_heads()) == 1
    command.upgrade(config, "0001_identity")
    owner = user(connection)
    child(connection, "sessions", owner)
    connection.commit()
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "1")
    for _ in range(2):
        command.upgrade(config, "0002_profiles")
        assert TABLES <= set(inspect(connection).get_table_names(schema=schema))
        rows = connection.execute(text("SELECT id, name, normalized_name FROM skills ORDER BY id"))
        assert [(str(row.id), row.name, row.normalized_name) for row in rows] == [
            (f"00000000-0000-4000-8000-{i:012d}", name, name.lower())
            for i, name in enumerate(NAMES, 1)
        ]
        profile(connection, user_id=owner)
        connection.commit()
        command.downgrade(config, "0001_identity")
        assert TABLES.isdisjoint(inspect(connection).get_table_names(schema=schema))
        assert connection.execute(text("SELECT id FROM users")).scalar_one() == owner
        assert connection.execute(text("SELECT user_id FROM sessions")).scalar_one() == owner
        connection.commit()
    command.upgrade(config, "0002_profiles")
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
        "0002_profiles"
    )


def test_downgrade_requires_explicit_permission(migration_db, monkeypatch):
    connection, config, schema = migration_db
    command.upgrade(config, "0002_profiles")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DOWNGRADE", raising=False)
    with pytest.raises(RuntimeError, match="explicit opt-in"):
        command.downgrade(config, "0001_identity")
    assert TABLES <= set(inspect(connection).get_table_names(schema=schema))

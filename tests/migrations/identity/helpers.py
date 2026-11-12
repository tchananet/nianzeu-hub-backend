from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import MetaData, Table

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def insert(connection, table, **values):
    target = Table(table, MetaData(), autoload_with=connection)
    connection.execute(target.insert().values(**values))


def user(connection, **changes):
    values = dict(
        id=uuid4(), email=f"{uuid4().hex}@example.test", role="talent",
        created_at=NOW, updated_at=NOW,
    )
    values.update(changes)
    insert(connection, "users", **values)
    return values["id"]


def child(connection, table, user_id, **changes):
    values = dict(user_id=user_id)
    if table == "credentials":
        values.update(password_hash="$argon2id$test-only-fixture", updated_at=NOW)
    else:
        values.update(
            id=uuid4(), token_hash=uuid4().hex * 2,
            created_at=NOW, expires_at=NOW + timedelta(days=7),
        )
        if table == "sessions":
            values.update(csrf_token="x" * 43, last_seen_at=NOW)
    values.update(changes)
    insert(connection, table, **values)

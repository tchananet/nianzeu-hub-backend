"""Initial identity schema; independent of application models."""

import os
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    ddl = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    for statement in ddl.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    connection = op.get_bind()
    url = connection.engine.url
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    if (
        os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE") != "1"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.endswith("_test")
    ):
        raise RuntimeError("Downgrade requires explicit opt-in and loopback _test database")
    for table in (
        "rate_limit_windows", "password_reset_tokens", "sessions", "credentials", "users"
    ):
        op.drop_table(table)

"""Profiles, contacts and deterministic skills; no application imports."""

import os
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "0002_profiles"
down_revision = "0001_identity"
branch_labels = None
depends_on = None


def upgrade():
    for section in ("base", "children", "contacts_views", "seed"):
        path = Path(__file__).with_name(f"0002_profiles_{section}.sql")
        for statement in path.read_text(encoding="utf-8").split(";"):
            if statement.strip():
                op.execute(statement)


def downgrade():
    connection = op.get_bind()
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    if (
        os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE") != "1"
        or connection.engine.url.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.endswith("_test")
    ):
        raise RuntimeError("Downgrade requires explicit opt-in and loopback _test database")
    for table in (
        "profile_view_dedup", "profile_views", "contact_settings", "certifications",
        "experiences", "profile_skills", "skills", "talent_profiles",
    ):
        op.drop_table(table)
